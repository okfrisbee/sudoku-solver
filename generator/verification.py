from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Literal

from z3 import And, Distinct, Int, Or, Solver, sat

from board_utils import board_size, format_board, parse_board


ValidityMode = Literal["solvable", "unique"]


@dataclass
class VerificationResult:
    valid: bool
    mode: ValidityMode
    solution: str | None
    solution_count: int | None
    runtime_seconds: float
    setup_seconds: float | None = None
    solve_seconds: float | None = None
    error: str | None = None


@dataclass
class DerivedVerificationResult:
    valid: bool
    mode: str
    solution: str | None
    solution_count: int | None
    runtime_seconds: float
    setup_seconds: float | None = None
    solve_seconds: float | None = None
    error: str | None = None


@dataclass
class DatasetVerificationFailure:
    record_number: int
    record_id: Any
    error: str | None


@dataclass
class DatasetVerificationSummary:
    mode: str
    total: int
    valid_count: int
    invalid_count: int
    runtime_seconds: float
    failures: list[DatasetVerificationFailure]


def build_z3_sudoku_solver(
    board: str | list[int],
) -> tuple[Solver, list[list[Int]], list[int], int, int]:
    values = parse_board(board)
    n, box = board_size(values)

    if n <= 0:
        raise ValueError("Board must contain at least one cell")

    solver = Solver()
    cells = [[Int(f"cell_{r}_{c}") for c in range(n)] for r in range(n)]

    for r in range(n):
        for c in range(n):
            solver.add(And(cells[r][c] >= 1, cells[r][c] <= n))

    for r in range(n):
        solver.add(Distinct(cells[r]))

    for c in range(n):
        solver.add(Distinct([cells[r][c] for r in range(n)]))

    for br in range(0, n, box):
        for bc in range(0, n, box):
            solver.add(
                Distinct(
                    [
                        cells[r][c]
                        for r in range(br, br + box)
                        for c in range(bc, bc + box)
                    ]
                )
            )

    for index, value in enumerate(values):
        if value != 0:
            r, c = divmod(index, n)
            solver.add(cells[r][c] == value)

    return solver, cells, values, n, box


def _solution_from_model(cells: list[list[Int]], n: int, model) -> list[int]:
    return [model[cells[r][c]].as_long() for r in range(n) for c in range(n)]


def verify_puzzle(
    board: str | list[int], mode: ValidityMode = "solvable"
) -> VerificationResult:
    start = time.perf_counter()
    setup_seconds = None
    solve_seconds = None

    if mode not in ("solvable", "unique"):
        return VerificationResult(
            valid=False,
            mode=mode,
            solution=None,
            solution_count=0,
            runtime_seconds=time.perf_counter() - start,
            error=f"Unsupported verification mode: {mode}",
        )

    try:
        setup_start = time.perf_counter()
        solver, cells, _values, n, _box = build_z3_sudoku_solver(board)
        setup_seconds = time.perf_counter() - setup_start

        solve_start = time.perf_counter()
        check_result = solver.check()
        if check_result != sat:
            solve_seconds = time.perf_counter() - solve_start
            return VerificationResult(
                valid=False,
                mode=mode,
                solution=None,
                solution_count=0,
                runtime_seconds=time.perf_counter() - start,
                setup_seconds=setup_seconds,
                solve_seconds=solve_seconds,
                error="Sudoku is UNSAT.",
            )

        model = solver.model()
        solved = _solution_from_model(cells, n, model)
        solution = format_board(solved)

        if mode == "solvable":
            solve_seconds = time.perf_counter() - solve_start
            return VerificationResult(
                valid=True,
                mode=mode,
                solution=solution,
                solution_count=1,
                runtime_seconds=time.perf_counter() - start,
                setup_seconds=setup_seconds,
                solve_seconds=solve_seconds,
            )

        solver.add(
            Or(
                [
                    cells[r][c] != solved[r * n + c]
                    for r in range(n)
                    for c in range(n)
                ]
            )
        )
        has_second_solution = solver.check() == sat
        solve_seconds = time.perf_counter() - solve_start

        return VerificationResult(
            valid=not has_second_solution,
            mode=mode,
            solution=solution,
            solution_count=2 if has_second_solution else 1,
            runtime_seconds=time.perf_counter() - start,
            setup_seconds=setup_seconds,
            solve_seconds=solve_seconds,
            error="Sudoku has multiple solutions." if has_second_solution else None,
        )
    except ValueError as exc:
        return VerificationResult(
            valid=False,
            mode=mode,
            solution=None,
            solution_count=0,
            runtime_seconds=time.perf_counter() - start,
            setup_seconds=setup_seconds,
            solve_seconds=solve_seconds,
            error=str(exc),
        )
    except Exception as exc:
        return VerificationResult(
            valid=False,
            mode=mode,
            solution=None,
            solution_count=0,
            runtime_seconds=time.perf_counter() - start,
            setup_seconds=setup_seconds,
            solve_seconds=solve_seconds,
            error=str(exc),
        )


def verify_dataset_records(
    records: list[dict[str, Any]],
    mode: str = "solvable",
    max_failures: int = 10,
) -> DatasetVerificationSummary:
    start = time.perf_counter()
    valid_count = 0
    failures: list[DatasetVerificationFailure] = []

    for record_number, record in enumerate(records, start=1):
        result = verify_puzzle(record["puzzle"], mode=mode)
        if result.valid:
            valid_count += 1
            continue

        if len(failures) < max_failures:
            failures.append(
                DatasetVerificationFailure(
                    record_number=record_number,
                    record_id=record.get("id"),
                    error=result.error,
                )
            )

    return DatasetVerificationSummary(
        mode=mode,
        total=len(records),
        valid_count=valid_count,
        invalid_count=len(records) - valid_count,
        runtime_seconds=time.perf_counter() - start,
        failures=failures,
    )


def verify_dataset(
    path: str | Path,
    expected_size: int | None = None,
    mode: str = "solvable",
    max_failures: int = 10,
) -> DatasetVerificationSummary:
    from .generation import read_dataset

    records = read_dataset(path, expected_size=expected_size)
    return verify_dataset_records(records, mode=mode, max_failures=max_failures)


def verify_dataset_menu():
    from cli_helpers import prompt_choice, prompt_size
    from .generation import select_dataset

    size = prompt_size()
    if size is None:
        return

    dataset_path = select_dataset(size)
    if dataset_path is None:
        return

    mode = prompt_choice("\nSelect verification mode:", ["solvable", "unique"])
    if mode is None:
        print("Invalid verification mode.")
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
