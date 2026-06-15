import os
import time

from benchmark import (
    benchmark_dataset,
    prompt_benchmark_solver_mode,
    prompt_write_csv,
    run_solver,
)
from cli_helpers import prompt_choice, prompt_size, select_dataset
from generator import (
    DIFFICULTIES,
    DIFFICULTY_PERCENT_RANGES,
    generate_dataset,
    verify_dataset,
)
from solvers.csp import solve_csp


ALL_DIFFICULTIES_OPTION = "all difficulties"


def prompt_difficulty():
    selected = prompt_choice(
        "\nSelect difficulty:",
        list(DIFFICULTIES) + [ALL_DIFFICULTIES_OPTION],
    )
    if selected is None:
        print("Invalid difficulty.")
    return selected


def prompt_verification_mode():
    selected = prompt_choice("\nSelect verification mode:", ["solvable", "unique"])
    if selected is None:
        print("Invalid verification mode.")
    return selected


def prompt_positive_int(message):
    print(message)
    value = input().strip()
    if not value.isdigit() or int(value) <= 0:
        print("Invalid count.")
        return None
    return int(value)


def generate_dataset_menu():
    size = prompt_size()
    if size is None:
        return

    difficulty = prompt_difficulty()
    if difficulty is None:
        return

    count_prompt = "\nHow many puzzles should be generated?"
    if difficulty == ALL_DIFFICULTIES_OPTION:
        count_prompt = "\nHow many puzzles should be generated per difficulty?"

    count = prompt_positive_int(count_prompt)
    if count is None:
        return

    difficulties = (
        list(DIFFICULTY_PERCENT_RANGES)
        if difficulty == ALL_DIFFICULTIES_OPTION
        else [difficulty]
    )
    difficulty_label = (
        "easy, medium, and hard"
        if difficulty == ALL_DIFFICULTIES_OPTION
        else difficulty
    )

    print(f"\nGenerating {count} {size}x{size} {difficulty_label} puzzle(s)...")
    start = time.perf_counter()
    paths = []
    try:
        for selected_difficulty in difficulties:
            paths.append(generate_dataset(size, selected_difficulty, count))
    except Exception as exc:
        print(f"Dataset generation failed: {exc}")
        return

    for path in paths:
        print(f"Dataset written to: {path}")
    print(f"Generation time: {time.perf_counter() - start:.4f}s")
def benchmark_menu():
    size = prompt_size()
    if size is None:
        return

    dataset_path = select_dataset(size)
    if dataset_path is None:
        return

    solver_mode = prompt_benchmark_solver_mode()
    if solver_mode is None:
        return
    solver_names = ["csp"] if solver_mode == "csp only" else None

    print()
    write_csv = prompt_write_csv()
    print()
    benchmark_dataset(
        dataset_path,
        size,
        write_csv=write_csv,
        solver_names=solver_names,
    )


def verify_dataset_menu():
    size = prompt_size()
    if size is None:
        return

    dataset_path = select_dataset(size)
    if dataset_path is None:
        return

    mode = prompt_verification_mode()
    if mode is None:
        return

    print(f"\nVerifying {dataset_path} with mode={mode}...")
    try:
        summary = verify_dataset(dataset_path, expected_size=size, mode=mode)
    except Exception as exc:
        print(f"Dataset verification failed: {exc}")
        return

    print("\n-----Verification Results-----")
    print(f"Dataset: {dataset_path}")
    print(f"Mode: {summary.mode}")
    print(f"Puzzles Checked: {summary.total}")
    print(f"Valid: {summary.valid_count}")
    print(f"Invalid: {summary.invalid_count}")
    print(f"Verification time: {summary.runtime_seconds:.4f}s")

    if summary.failures:
        print("\nFailures:")
        for failure in summary.failures:
            print(
                f"{failure.record_number}: "
                f"id={failure.record_id} error={failure.error or 'verification failed'}"
            )


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
            time_elapsed = run_solver(puzzle, solve_csp, show_board=True)
            if time_elapsed != -1:
                print(f"Time Elapsed: {time_elapsed:.4f}s")

        elif user_input == "2":
            os.system("clear")
            generate_dataset_menu()

        elif user_input == "3":
            os.system("clear")
            verify_dataset_menu()

        elif user_input == "4":
            os.system("clear")
            benchmark_menu()

        elif user_input == "5":
            return

        else:
            print("Invalid Choice")
            print("Try Again")
            continue


if __name__ == "__main__":
    main()
