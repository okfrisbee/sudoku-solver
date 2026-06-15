import contextlib
import io
from pathlib import Path
import random
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from cli_helpers import prompt_size
import generator.verification as verification_module
from generator import (
    DIFFICULTY_PERCENT_RANGES,
    clue_count,
    dataset_path,
    dataset_size_from_path,
    expand_difficulties,
    generation as generation_module,
    generate_dataset_records,
    generate_puzzle,
    list_datasets,
    prompt_difficulty,
    read_dataset,
    verify_dataset_records,
    write_dataset_records,
)


class SudokuDatasetTests(unittest.TestCase):
    def test_clue_count_uses_difficulty_percentage_ranges(self):
        for difficulty, (low, high) in DIFFICULTY_PERCENT_RANGES.items():
            target_clues, clue_percent = clue_count(
                9,
                difficulty,
                random.Random(123),
            )

            self.assertGreaterEqual(clue_percent, low)
            self.assertLessEqual(clue_percent, high)
            self.assertEqual(target_clues, round(9 * 9 * clue_percent))

    def test_mixed_difficulty_distribution_assigns_remainders_in_order(self):
        self.assertEqual(
            expand_difficulties("mixed", 5),
            ["easy", "easy", "medium", "medium", "hard"],
        )

    def test_dataset_generation_is_deterministic_with_seed(self):
        first = generate_dataset_records(9, "easy", 5, seed=123, verify=False)
        second = generate_dataset_records(9, "easy", 5, seed=123, verify=False)

        self.assertEqual(
            [record["clue_percent"] for record in first],
            [record["clue_percent"] for record in second],
        )
        self.assertEqual(
            [record["target_clues"] for record in first],
            [record["target_clues"] for record in second],
        )

    def test_dataset_generation_randomizes_clue_percent_per_puzzle(self):
        records = generate_dataset_records(9, "easy", 5, seed=123, verify=False)

        self.assertGreater(
            len({record["clue_percent"] for record in records}),
            1,
        )

    def test_generated_records_use_difficulty_percentage_ranges(self):
        for difficulty, (low, high) in DIFFICULTY_PERCENT_RANGES.items():
            records = generate_dataset_records(9, difficulty, 5, seed=123, verify=False)

            for record in records:
                self.assertGreaterEqual(record["clue_percent"], low)
                self.assertLessEqual(record["clue_percent"], high)
                self.assertEqual(
                    record["target_clues"],
                    round(record["size"] * record["size"] * record["clue_percent"]),
                )

    def test_dataset_jsonl_roundtrip(self):
        records = generate_dataset_records(36, "hard", 1, seed=123, verify=False)

        with tempfile.TemporaryDirectory() as root:
            path = write_dataset_records(
                records,
                size=36,
                difficulty="hard",
                root=root,
            )
            loaded = read_dataset(path, expected_size=36)

        self.assertEqual(len(loaded), 1)
        self.assertEqual(path.name, "36x36_hard_1.jsonl")
        self.assertEqual(loaded[0]["size"], 36)
        self.assertEqual(loaded[0]["difficulty"], "hard")
        self.assertEqual(loaded[0]["verification_mode"], "derived")
        self.assertFalse(loaded[0]["unique"])

    def test_dataset_reader_rejects_wrong_size(self):
        records = generate_dataset_records(36, "easy", 1, seed=123, verify=False)

        with tempfile.TemporaryDirectory() as root:
            path = write_dataset_records(
                records,
                size=36,
                difficulty="easy",
                root=root,
            )
            with self.assertRaises(ValueError):
                read_dataset(path, expected_size=9)

    def test_dataset_path_uses_stable_size_and_difficulty(self):
        self.assertEqual(
            dataset_path(9, "medium", 100),
            Path("data/datasets") / "9x9_medium_100.jsonl",
        )

    def test_dataset_writer_uses_record_count_in_filename(self):
        first_records = generate_dataset_records(4, "easy", 1, seed=123, verify=False)
        second_records = generate_dataset_records(4, "easy", 2, seed=456, verify=False)

        with tempfile.TemporaryDirectory() as root:
            first = write_dataset_records(first_records, 4, "easy", root=root)
            second = write_dataset_records(second_records, 4, "easy", root=root)
            loaded = read_dataset(second, expected_size=4)

        self.assertNotEqual(first, second)
        self.assertEqual(first.name, "4x4_easy_1.jsonl")
        self.assertEqual(second.name, "4x4_easy_2.jsonl")
        self.assertEqual(len(loaded), 2)

    def test_list_datasets_returns_stable_difficulty_files(self):
        records = generate_dataset_records(4, "easy", 1, seed=123, verify=False)

        with tempfile.TemporaryDirectory() as root:
            easy = write_dataset_records(records, 4, "easy", root=root)
            medium = write_dataset_records(records, 4, "medium", root=root)
            datasets = list_datasets(4, root=root)

        self.assertEqual(datasets, [easy, medium])

    def test_list_datasets_can_return_all_available_datasets(self):
        records = generate_dataset_records(4, "easy", 1, seed=123, verify=False)

        with tempfile.TemporaryDirectory() as root:
            small = write_dataset_records(records, 4, "easy", root=root)
            large = write_dataset_records(records, 9, "medium", root=root)
            datasets = list_datasets(root=root)

        self.assertEqual(datasets, [small, large])

    def test_dataset_size_from_path_uses_dataset_filename(self):
        self.assertEqual(
            dataset_size_from_path("data/datasets/16x16_hard_100.jsonl"),
            16,
        )

    def test_large_dataset_records_have_required_metadata_and_board_lengths(self):
        record = generate_dataset_records(36, "medium", 1, seed=123, verify=False)[0]

        self.assertEqual(
            set(record),
            {
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
            },
        )
        self.assertEqual(len(record["puzzle"].split()), 36 * 36)
        self.assertEqual(len(record["solution"].split()), 36 * 36)


