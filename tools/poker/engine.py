from typing import TYPE_CHECKING
import pickle

if TYPE_CHECKING:
    pass
from tools.poker.table import PokerTable

import os
curPath = os.path.abspath(os.path.dirname(__file__))
with open(curPath+"/five_card_rank.pkl", "rb") as fb:
    five_card_rank = pickle.load(fb)

class PokerEngine:
    def __init__(self, table: PokerTable, small_blind: int, big_blind: int):
        """"""
        self.table = table
        self.small_blind = small_blind
        self.big_blind = big_blind

    def round_setup(self):
        """Code that must be done to setup the round before the game starts."""
        self.table.reset()
        self._assign_blinds()

    def compute_payout(self):
        for player in self.table.players:
            if player.active:
                player.add_chips(self.table.pot.total)
        self.table.pot.reset()

    def Maxstrength(self,cards):
        if len(cards) != 7:
            raise Exception('need seven cards')
        strength = 100000
        for k in range(len(cards)):
            for j in range(k + 1, len(cards)):
                cnt = 0
                for i in range(len(cards)):
                    if i != k and i != j:
                        cnt += 1 << cards[i].eval_card
                v = five_card_rank[cnt]
                if strength > v:
                    strength = v
        return strength


    def compute_winner(self):
        community_cards  = self.table.community_cards
        strength1 = self.Maxstrength(self.table.players[0].cards + community_cards)
        strength2 = self.Maxstrength(self.table.players[1].cards + community_cards)
        if strength1 < strength2:
            self.table.players[0].add_chips(self.table.pot.total)
        elif strength1 > strength2:
            self.table.players[1].add_chips(self.table.pot.total)
        else:
            self.table.players[0].n_chips = self.table.players[0].initial_chips
            self.table.players[1].n_chips = self.table.players[0].initial_chips
        self.table.pot.reset()

    def _assign_blinds(self):
        """Assign the blinds to the players."""
        self.table.players[0].add_to_pot(self.small_blind)
        self.table.players[1].add_to_pot(self.big_blind)

