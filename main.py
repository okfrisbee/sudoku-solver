import time
import os
import Sudoku

def iterate_sudoku_puzzles(file):
    with open(file) as f:
        for line in f:
            _, puzzle, _ = line.split()
            if len(puzzle) == 81 and puzzle.isdigit():
                yield puzzle
    
def run_solver(puzzle, mode="mrv", print_board=False):
    start = time.perf_counter()
    solver = Sudoku.Sudoku(puzzle)

    if mode == "naive":
        solver.backtrack_naive()
    else:
        solver.solve()

    if print_board:
        print("\nSolved Board:", end="")
        solver.print_board()
    
    return time.perf_counter() - start

def benchmark(limit):
    naive_total = 0.0
    mrv_total = 0.0
    count = 0

    for i, puzzle in enumerate(iterate_sudoku_puzzles("puzzle_bank.txt"), start=1):
        if limit and i > limit:
            break

        naive_time = run_solver(puzzle, "naive")
        mrv_time = run_solver(puzzle, "mrv")

        naive_total += naive_time
        mrv_total += mrv_time
        count += 1

        print(f"{i}: naive={naive_time:.4f}s | mrv={mrv_time:.4f}s")

    naive_avg = naive_total / count
    mrv_avg = mrv_total/ count

    faster = "MRV" if mrv_total < naive_total else "Naive"
    speedup = (naive_total / mrv_total) if faster == "MRV" else (mrv_total / naive_total)

    print("\n-----Results-----")
    print(f"Puzzles Solved: {count}")
    print(f"Total Time:   naive={naive_total:.4f}s | mrv={mrv_total:.4f}s")
    print(f"Average Time: naive={naive_avg:.6f}s | mrv={mrv_avg:.6f}s")
    print(f"{faster} was faster by {speedup:.2f}x")
        
def main():
    print("Sudoku Solver:")
    while True:
        print("\n-----Menu-----")
        print("1. Enter Puzzle")
        print("2. Benchmark")
        print("3. Quit")
        user_input = input()

        os.system("clear")

        if user_input == "1":
            print("\nEnter puzzle as one line:")
            print("(Example: 083020090000800100029300008000098700070000060006740000300006980002005000010030540)")
            puzzle = input()

            while len(puzzle) != 81 or not puzzle.isdigit():
                os.system("clear")
                print("Invalid Puzzle")
                attempt_again = input("Try again? (y or n): ")
                if attempt_again == "y":
                    print("Enter puzzle again:")
                    print("(Example: 083020090000800100029300008000098700070000060006740000300006980002005000010030540)")
                    puzzle = input()
                else:
                    return
            
            time_elapsed = run_solver(puzzle, print_board=True)
            print(f"Time Elapsed: {time_elapsed:.4f}s")
            break
        elif user_input == "2":
            print("How many puzzles do you want to test? (Default: 1000)")
            test_count = input()
            if not test_count.isdigit() or int(test_count) < 0:
                test_count = 1000

            print()
            benchmark(int(test_count))
            break
        elif user_input == "3":
            return
        else:
            print("Invalid Choice")
            print("Try Again")
            continue

if __name__ == "__main__":
    main()
