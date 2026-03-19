# dlx_solver.py

from __future__ import annotations


class Node:
    def __init__(self):
        self.left: Node = self
        self.right: Node = self
        self.up: Node = self
        self.down: Node = self
        self.column: ColumnNode | None = None
        self.row_data: tuple[int, int, int] | None = None  # (r, c, n)


class ColumnNode(Node):
    def __init__(self, name: str):
        super().__init__()
        self.size = 0
        self.name = name
        self.column = self


class DancingLinks:
    def __init__(self, column_names: list[str]):
        self.header = ColumnNode("header")
        self.columns: list[ColumnNode] = []

        prev = self.header
        for name in column_names:
            col = ColumnNode(name)
            self.columns.append(col)

            col.left = prev
            col.right = self.header
            prev.right = col
            self.header.left = col

            prev = col

        self.solution: list[Node] = []

    def add_row(self, row_data: tuple[int, int, int], col_indices: list[int]):
        first: Node | None = None
        prev: Node | None = None

        for idx in col_indices:
            col = self.columns[idx]
            node = Node()
            node.column = col
            node.row_data = row_data

            # Insert into column (at the bottom)
            node.down = col
            node.up = col.up
            col.up.down = node
            col.up = node
            col.size += 1

            # Insert into row (circular doubly linked)
            if first is None:
                first = node
                prev = node
            else:
                node.left = prev
                node.right = first
                prev.right = node
                first.left = node
                prev = node

    def cover(self, col: ColumnNode):
        col.right.left = col.left
        col.left.right = col.right

        row = col.down
        while row != col:
            node = row.right
            while node != row:
                node.down.up = node.up
                node.up.down = node.down
                node.column.size -= 1
                node = node.right
            row = row.down

    def uncover(self, col: ColumnNode):
        row = col.up
        while row != col:
            node = row.left
            while node != row:
                node.column.size += 1
                node.down.up = node
                node.up.down = node
                node = node.left
            row = row.up

        col.right.left = col
        col.left.right = col

    def choose_column(self) -> ColumnNode | None:
        col = self.header.right
        if col == self.header:
            return None

        best = col
        smallest = col.size

        cur = col.right
        while cur != self.header:
            if cur.size < smallest:
                best = cur
                smallest = cur.size
            cur = cur.right

        return best

    def search(self) -> bool:
        if self.header.right == self.header:
            return True

        col = self.choose_column()
        if col is None or col.size == 0:
            return False

        self.cover(col)

        row = col.down
        while row != col:
            self.solution.append(row)

            node = row.right
            while node != row:
                self.cover(node.column)
                node = node.right

            if self.search():
                return True

            self.solution.pop()
            node = row.left
            while node != row:
                self.uncover(node.column)
                node = node.left

            row = row.down

        self.uncover(col)
        return False


def sudoku_exact_cover_columns() -> list[str]:
    cols = []

    # 1. Cell constraint: each cell gets one number
    for r in range(9):
        for c in range(9):
            cols.append(f"cell-{r}-{c}")

    # 2. Row constraint: each row has each number once
    for r in range(9):
        for n in range(1, 10):
            cols.append(f"row-{r}-{n}")

    # 3. Column constraint: each column has each number once
    for c in range(9):
        for n in range(1, 10):
            cols.append(f"col-{c}-{n}")

    # 4. Box constraint: each 3x3 box has each number once
    for b in range(9):
        for n in range(1, 10):
            cols.append(f"box-{b}-{n}")

    return cols


def box_index(r: int, c: int) -> int:
    return (r // 3) * 3 + (c // 3)


def candidate_to_columns(r: int, c: int, n: int) -> list[int]:
    # Offsets
    cell_offset = 0
    row_offset = 81
    col_offset = 162
    box_offset = 243

    return [
        cell_offset + (r * 9 + c),
        row_offset + (r * 9 + (n - 1)),
        col_offset + (c * 9 + (n - 1)),
        box_offset + (box_index(r, c) * 9 + (n - 1)),
    ]


def build_dlx(board: str) -> DancingLinks | None:
    if len(board) != 81 or not board.isdigit():
        raise ValueError("Board must be an 81-character digit string")

    dlx = DancingLinks(sudoku_exact_cover_columns())

    # Validate givens while building rows
    for r in range(9):
        for c in range(9):
            ch = board[r * 9 + c]

            if ch == "0":
                for n in range(1, 10):
                    dlx.add_row((r, c, n), candidate_to_columns(r, c, n))
            else:
                n = int(ch)
                dlx.add_row((r, c, n), candidate_to_columns(r, c, n))

    return dlx


def solve_dlx(board: str) -> str | None:
    try:
        dlx = build_dlx(board)
    except ValueError:
        return None

    # Pre-cover givens by selecting matching rows
    givens = []
    for r in range(9):
        for c in range(9):
            ch = board[r * 9 + c]
            if ch != "0":
                givens.append((r, c, int(ch)))

    # For each given, locate the corresponding row in the exact-cover structure
    for given in givens:
        target_node = None

        # Find the cell constraint column for this (r, c)
        r, c, n = given
        cell_col_idx = r * 9 + c
        col = dlx.columns[cell_col_idx]

        row = col.down
        while row != col:
            if row.row_data == given:
                target_node = row
                break
            row = row.down

        if target_node is None:
            return None

        dlx.solution.append(target_node)

        node = target_node
        while True:
            dlx.cover(node.column)
            node = node.right
            if node == target_node:
                break

    if not dlx.search():
        return None

    result = ["0"] * 81
    for row_node in dlx.solution:
        r, c, n = row_node.row_data
        result[r * 9 + c] = str(n)

    solved = "".join(result)

    # Final sanity check
    if "0" in solved:
        return None

    return solved