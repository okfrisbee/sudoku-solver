import multiprocessing
from pathlib import Path
import queue
import time

from cli_helpers import prompt_choice
from generator import dataset_size_from_path, read_dataset, select_dataset
from .reporting import (
    next_run_paths,
    print_summary_table,
    result_row,
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


BENCHMARK_SOLVER_TIMEOUT_SECONDS = 60


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


def _solve_worker(solver_fn, puzzle, result_queue):
    result_queue.put(safe_solve(solver_fn, puzzle))


def solve_with_timeout(
    solver_fn,
    puzzle,
    timeout_seconds=BENCHMARK_SOLVER_TIMEOUT_SECONDS,
) -> SolverResult:
    start = time.perf_counter()
    context_name = "fork" if "fork" in multiprocessing.get_all_start_methods() else None
    context = multiprocessing.get_context(context_name)
    result_queue = context.Queue(maxsize=1)
    process = context.Process(target=_solve_worker, args=(solver_fn, puzzle, result_queue))

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


def benchmark_dataset(
    dataset_path,
    size,
    write_csv=False,
    solver_names=None,
    timeout_seconds=BENCHMARK_SOLVER_TIMEOUT_SECONDS,
):
    records = read_dataset(dataset_path, expected_size=size)
    if not records:
        print("\nDataset has no puzzles.")
        return None

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
            return None

    record_difficulties = {
        record.get("difficulty", "")
        for record in records
        if record.get("difficulty")
    }
    difficulty = (
        next(iter(record_difficulties))
        if len(record_difficulties) == 1
        else Path(dataset_path).stem
    )
    csv_rows = []
    tested = 0
    dataset_name = Path(dataset_path).name

    for i, record in enumerate(records, start=1):
        puzzle = record["puzzle"]
        row_parts = [f"{i}:"]
        for name, fn in solvers.items():
            result = solve_with_timeout(
                fn,
                puzzle,
                timeout_seconds=timeout_seconds,
            )
            csv_rows.append(
                result_row(
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

    results_table = results_dataframe(csv_rows)
    summary_table = summary_dataframe(results_table, tested)

    print("\n-----Results-----")
    print(f"Puzzles Tested: {tested}\n")
    print_summary_table(summary_table)
    if write_csv:
        csv_path, summary_path = next_run_paths(size, difficulty)
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

    solver_mode = prompt_choice("\nSelect benchmark solver mode:", ["all", "csp only"])
    if solver_mode is None:
        print("Invalid benchmark solver mode.")
        return
    solver_names = ["csp"] if solver_mode == "csp only" else None

    print()
    write_csv = input("Save benchmark results and summary to CSV? (y/n): ").strip().lower() == "y"
    print()
    return benchmark_dataset(
        dataset_path,
        size,
        write_csv=write_csv,
        solver_names=solver_names,
    )


if __name__ == "__main__":
    benchmark_menu()
