import time

from solvers.metrics import SolverResult


def solve_naive(board: str) -> SolverResult:
    start = time.perf_counter()
    recursive_calls = 0
    assignments = 0
    backtracks = 0

    try:
        cells = [int(x) for x in board.strip()]
        if len(cells) != 81:
            return SolverResult(
                solution=None,
                status="failed",
                runtime_seconds=time.perf_counter() - start,
                backtracks=backtracks,
                assignments=assignments,
                recursive_calls=recursive_calls,
                error="Naive solver only supports 9x9 boards.",
            )
    except ValueError as exc:
        return SolverResult(
            solution=None,
            status="error",
            runtime_seconds=time.perf_counter() - start,
            backtracks=backtracks,
            assignments=assignments,
            recursive_calls=recursive_calls,
            error=str(exc),
        )

    def valid_group(values: list[int]) -> bool:
        seen = set()
        for value in values:
            if value == 0:
                continue
            if not 1 <= value <= 9 or value in seen:
                return False
            seen.add(value)
        return True

    for row in range(9):
        if not valid_group(cells[row * 9 : (row + 1) * 9]):
            return SolverResult(
                solution=None,
                status="failed",
                runtime_seconds=time.perf_counter() - start,
                backtracks=backtracks,
                assignments=assignments,
                recursive_calls=recursive_calls,
                error="Invalid board state.",
            )

    for col in range(9):
        if not valid_group([cells[row * 9 + col] for row in range(9)]):
            return SolverResult(
                solution=None,
                status="failed",
                runtime_seconds=time.perf_counter() - start,
                backtracks=backtracks,
                assignments=assignments,
                recursive_calls=recursive_calls,
                error="Invalid board state.",
            )

    for box_row in range(0, 9, 3):
        for box_col in range(0, 9, 3):
            values = [
                cells[row * 9 + col]
                for row in range(box_row, box_row + 3)
                for col in range(box_col, box_col + 3)
            ]
            if not valid_group(values):
                return SolverResult(
                    solution=None,
                    status="failed",
                    runtime_seconds=time.perf_counter() - start,
                    backtracks=backtracks,
                    assignments=assignments,
                    recursive_calls=recursive_calls,
                    error="Invalid board state.",
                )

    def is_valid(index: int, value: int) -> bool:
        row, col = divmod(index, 9)

        for c in range(9):
            if cells[row * 9 + c] == value:
                return False

        for r in range(9):
            if cells[r * 9 + col] == value:
                return False

        br, bc = (row // 3) * 3, (col // 3) * 3
        for r in range(br, br + 3):
            for c in range(bc, bc + 3):
                if cells[r * 9 + c] == value:
                    return False

        return True

    def backtrack(index: int = 0) -> bool:
        nonlocal recursive_calls, assignments, backtracks
        recursive_calls += 1

        if index == 81:
            return True

        if cells[index] != 0:
            return backtrack(index + 1)

        for value in range(1, 10):
            if is_valid(index, value):
                cells[index] = value
                assignments += 1
                if backtrack(index + 1):
                    return True
                cells[index] = 0
                backtracks += 1

        return False

    solved = backtrack()
    return SolverResult(
        solution=" ".join(map(str, cells)) if solved else None,
        status="solved" if solved else "failed",
        runtime_seconds=time.perf_counter() - start,
        backtracks=backtracks,
        assignments=assignments,
        recursive_calls=recursive_calls,
    )
