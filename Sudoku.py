class Sudoku():
    # Constructor and Setup
    def __init__(self, board):
        """Initialize a Sudoku board along with helper structures."""
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

    def build_houses(self):
        """Creates lists of cell indices for each row, column, and box."""
        for cell in range(81):
            row, col, box = self.index_to_coordinates(cell)
            self.rows[row].append(cell)
            self.cols[col].append(cell)
            self.boxes[box].append(cell)

    def build_peers(self):
        """Creates for each cell a set of indices of neighboring cells in the same row, column, or box."""
        for cell in range(81):
            row, col, box = self.index_to_coordinates(cell)
            self.peers[cell] = (set(self.rows[row]) | set(self.cols[col]) | set(self.boxes[box])) - {cell}

    def build_candidates(self):
        """Creates a set of possible candidates for each cell if not already assigned."""
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
        """Records indices of all currently empty cells (with a value of 0)."""
        for i, cell in enumerate(self.board):
            if cell == 0:
                self.unassigned.add(i)


    # Helper Methods
    def index_to_coordinates(self, index):
        """Coverts a 0-80 index to (row, col, box) coordinates."""
        row, col = divmod(index, 9)
        box = (row // 3) * 3 + (col // 3)
        return row, col, box
    
    def print_board(self):
        """Prints the current Sudoku board in a 9x9 grid."""
        for i, cell in enumerate(self.board):
            if i % 9 == 0:
                print()
            print(cell, end=" ")
        print()

    def is_valid(self, index, value):
        """Returns True or False if placing value at index violates the rules of Sudoku. """
        for peer in self.peers[index]:
            if self.board[peer] == value:
                return False
        return True
    
    def is_complete(self):
        """Returns True if no unassigned cells remain."""
        return len(self.unassigned) == 0


    # Assignment Methods
    def assign(self, index, value):
        """Assigns a value to a cell and updates the peers' candidate sets."""
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
        """Unassigns a cell's value and restores the candidate set."""
        self.board[index] = 0
        self.candidates[index] = previous_candidates
        self.unassigned.add(index)
        
        for peer in removed_peers:
            if self.board[peer] == 0 and self.is_valid(peer, value):
                self.candidates[peer].add(value)


    # Sudoku Strategies
    def eliminate_naked_singles(self):
        "Automatically fills any cells that has exactly only one possible candidate."
        eliminated = 0
        for cell in list(self.unassigned):
            if len(self.candidates[cell]) == 1:
                self.assign(cell, list(self.candidates[cell])[0])
                eliminated += 1
        return eliminated

    def eliminate_hidden_singles(self):
        """Fills cells with values that only appear in one place within a row, column, or box."""
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
        """Finds naked pairs and removes them from the candidates of other cells in the same house."""
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


    # Heuristics and Search
    def find_mrv(self):
        """Returns the index of an unassigned cell with the fewest remaining candidates."""
        return min(self.unassigned, key=lambda index: len(self.candidates[index]), default=None)

    def backtrack_naive(self, index=0):
            """Simple recursive backtracking."""
            if index == 81:
                return True
            
            if self.board[index] != 0:
                return self.backtrack(index + 1)

            for candidate in self.candidates[index]:
                if not self.is_valid(index, candidate):
                    continue
                self.board[index] = candidate
                if self.backtrack_naive(index + 1):
                    return True
                self.board[index] = 0
            
            return False

    def backtrack(self):
        """Backtracking with MRV and forward checking."""
        if self.is_complete():
            return True
        
        index = self.find_mrv()
        if index == None:
            return True

        for candidate in self.candidates[index]:
            previous, removed, valid = self.assign(index, candidate)
            if valid and self.backtrack():
                return True
            self.unassign(index, candidate, previous, removed)
        
        return False
    
    def solve(self):
        """Tries Sudoku strategies before searching for a complete solution."""
        while not self.is_complete():
            eliminated = self.eliminate_naked_singles()
            
            if eliminated == 0:
                eliminated += self.eliminate_hidden_singles()
            
            if eliminated == 0:
                eliminated += self.eliminate_naked_pairs()

            if eliminated == 0:
                break

        return self.backtrack()
