from z3 import Int, Solver, Distinct, And, sat

from board_utils import parse_board, board_size, format_board


def solve_smt(board: str | list[int]) -> str | None:
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

    if solver.check() != sat:
        return None

    model = solver.model()
    solved = [model[cells[r][c]].as_long() for r in range(n) for c in range(n)]
    return format_board(solved)
