import multiprocessing
from pathlib import Path
import queue
import time

from cli_helpers import prompt_choice, prompt_size, select_dataset
from generator import read_dataset
from .reporting import (
    benchmark_summary_rows,
    csv_row,
    next_benchmark_run_paths,
    print_summary_table,
    write_benchmark_csv,
    write_benchmark_summary_json,
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
            result = solve_with_timeout(
                fn,
                puzzle,
                timeout_seconds=timeout_seconds,
            )
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
    benchmark_result = {
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
        "results_by_solver": results_by_solver,
        "times_by_solver": times_by_solver,
    }

    print("\n-----Results-----")
    print(f"Puzzles Tested: {tested}\n")
    print_summary_table(summary_rows)
    if write_csv:
        csv_path, json_path = next_benchmark_run_paths(size, difficulty)
        csv_file = write_benchmark_csv(csv_rows, csv_path)
        summary_file = write_benchmark_summary_json(
            {
                "dataset": benchmark_result["dataset"],
                "tested": benchmark_result["tested"],
                "solvers": benchmark_result["solvers"],
                "summary_rows": benchmark_result["summary_rows"],
            },
            json_path,
        )
        print(f"\nCSV written to: {csv_file}")
        print(f"JSON summary written to: {summary_file}")

    return benchmark_result


def benchmark_menu():
    size = prompt_size()
    if size is None:
        return

    dataset_path = select_dataset(size)
    if dataset_path is None:
        return

    solver_mode = prompt_choice("\nSelect benchmark solver mode:", ["all", "csp only"])
    if solver_mode is None:
        print("Invalid benchmark solver mode.")
        return
    solver_names = ["csp"] if solver_mode == "csp only" else None

    print()
    write_csv = input("Save benchmark results to CSV and JSON? (y/n): ").strip().lower() == "y"
    print()
    return benchmark_dataset(
        dataset_path,
        size,
        write_csv=write_csv,
        solver_names=solver_names,
    )


if __name__ == "__main__":
    benchmark_menu()
