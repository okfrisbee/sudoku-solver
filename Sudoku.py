import time

class Sudoku():
    def __init__(self, board):
        self.board = [int(num) for num in board]
        self.rows = [[] for _ in range(9)]
        self.cols = [[] for _ in range(9)]
        self.boxes = [[] for _ in range(9)]
        self.peers = [set() for _ in range(81)]
        self.candidates = [set() for _ in range(81)]

        self.build_houses()
        self.build_peers()
        self.build_candidates()

    def build_houses(self):
        for cell in range(81):
            row, col, box = self.index_to_coordinates(cell)
            self.rows[row].append(cell)
            self.cols[col].append(cell)
            self.boxes[box].append(cell)

    def build_peers(self):
        for cell in range(81):
            row, col, box = self.index_to_coordinates(cell)
            self.peers[cell] = (set(self.rows[row]) | set(self.cols[col]) | set(self.boxes[box])) - {cell}

    def build_candidates(self):
        digits = set(range(1, 10))
        for cell in range(81):
            current_cell_value = self.board[cell]
            if current_cell_value:
                self.candidates[cell] = {current_cell_value}
            else:
                used = set()
                for peer in self.peers[cell]:
                    peer_value = self.board[peer]
                    if peer_value:
                        used.add(peer_value)
                self.candidates[cell] = digits - used

    def print_board(self):
        for i, cell in enumerate(self.board):
            if i % 9 == 0:
                print()
            print(cell, end=" ")
        print()

    def index_to_coordinates(self, index):
        row, col = divmod(index, 9)
        box = (row // 3) * 3 + (col // 3)
        return row, col, box

    def assign(self, index, value):
        previous_candidates = self.candidates[index]
        self.board[index] = value
        self.candidates[index] = {value}
        
        removed_peers = []
        for peer in self.peers[index]:
            if self.board[peer] == 0 and value in self.candidates[peer]:
                self.candidates[peer].remove(value)
                removed_peers.append(peer)
        return previous_candidates, removed_peers

    def unassign(self, index, value, previous_candidates, removed_peers):
        self.board[index] = 0
        self.candidates[index] = previous_candidates
        for peer in removed_peers:
            if self.board[peer] == 0 and self.is_valid(peer, value):
                self.candidates[peer].add(value)

    def is_valid(self, index, value):
        for peer in self.peers[index]:
            if self.board[peer] == value:
                return False
        return True

    # def backtrack(self, index=0):
    #     if index == 81:
    #         return True
        
    #     if self.board[index] != 0:
    #         return self.backtrack(index + 1)

    #     options = self.candidates[index]
    #     for candidate in options:
    #         if not self.is_valid(index, candidate):
    #             continue
    #         previous_candidates, removed = self.assign(index, candidate)
    #         if self.backtrack(index + 1):
    #             return True
    #         self.unassign(index, candidate, previous_candidates, removed)
        
    #     return False


    def backtrack(self, index=0):
            if index == 81:
                return True
            
            if self.board[index] != 0:
                return self.backtrack(index + 1)

            options = self.candidates[index]
            for candidate in options:
                if not self.is_valid(index, candidate):
                    continue
                self.board[index] = candidate
                if self.backtrack(index + 1):
                    return True
                self.board[index] = 0
            
            return False
