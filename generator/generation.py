from dataclasses import dataclass
import json
from pathlib import Path
import random
import re
import time
from typing import Any

from board_utils import format_board, parse_board, validate_size
from cli_helpers import prompt_choice, prompt_positive_int, prompt_size
from config import load_config
from .verification import VerificationResult, verify_puzzle


DATASETS_DIR = load_config()["paths"]["datasets_dir"]
DIFFICULTY_PERCENT_RANGES = load_config()["generation"]["clue_percent_ranges"]
DIFFICULTIES = tuple(DIFFICULTY_PERCENT_RANGES) + ("mixed",)
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


@dataclass
class GeneratedPuzzle:
    puzzle: str
    solution: str
    size: int
    box_size: int
    target_clues: int
    actual_clues: int
    verification: VerificationResult


def _difficulty_percent_ranges() -> dict[str, tuple[float, float]]:
    return load_config()["generation"]["clue_percent_ranges"]


def _difficulties() -> tuple[str, ...]:
    return tuple(_difficulty_percent_ranges()) + ("mixed",)


def generate_pattern_solution(size: int = 9, seed: int | None = None) -> str:
    n, box = validate_size(size)
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
    n, box = validate_size(size)

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
        verification = verify_puzzle(puzzle_values, mode="solvable")
    else:
        verification = VerificationResult(
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


def random_clue_percent(difficulty: str, rng: random.Random) -> float:
    ranges = _difficulty_percent_ranges()
    if difficulty not in ranges:
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    low, high = ranges[difficulty]
    return rng.uniform(low, high)


def clue_count(size: int, difficulty: str, rng: random.Random) -> tuple[int, float]:
    clue_percent = random_clue_percent(difficulty, rng)
    return round(size * size * clue_percent), clue_percent


def expand_difficulties(difficulty: str, count: int) -> list[str]:
    ranges = _difficulty_percent_ranges()
    if difficulty not in _difficulties():
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    if count <= 0:
        raise ValueError("Count must be positive")
    if difficulty != "mixed":
        return [difficulty] * count

    base, remainder = divmod(count, len(ranges))
    expanded: list[str] = []
    for name in ranges:
        expanded.extend([name] * (base + (1 if remainder > 0 else 0)))
        remainder -= 1
    return expanded


def dataset_path(
    size: int,
    difficulty: str,
    count: int,
) -> Path:
    validate_size(size)
    if difficulty not in _difficulties():
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    if count < 0:
        raise ValueError("Count cannot be negative")
    return Path(load_config()["paths"]["datasets_dir"]) / f"{size}x{size}_{difficulty}_{count}.jsonl"


def list_datasets(size: int | None = None) -> list[Path]:
    if size is not None:
        validate_size(size)
    directory = Path(load_config()["paths"]["datasets_dir"])
    if not directory.exists():
        return []
    pattern = f"{size}x{size}_*.jsonl" if size is not None else "*.jsonl"
    return sorted(directory.glob(pattern))


def dataset_size_from_path(path: str | Path) -> int:
    match = re.match(r"^(\d+)x\1_", Path(path).name)
    if not match:
        raise ValueError(f"Cannot determine dataset size from filename: {path}")
    return int(match.group(1))


def write_dataset_records(
    records: list[dict[str, Any]],
    size: int,
    difficulty: str,
) -> Path:
    validate_size(size)
    directory = Path(load_config()["paths"]["datasets_dir"])
    directory.mkdir(parents=True, exist_ok=True)
    if difficulty not in _difficulties():
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    path = dataset_path(size, difficulty, len(records))

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
    verify: bool = False,
) -> list[dict[str, Any]]:
    validate_size(size)
    rng = random.Random(seed)
    records = []

    for index, actual_difficulty in enumerate(expand_difficulties(difficulty, count), start=1):
        puzzle_seed = rng.randrange(2**63)
        target_clues, clue_percent = clue_count(size, actual_difficulty, rng)

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
        verification_mode = generated.verification.mode
        unique = False

        records.append(
            {
                "id": index,
                "size": size,
                "difficulty": actual_difficulty,
                "clue_percent": clue_percent,
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
    seed: int | None = None,
) -> Path:
    records = generate_dataset_records(size, difficulty, count, seed=seed, verify=False)
    return write_dataset_records(records, size, difficulty)


def prompt_difficulty():
    selected = prompt_choice(
        "\nSelect difficulty:",
        list(_difficulties()),
    )
    if selected is None:
        print("Invalid difficulty.")
    return selected


def select_dataset(size: int | None = None):
    datasets = list_datasets(size)
    if not datasets:
        size_label = f" for {size}x{size}" if size is not None else ""
        print(f"\nNo datasets found{size_label}. Generate a dataset first.")
        return None

    options = [path.name for path in datasets]
    selected = prompt_choice("\nAvailable datasets:", options)
    if selected is None:
        print("Invalid dataset.")
        return None

    return datasets[options.index(selected)]


def generate_dataset_menu():
    size = prompt_size()
    if size is None:
        return

    difficulty = prompt_difficulty()
    if difficulty is None:
        return

    count = prompt_positive_int("\nHow many puzzles should be generated?")
    if count is None:
        return

    print(f"\nGenerating {count} {size}x{size} {difficulty} puzzle(s)...")
    start = time.perf_counter()
    try:
        path = generate_dataset(size, difficulty, count)
    except Exception as exc:
        print(f"Dataset generation failed: {exc}")
        return

    print(f"Dataset written to: {path}")
    print(f"Generation time: {time.perf_counter() - start:.4f}s")
