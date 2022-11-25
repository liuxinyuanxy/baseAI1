from __future__ import annotations

import uuid
from typing import List, TYPE_CHECKING


if TYPE_CHECKING:
    from tools.poker.card import Card
    from tools.poker.pot import Pot


# logger = logging.getLogger(__name__)

# from numba import jitclass
# from numba import int32, float32, deferred_type, boolean
# my_inst_type = deferred_type()
# my_inst_type.define(Pot.class_type.instance_type)
# spec = [
#     ('initial_chips', int32),               # a simple scalar field
#     ('name', float32[:]),          # an array field
#     ('pot',my_inst_type),
#     ('is_big_blind',my_inst_type),
#     ('is_dealer',my_inst_type),
#     ('active',my_inst_type),
# ]
#
# @jitclass(spec)
class Player:
    """Abstract base class for all poker-playing agents.

    All agents should inherit from this class and implement the take_action
    method.

    A poker player has a name, holds chips to bet with, and has private cards
    to play with. The n_chips of contributions to the pot for a given hand of
    poker are stored cumulative, as the total pot to cash out is just the sum
    of all players' contributions.
    """

    def __init__(self, id: int, initial_chips: int, pot: Pot):
        """Instanciate a player."""
        self.initial_chips = initial_chips
        self.n_chips: int = initial_chips
        self.cards: List[Card] = []
        self.id = id
        self.pot = pot
        self.is_small_blind = False
        self.is_big_blind = False
        self.is_dealer = False
        self.active = True
        self.clusters = []

    def reset(self):
        self.n_chips: int = self.initial_chips
        self.cards: List[Card] = []
        self.active = True

    def __repr__(self):
        """"""
        return '<Player name="{}" n_chips={:05d} n_bet_chips={:05d} >'.format(
                self.name,
                self.n_chips,
                self.n_bet_chips)

    def add_chips(self, chips: int):
        """Add chips."""
        self.n_chips += chips

    def call(self, players: List[Player]):
        """Call the highest bet among all active players."""
        biggest_bet = max(p.n_bet_chips for p in players)
        n_chips_to_call = biggest_bet - self.n_bet_chips
        self.add_to_pot(n_chips_to_call)

    def raise_to(self, n_chips: int):
        """Raise your bet to a certain n_chips."""
        self.add_to_pot(n_chips)

    def _try_to_make_full_bet(self, n_chips: int):
        """Ensures no bet is greater than the n_chips of chips left."""
        if self.n_chips - n_chips < 0:
            # We can't bet more than we have.
            n_chips = self.n_chips
        return n_chips

    def add_to_pot(self, n_chips: int):
        """Add to the n_chips put into the pot by this player."""
        if n_chips < 0:
            raise ValueError(f'Can not subtract chips from pot.')
        # TODO(fedden): This code is called by engine.py for the small and big
        #               blind. What if the player can't actually add the blind?
        #               What do the rules stipulate in these circumstances.
        #               Ensure that this is sorted.
        # n_chips = self._try_to_make_full_bet(n_chips)
        self.pot.add_chips(self, n_chips)
        self.n_chips -= n_chips


    def add_private_card(self, card: Card):
        """Add a private card to this player."""
        self.cards.append(card)

    @property
    def n_bet_chips(self) -> int:
        """Returns the n_chips this player has bet so far."""
        return self.pot[self]
