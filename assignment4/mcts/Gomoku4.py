#!/usr/bin/env python
#/usr/local/bin/python3
# Set the path to your python3 above

from gtp_connection import GtpConnection
from board_util import GoBoardUtil, EMPTY
from simple_board import SimpleGoBoard

import random
import numpy as np

from mcts import MCTS

class GomokuSimulationPlayer(object):
    """
    For each move do `n_simualtions_per_move` playouts,
    then select the one with best win-rate.
    playout could be either random or rule_based (i.e., uses pre-defined patterns) 
    """
    def __init__(self, n_simualtions_per_move=100, playout_policy='random', board_size=7, exploration=0.4):
        assert(playout_policy in ['random', 'rule_based'])
        self.n_simualtions_per_move=n_simualtions_per_move
        self.board_size=board_size
        self.playout_policy=playout_policy

        #NOTE: pattern has preference, later pattern is ignored if an earlier pattern is found
        self.pattern_list=['Win', 'BlockWin', 'OpenFour', 'BlockOpenFour', 'Random']

        self.name="Gomoku4"
        self.version = 4.0
        self.best_move=None

        self.parent = None
        self.MCTS = MCTS()
        self.exploration = exploration

    def reset(self):
        self.MCTS = MCTS()

    def update(self, move):
        self.parent = self.MCTS._root 
        self.MCTS.update_with_move(move)
    
    def set_playout_policy(self, playout_policy='random'):
        assert(playout_policy in ['random', 'rule_based'])
        self.playout_policy=playout_policy

    def get_move(self, board, color_to_play):
        move = self.MCTS.get_move(board,
                color_to_play,
                num_simulation = self.n_simualtions_per_move,
                exploration = self.exploration, 
                playout_policy = self.playout_policy)
        self.update(move)
        return move

def run():
    """
    start the gtp connection and wait for commands.
    """
    board = SimpleGoBoard(7)
    con = GtpConnection(GomokuSimulationPlayer(), board)
    con.start_connection()

if __name__=='__main__':
    run()
