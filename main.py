import csv
import json
import os
from pathlib import Path
import time
import board_utils

from solvers.naive_solver import solve_naive
from solvers.csp_solver import solve_csp
from solvers.dlx_solver import solve_dlx
from solvers.metrics import SolverResult
from sudoku_datasets import (
    DIFFICULTIES,
    DIFFICULTY_PERCENT_RANGES,
    SUPPORTED_SIZES,
    generate_dataset,
    list_datasets,
    read_dataset,
    verify_dataset,
)

try:
    from solvers.sat_solver import solve_sudoku as solve_sat
except ImportError as exc:
    SAT_IMPORT_ERROR = exc

    def solve_sat(_board):
        return unavailable_solver_result("sat", SAT_IMPORT_ERROR)


try:
    from solvers.smt_solver import solve_smt
except ImportError as exc:
    SMT_IMPORT_ERROR = exc

    def solve_smt(_board):
        return unavailable_solver_result("smt", SMT_IMPORT_ERROR)


CSV_FIELDS = [
    "benchmark_type",
    "dataset",
    "size",
    "difficulty",
    "clues",
    "puzzle_index",
    "solver",
    "status",
    "runtime_seconds",
    "setup_seconds",
    "solve_seconds",
    "backtracks",
    "assignments",
    "recursive_calls",
    "solution_found",
    "error",
]
BENCHMARK_RESULTS_DIR = "benchmark_results"
ALL_DIFFICULTIES_OPTION = "all difficulties"


def unavailable_solver_result(name, exc):
    return SolverResult(
        solution=None,
        status="error",
        runtime_seconds=0.0,
        error=f"{name} solver unavailable: {exc}",
    )


def safe_solve(solver_fn, puzzle) -> SolverResult:
    start = time.perf_counter()
    try:
        return solver_fn(puzzle)
    except Exception as exc:
        return SolverResult(
            solution=None,
            status="error",
            runtime_seconds=time.perf_counter() - start,
            error=str(exc),
        )


def format_seconds(value):
    return "" if value is None else f"{value:.6f}"


def format_metric(value):
    return "" if value is None else str(value)


def csv_row(benchmark_type, puzzle_index, solver_name, result, metadata=None):
    metadata = metadata or {}
    return {
        "benchmark_type": benchmark_type,
        "dataset": metadata.get("dataset", ""),
        "size": metadata.get("size", ""),
        "difficulty": metadata.get("difficulty", ""),
        "clues": metadata.get("clues", ""),
        "puzzle_index": puzzle_index,
        "solver": solver_name,
        "status": result.status,
        "runtime_seconds": format_seconds(result.runtime_seconds),
        "setup_seconds": format_seconds(result.setup_seconds),
        "solve_seconds": format_seconds(result.solve_seconds),
        "backtracks": format_metric(result.backtracks),
        "assignments": format_metric(result.assignments),
        "recursive_calls": format_metric(result.recursive_calls),
        "solution_found": result.solved,
        "error": result.error or "",
    }


def benchmark_data_directory(size, difficulty, results_dir=None):
    if results_dir is None:
        results_dir = BENCHMARK_RESULTS_DIR
    return Path(results_dir) / f"{size}x{size}" / difficulty / "data"


def benchmark_summary_directory(size, difficulty, results_dir=None):
    if results_dir is None:
        results_dir = BENCHMARK_RESULTS_DIR
    return Path(results_dir) / f"{size}x{size}" / difficulty / "summary"


