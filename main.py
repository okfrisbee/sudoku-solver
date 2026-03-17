import os
import time
import matplotlib
import matplotlib.pyplot as plt

from naive_solver import solve_naive
from csp_solver import solve_csp
from sat_solver import solve_sudoku

matplotlib.use("TkAgg")


def iterate_sudoku_puzzles(file):
    with open(file) as f:
        for line in f:
            _, puzzle, _ = line.split()
            if len(puzzle) == 81 and puzzle.isdigit():
                yield puzzle


def solve_sat(board) -> str | None:
    try:
        return solve_sudoku(board, solver_name="cadical195")
    except ValueError:
        return None


def print_board(board: str):
    for i, cell in enumerate(board):
        if i % 9 == 0:
            print()
        print(cell, end=" ")
    print()


def time_solver(solver_fn, puzzle):
    start = time.perf_counter()
    solved = solver_fn(puzzle)
    elapsed = time.perf_counter() - start
    return solved, elapsed


def run_solver(puzzle, solver_fn, show_board=False):
    solved, elapsed = time_solver(solver_fn, puzzle)

    if solved is None:
        print("Puzzle is not solvable")
        return -1

    if show_board:
        print("\nSolved Board: ")
        print_board(solved)

    return elapsed


def benchmark(limit, solvers):
    total_times = {name: 0.0 for name in solvers}
    solved_counts = {name: 0 for name in solvers}
    times_by_solver = {name: [] for name in solvers}
    tested = 0
    avgs = {}

    for i, puzzle in enumerate(iterate_sudoku_puzzles("puzzle_bank.txt"), start=1):
        if limit and i > limit:
            break

        row_parts = [f"{i}:"]
        for name, fn in solvers.items():
            solved, t = time_solver(fn, puzzle)
            ok = solved is not None

            if ok:
                total_times[name] += t
                solved_counts[name] += 1
                times_by_solver[name].append(t)
                row_parts.append(f"{name}={t:.4f}s")
            else:
                row_parts.append(f"{name}=FAIL")

        tested += 1
        print(" | ".join(row_parts))

    print("\n-----Results-----")
    print(f"Puzzles Tested: {tested}")
    for name in solvers:
        c = solved_counts[name]
        total = total_times[name]
        avgs[name] = total / c
        print(f"{name}: solved={c}/{tested} total={total:.4f}s avg={avgs[name]:.6f}s")

    visual = input("\nVisualize data? (y/n): ").strip().lower()
    if visual == "y":
        show_naive = input("Show naive solver on graph? (y/n): ").strip().lower() == "y"
        visualize_benchmark(times_by_solver, tested, avgs, show_naive=show_naive)


def visualize_benchmark(times_by_solver, tested, avgs, show_naive=True):
    plt.figure()
    for name, ts in times_by_solver.items():
        if name == "naive" and not show_naive:
            continue
        xs = range(1, len(ts) + 1)
        ys = ts
        plt.plot(xs, ys, label=name)
    plt.title(f"Sudoku Benchmark: Per-puzzle solve times (n={tested})")
    plt.xlabel("Puzzle #")
    plt.ylabel("Time (seconds)")
    plt.legend()
    plt.tight_layout()

    plt.figure()
    names, values = list(avgs.keys()), list(avgs.values())
    plt.bar(names, values)
    plt.title("Average solve time")
    plt.xlabel("Solver")
    plt.ylabel("Avg time (seconds)")
    plt.tight_layout()

    plt.show()


def main():
    print("Sudoku Solver:")
    while True:
        print("\n-----Menu-----")
        print("1. Enter Puzzle")
        print("2. Benchmark")
        print("3. Quit")
        user_input = input().strip()

        os.system("clear")

        if user_input == "1":
            print("\nEnter puzzle as one line:")
            print(
                "(Example: 083020090000800100029300008000098700070000060006740000300006980002005000010030540)"
            )
            puzzle = input().strip()

            while len(puzzle) != 81 or not puzzle.isdigit():
                os.system("clear")
                print("Invalid Puzzle")
                attempt_again = input("Try again? (y or n): ").strip().lower()
                if attempt_again == "y":
                    print("Enter puzzle again:")
                    print(
                        "(Example: 083020090000800100029300008000098700070000060006740000300006980002005000010030540)"
                    )
                    puzzle = input().strip()
                else:
                    return

            time_elapsed = run_solver(puzzle, solve_csp, show_board=True)
            if time_elapsed != -1:
                print(f"Time Elapsed: {time_elapsed:.4f}s")

        elif user_input == "2":
            print(
                "How many puzzles do you want to test? (Default: 1000 and Maximum: 100000)"
            )
            test_count = input().strip()
            if not test_count.isdigit() or int(test_count) < 0:
                test_count = 1000

            print()

            solvers = {
                "naive": solve_naive,
                "mrv": solve_csp,
                "sat": solve_sat,
            }
            benchmark(int(test_count), solvers)

        elif user_input == "3":
            return

        else:
            print("Invalid Choice")
            print("Try Again")
            continue


if __name__ == "__main__":
    main()
