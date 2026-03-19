from math import isqrt


def parse_board(board: str | list[int]) -> list[int]:
    if isinstance(board, str):
        board = board.strip()
        if not board:
            return []
        if any(ch.isspace() for ch in board):
            values = [int(tok) for tok in board.split()]
        else:
            values = [int(ch) for ch in board]  # legacy 9x9 support
    else:
        values = [int(x) for x in board]

    size = isqrt(len(values))
    if size * size != len(values):
        raise ValueError("Board length must be a perfect square")

    box = isqrt(size)
    if box * box != size:
        raise ValueError("Board width must be a perfect square")

    for v in values:
        if not (0 <= v <= size):
            raise ValueError(f"Cell value {v} out of range 0..{size}")

    return values


def print_board(board: str):
    values = parse_board(board)
    size, width = board_size(values)

    for r in range(size):
        row = values[r * size : (r + 1) * size]
        print(" ".join(f"{value:0{width}d}" for value in row))


def board_size(values: list[int]) -> tuple[int, int]:
    n = isqrt(len(values))
    b = isqrt(n)
    return n, b


def format_board(values: list[int]) -> str:
    return " ".join(map(str, values))
