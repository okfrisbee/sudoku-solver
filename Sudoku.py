class Sudoku():
    def __init__(self, board):
        self.board = [int(num) for num in board]
        self.rows = [[] for _ in range(9)]
        self.cols = [[] for _ in range(9)]
        self.boxes = [[] for _ in range(9)]
        self.peers = [set() for _ in range(81)]
        self.candidates = [set() for _ in range(81)]
        self.unassigned = set()

        self.build_houses()
        self.build_peers()
        self.build_candidates()
        self.build_unassigned()

    def index_to_coordinates(self, index):
        row, col = divmod(index, 9)
        box = (row // 3) * 3 + (col // 3)
        return row, col, box
    
    def print_board(self):
        for i, cell in enumerate(self.board):
            if i % 9 == 0:
                print()
            print(cell, end=" ")
        print()

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

    def build_unassigned(self):
        for i, cell in enumerate(self.board):
            if cell == 0:
                self.unassigned.add(i)

    def is_valid(self, index, value):
        for peer in self.peers[index]:
            if self.board[peer] == value:
                return False
        return True
    
    def is_complete(self):
        return len(self.unassigned) == 0

    def assign(self, index, value):
        previous_candidates = self.candidates[index]
        self.board[index] = value
        self.candidates[index] = {value}
        self.unassigned.remove(index)
        
        valid = True
        removed_peers = []
        for peer in self.peers[index]:
            if self.board[peer] == 0 and value in self.candidates[peer]:
                self.candidates[peer].remove(value)
                removed_peers.append(peer)
                if len(self.candidates[peer]) == 0:
                    valid = False

        return previous_candidates, removed_peers, valid

    def unassign(self, index, value, previous_candidates, removed_peers):
        self.board[index] = 0
        self.candidates[index] = previous_candidates
        self.unassigned.add(index)
        
        for peer in removed_peers:
            if self.board[peer] == 0 and self.is_valid(peer, value):
                self.candidates[peer].add(value)

    def backtrack(self, index=0):
            if index == 81:
                return True
            
            if self.board[index] != 0:
                return self.backtrack(index + 1)

            for candidate in self.candidates[index]:
                if not self.is_valid(index, candidate):
                    continue
                self.board[index] = candidate
                if self.backtrack(index + 1):
                    return True
                self.board[index] = 0
            
            return False

    def backtrack_with_mrv_fc(self):
        if self.is_complete():
            return True
        
        index = self.find_mrv()
        if index == None:
            return True

        for candidate in self.candidates[index]:
            previous, removed, valid = self.assign(index, candidate)
            if valid and self.backtrack_with_mrv_fc():
                return True
            self.unassign(index, candidate, previous, removed)
        
        return False
    
    def solve(self):
        while not self.is_complete():
            eliminated = self.eliminate_naked_singles()
            
            if eliminated == 0:
                eliminated += self.eliminate_hidden_singles()
            
            if eliminated == 0:
                eliminated += self.eliminate_naked_pairs()

            if eliminated == 0:
                break

        return self.backtrack()

    def find_mrv(self):
        return min(self.unassigned, key=lambda index: len(self.candidates[index]), default=None)

    def eliminate_naked_singles(self):
        eliminated = 0
        for cell in list(self.unassigned):
            if len(self.candidates[cell]) == 1:
                self.assign(cell, list(self.candidates[cell])[0])
                eliminated += 1
        return eliminated

    def eliminate_hidden_singles(self):
        eliminated = 0
        houses = self.rows + self.cols + self.boxes

        for house in houses:
            seen = [None for _ in range(9)]

            for cell in house:
                if self.board[cell] != 0:
                    continue

                for candidate in self.candidates[cell]:
                    match seen[candidate - 1]:
                        case -1:
                            continue
                        case None:
                            seen[candidate - 1] = cell
                        case _:
                            seen[candidate - 1] = -1

            for i, cell in enumerate(seen):
                match cell:
                    case -1 | None:
                        continue
                    case _:
                        self.assign(cell, i + 1)
                        eliminated += 1
                        
        return eliminated

    def eliminate_naked_pairs(self):
        eliminated = 0
        houses = self.rows + self.cols + self.boxes

        for house in houses:
            two_celled = []
            for cell in house:
                if self.board[cell] != 0:
                    continue

                if len(self.candidates[cell]) == 2:
                    two_celled.append(cell)

            if len(two_celled) != 2:
                continue

            if self.candidates[two_celled[0]] == self.candidates[two_celled[1]]:
                for cell in house:
                    if cell in two_celled:
                        continue
                    
                    if self.candidates[two_celled[0]].issubset(self.candidates[cell]):
                        self.candidates[cell] -= self.candidates[two_celled[0]]
                        eliminated += 1

        return eliminated
