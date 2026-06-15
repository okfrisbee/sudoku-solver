from dataclasses import dataclass
import time
from typing import Literal

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
