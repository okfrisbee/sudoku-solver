from __future__ import annotations

from itertools import combinations
from typing import List, Tuple, Optional

from pysat.formula import CNF
from pysat.solvers import Solver


# ---------------------------
# Variable mapping (DIMACS)
# var(r,c,d) in 1..729
# ---------------------------
def var_id(r: int, c: int, d: int) -> int:
    """1-indexed r,c,d in {1..9} -> DIMACS var id in {1..729}."""
    return 81 * (r - 1) + 9 * (c - 1) + d


def parse_board(board: str) -> List[Optional[int]]:
    """
    Parse a Sudoku board string into a list of 81 entries.
    Accepted:
      - digits '1'..'9' as givens
      - '.' or '0' as empty
    Ignores whitespace/newlines.
    """
    s = "".join(ch for ch in board if not ch.isspace())
    if len(s) != 81:
        raise ValueError(f"Expected 81 characters (excluding whitespace), got {len(s)}")
    out: List[Optional[int]] = []
    for ch in s:
        if ch in ".0":
            out.append(None)
        elif "1" <= ch <= "9":
            out.append(int(ch))
        else:
            raise ValueError(f"Invalid character in board: {ch!r}")
    return out


def encode_sudoku_cnf(board: str) -> CNF:
    """
    Encode a 9x9 Sudoku into CNF using:
      - x_{r,c,d} means cell (r,c) has digit d
      - exactly-one per cell
      - exactly-one per row/col/block per digit
      - unit clauses for givens
    """
    givens = parse_board(board)
    cnf = CNF()

    digits = range(1, 10)
    rows = range(1, 10)
    cols = range(1, 10)

    # --- Cell constraints: exactly one digit per cell ---
    for r in rows:
        for c in cols:
            # At least one digit
            cnf.append([var_id(r, c, d) for d in digits])
            # At most one digit (pairwise)
            for d, e in combinations(digits, 2):
                cnf.append([-var_id(r, c, d), -var_id(r, c, e)])

    # --- Row constraints: each digit appears exactly once per row ---
    for r in rows:
        for d in digits:
            # At least one column
            cnf.append([var_id(r, c, d) for c in cols])
            # At most one column (pairwise)
            for c1, c2 in combinations(cols, 2):
                cnf.append([-var_id(r, c1, d), -var_id(r, c2, d)])

    # --- Column constraints: each digit appears exactly once per column ---
    for c in cols:
        for d in digits:
            # At least one row
            cnf.append([var_id(r, c, d) for r in rows])
            # At most one row (pairwise)
            for r1, r2 in combinations(rows, 2):
                cnf.append([-var_id(r1, c, d), -var_id(r2, c, d)])

    # --- Block constraints: each digit appears exactly once per 3x3 block ---
    for br in (1, 4, 7):
        for bc in (1, 4, 7):
            block_cells: List[Tuple[int, int]] = [
                (r, c) for r in range(br, br + 3) for c in range(bc, bc + 3)
            ]
            for d in digits:
                # At least one cell in block has digit d
                cnf.append([var_id(r, c, d) for (r, c) in block_cells])
                # At most one cell in block has digit d (pairwise)
                for (r1, c1), (r2, c2) in combinations(block_cells, 2):
                    cnf.append([-var_id(r1, c1, d), -var_id(r2, c2, d)])

    # --- Givens (unit clauses) ---
    for idx, val in enumerate(givens):
        if val is None:
            continue
        r = idx // 9 + 1
        c = idx % 9 + 1
        cnf.append([var_id(r, c, val)])

    return cnf


def solve_sudoku(board: str, solver_name: str = "glucose3") -> str:
    """
    Solve Sudoku via SAT and return solved 81-char string of digits.
    Raises ValueError if UNSAT.
    """
    cnf = encode_sudoku_cnf(board)

    with Solver(name=solver_name, bootstrap_with=cnf) as s:
        sat = s.solve()
        if not sat:
            raise ValueError("Sudoku is UNSAT (no solution).")
        model = s.get_model()

    # Decode model: pick the true digit var for each cell
    true_vars = set(lit for lit in model if lit > 0)

    out_digits: List[str] = []
    for r in range(1, 10):
        for c in range(1, 10):
            found = None
            for d in range(1, 10):
                if var_id(r, c, d) in true_vars:
                    found = d
                    break
            if found is None:
                raise RuntimeError(f"Model missing assignment for cell ({r},{c})")
            out_digits.append(str(found))

    return "".join(out_digits)


# ---------------------------
# Example usage
# ---------------------------
if __name__ == "__main__":
    puzzle = (
        "53..7...."
        "6..195..."
        ".98....6."
        "8...6...3"
        "4..8.3..1"
        "7...2...6"
        ".6....28."
        "...419..5"
        "....8..79"
    )
    solution = solve_sudoku(puzzle)
    print(solution)
