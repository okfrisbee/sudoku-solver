import time
import Sudoku

def get_sudoku_puzzles(file):
    with open(file) as f:
        digits = []
        for line in f:
            digits.append(line.split()[1])
        return digits

def create_matrix(board):
    board = list(map(int, board))
    return [board[i:i+9] for i in range(0, 81, 9)]
        
def main():
    board = "608000301700050002040000050200608004105020708000070000000000000810000079070103080"
    grid = create_matrix(board)
    startTime = time.perf_counter()
    sudoku = Sudoku.Sudoku(grid)
    print(sudoku.candidates)
    endTime = time.perf_counter()
    print(f"Total Time Took: {endTime - startTime}")
        

if __name__ == "__main__":
    main()
