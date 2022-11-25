from __future__ import annotations

import copy
import json
import os
from typing import Dict, List, Optional, Tuple
import math
import dill as pickle

from tools import utils
from tools.poker.card import Card
from tools.poker.engine import PokerEngine
from tools.poker.player import Player
from tools.poker.pot import Pot
from tools.poker.table import PokerTable

# logger = logging.getLogger("tools.games.short_deck.state")
InfoSetLookupTable = Dict[str, Dict[Tuple[int, ...], str]]
import tools.EHS_based_v2.EHS_based_bucket as EHS_based_bucket


def load_pickle_files(pickle_dir: str) -> Dict[str, Dict[Tuple[int, ...], str]]:
    """Load pickle files into memory."""
    file_names = [
        "preflop_hand_clusters.pkl",
        "flop_hand_clusters.pkl",
        "turn_hand_clusters.pkl",
        "river_hand_clusters.pkl",
    ]
    betting_stages = ["pre_flop", "flop", "turn", "river"]
    info_set_lut: Dict[str, Dict[Tuple[int, ...], str]] = {}
    for file_name, betting_stage in zip(file_names, betting_stages):
        file_path = os.path.join(pickle_dir, file_name)
        if not os.path.isfile(file_path):
            raise ValueError(
                f"File path not found {file_path}. Ensure pickle_dir is "
                f"set to directory containing pickle files"
            )
        with open(file_path, "rb") as fp:
            info_set_lut[betting_stage] = pickle.load(fp)
    return info_set_lut


# with open("../clustering/data/turn_lossy.pkl", "rb") as fp:
#     rrs = pickle.load(fp)
# info_set_lut = load_pickle_files("../clustering/data")
# r = np.array(list((info_set_lut['river'].keys())))
# rr0 = np.unique(r[:])
# from tools.poker.evaluation.eval_card import EvaluationCard
# for rc in rr0:
#     print(EvaluationCard.int_to_str(rc),end=' ')

def new_game(
    n_players: int, info_set_luts: InfoSetLookupTable = {}, **kwargs
) -> PokerState:
    """Create a new game of short deck poker."""
    pot = Pot()
    players = [
        Player(id=player_i, initial_chips=10000, pot=pot)
        for player_i in range(n_players)
    ]
    if info_set_luts:
        # Don't reload massive files, it takes ages.
        state = PokerState(players=players, **kwargs)
        # state = ShortDeckPokerState(players=players, load_pickle_files=False, **kwargs)
        info_set_lut = info_set_luts
    else:
        # Load massive files.
        state = PokerState(players=players, **kwargs)
    return state


