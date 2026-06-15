import time

from board_utils import board_size, format_board, parse_board
from solvers.metrics import SolverResult


def solve_naive(board: str | list[int]) -> SolverResult:
    start = time.perf_counter()
    recursive_calls = 0
    assignments = 0
    backtracks = 0

    def failed(error: str) -> SolverResult:
        return SolverResult(
            solution=None,
            status="failed",
            runtime_seconds=time.perf_counter() - start,
            backtracks=backtracks,
            assignments=assignments,
            recursive_calls=recursive_calls,
            error=error,
        )

    try:
        cells = parse_board(board)
        n, box = board_size(cells)
        if n <= 0:
            return failed("Board must contain at least one cell.")
    except ValueError as exc:
        return failed(str(exc))

    def valid_group(values: list[int]) -> bool:
        seen = set()
        for value in values:
            if value == 0:
                continue
            if value in seen:
                return False
            seen.add(value)
        return True

    for row in range(n):
        if not valid_group(cells[row * n : (row + 1) * n]):
            return failed("Invalid board state.")

    for col in range(n):
        if not valid_group([cells[row * n + col] for row in range(n)]):
            return failed("Invalid board state.")

    for box_row in range(0, n, box):
        for box_col in range(0, n, box):
            values = [
                cells[row * n + col]
                for row in range(box_row, box_row + box)
                for col in range(box_col, box_col + box)
            ]
            if not valid_group(values):
                return failed("Invalid board state.")

    def is_valid(index: int, value: int) -> bool:
        row, col = divmod(index, n)

        for c in range(n):
            if cells[row * n + c] == value:
                return False

        for r in range(n):
            if cells[r * n + col] == value:
                return False

        br, bc = (row // box) * box, (col // box) * box
        for r in range(br, br + box):
            for c in range(bc, bc + box):
                if cells[r * n + c] == value:
                    return False

        return True

    def backtrack(index: int = 0) -> bool:
        nonlocal recursive_calls, assignments, backtracks
        recursive_calls += 1

        if index == len(cells):
            return True

        if cells[index] != 0:
            return backtrack(index + 1)

        for value in range(1, n + 1):
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
        solution=format_board(cells) if solved else None,
        status="solved" if solved else "failed",
        runtime_seconds=time.perf_counter() - start,
        backtracks=backtracks,
        assignments=assignments,
        recursive_calls=recursive_calls,
    )
