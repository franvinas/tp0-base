from threading import Lock

import common.utils as utils


class BetsVault:
    def __init__(self):
        self.__lock = Lock()

    def store_bets(self, bets):
        with self.__lock:
            utils.store_bets(bets)

    def draw_winners(self):
        with self.__lock:
            return utils.draw_winners()