class PokerState:
    """The state of a Short Deck Poker game at some given point in time.

    The class is immutable and new state can be instanciated from once an
    action is applied via the `ShortDeckPokerState.new_state` method.
    """

    def __init__(
        self,
        players: List[PokerState],
        small_blind: int = 50,
        big_blind: int = 100,
        # pickle_dir: str = "../clustering/data",
        # load_pickle_files: bool = True,
    ):
        """Initialise state."""
        n_players = len(players)
        if n_players <= 1:
            raise ValueError(
                f"At least 2 players must be provided but only {n_players} "
                f"were provided."
            )
        # if load_pickle_files:
        #     self.info_set_lut = self.load_pickle_files(pickle_dir)
        # else:
        #     self.info_set_lut = {}
        # Get a reference of the pot from the first player.
        self._table = PokerTable(
            players=players, pot=players[0].pot, include_ranks=[2,3,4,5,6,7,8,9,10, 11, 12, 13, 14]
        )
        # Get a reference of the initial number of chips for the payout.
        self._initial_n_chips = players[0].n_chips
        self.small_blind = small_blind
        self.big_blind = big_blind
        self._poker_engine = PokerEngine(
            table=self._table, small_blind=small_blind, big_blind=big_blind
        )
        # Reset the pot, assign betting order to players (might need to remove
        # this), assign blinds to the players.
        self._poker_engine.round_setup()
        # Deal private cards to players.
        self._table.dealer.deal_private_cards(self._table.players)
        for player in self._table.players:
            player.clusters.append(EHS_based_bucket.lossless([player.cards[1].card_char, player.cards[0].card_char]))
        # Store the actions as they come in here.
        self._history: List[List[str]] = [[],[],[],[]]
        self._betting_stage = "pre_flop"
        self._betting_stage_to_round: Dict[str, int] = {
            "pre_flop": 0,
            "flop": 1,
            "turn": 2,
            "river": 3,
            "show_down": 4,
        }
        self._street = ["pre_flop","flop","turn","river"]
        # Rotate the big and small blind to the final positions for the pre
        # flop round only.
        player_i_order: List[int] = [p_i for p_i in range(n_players)]
        self.players[0].is_small_blind = True
        self.players[1].is_big_blind = True
        self.players[-1].is_dealer = True
        self.clusters = []
        # self._player_i_lut: Dict[str, List[int]] = {
        #     "pre_flop": player_i_order,
        #     "flop": player_i_order,
        #     "turn": player_i_order,
        #     "river": player_i_order,
        #     "show_down": player_i_order,
        #     "terminal": player_i_order,
        # }
        # self._skip_counter = 0
        self._first_move_of_current_round = True
        self._reset_betting_round_state()
        # for player in self.players:
        #     player.is_turn = False
        # self.current_player.is_turn = True
        self.last_raise = 0
        self.has_allin = False

    def __repr__(self):
        """Return a helpful description of object in strings and debugger."""
        return f"<PokerState player_i={self.player_i} betting_stage={self._betting_stage}>"
    # @jit(nopython=True)
    def apply_action(self, action_str: Optional[str]) -> PokerState:
        """Create a new state after applying an action.

        Parameters
        ----------
        action_str : str or None
            The description of the action the current player is making. Can be
            any of {"fold, "call", "raise"}, the latter two only being possible
            if the agent hasn't folded already.

        Returns
        -------
        new_state : ShortDeckPokerState
            A poker state instance that represents the game in the next
            timestep, after the action has been applied.
        """
        if action_str not in self.legal_actions:
            raise Exception('the action is invalid')
            # raise ValueError(
            #     f"Action '{action_str}' not in legal actions: " f"{self.legal_actions}"
            # )
        # Deep copy the parts of state that are needed that must be immutable
        # from state to state.
        # lut = self.info_set_lut
        # self.info_set_lut = {}
        new_state = copy.deepcopy(self)
        # new_state.info_set_lut = self.info_set_lut = lut
        # An action has been made, so alas we are not in the first move of the
        # current betting round.
        new_state._history[new_state._betting_stage_to_round[new_state.betting_stage]].append(str(action_str[-1]))
        if action_str is None:
            # Assert active player has folded already.
            assert (
                not new_state.current_player.is_active
            ), "Active player cannot do nothing!"
        elif action_str == "call":
            new_state.current_player.call(players=new_state.players)
            # if new_state._first_move_of_current_round == False:
            #     new_state._increment_stage()
            # logger.debug("calling")
        elif action_str == "fold":
            new_state.current_player.active = False
            new_state._betting_stage = "terminal"
        elif action_str.__contains__('big'):
            if action_str == "bigone":
                bet_n_chips = new_state.big_blind
            elif action_str == "bigfour":
                bet_n_chips = new_state.big_blind * 4
            elif action_str == "bigtwenty":
                bet_n_chips = new_state.big_blind * 20
            biggest_bet = max(p.n_bet_chips for p in new_state.players)
            n_chips_to_call = biggest_bet - new_state.current_player.n_bet_chips
            raise_n_chips = bet_n_chips + n_chips_to_call
            new_state.last_raise = bet_n_chips
            # logger.debug(f"betting {raise_n_chips} n chips")
            action = new_state.current_player.raise_to(n_chips=raise_n_chips)
            new_state._n_raises += 1
        elif action_str == "raiseh":
            pot = new_state._table.players[self.player_i].pot.total
            biggest_bet = max(p.n_bet_chips for p in new_state.players)
            n_chips_to_call = biggest_bet - new_state.current_player.n_bet_chips
            halfpot = math.ceil(pot / 200) * 100
            raise_n_chips = halfpot + n_chips_to_call
            new_state.last_raise = halfpot
            # logger.debug(f"betting {raise_n_chips} n chips")
            action = new_state.current_player.raise_to(n_chips=raise_n_chips)
            new_state._n_raises += 1
        elif action_str == "raiseo":
            pot = new_state._table.players[self.player_i].pot.total
            biggest_bet = max(p.n_bet_chips for p in new_state.players)
            n_chips_to_call = biggest_bet - new_state.current_player.n_bet_chips
            raise_n_chips = pot + n_chips_to_call
            new_state.last_raise = pot
            # logger.debug(f"betting {raise_n_chips} n chips")
            action = new_state.current_player.raise_to(n_chips=raise_n_chips)
            new_state._n_raises += 1
        elif action_str == 'allin':
            raise_n_chips = new_state.current_player.n_bet_chips + new_state.current_player.n_chips
            new_state.last_raise = 0
            # logger.debug(f"betting {raise_n_chips} n chips")
            action = new_state.current_player.raise_to(n_chips=raise_n_chips)
            new_state.has_allin = True
        else:
            raise Exception('the action is not define')
        # Update the new state.
        # skip_actions = ["skip" for _ in range(new_state._skip_counter)]
        # new_state._history[new_state.betting_stage] += skip_actions
        # new_state._n_actions += 1
        # new_state._skip_counter = 0
        # Player has made move, increment the player that is next.
        new_state._move_to_next_player()
        if new_state._betting_stage == "terminal":
            #had one person fold, ending game
            new_state._poker_engine.compute_payout()
        elif action_str == "call" and new_state._first_move_of_current_round == False:
            #second person call,next street
            if new_state.has_allin:
                # allin increment stage to last street
                while new_state._betting_stage != "show_down":
                    new_state._increment_stage()
            else:
                new_state._increment_stage()
                new_state._reset_betting_round_state()
                new_state._first_move_of_current_round = True
            if new_state._betting_stage == "show_down":
                new_state._poker_engine.compute_winner()
            return new_state
        new_state._first_move_of_current_round = False
        return new_state

    def _move_to_next_player(self):
        """Ensure state points to next valid active player."""
        self._player_i_index ^= 1
        # if self._player_i_index >= len(self.players):
        #     self._player_i_index = 0

    def _reset_betting_round_state(self):
        """Reset the state related to counting types of actions."""
        self._all_players_have_made_action = False
        # self._n_actions = 0
        self._n_raises = 0
        self._player_i_index = 0
        # self._n_players_started_round = self._poker_engine.n_active_players
        # while not self.current_player.is_active:
        #     self._skip_counter += 1
        #     self._player_i_index += 1

    def _increment_stage(self):
        self._first_move_of_current_round = True
        """Once betting has finished, increment the stage of the poker game."""
        # Progress the stage of the game.
        if self._betting_stage == "pre_flop":
            # Progress from private cards to the flop.
            self._betting_stage = "flop"
            self._poker_engine.table.dealer.deal_flop(self._table)
            co_cards = [card.card_char for card in self._table.community_cards[:3]]
            for player in self._table.players:
                player.clusters.append(
                    EHS_based_bucket.lossy_single(co_cards, [player.cards[1].card_char, player.cards[0].card_char]))
        elif self._betting_stage == "flop":
            # Progress from flop to turn.
            self._betting_stage = "turn"
            self._poker_engine.table.dealer.deal_turn(self._table)
            co_cards = [card.card_char for card in self._table.community_cards[:4]]
            for player in self._table.players:
                player.clusters.append(
                    EHS_based_bucket.lossy_single(co_cards, [player.cards[1].card_char, player.cards[0].card_char]))
        elif self._betting_stage == "turn":
            # Progress from turn to river.
            self._betting_stage = "river"
            self._poker_engine.table.dealer.deal_river(self._table)
            co_cards = [card.card_char for card in self._table.community_cards[:5]]
            for player in self._table.players:
                player.clusters.append(
                    EHS_based_bucket.lossy_single(co_cards, [player.cards[1].card_char, player.cards[0].card_char]))
        elif self._betting_stage == "river":
            # Progress to the showdown.
            self._betting_stage = "show_down"
        elif self._betting_stage in {"show_down", "terminal"}:
            pass
        else:
            raise ValueError(f"Unknown betting_stage: {self._betting_stage}")

    @property
    def player_i(self) -> int:
        """Get the index of the players turn it is."""
        return self._player_i_index

    @property
    def community_cards(self) -> List[Card]:
        """Return all shared/public cards."""
        return self._table.community_cards

    @property
    def private_hands(self) -> Dict[Player, List[Card]]:
        """Return all private hands."""
        return {p: p.cards for p in self.players}

    @property
    def initial_regret(self) -> Dict[str, float]:
        """Returns the default regret for this state."""
        return {action: 0 for action in self.legal_actions}

    @property
    def initial_strategy(self) -> Dict[str, float]:
        """Returns the default strategy for this state."""
        return {action: 0 for action in self.legal_actions}

    @property
    def betting_stage(self) -> str:
        """Return betting stage."""
        return self._betting_stage

    # @property
    # def all_players_have_actioned(self) -> bool:
    #     """Return whether all players have made atleast one action."""
    #     return self._n_actions >= self._n_players_started_round
    #
    # @property
    # def n_players_started_round(self) -> bool:
    #     """Return n_players that started the round."""
    #     return self._n_players_started_round

    # @property
    # def player_i(self) -> int:
    #     """Get the index of the players turn it is."""
    #     return self._player_i_lut[self._betting_stage][self._player_i_index]

    # @player_i.setter
    # def player_i(self, _: Any):
    #     """Raise an error if player_i is set."""
    #     raise ValueError(f"The player_i property should not be set.")

    @property
    def betting_round(self) -> int:
        """Algorithm 1 of tools supp. material references betting_round."""
        try:
            betting_round = self._betting_stage_to_round[self._betting_stage]
        except KeyError:
            raise ValueError(
                f"Attemped to get betting round for stage "
                f"{self._betting_stage} but was not supported in the lut with "
                f"keys: {list(self._betting_stage_to_round.keys())}"
            )
        return betting_round

    @property
    def info_set(self) -> str:
        """Get the information set for the current player."""
        # cards = sorted(
        #     self.current_player.cards,
        #     key=operator.attrgetter("eval_card"),
        #     reverse=True,
        # )
        # cards_cluster = [EHS_based_bucket.lossless([cards[1].card_char, cards[0].card_char])]
        # # eval_cards = (cards[1].eval_card << 58) + (cards[0].eval_card << 52)
        # # eval_cards = tuple([card.eval_card for card in cards])
        # try:
        #     # cards_cluster = [info_set_lut["pre_flop"][eval_cards]]
        #     street = self._betting_stage_to_round[self._betting_stage]
        #     if street >= 1:
        #         # ecd = eval_cards
        #         co_cards = [card.card_char for card in self._table.community_cards[:3]]
        #         # cards_cluster.append(info_set_lut["flop"][ecd])
        #         cards_cluster.append(EHS_based_bucket.lossy(co_cards,[cards[1].card_char, cards[0].card_char]))
        #     if street >= 2:
        #         # ecd = eval_cards
        #         # for card in self._table.community_cards[:4]:
        #         #     ecd += 1 << card.eval_card
        #         # cards_cluster.append(info_set_lut["turn"][ecd])
        #         co_cards = [card.card_char for card in self._table.community_cards[:4]]
        #         cards_cluster.append(EHS_based_bucket.lossy(co_cards, [cards[1].card_char, cards[0].card_char]))
        #     if street >= 3:
        #         # ecd = eval_cards
        #         # for card in self._table.community_cards[:5]:
        #         #     ecd += 1 << card.eval_card
        #         # cards_cluster.append(info_set_lut["river"][ecd])
        #         co_cards = [card.card_char for card in self._table.community_cards[:5]]
        #         cards_cluster.append(EHS_based_bucket.lossy(co_cards, [cards[1].card_char, cards[0].card_char]))
        # except KeyError:
        #     print('++++++++',cards[1].eval_card,cards[0].eval_card)
        #     print('community_cards',self._table.community_cards)
        #     print(self._betting_stage,[cards[1].card_char, cards[0].card_char])
        #     raise Exception("default info set, please ensure you load it correctly888")
            # return "default info set, please ensure you load it correctly"
        # Convert history from a dict of lists to a list of dicts as I'm
        # paranoid about JSON's lack of care with insertion order.
        cards_cluster = self.current_player.clusters
        try:
            info_set_dict = [
                [[cards_cluster[actionsi]]+[str(action) for action in self._history[actionsi]]]
                for actionsi in range(len(cards_cluster))
            ]
            return json.dumps(
                info_set_dict, separators=(",", ":"), cls=utils.io.NumpyJSONEncoder
            )
        except Exception:
            print('cards_cluster', cards_cluster,"_history",self._history)
            raise Exception("_history is error")

    @property
    def payout(self) -> Dict[int, int]:
        """Return player index to payout number of chips dictionary."""
        n_chips_delta = dict()
        for player_i, player in enumerate(self.players):
            n_chips_delta[player_i] = player.n_chips - self._initial_n_chips
        return n_chips_delta

    @property
    def is_terminal(self) -> bool:
        """Returns whether this state is terminal or not.

        The state is terminal once all rounds of betting are complete and we
        are at the show down stage of the game or if all players have folded.
        """
        return self._betting_stage in {"show_down", "terminal"}

    @property
    def players(self) -> List[Player]:
        """Returns players in table."""
        return self._table.players

    @property
    def current_player(self) -> Player:
        """Returns a reference to player that makes a move for this state."""
        return self._table.players[self._player_i_index]

    @property
    def legal_actions(self) -> List[Optional[str]]:
        """Return the actions that are legal for this game state."""
        chips = self._table.players[self.player_i].n_chips
        pot = self._table.players[self.player_i].pot.total
        biggest_bet = max(p.n_bet_chips for p in self.players)
        n_chips_to_call = biggest_bet - self.current_player.n_bet_chips
        halfpot = math.ceil(pot / 200) * 100
        onepot = math.ceil(pot / 100) * 100
        actions: List[Optional[str]] = []
        if self.current_player.active:
            if n_chips_to_call != 0:
                actions += ["fold"]
            actions += ["call"]
            if self.has_allin == False:
                if self._betting_stage == 'pre_flop':
                    if self._n_raises < 1:
                        actions += ['bigone']
                    if self.last_raise <= 4 * self.big_blind:
                        actions += ['bigfour']
                    if self.last_raise <= 20 * self.big_blind and n_chips_to_call + 2000 < chips:
                        actions += ['bigtwenty']
                elif self._betting_stage == 'flop' and self.last_raise <= halfpot and chips > n_chips_to_call + halfpot and self._n_raises < 4:
                    # In limit hold'em we can only bet/raise if there have been
                    # less than three raises in this round of betting, or if there
                    # are two players playing.
                    actions += ["raiseh","raiseo"]
                elif self._n_raises < 1 and self.last_raise <= halfpot and chips > n_chips_to_call + halfpot:
                    actions += ["raiseh","raiseo"]
                elif self.last_raise <= onepot and chips > n_chips_to_call + onepot:
                    actions += ["raiseo"]
                if chips > 0:
                    actions += ['allin']
        else:
            actions += [None]
        return actions
