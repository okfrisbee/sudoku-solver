import time

from z3 import sat

from board_utils import format_board
from benchmark.generation import build_z3_sudoku_solver
from solvers.metrics import SolverResult


def solve_smt(board: str | list[int]) -> SolverResult:
    start = time.perf_counter()
    setup_seconds = None
    solve_seconds = None

    try:
        setup_start = time.perf_counter()
        solver, cells, _values, n, _box = build_z3_sudoku_solver(board)
        setup_seconds = time.perf_counter() - setup_start

        solve_start = time.perf_counter()
        check_result = solver.check()
        solve_seconds = time.perf_counter() - solve_start

        if check_result != sat:
            return SolverResult(
                solution=None,
                status="failed",
                runtime_seconds=time.perf_counter() - start,
                setup_seconds=setup_seconds,
                solve_seconds=solve_seconds,
                error="Sudoku is UNSAT.",
            )

        model = solver.model()
        solved = [model[cells[r][c]].as_long() for r in range(n) for c in range(n)]
        return SolverResult(
            solution=format_board(solved),
            status="solved",
            runtime_seconds=time.perf_counter() - start,
            setup_seconds=setup_seconds,
            solve_seconds=solve_seconds,
        )
    except ValueError as exc:
        return SolverResult(
            solution=None,
            status="failed",
            runtime_seconds=time.perf_counter() - start,
            setup_seconds=setup_seconds,
            solve_seconds=solve_seconds,
            error=str(exc),
        )
    except Exception as exc:
        return SolverResult(
            solution=None,
            status="error",
            runtime_seconds=time.perf_counter() - start,
            setup_seconds=setup_seconds,
            solve_seconds=solve_seconds,
            error=str(exc),
        )
