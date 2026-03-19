def solve_naive(board: str) -> str | None:
    cells = [int(x) for x in board]

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
        if index == 81:
            return True

        if cells[index] != 0:
            return backtrack(index + 1)

        for value in range(1, 10):
            if is_valid(index, value):
                cells[index] = value
                if backtrack(index + 1):
                    return True
                cells[index] = 0

        return False

    return "".join(map(str, cells)) if backtrack() else None