def next_benchmark_run_paths(size, difficulty, results_dir=None):
    data_dir = benchmark_data_directory(size, difficulty, results_dir)
    summary_dir = benchmark_summary_directory(size, difficulty, results_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    index = 0
    while True:
        csv_path = data_dir / f"run_{index}.csv"
        json_path = summary_dir / f"run_{index}.json"
        if not csv_path.exists() and not json_path.exists():
            return csv_path, json_path
        index += 1


def write_benchmark_csv(rows, csv_path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    filename = csv_path
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return filename


def write_benchmark_summary_json(summary, json_path):
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    return json_path


def average_present(results, attr):
    values = [
        getattr(result, attr)
        for result in results
        if getattr(result, attr) is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)


def benchmark_summary_rows(results_by_solver, tested):
    rows = []

    for name, results in results_by_solver.items():
        solved = sum(1 for result in results if result.solved)
        total_runtime = sum(result.runtime_seconds for result in results)
        avg_runtime = total_runtime / tested if tested else 0.0
        success_rate = (solved / tested * 100) if tested else 0.0
        solve_average = average_present(results, "solve_seconds")
        if solve_average is None and any(result.status != "error" for result in results):
            solve_average = avg_runtime

        rows.append(
            {
                "solver": name,
                "solved": f"{solved}/{tested}",
                "success_rate": f"{success_rate:.1f}%",
                "total_runtime_s": f"{total_runtime:.4f}",
                "avg_runtime_s": f"{avg_runtime:.6f}",
                "setup_avg_s": format_summary_seconds(
                    average_present(results, "setup_seconds")
                ),
                "solve_avg_s": format_summary_seconds(solve_average),
                "backtracks_avg": format_summary_average(
                    average_present(results, "backtracks")
                ),
                "assignments_avg": format_summary_average(
                    average_present(results, "assignments")
                ),
                "recursive_calls_avg": format_summary_average(
                    average_present(results, "recursive_calls")
                ),
            }
        )

    return rows


def format_summary_seconds(value):
    return "-" if value is None else f"{value:.6f}"


def format_summary_average(value):
    return "-" if value is None else f"{value:.2f}"


def print_summary_table(rows):
    try:
        import pandas as pd
    except ImportError:
        print_plain_summary_table(rows)
        return

    table = pd.DataFrame(rows)
    print(table.to_string(index=False))


def print_plain_summary_table(rows):
    if not rows:
        return

    headers = list(rows[0].keys())
    widths = {
        header: max(len(header), *(len(str(row[header])) for row in rows))
        for header in headers
    }
    header_row = "  ".join(header.ljust(widths[header]) for header in headers)
    divider = "  ".join("-" * widths[header] for header in headers)

    print(header_row)
    print(divider)
    for row in rows:
        print("  ".join(str(row[header]).ljust(widths[header]) for header in headers))


def print_benchmark_summary(results_by_solver, tested):
    print("\n-----Results-----")
    print(f"Puzzles Tested: {tested}\n")
    print_summary_table(benchmark_summary_rows(results_by_solver, tested))


def prompt_write_csv():
    return input("Save benchmark results to CSV and JSON? (y/n): ").strip().lower() == "y"


def prompt_choice(title, options):
    print(title)
    for index, option in enumerate(options, start=1):
        print(f"{index}. {option}")

    choice = input().strip()
    if not choice.isdigit():
        return None

    index = int(choice)
    if index < 1 or index > len(options):
        return None
    return options[index - 1]


def prompt_size():
    options = [f"{size}x{size}" for size in SUPPORTED_SIZES]
    selected = prompt_choice("\nSelect puzzle size:", options)
    if selected is None:
        print("Invalid size.")
        return None
    return int(selected.split("x", 1)[0])


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


def prompt_benchmark_solver_mode():
    selected = prompt_choice("\nSelect benchmark solver mode:", ["all", "csp only"])
    if selected is None:
        print("Invalid benchmark solver mode.")
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


def select_dataset(size):
    datasets = list_datasets(size)
    if not datasets:
        print(f"\nNo datasets found for {size}x{size}. Generate a dataset first.")
        return None

    options = [path.name for path in datasets]
    selected = prompt_choice("\nSelect dataset:", options)
    if selected is None:
        print("Invalid dataset.")
        return None

    return datasets[options.index(selected)]


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


def run_solver(board, solver_fn, show_board=False):
    result = safe_solve(solver_fn, board)

    if not result.solved:
        print("Puzzle is not solvable")
        return -1

    if show_board:
        print("\nSolved Board: ")
        board_utils.print_board(result.solution)

    return result.runtime_seconds


def solvers_for_size(size):
    solvers = {
        "csp": solve_csp,
        "sat": solve_sat,
        "smt": solve_smt,
        "dlx": solve_dlx,
    }
    if size in {4, 9, 16}:
        return {"naive": solve_naive, **solvers}
    return solvers


def puzzle_for_solver(puzzle, solver_name):
    return puzzle


def benchmark_dataset(dataset_path, size, write_csv=False, solver_names=None):
    records = read_dataset(dataset_path, expected_size=size)
    if not records:
        print("\nDataset has no puzzles.")
        return

    solvers = solvers_for_size(size)
    if solver_names is not None:
        requested = set(solver_names)
        solvers = {
            name: solver
            for name, solver in solvers.items()
            if name in requested
        }
        missing = requested - set(solvers)
        if missing:
            print(f"\nNo solver found for: {', '.join(sorted(missing))}")
            return

    difficulty = Path(dataset_path).stem
    csv_rows = []
    results_by_solver = {name: [] for name in solvers}
    times_by_solver = {name: [] for name in solvers}
    tested = 0
    dataset_name = Path(dataset_path).name

    for i, record in enumerate(records, start=1):
        puzzle = record["puzzle"]
        row_parts = [f"{i}:"]
        for name, fn in solvers.items():
            result = safe_solve(fn, puzzle_for_solver(puzzle, name))
            results_by_solver[name].append(result)
            times_by_solver[name].append(result.runtime_seconds)
            if write_csv:
                csv_rows.append(
                    csv_row(
                        f"{size}x{size}",
                        i,
                        name,
                        result,
                        metadata={
                            "dataset": dataset_name,
                            "size": size,
                            "difficulty": record.get("difficulty", ""),
                            "clues": record.get("actual_clues", ""),
                        },
                    )
                )

            if result.solved:
                row_parts.append(f"{name}={result.runtime_seconds:.4f}s")
            else:
                row_parts.append(f"{name}={result.status.upper()}")

        tested += 1
        print(" | ".join(row_parts))

    summary_rows = benchmark_summary_rows(results_by_solver, tested)
    print("\n-----Results-----")
    print(f"Puzzles Tested: {tested}\n")
    print_summary_table(summary_rows)
    if write_csv:
        csv_path, json_path = next_benchmark_run_paths(size, difficulty)
        csv_file = write_benchmark_csv(csv_rows, csv_path)
        summary_file = write_benchmark_summary_json(
            {
                "dataset": {
                    "path": str(dataset_path),
                    "name": dataset_name,
                    "size": size,
                    "difficulty": difficulty,
                    "puzzle_count": len(records),
                },
                "tested": tested,
                "solvers": list(solvers),
                "summary_rows": summary_rows,
            },
            json_path,
        )
        print(f"\nCSV written to: {csv_file}")
        print(f"JSON summary written to: {summary_file}")

    visual = input("\nVisualize data? (y/n): ").strip().lower()
    if visual == "y":
        show_naive = True
        if "naive" in times_by_solver:
            show_naive = input("Show naive solver on graph? (y/n): ").strip().lower() == "y"
        avgs = {
            name: (sum(result.runtime_seconds for result in results) / tested)
            if tested
            else 0.0
            for name, results in results_by_solver.items()
        }
        visualize_benchmark(times_by_solver, tested, avgs, show_naive=show_naive)


def visualize_benchmark(times_by_solver, tested, avgs, show_naive=True):
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("TkAgg")

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
