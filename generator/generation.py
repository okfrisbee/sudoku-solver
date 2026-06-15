from dataclasses import dataclass
import json
from pathlib import Path
import random
import time
from typing import TYPE_CHECKING, Any

from board_utils import format_board, parse_board, validate_size
from cli_helpers import prompt_choice, prompt_positive_int, prompt_size

if TYPE_CHECKING:
    from .verification import DerivedVerificationResult, VerificationResult


DATASETS_DIR = "data/datasets"
DIFFICULTY_PERCENT_RANGES = {
    "easy": (0.75, 0.85),
    "medium": (0.50, 0.60),
    "hard": (0.25, 0.35),
}
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
    verification: "VerificationResult | DerivedVerificationResult"


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
        from .verification import verify_puzzle

        verification = verify_puzzle(puzzle_values, mode="solvable")
    else:
        from .verification import DerivedVerificationResult

        verification = DerivedVerificationResult(
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
    if difficulty not in DIFFICULTY_PERCENT_RANGES:
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    low, high = DIFFICULTY_PERCENT_RANGES[difficulty]
    return rng.uniform(low, high)


def clue_count(size: int, difficulty: str, rng: random.Random) -> tuple[int, float]:
    clue_percent = random_clue_percent(difficulty, rng)
    return round(size * size * clue_percent), clue_percent


def expand_difficulties(difficulty: str, count: int) -> list[str]:
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    if count <= 0:
        raise ValueError("Count must be positive")
    if difficulty != "mixed":
        return [difficulty] * count

    base, remainder = divmod(count, len(DIFFICULTY_PERCENT_RANGES))
    expanded: list[str] = []
    for name in DIFFICULTY_PERCENT_RANGES:
        expanded.extend([name] * (base + (1 if remainder > 0 else 0)))
        remainder -= 1
    return expanded


def dataset_directory(size: int, root: str | Path = DATASETS_DIR) -> Path:
    validate_size(size)
    return Path(root) / f"{size}x{size}"


def dataset_path(
    size: int,
    difficulty: str,
    root: str | Path = DATASETS_DIR,
) -> Path:
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    return dataset_directory(size, root) / f"{difficulty}.jsonl"


def list_datasets(size: int, root: str | Path = DATASETS_DIR) -> list[Path]:
    directory = dataset_directory(size, root)
    if not directory.exists():
        return []
    return sorted(directory.glob("*.jsonl"))


def write_dataset_records(
    records: list[dict[str, Any]],
    size: int,
    difficulty: str,
    root: str | Path = DATASETS_DIR,
) -> Path:
    directory = dataset_directory(size, root)
    directory.mkdir(parents=True, exist_ok=True)
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unsupported difficulty: {difficulty}")
    path = directory / f"{difficulty}.jsonl"

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
    root: str | Path = DATASETS_DIR,
    seed: int | None = None,
) -> Path:
    records = generate_dataset_records(size, difficulty, count, seed=seed, verify=False)
    return write_dataset_records(records, size, difficulty, root=root)


ALL_DIFFICULTIES_OPTION = "all difficulties"


def prompt_difficulty():
    selected = prompt_choice(
        "\nSelect difficulty:",
        list(DIFFICULTIES) + [ALL_DIFFICULTIES_OPTION],
    )
    if selected is None:
        print("Invalid difficulty.")
    return selected


def select_dataset(size):
    datasets = list_datasets(size)
    if not datasets:
        print(f"\nNo datasets found for {size}x{size}. Generate a dataset first.")
        return None

    options = [path.name for path in datasets]
    selected = prompt_choice("\nSelect dataset:", options)
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

    count_prompt = "\nHow many puzzles should be generated?"
    if difficulty == ALL_DIFFICULTIES_OPTION:
        count_prompt = "\nHow many puzzles should be generated per difficulty?"

    count = prompt_positive_int(count_prompt)
    if count is None:
        return

    difficulties = (
        list(DIFFICULTY_PERCENT_RANGES)
        if difficulty == ALL_DIFFICULTIES_OPTION
        else [difficulty]
    )
    difficulty_label = (
        "easy, medium, and hard"
        if difficulty == ALL_DIFFICULTIES_OPTION
        else difficulty
    )

    print(f"\nGenerating {count} {size}x{size} {difficulty_label} puzzle(s)...")
    start = time.perf_counter()
    paths = []
    try:
        for selected_difficulty in difficulties:
            paths.append(generate_dataset(size, selected_difficulty, count))
    except Exception as exc:
        print(f"Dataset generation failed: {exc}")
        return

    for path in paths:
        print(f"Dataset written to: {path}")
    print(f"Generation time: {time.perf_counter() - start:.4f}s")

