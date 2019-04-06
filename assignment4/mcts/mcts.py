#!/usr/bin/python3
"""
This function is loosely based on https://github.com/Rochester-NRT/RocAlphaGo/blob/develop/AlphaGo/mcts.py
"""
import os, sys
import numpy as np
import random
from board_util import GoBoardUtil, EMPTY, BLACK, WHITE
from simple_board import SimpleGoBoard
from gtp_connection import point_to_coord, format_point

import time

def uct_val(node, child, exploration, max_flag): 
    if child._n_visits == 0:
        return float("inf")
    if max_flag:
        return float(child._n_wins)/child._n_visits + exploration*np.sqrt(np.log(node._n_visits)/child._n_visits)
    else:
        return float(child._n_visits - child._n_wins)/child._n_visits + exploration*np.sqrt(np.log(node._n_visits)/child._n_visits)

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

class TreeNode(object):
    """
    A node in the MCTS tree.
    """
    version = 0.22
    name = "MCTS Player"
    def __init__(self, parent):
        """
        parent is set when a node gets expanded
        """
        self._parent = parent
        self._children = {}  # a map from move to TreeNode
        self._n_visits = 0
        self._n_wins = 0
        self._expanded = False
        self._move = None

    def expand(self, board, color):
        """
        Expands tree by creating new children.
        """
        moves = GoBoardUtil.generate_legal_moves_gomoku(board)
        for move in moves:
            if move not in self._children:
                self._children[move] = TreeNode(self)
                self._children[move]._move = move
        self._expanded = True

    def select(self, exploration, max_flag):
        """
        Select move among children that gives maximizes UCT. 
        If number of visits are zero for a node, value for that node is infinite, so definitely will get selected

        It uses: argmax(child_num_n_wins/child_num_vists + C * sqrt(2 * ln * Parent_num_vists/child_num_visits) )
        Returns:
        A tuple of (move, next_node)
        """
        return max(self._children.items(), key=lambda items:uct_val(self, items[1], exploration, max_flag))
        
    def update(self, leaf_value):
        """
        Update node values from leaf evaluation.
        Arguments:
        leaf_value -- the value of subtree evaluation from the current player's perspective.
        
        Returns:
        None
        """
        self._n_wins += leaf_value
        self._n_visits += 1

    def update_recursive(self, leaf_value):
        """
        Like a call to update(), but applied recursively for all ancestors.

        Note: it is important that this happens from the root downward so that 'parent' visit
        counts are correct.
        """
        # If it is not root, this node's parent should be updated first.
        if self._parent:
            self._parent.update_recursive(leaf_value)
        self.update(leaf_value)

    def is_leaf(self):
        """
        Check if leaf node (i.e. no nodes below this have been expanded).
        """
        return self._children == {}

    def is_root(self):
        return self._parent is None


class MCTS(object):
    def __init__(self):
        self._root = TreeNode(None)
        self.toplay = self.int_to_color(BLACK)
        self.pattern_list=['Win', 'BlockWin', 'OpenFour', 'BlockOpenFour', 'Random']

    def _playout(self, board, color):
        """
        Run a single playout from the root to the given depth, getting a value at the leaf and
        propagating it back through its parents. State is modified in-place, so a copy must be
        provided.

        Arguments:
        board -- a copy of the board.
        color -- color to play
        

        Returns:
        None
        """
        node = self._root 
        # This will be True olny once for the root
        if not node._expanded:
            node.expand(board, color)
        while not node.is_leaf():
            # Greedily select next move.                
            max_flag = color == self.toplay
            move, next_node = node.select(self.exploration,max_flag)
            board.play_move_gomoku(move, color)
            color = GoBoardUtil.opponent(color) 
            node = next_node
        assert node.is_leaf()
        if not node._expanded:
            node.expand(board, color)

        assert board.current_player == color
        leaf_value = self._evaluate_rollout(board)  
        # Update value and visit count of nodes in this traversal.
        node.update_recursive(leaf_value)

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

    def _evaluate_rollout(self, board):
        """
        Use the rollout policy to play until the end of the game, returning +1 if the current
        player wins, -1 if the opponent wins, and 0 if it is a tie.
        """

        res=game_result(board)
        simulation_moves=[]
        while(res is None):
            _ , candidate_moves = self.policy_moves(board, board.current_player)
            playout_move=random.choice(candidate_moves)
            play_move(board, playout_move, board.current_player)
            simulation_moves.append(playout_move)
            res=game_result(board)
        for m in simulation_moves[::-1]:
            undo(board, m)
        if res == self.toplay:
            return 1.0
        else:
            return 0.0

    def get_move(self,
            board,
            color_to_play,
            num_simulation,
            exploration = 0.4, 
            playout_policy = 'random'):
        """
        Runs all playouts sequentially and returns the most visited move.
        """

        start = time.time()

        if self.toplay != color_to_play:
            sys.stderr.write("Dumping the subtree! \n")
            sys.stderr.flush()
            self._root = TreeNode(None)
        self.toplay = color_to_play
        self.exploration = exploration
        self.playout_policy = playout_policy
        #for n in range(num_simulation):
        while True:
            board_copy = board.copy()
            self._playout(board_copy, color_to_play)

            if (time.time() - start > 58.0):
                break
        # choose a move that has the most visit 
        moves_ls =  [(move, node._n_visits) for move, node in self._root._children.items()]
        if not moves_ls:
            return None
        moves_ls = sorted(moves_ls,key=lambda i:i[1],reverse=True)
        move = moves_ls[0]
        #self.print_stat(board, self._root, color_to_play)
        #self.good_print(board,self._root,self.toplay,10)
        #assert board.is_legal(move[0], color_to_play)
        return move[0]
        
    def update_with_move(self, last_move):
        """
        Step forward in the tree, keeping everything we already know about the subtree, assuming
        that get_move() has been called already. Siblings of the new root will be garbage-collected.
        """
        if last_move in self._root._children:
            self._root = self._root._children[last_move]
        else:
            self._root = TreeNode(None)
        self._root._parent = None
        self.toplay = GoBoardUtil.opponent(self.toplay)

    def int_to_color(self, i):
        """convert number representing player color to the appropriate character """
        int_to_color = {BLACK:"b", WHITE:"w"}
        try:
           return int_to_color[i] 
        except:
            raise ValueError("Provided integer value for color is invalid")
