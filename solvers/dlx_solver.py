from __future__ import annotations

from typing import Iterable

from board_utils import parse_board, board_size, format_board


class Node:
    __slots__ = ("left", "right", "up", "down", "column", "row_data")

    def __init__(self):
        self.left: Node = self
        self.right: Node = self
        self.up: Node = self
        self.down: Node = self
        self.column: ColumnNode | None = None
        self.row_data: tuple[int, int, int] | None = None


class ColumnNode(Node):
    __slots__ = ("size", "name")

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

    def add_row(self, row_data: tuple[int, int, int], col_indices: list[int]) -> None:
        first: Node | None = None
        prev: Node | None = None

        for idx in col_indices:
            col = self.columns[idx]
            node = Node()
            node.column = col
            node.row_data = row_data

            node.down = col
            node.up = col.up
            col.up.down = node
            col.up = node
            col.size += 1

            if first is None:
                first = node
                prev = node
            else:
                node.left = prev
                node.right = first
                prev.right = node
                first.left = node
                prev = node

    def cover(self, col: ColumnNode) -> None:
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

    def uncover(self, col: ColumnNode) -> None:
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


def sudoku_exact_cover_columns(n: int) -> list[str]:
    cols: list[str] = []

    for r in range(n):
        for c in range(n):
            cols.append(f"cell-{r}-{c}")

    for r in range(n):
        for value in range(1, n + 1):
            cols.append(f"row-{r}-{value}")

    for c in range(n):
        for value in range(1, n + 1):
            cols.append(f"col-{c}-{value}")

    for b in range(n):
        for value in range(1, n + 1):
            cols.append(f"box-{b}-{value}")

    return cols


def box_index(r: int, c: int, box: int) -> int:
    return (r // box) * box + (c // box)


def candidate_to_columns(r: int, c: int, value: int, n: int, box: int) -> list[int]:
    cell_offset = 0
    row_offset = n * n
    col_offset = 2 * n * n
    box_offset = 3 * n * n

    return [
        cell_offset + (r * n + c),
        row_offset + (r * n + (value - 1)),
        col_offset + (c * n + (value - 1)),
        box_offset + (box_index(r, c, box) * n + (value - 1)),
    ]


def build_dlx(board: str | Iterable[int]) -> tuple[DancingLinks, list[int], int, int]:
    values = parse_board(board)
    n, box = board_size(values)

    dlx = DancingLinks(sudoku_exact_cover_columns(n))

    for r in range(n):
        for c in range(n):
            current = values[r * n + c]
            if current == 0:
                for value in range(1, n + 1):
                    dlx.add_row(
                        (r, c, value),
                        candidate_to_columns(r, c, value, n, box),
                    )
            else:
                dlx.add_row(
                    (r, c, current),
                    candidate_to_columns(r, c, current, n, box),
                )

    return dlx, values, n, box


def solve_dlx(board: str | Iterable[int]) -> str | None:
    try:
        dlx, values, n, _box = build_dlx(board)
    except ValueError:
        return None

    givens: list[tuple[int, int, int]] = []
    for r in range(n):
        for c in range(n):
            value = values[r * n + c]
            if value != 0:
                givens.append((r, c, value))

    for given in givens:
        r, c, value = given
        cell_col_idx = r * n + c
        col = dlx.columns[cell_col_idx]

        target_node = None
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

    result = [0] * (n * n)
    for row_node in dlx.solution:
        r, c, value = row_node.row_data
        result[r * n + c] = value

    if any(value == 0 for value in result):
        return None

    return format_board(result)
