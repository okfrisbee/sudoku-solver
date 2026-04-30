from __future__ import annotations

import json
from pathlib import Path
import random
from typing import Any

from board_utils import parse_board
from sudoku_generator import generate_puzzle


DATASETS_DIR = "datasets"
SUPPORTED_SIZES = (4, 9, 16, 25, 36, 49, 64, 81, 100)
DIFFICULTY_PERCENTS = {
    "easy": 0.60,
    "medium": 0.45,
    "hard": 0.30,
}
DIFFICULTIES = tuple(DIFFICULTY_PERCENTS) + ("mixed",)
REQUIRED_RECORD_FIELDS = {
    "id",
    "size",
    "difficulty",
    "clue_percent",
    "target_clues",
    "actual_clues",
    "puzzle",
    "solution",
    "seed",
    "verification_mode",
    "unique",
}


def validate_size(size: int) -> int:
    if size not in SUPPORTED_SIZES:
        raise ValueError(f"Unsupported size: {size}")
    return size


def clue_count(size: int, difficulty: str) -> int:
    validate_size(size)
    if difficulty not in DIFFICULTY_PERCENTS:
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    return round(size * size * DIFFICULTY_PERCENTS[difficulty])


def expand_difficulties(difficulty: str, count: int) -> list[str]:
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    if count <= 0:
        raise ValueError("Count must be positive")
    if difficulty != "mixed":
        return [difficulty] * count

    base, remainder = divmod(count, len(DIFFICULTY_PERCENTS))
    expanded: list[str] = []
    for name in DIFFICULTY_PERCENTS:
        expanded.extend([name] * (base + (1 if remainder > 0 else 0)))
        remainder -= 1
    return expanded


def dataset_directory(size: int, root: str | Path = DATASETS_DIR) -> Path:
    validate_size(size)
    return Path(root) / f"{size}x{size}"


def dataset_filename(
    size: int,
    difficulty: str,
    count: int,
    index: int,
) -> str:
    validate_size(size)
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    if count <= 0:
        raise ValueError("Count must be positive")
    if index < 0:
        raise ValueError("Index must be non-negative")
    return f"{size}x{size}_{difficulty}_{count}_{index}.jsonl"


def next_dataset_path(
    size: int,
    difficulty: str,
    count: int,
    root: str | Path = DATASETS_DIR,
) -> Path:
    directory = dataset_directory(size, root)
    index = 0
    while True:
        path = directory / dataset_filename(size, difficulty, count, index)
        if not path.exists():
            return path
        index += 1


def list_datasets(size: int, root: str | Path = DATASETS_DIR) -> list[Path]:
    directory = dataset_directory(size, root)
    if not directory.exists():
        return []
    return sorted(directory.glob("*.jsonl"))


def write_dataset_records(
    records: list[dict[str, Any]],
    size: int,
    difficulty: str,
    count: int,
    root: str | Path = DATASETS_DIR,
) -> Path:
    directory = dataset_directory(size, root)
    directory.mkdir(parents=True, exist_ok=True)
    path = next_dataset_path(size, difficulty, count, root=root)

    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, sort_keys=True))
            f.write("\n")

    return path


def read_dataset(path: str | Path, expected_size: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            missing = REQUIRED_RECORD_FIELDS - set(record)
            if missing:
                raise ValueError(
                    f"Record {line_number} is missing fields: {', '.join(sorted(missing))}"
                )
            size = int(record["size"])
            if expected_size is not None and size != expected_size:
                raise ValueError(
                    f"Record {line_number} has size {size}, expected {expected_size}"
                )
            values = parse_board(record["puzzle"])
            if len(values) != size * size:
                raise ValueError(
                    f"Record {line_number} puzzle length does not match size {size}"
                )
            solution_values = parse_board(record["solution"])
            if len(solution_values) != size * size:
                raise ValueError(
                    f"Record {line_number} solution length does not match size {size}"
                )
            records.append(record)
    return records


def generate_dataset_records(
    size: int,
    difficulty: str,
    count: int,
    seed: int | None = None,
    verify: bool = True,
) -> list[dict[str, Any]]:
    validate_size(size)
    rng = random.Random(seed)
    records = []

    for index, actual_difficulty in enumerate(expand_difficulties(difficulty, count), start=1):
        puzzle_seed = rng.randrange(2**63)
        target_clues = clue_count(size, actual_difficulty)

        generated = generate_puzzle(
            size=size,
            clues=target_clues,
            seed=puzzle_seed,
            verify=verify,
        )
        if not generated.verification.valid:
            raise RuntimeError(
                f"Generated puzzle {index} failed verification: "
                f"{generated.verification.error}"
            )
        verification_mode = "solvable"
        unique = False

        records.append(
            {
                "id": index,
                "size": size,
                "difficulty": actual_difficulty,
                "clue_percent": DIFFICULTY_PERCENTS[actual_difficulty],
                "target_clues": target_clues,
                "actual_clues": generated.actual_clues,
                "puzzle": generated.puzzle,
                "solution": generated.solution,
                "seed": puzzle_seed,
                "verification_mode": verification_mode,
                "unique": unique,
            }
        )

    return records


def generate_dataset(
    size: int,
    difficulty: str,
    count: int,
    root: str | Path = DATASETS_DIR,
    seed: int | None = None,
) -> Path:
    records = generate_dataset_records(size, difficulty, count, seed=seed, verify=True)
    return write_dataset_records(records, size, difficulty, count, root=root)
