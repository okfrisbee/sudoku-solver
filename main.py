import time
import Sudoku

def get_sudoku_puzzles(file):
    with open(file) as f:
        digits = []
        for line in f:
            digits.append(line.split()[1])
        return digits
        
def main():
    board = "800000000043900008001000405039600027000000000006230004000300040020800900000005102"
    startTime = time.perf_counter()
    sudoku = Sudoku.Sudoku(board)
    sudoku.print_board()
    sudoku.backtrack()
    sudoku.print_board()
    endTime = time.perf_counter()
    print(f"Total Time Took: {endTime - startTime}")
        

if __name__ == "__main__":
    main()
