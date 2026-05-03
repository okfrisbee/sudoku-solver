from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
import random
from typing import TYPE_CHECKING

from board_utils import format_board, parse_board

if TYPE_CHECKING:
    from sudoku_verifier import VerificationResult


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
class GeneratedPuzzle:
    puzzle: str
    solution: str
    size: int
    box_size: int
    target_clues: int
    actual_clues: int
    verification: VerificationResult | DerivedVerificationResult


def _validate_size(size: int) -> tuple[int, int]:
    if size <= 0:
        raise ValueError("Size must be positive")

    box = isqrt(size)
    if box * box != size:
        raise ValueError("Size must have an integer square-root box size")

    return size, box


def generate_pattern_solution(size: int = 9, seed: int | None = None) -> str:
    n, box = _validate_size(size)
    rng = random.Random(seed)

    def pattern(row: int, col: int) -> int:
        return (box * (row % box) + row // box + col) % n

    def shuffled_groups() -> list[int]:
        groups = list(range(box))
        rng.shuffle(groups)
        indexes = []
        for group in groups:
            members = list(range(group * box, (group + 1) * box))
            rng.shuffle(members)
            indexes.extend(members)
        return indexes

    rows = shuffled_groups()
    cols = shuffled_groups()
    digits = list(range(1, n + 1))
    rng.shuffle(digits)

    values = [
        digits[pattern(row, col)]
        for row in rows
        for col in cols
    ]
    return format_board(values)


def generate_puzzle(
    size: int = 9,
    clues: int | None = None,
    seed: int | None = None,
    verify: bool = False,
) -> GeneratedPuzzle:
    n, box = _validate_size(size)

    if clues is None:
        clues = max(n, round(n * n * 0.4))
    if not (0 <= clues <= n * n):
        raise ValueError(f"Clues must be in range 0..{n * n}")

    solution = generate_pattern_solution(n, seed=seed)
    puzzle_values = parse_board(solution)
    indexes = list(range(n * n))
    random.Random(seed).shuffle(indexes)

    for index in indexes[: n * n - clues]:
        puzzle_values[index] = 0

    if verify:
        from sudoku_verifier import verify_puzzle

        verification = verify_puzzle(puzzle_values, mode="solvable")
    else:
        verification = DerivedVerificationResult(
            valid=True,
            mode="derived",
            solution=solution,
            solution_count=None,
            runtime_seconds=0.0,
        )

    return GeneratedPuzzle(
        puzzle=format_board(puzzle_values),
        solution=solution,
        size=n,
        box_size=box,
        target_clues=clues,
        actual_clues=sum(1 for value in puzzle_values if value != 0),
        verification=verification,
    )