class SudokuGenerationPolicyTests(unittest.TestCase):
    def test_generate_puzzle_only_verifies_solvability_when_requested(self):
        verify = Mock()
        verify.return_value = SimpleNamespace(
            valid=True,
            error=None,
            mode="solvable",
            solution=None,
            solution_count=1,
            runtime_seconds=0.0,
        )
        with patch("generator.generation.verify_puzzle", verify):
            generated = generate_puzzle(size=4, clues=6, seed=123, verify=True)

        self.assertEqual(generated.actual_clues, 6)
        self.assertEqual(verify.call_count, 1)
        self.assertEqual(verify.call_args.kwargs["mode"], "solvable")

    def test_small_dataset_records_are_solvable_only(self):
        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        self.assertEqual(record["verification_mode"], "derived")
        self.assertFalse(record["unique"])

    def test_dataset_generation_does_not_verify_by_default(self):
        verify = Mock(side_effect=AssertionError("verification should be explicit"))
        with patch("generator.generation.verify_puzzle", verify):
            records = generate_dataset_records(4, "easy", 2, seed=123)

        self.assertEqual(len(records), 2)
        self.assertEqual(verify.call_count, 0)

    def test_skipped_verification_does_not_claim_solution_count(self):
        generated = generate_puzzle(size=4, clues=6, seed=123, verify=False)

        self.assertEqual(generated.verification.mode, "derived")
        self.assertIsNone(generated.verification.solution_count)

    def test_verify_dataset_records_uses_selected_mode(self):
        records = generate_dataset_records(4, "easy", 2, seed=123, verify=False)
        with patch(
            "generator.verification.verify_puzzle",
            side_effect=[
                SimpleNamespace(valid=True, error=None),
                SimpleNamespace(valid=False, error="Sudoku has multiple solutions."),
            ],
        ) as verify:
            summary = verify_dataset_records(records, mode="unique")

        self.assertEqual(summary.mode, "unique")
        self.assertEqual(summary.total, 2)
        self.assertEqual(summary.valid_count, 1)
        self.assertEqual(summary.invalid_count, 1)
        self.assertEqual(summary.failures[0].record_number, 2)
        self.assertEqual(summary.failures[0].record_id, 2)
        self.assertEqual(verify.call_count, 2)
        self.assertEqual(verify.call_args.kwargs["mode"], "unique")


class DatasetMenuSmokeTests(unittest.TestCase):
    def test_generate_dataset_menu_generates_selected_difficulty(self):
        generated = []

        def fake_generate_dataset(size, difficulty, count):
            generated.append((size, difficulty, count))
            return Path(f"data/datasets/{size}x{size}_{difficulty}_{count}.jsonl")

        output = io.StringIO()
        with patch("generator.generation.prompt_size", return_value=4):
            with patch(
                "generator.generation.prompt_difficulty",
                return_value="medium",
            ):
                with patch("generator.generation.prompt_positive_int", return_value=2):
                    with patch(
                        "generator.generation.generate_dataset",
                        side_effect=fake_generate_dataset,
                    ):
                        with contextlib.redirect_stdout(output):
                            generation_module.generate_dataset_menu()

        self.assertEqual(
            generated,
            [(4, "medium", 2)],
        )
        self.assertIn("4x4_medium_2.jsonl", output.getvalue())

    def test_prompt_difficulty_includes_mixed_option(self):
        output = io.StringIO()
        with patch("builtins.input", return_value="4"):
            with contextlib.redirect_stdout(output):
                selected = prompt_difficulty()

        self.assertEqual(selected, "mixed")

    def test_verify_dataset_menu_selects_from_all_available_datasets(self):
        selected_path = Path("data/datasets/4x4_easy_1.jsonl")

        with patch("generator.generation.select_dataset", return_value=selected_path) as select:
            with patch("cli_helpers.prompt_choice", return_value="solvable"):
                with patch(
                    "generator.verification.verify_dataset",
                    return_value=SimpleNamespace(
                        mode="solvable",
                        total=1,
                        valid_count=1,
                        invalid_count=0,
                        runtime_seconds=0.0,
                        failures=[],
                    ),
                ) as verify:
                    with contextlib.redirect_stdout(io.StringIO()):
                        verification_module.verify_dataset_menu()

        select.assert_called_once_with()
        verify.assert_called_once_with(
            selected_path,
            expected_size=4,
            mode="solvable",
        )


class CliHelperTests(unittest.TestCase):
    def test_prompt_size_accepts_numeric_sudoku_size(self):
        output = io.StringIO()
        with patch("builtins.input", return_value="9"):
            with contextlib.redirect_stdout(output):
                size = prompt_size()

        self.assertEqual(size, 9)

    def test_prompt_size_rejects_non_square_box_size(self):
        output = io.StringIO()
        with patch("builtins.input", return_value="10"):
            with contextlib.redirect_stdout(output):
                size = prompt_size()

        self.assertIsNone(size)
        self.assertIn("Invalid size.", output.getvalue())

    def test_prompt_size_rejects_non_numeric_and_non_positive_input(self):
        for value in ("abc", "0"):
            output = io.StringIO()
            with patch("builtins.input", return_value=value):
                with contextlib.redirect_stdout(output):
                    size = prompt_size()

            self.assertIsNone(size)
            self.assertIn("Invalid size.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
