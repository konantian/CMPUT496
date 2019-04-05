#!/usr/bin/env python
#/usr/local/bin/python3
# Set the path to your python3 above

from gtp_connection import GtpConnection,move_to_coord,coord_to_point,point_to_coord,format_point
from board_util import GoBoardUtil, EMPTY
from simple_board import SimpleGoBoard

import random
import numpy as np

def undo(board,move):

    if isinstance(move,str):
        coord = move_to_coord(move,board.size)
        point = coord_to_point(coord[0],coord[1],board.size)
        board.board[point]=EMPTY
        board.current_player=GoBoardUtil.opponent(board.current_player)
    else:
        board.board[move]=EMPTY
        board.current_player=GoBoardUtil.opponent(board.current_player)

def play_move(board, move, color):
    #print(type(move))
    if isinstance(move,str):
        coord = move_to_coord(move,board.size)
        point = coord_to_point(coord[0],coord[1],board.size)
        board.play_move_gomoku(point, color)
    else:
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

class GomokuSimulationPlayer(object):
    """
    For each move do `n_simualtions_per_move` playouts,
    then select the one with best win-rate.
    playout could be either random or rule_based (i.e., uses pre-defined patterns) 
    """
    def __init__(self, n_simualtions_per_move=10, playout_policy='rule_based', board_size=7):
        assert(playout_policy in ['random', 'rule_based'])
        self.n_simualtions_per_move=n_simualtions_per_move
        self.board_size=board_size
        self.playout_policy=playout_policy

        #NOTE: pattern has preference, later pattern is ignored if an earlier pattern is found
        self.pattern_list=['Win', 'BlockWin', 'OpenFour', 'BlockOpenFour', 'Random']

        self.name="Gomoku3"
        self.version = 3.0
        self.best_move=None

    
    def set_playout_policy(self, playout_policy='random'):
        assert(playout_policy in ['random', 'rule_based'])
        self.playout_policy=playout_policy

    def _random_moves(self, board, color_to_play):
        return GoBoardUtil.generate_legal_moves_gomoku(board)
    
    def policy_moves(self, board, color_to_play):
        if(self.playout_policy=='random'):
            return "Random", self._random_moves(board, color_to_play)
        else:
            assert(self.playout_policy=='rule_based')
            assert(isinstance(board, SimpleGoBoard))
            ret=board.get_pattern_moves()
            if ret is None:
                return "Random", self._random_moves(board, color_to_play)
            movetype_id, moves=ret
            return self.pattern_list[movetype_id], moves


    def legalMoves(self,board):
        moves = GoBoardUtil.generate_legal_moves_gomoku(board)
        gtp_moves = []
        for move in moves:
            coords = point_to_coord(move, board.size)
            gtp_moves.append(format_point(coords))

        return gtp_moves

    def my_policy_moves(self,board,color):

        points = GoBoardUtil.generate_legal_moves_gomoku(board)
        moves = self.legalMoves(board)
        self.move_to_point=dict(zip(moves,points))
        self.point_to_move=dict(zip(points,moves))

        empty_moves = self.legalMoves(board)
        win_moves = []
        block_win_moves = []
        open_four_moves = []
        block_open_four_moves = []
        open_three_moves = []
        steps = [1,board.NS,board.NS-1,board.NS+1]
        for move in empty_moves:
            for step in steps:
                point = self.move_to_point[move]
                if board.five_in_row(point,board.current_player,step):
                    win_moves.append(move)
                elif board.five_in_row(point,GoBoardUtil.opponent(board.current_player),step):
                    block_win_moves.append(move)
                elif board.OpenFour(point,board.current_player,step):
                    open_four_moves.append(move)
                elif board.BlockOpenFour(point,GoBoardUtil.opponent(board.current_player),step):
                    block_open_four_moves.append(move)

        move_types=["Win ","BlockWin ","OpenFour ","BlockOpenFour ","Random "]
        moves=[win_moves,block_win_moves,open_four_moves,block_open_four_moves,empty_moves]
        for i in range(len(move_types)):
            if moves[i]:
                return move_types,moves[i]
    
    def _do_playout(self, board, color_to_play):
        res=game_result(board)
        simulation_moves=[]
        while(res is None):
            _ , candidate_moves = self.my_policy_moves(board, board.current_player)
            #print(candidate_moves)
            playout_move=random.choice(candidate_moves)
            play_move(board, playout_move, board.current_player)
            simulation_moves.append(playout_move)
            res=game_result(board)
        for m in simulation_moves[::-1]:
            undo(board, m)
        if res == color_to_play:
            return 1.0
        elif res == 'draw':
            return 0.0
        else:
            assert(res == GoBoardUtil.opponent(color_to_play))
            return -1.0

    def get_move(self, board, color_to_play):
        """
        The genmove function called by gtp_connection
        """
        moves=GoBoardUtil.generate_legal_moves_gomoku(board)
        #moves = pending_moves
        toplay=board.current_player
        best_result, best_move=-1.1, None
        best_move=moves[0]
        wins = np.zeros(len(moves))
        visits = np.zeros(len(moves))
        while True:
            for i, move in enumerate(moves):
                play_move(board, move, toplay)
                res=game_result(board)
                if res == toplay:
                    undo(board, move)
                    #This move is a immediate win
                    self.best_move=move
                    return move
                ret=self._do_playout(board, toplay)
                wins[i] += ret
                visits[i] += 1
                win_rate = wins[i] / visits[i]
                if win_rate > best_result:
                    best_result=win_rate
                    best_move=move
                    self.best_move=best_move
                undo(board, move)
        assert(best_move is not None)
        return best_move

def run():
    """
    start the gtp connection and wait for commands.
    """
    board = SimpleGoBoard(7)
    con = GtpConnection(GomokuSimulationPlayer(), board)
    con.start_connection()

if __name__=='__main__':
    run()
