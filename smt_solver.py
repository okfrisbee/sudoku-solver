from z3 import Int, Solver, Distinct, And, sat


def solve_smt(board: str) -> str | None:
    """
    Solve a Sudoku puzzle using SMT (Z3).
    Input: 81-character string of digits, where 0 means empty.
    Output: solved 81-character string, or None if unsat.
    """
    if len(board) != 81 or not board.isdigit():
        raise ValueError("Board must be an 81-character string of digits.")

    solver = Solver()

    # 9x9 grid of integer variables
    cells = [[Int(f"cell_{r}_{c}") for c in range(9)] for r in range(9)]

    # Each cell is between 1 and 9
    for r in range(9):
        for c in range(9):
            solver.add(And(cells[r][c] >= 1, cells[r][c] <= 9))

    # Rows contain distinct digits
    for r in range(9):
        solver.add(Distinct(cells[r]))

    # Columns contain distinct digits
    for c in range(9):
        solver.add(Distinct([cells[r][c] for r in range(9)]))

    # 3x3 boxes contain distinct digits
    for box_r in range(0, 9, 3):
        for box_c in range(0, 9, 3):
            solver.add(
                Distinct([
                    cells[r][c]
                    for r in range(box_r, box_r + 3)
                    for c in range(box_c, box_c + 3)
                ])
            )

    # Givens
    for i, ch in enumerate(board):
        if ch != "0":
            r, c = divmod(i, 9)
            solver.add(cells[r][c] == int(ch))

    # Solve
    if solver.check() != sat:
        return None

    model = solver.model()
    solved = []
    for r in range(9):
        for c in range(9):
            solved.append(str(model[cells[r][c]].as_long()))

    return "".join(solved)