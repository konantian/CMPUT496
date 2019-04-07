#!/usr/bin/env python
#/usr/local/bin/python3
# Set the path to your python3 above

from gtp_connection import GtpConnection
from board_util import GoBoardUtil, EMPTY
from simple_board import SimpleGoBoard
from mcts import MCTS

import random
import numpy as np

def undo(board,move):
    board.board[move]=EMPTY
    board.current_player=GoBoardUtil.opponent(board.current_player)

def play_move(board, move, color):
    board.play_move_gomoku(move, color)

def game_result(board):
    game_end, winner = board.check_game_end_gomoku()
    moves = board.get_empty_points()
    board_full = (len(moves) == 0)
    if game_end:
        #return 1 if winner == board.current_player else -1
        return winner
    if board_full:
        return 'draw'
    return None

class Gomoku4(object):
    """
    For each move do `n_simualtions_per_move` playouts,
    then select the one with best win-rate.
    playout could be either random or rule_based (i.e., uses pre-defined patterns) 
    """
    def __init__(self, n_simualtions_per_move=10000, board_size=7, exploration=0.4):
        self.n_simualtions_per_move=n_simualtions_per_move
        self.board_size=board_size
        self.exploration = exploration
        self.parent = None

        self.name="Gomoku4"
        self.version = 4.0
        self.best_move=None

        self.MCTS = MCTS()

    def reset(self):
        self.MCTS = MCTS()

    def update(self, move):
        self.parent = self.MCTS._root 
        self.MCTS.update_with_move(move)

    def get_move(self, board, color_to_play):
        """
        The genmove function called by gtp_connection
        """
        move = self.MCTS.get_move(board, color_to_play, self.n_simualtions_per_move, self.exploration)
        self.update(move)
        return move

def run():
    """
    start the gtp connection and wait for commands.
    """
    board = SimpleGoBoard(7)
    con = GtpConnection(Gomoku4(), board)
    con.start_connection()

if __name__=='__main__':
    run()
