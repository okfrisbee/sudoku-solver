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
    mrv = Sudoku.Sudoku(board)
    mrv.print_board()
    mrv.backtrack_with_mrv_fc()
    mrv.print_board()
    endTime = time.perf_counter()
    mrv_time = endTime - startTime

    startTime = time.perf_counter()
    no_mrv = Sudoku.Sudoku(board)
    no_mrv.backtrack()
    no_mrv.print_board()
    endTime = time.perf_counter()
    no_mrv_time = endTime - startTime
    
    print()
    print(f"Total Time Took:\nMRV: {mrv_time}\nNo MRV: {no_mrv_time}")
    quickest = "MRV" if mrv_time < no_mrv_time else "No MRV"
    print(f"{quickest} was faster by {round(max(mrv_time, no_mrv_time)/min(mrv_time, no_mrv_time))} times.")
        

if __name__ == "__main__":
    main()
