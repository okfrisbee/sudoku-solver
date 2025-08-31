import time
import Sudoku

def get_sudoku_puzzles(file):
    with open(file) as f:
        digits = []
        for line in f:
            digits.append(line.split()[1])
        return digits
    
def benchmark():
    no_mrv_time = 0
    mrv_time = 0
    for i, puzzle in enumerate(get_sudoku_puzzles("puzzle_bank.txt")):
        startTime = time.perf_counter()
        no_mrv = Sudoku.Sudoku(puzzle)
        no_mrv.backtrack()
        endTime = time.perf_counter()
        no_mrv_time += endTime - startTime
        print(f"No MRV Finished {i + 1} and {puzzle}")

        startTime = time.perf_counter()
        mrv = Sudoku.Sudoku(puzzle)
        mrv.backtrack_with_mrv_fc()
        endTime = time.perf_counter()
        mrv_time += endTime - startTime
        print(f"MRV Finished {i + 1} and {puzzle}")

    print(f"Total Time Took for 200 Puzzles:\nNo MRV: {no_mrv_time}\nMRV: {mrv_time}")
    quickest = "MRV" if mrv_time < no_mrv_time else "No MRV"
    print(f"{quickest} was faster by {round(max(mrv_time, no_mrv_time)/min(mrv_time, no_mrv_time))} times.")
        
def main():
    benchmark()

if __name__ == "__main__":
    main()
