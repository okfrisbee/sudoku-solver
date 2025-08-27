class Sudoku():
    def __init__(self, board):
        self.board = board
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
            current_cell_value = self.get_cell_value(cell)
            if current_cell_value:
                self.candidates[cell] = {current_cell_value}
            else:
                used = set()
                for peer in self.peers[cell]:
                    peer_value = self.get_cell_value(peer)
                    if peer_value:
                        used.add(peer_value)
                self.candidates[cell] = digits - used

    def print_board(self):
        for i, cell in enumerate(self.board):
            if i % 9 == 0:
                print()
            print(cell, end=" ")
        print()

    def get_cell_value(self, index):
        return int(self.board[index])

    def index_to_coordinates(self, index):
        row, col = divmod(index, 9)
        box = (row // 3) * 3 + (col // 3)
        return row, col, box

    def assign(self, index, value):
        self.board[index] = value
        self.candidates[index] = {value}
        for peer in self.peers[index]:
            self.candidates[peer].discard(value)

    def is_valid(self, index, value):
        for peer in self.peers[index]:
            if self.get_cell_value(peer) == value:
                return False
        return True
