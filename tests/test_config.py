from pathlib import Path
import tempfile
import unittest

from config import load_config
from tests.config_helpers import write_config


class ConfigTests(unittest.TestCase):
    def test_load_config_reads_valid_toml(self):
        with tempfile.TemporaryDirectory() as root:
            config_path = write_config(
                root,
                datasets_dir=Path(root) / "datasets",
                benchmark_results_dir=Path(root) / "results",
                solver_timeout_seconds=12.5,
            )

            config = load_config(config_path)

        self.assertEqual(config["paths"]["datasets_dir"], str(Path(root) / "datasets"))
        self.assertEqual(
            config["paths"]["benchmark_results_dir"],
            str(Path(root) / "results"),
        )
        self.assertEqual(
            config["generation"]["clue_percent_ranges"]["easy"],
            (0.75, 0.85),
        )
        self.assertEqual(config["benchmark"]["solver_timeout_seconds"], 12.5)

    def test_load_config_rejects_missing_required_section(self):
        with tempfile.TemporaryDirectory() as root:
            config_path = Path(root) / "config.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[paths]",
                        'datasets_dir = "data/datasets"',
                        'benchmark_results_dir = "data/results"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "generation"):
                load_config(config_path)

    def test_load_config_rejects_invalid_clue_range(self):
        with tempfile.TemporaryDirectory() as root:
            config_path = write_config(
                root,
                datasets_dir=Path(root) / "datasets",
                benchmark_results_dir=Path(root) / "results",
                clue_percent_ranges={"easy": (0.9, 0.7)},
            )

            with self.assertRaisesRegex(ValueError, "easy"):
                load_config(config_path)

    def test_load_config_rejects_non_positive_timeout(self):
        with tempfile.TemporaryDirectory() as root:
            config_path = write_config(
                root,
                datasets_dir=Path(root) / "datasets",
                benchmark_results_dir=Path(root) / "results",
                solver_timeout_seconds=0,
            )

            with self.assertRaisesRegex(ValueError, "solver_timeout_seconds"):
                load_config(config_path)

    def test_load_config_rejects_missing_file(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                load_config(Path(root) / "config.toml")


if __name__ == "__main__":
    unittest.main()
