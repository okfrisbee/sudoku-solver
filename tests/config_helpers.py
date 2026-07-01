from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


def write_config(
    root: str | Path,
    datasets_dir: str | Path,
    benchmark_results_dir: str | Path,
    solver_timeout_seconds: float = 60,
    clue_percent_ranges: dict[str, tuple[float, float]] | None = None,
) -> Path:
    ranges = clue_percent_ranges or {
        "easy": (0.75, 0.85),
        "medium": (0.50, 0.60),
        "hard": (0.25, 0.35),
    }
    path = Path(root) / "config.toml"
    range_lines = "\n".join(
        f"{name} = [{low}, {high}]"
        for name, (low, high) in ranges.items()
    )
    path.write_text(
        "\n".join(
            [
                "[paths]",
                f'datasets_dir = "{Path(datasets_dir)}"',
                f'benchmark_results_dir = "{Path(benchmark_results_dir)}"',
                "",
                "[generation.clue_percent_ranges]",
                range_lines,
                "",
                "[benchmark]",
                f"solver_timeout_seconds = {solver_timeout_seconds}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


@contextmanager
def temporary_config(
    root: str | Path,
    datasets_dir: str | Path | None = None,
    benchmark_results_dir: str | Path | None = None,
    solver_timeout_seconds: float = 60,
    clue_percent_ranges: dict[str, tuple[float, float]] | None = None,
) -> Iterator[Path]:
    root_path = Path(root)
    config_path = write_config(
        root_path,
        datasets_dir or root_path / "datasets",
        benchmark_results_dir or root_path / "results",
        solver_timeout_seconds=solver_timeout_seconds,
        clue_percent_ranges=clue_percent_ranges,
    )
    with patch("config.CONFIG_PATH", config_path):
        yield config_path
