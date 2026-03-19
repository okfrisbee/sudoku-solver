from __future__ import annotations

from typing import Iterable

from pysat.card import CardEnc, EncType
from pysat.formula import CNF, IDPool
from pysat.solvers import Solver

from board_utils import parse_board, board_size, format_board


DEFAULT_SOLVER = "cadical153"


def encode_sudoku_cnf(board: str | Iterable[int]) -> tuple[CNF, IDPool, int]:
    """Encode an NxN Sudoku into CNF.

    This version supports boards such as 4x4, 9x9, 16x16, 25x25, and 100x100
    as long as sqrt(N) is an integer.

    Uses sequential-counter cardinality constraints instead of pairwise
    at-most-one clauses so the SAT model stays much smaller on large boards.
    """
    values = parse_board(board)
    n, box = board_size(values)

    cnf = CNF()
    vpool = IDPool()

    def var(r: int, c: int, value: int) -> int:
        return vpool.id(("x", r, c, value))

    def exactly_one(lits: list[int]) -> None:
        enc = CardEnc.equals(
            lits=lits,
            bound=1,
            vpool=vpool,
            encoding=EncType.seqcounter,
        )
        cnf.extend(enc.clauses)

    # Each cell gets exactly one value.
    for r in range(n):
        for c in range(n):
            exactly_one([var(r, c, value) for value in range(1, n + 1)])

    # Each row contains each value exactly once.
    for r in range(n):
        for value in range(1, n + 1):
            exactly_one([var(r, c, value) for c in range(n)])

    # Each column contains each value exactly once.
    for c in range(n):
        for value in range(1, n + 1):
            exactly_one([var(r, c, value) for r in range(n)])

    # Each box contains each value exactly once.
    for br in range(0, n, box):
        for bc in range(0, n, box):
            for value in range(1, n + 1):
                exactly_one(
                    [
                        var(r, c, value)
                        for r in range(br, br + box)
                        for c in range(bc, bc + box)
                    ]
                )

    # Givens.
    for index, given in enumerate(values):
        if given != 0:
            r, c = divmod(index, n)
            cnf.append([var(r, c, given)])

    return cnf, vpool, n


def solve_sudoku(board: str | Iterable[int], solver_name: str = DEFAULT_SOLVER) -> str:
    """Solve an NxN Sudoku via SAT.

    Returns a whitespace-separated solution string.
    Raises ValueError if UNSAT.
    """
    cnf, vpool, n = encode_sudoku_cnf(board)

    def var(r: int, c: int, value: int) -> int:
        return vpool.id(("x", r, c, value))

    with Solver(name=solver_name, bootstrap_with=cnf) as solver:
        if not solver.solve():
            raise ValueError("Sudoku is UNSAT (no solution).")
        model = solver.get_model()

    true_vars = {lit for lit in model if lit > 0}

    solved: list[int] = []
    for r in range(n):
        for c in range(n):
            found = None
            for value in range(1, n + 1):
                if var(r, c, value) in true_vars:
                    found = value
                    break
            if found is None:
                raise RuntimeError(f"Model missing assignment for cell ({r}, {c})")
            solved.append(found)

    return format_board(solved)
