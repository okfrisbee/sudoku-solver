import os

import board_utils
from benchmark import (
    benchmark_menu,
    solve_with_timeout,
)
from benchmark.visualization import visualization_menu
from generator import (
    generate_dataset_menu,
    verify_dataset_menu,
)
from solvers.csp import solve_csp


def main():
    print("Sudoku Solver:")
    while True:
        print("\n-----Menu-----")
        print("1. Enter Puzzle")
        print("2. Generate Dataset")
        print("3. Verify Dataset")
        print("4. Benchmark")
        print("5. Quit")
        user_input = input().strip()

        if user_input == "1":
            os.system("clear")
            print("\nEnter puzzle as one line:")
            print(
                "(Example: 083020090000800100029300008000098700070000060006740000300006980002005000010030540)"
            )
            puzzle = input().strip()
            print()
            result = solve_with_timeout(solve_csp, puzzle)
            if result.solved:
                print("\nSolved Board: ")
                board_utils.print_board(result.solution)
                print(f"Time Elapsed: {result.runtime_seconds:.4f}s")
            else:
                print("Puzzle is not solvable")

        elif user_input == "2":
            os.system("clear")
            generate_dataset_menu()

        elif user_input == "3":
            os.system("clear")
            verify_dataset_menu()

        elif user_input == "4":
            os.system("clear")
            benchmark_result = benchmark_menu()
            visualization_menu(benchmark_result)

        elif user_input == "5":
            return

        else:
            print("Invalid Choice")
            print("Try Again")
            continue


if __name__ == "__main__":
    main()
