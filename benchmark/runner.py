import multiprocessing
import queue
import time

from cli_helpers import prompt_choice
from config import load_config
from generator import dataset_size_from_path, read_dataset, select_dataset
from .reporting import (
    print_summary_table,
    result_paths,
    results_dataframe,
    summary_dataframe,
    write_csv as write_table_csv,
)

from solvers.csp import solve_csp
from solvers.dlx import solve_dlx
from solvers.metrics import SolverResult
from solvers.naive import solve_naive
from solvers.sat import solve_sudoku as solve_sat
from solvers.smt import solve_smt

BENCHMARK_SOLVER_TIMEOUT_SECONDS = load_config()["benchmark"]["solver_timeout_seconds"]
SOLVERS = {
    "naive": solve_naive,
    "csp": solve_csp,
    "sat": solve_sat,
    "smt": solve_smt,
    "dlx": solve_dlx,
}


def _run_solver_process(solver_fn, puzzle, result_queue):
    result_queue.put(solver_fn(puzzle))


def solve_with_timeout(
    solver_fn,
    puzzle,
) -> SolverResult:
    timeout_seconds = load_config()["benchmark"]["solver_timeout_seconds"]
    start = time.perf_counter()
    context_name = "fork" if "fork" in multiprocessing.get_all_start_methods() else None
    context = multiprocessing.get_context(context_name)
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_run_solver_process,
        args=(solver_fn, puzzle, result_queue),
    )

    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join()
        elapsed = time.perf_counter() - start
        return SolverResult(
            solution=None,
            status="timeout",
            runtime_seconds=elapsed,
            error=f"Timed out after {timeout_seconds} seconds.",
        )

    try:
        return result_queue.get_nowait()
    except queue.Empty:
        return SolverResult(
            solution=None,
            status="error",
            runtime_seconds=time.perf_counter() - start,
            error=f"Solver process exited with code {process.exitcode} without a result.",
        )


def _csv_row(size, puzzle_index, solver_name, result, record):
    return {
        "puzzle_index": puzzle_index,
        "solver_name": solver_name,
        "result": result,
        "metadata": {
            "size": size,
            "difficulty": record.get("difficulty", ""),
            "clues": record.get("actual_clues", ""),
        },
    }


def benchmark_dataset(
    dataset_path,
    size,
    write_csv=False,
    solver_names=None,
):
    records = read_dataset(dataset_path, expected_size=size)
    if not records:
        print("\nDataset has no puzzles.")
        return None

    solvers = dict(SOLVERS)
    if solver_names is not None:
        solvers = {
            name: solver for name, solver in solvers.items() if name in solver_names
        }

    csv_rows = []
    tested = 0

    for i, record in enumerate(records, start=1):
        puzzle = record["puzzle"]
        row_parts = [f"{i}:"]
        for name, fn in solvers.items():
            result = solve_with_timeout(
                fn,
                puzzle,
            )
            csv_rows.append(_csv_row(size, i, name, result, record))

            if result.solved:
                row_parts.append(f"{name}={result.runtime_seconds:.4f}s")
            else:
                row_parts.append(f"{name}={result.status.upper()}")

        tested += 1
        print(" | ".join(row_parts))

    results_table = results_dataframe(csv_rows)
    summary_table = summary_dataframe(results_table, tested)

    print("\n-----Results-----")
    print(f"Puzzles Tested: {tested}\n")
    print_summary_table(summary_table)
    if write_csv:
        csv_path, summary_path = result_paths(dataset_path)
        csv_file = write_table_csv(results_table, csv_path)
        summary_file = write_table_csv(summary_table, summary_path)
        print(f"\nCSV written to: {csv_file}")
        print(f"Summary CSV written to: {summary_file}")

    return results_table


def benchmark_menu():
    dataset_path = select_dataset()
    if dataset_path is None:
        return
    try:
        size = dataset_size_from_path(dataset_path)
    except ValueError as exc:
        print(exc)
        return

    solver_options = ["all", *SOLVERS]
    solver_mode = prompt_choice("\nSelect benchmark solver mode:", solver_options)
    if solver_mode is None:
        print("Invalid benchmark solver mode.")
        return
    solver_names = None if solver_mode == "all" else [solver_mode]

    print()
    write_csv = (
        input("Save benchmark results and summary to CSV? (y/n): ").strip().lower()
        == "y"
    )
    print()
    return benchmark_dataset(
        dataset_path,
        size,
        write_csv=write_csv,
        solver_names=solver_names,
    )


if __name__ == "__main__":
    benchmark_menu()
