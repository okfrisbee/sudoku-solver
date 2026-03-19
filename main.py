import os
import time
import matplotlib
import matplotlib.pyplot as plt
import board_utils

from solvers.naive_solver import solve_naive
from solvers.csp_solver import solve_csp
from solvers.sat_solver import solve_sudoku
from solvers.smt_solver import solve_smt as smt
from solvers.dlx_solver import solve_dlx

matplotlib.use("TkAgg")


def iterate_sudoku_puzzles(file):
    with open(file) as f:
        for line in f:
            _, puzzle, _ = line.split()
            if len(puzzle) == 81 and puzzle.isdigit():
                yield puzzle


def solve_sat(board) -> str | None:
    try:
        return solve_sudoku(board)
    except ValueError:
        return None


def solve_smt(board) -> str | None:
    try:
        return smt(board)
    except ValueError:
        return None


def time_solver(solver_fn, puzzle):
    start = time.perf_counter()
    solved = solver_fn(puzzle)
    elapsed = time.perf_counter() - start
    return solved, elapsed


def run_solver(board, solver_fn, show_board=False):
    solved, elapsed = time_solver(solver_fn, board)

    if solved is None:
        print("Puzzle is not solvable")
        return -1

    if show_board:
        print("\nSolved Board: ")
        board_utils.print_board(solved)

    return elapsed


def benchmark_9x9(limit, solvers):
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


def benchmark_100x100(solvers):
    total_times = {name: 0.0 for name in solvers}
    solved_counts = {name: 0 for name in solvers}
    times_by_solver = {name: 0 for name in solvers}
    avgs = {}

    with open("puzzle100.txt") as f:
        puzzle = f.read()

    for name, fn in solvers.items():
        solved, t = time_solver(fn, puzzle)
        ok = solved is not None

        if ok:
            total_times[name] += t
            solved_counts[name] += 1
            times_by_solver[name] += t

    print("\n-----Results-----")
    for name in solvers:
        c = solved_counts[name]
        total = total_times[name]
        print(f"{name}: solved={"True" if c == 1 else "False"} total={total:.4f}s")


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
            time_elapsed = run_solver(puzzle, solve_csp, show_board=True)
            if time_elapsed != -1:
                print(f"Time Elapsed: {time_elapsed:.4f}s")

        elif user_input == "2":
            print("1. 9x9\n2. 100x100")
            user_input = input().strip()

            if user_input == "1":
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
                    "smt": solve_smt,
                    "dlx": solve_dlx,
                }
                benchmark_9x9(int(test_count), solvers)

            else:
                solvers = {
                    "mrv": solve_csp,
                    "sat": solve_sat,
                    "smt": solve_smt,
                }
                benchmark_100x100(solvers)

        elif user_input == "3":
            return

        else:
            print("Invalid Choice")
            print("Try Again")
            continue


if __name__ == "__main__":
    main()
