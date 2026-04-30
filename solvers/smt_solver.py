import time

from z3 import Int, Solver, Distinct, And, sat

from board_utils import parse_board, board_size, format_board
from solvers.metrics import SolverResult


def solve_smt(board: str | list[int]) -> SolverResult:
    start = time.perf_counter()
    setup_seconds = None
    solve_seconds = None

    try:
        setup_start = time.perf_counter()
        values = parse_board(board)
        n, box = board_size(values)

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

        for i, v in enumerate(values):
            if v != 0:
                r, c = divmod(i, n)
                solver.add(cells[r][c] == v)

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
