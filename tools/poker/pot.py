from __future__ import annotations

import collections
import uuid

from tools.poker.player import Player
# from numba import jitclass,int32, deferred_type, boolean,int16,types

class Pot:
    """"""

    def __init__(self):
        """"""
        self._pot = collections.Counter()
        self._uid = str(uuid.uuid4().hex)

    def __repr__(self):
        """Nicer way to print a Pot object."""
        return f"<Pot n_chips={self.total}>"

    def __getitem__(self, player: Player):
        """Get a players contribution to the pot."""
        if not isinstance(player, Player):
            raise ValueError(
                f'Index the pot with the player to get the contribution.')
        return self._pot[player]

    def add_chips(self, player: Player, n_chips: int):
        """Add chips to the pot, from a player for a given round."""
        self._pot[player] += n_chips

    def reset(self):
        """Reset the pot."""
        self._pot = collections.Counter()

    @property
    def uid(self):
        """Get a unique identifier for this pot."""
        return self._uid

    @property
    def total(self):
        """Return the total in the pot from all players."""
        return sum(self._pot.values())
