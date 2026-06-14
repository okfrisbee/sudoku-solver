import contextlib
import io
from pathlib import Path
import random
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from sudoku_datasets import (
    DIFFICULTY_PERCENT_RANGES,
    clue_count,
    dataset_path,
    expand_difficulties,
    generate_dataset_records,
    generate_puzzle,
    list_datasets,
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
        self.assertEqual(path.name, "hard.jsonl")
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
            dataset_path(9, "medium"),
            Path("datasets") / "9x9" / "medium.jsonl",
        )

    def test_dataset_writer_overwrites_same_size_and_difficulty(self):
        first_records = generate_dataset_records(4, "easy", 1, seed=123, verify=False)
        second_records = generate_dataset_records(4, "easy", 2, seed=456, verify=False)

        with tempfile.TemporaryDirectory() as root:
            first = write_dataset_records(first_records, 4, "easy", root=root)
            second = write_dataset_records(second_records, 4, "easy", root=root)
            loaded = read_dataset(second, expected_size=4)

        self.assertEqual(first, second)
        self.assertEqual(second.name, "easy.jsonl")
        self.assertEqual(len(loaded), 2)

    def test_list_datasets_returns_stable_difficulty_files(self):
        records = generate_dataset_records(4, "easy", 1, seed=123, verify=False)

        with tempfile.TemporaryDirectory() as root:
            easy = write_dataset_records(records, 4, "easy", root=root)
            medium = write_dataset_records(records, 4, "medium", root=root)
            datasets = list_datasets(4, root=root)

        self.assertEqual(datasets, [easy, medium])

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
        fake_verifier = SimpleNamespace(verify_puzzle=verify)

        with patch.dict("sys.modules", {"sudoku_verifier": fake_verifier}):
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
        fake_verifier = SimpleNamespace(verify_puzzle=verify)

        with patch.dict("sys.modules", {"sudoku_verifier": fake_verifier}):
            records = generate_dataset_records(4, "easy", 2, seed=123)

        self.assertEqual(len(records), 2)
        self.assertEqual(verify.call_count, 0)

    def test_skipped_verification_does_not_claim_solution_count(self):
        generated = generate_puzzle(size=4, clues=6, seed=123, verify=False)

        self.assertEqual(generated.verification.mode, "derived")
        self.assertIsNone(generated.verification.solution_count)

    def test_verify_dataset_records_uses_selected_mode(self):
        records = generate_dataset_records(4, "easy", 2, seed=123, verify=False)
        verify = Mock(
            side_effect=[
                SimpleNamespace(valid=True, error=None),
                SimpleNamespace(valid=False, error="Sudoku has multiple solutions."),
            ]
        )
        fake_verifier = SimpleNamespace(verify_puzzle=verify)

        with patch.dict("sys.modules", {"sudoku_verifier": fake_verifier}):
            summary = verify_dataset_records(records, mode="unique")

        self.assertEqual(summary.mode, "unique")
        self.assertEqual(summary.total, 2)
        self.assertEqual(summary.valid_count, 1)
        self.assertEqual(summary.invalid_count, 1)
        self.assertEqual(summary.failures[0].record_number, 2)
        self.assertEqual(summary.failures[0].record_id, 2)
        self.assertEqual(verify.call_count, 2)
        self.assertEqual(verify.call_args.kwargs["mode"], "unique")


class MainDatasetMenuSmokeTests(unittest.TestCase):
    def test_generate_dataset_menu_can_generate_all_difficulties(self):
        import main

        generated = []

        def fake_generate_dataset(size, difficulty, count):
            generated.append((size, difficulty, count))
            return Path(f"datasets/{size}x{size}/{difficulty}.jsonl")

        output = io.StringIO()
        with patch("main.prompt_size", return_value=4):
            with patch("main.prompt_difficulty", return_value=main.ALL_DIFFICULTIES_OPTION):
                with patch("main.prompt_positive_int", return_value=2):
                    with patch("main.generate_dataset", side_effect=fake_generate_dataset):
                        with contextlib.redirect_stdout(output):
                            main.generate_dataset_menu()

        self.assertEqual(
            generated,
            [
                (4, "easy", 2),
                (4, "medium", 2),
                (4, "hard", 2),
            ],
        )
        self.assertIn("easy.jsonl", output.getvalue())
        self.assertIn("medium.jsonl", output.getvalue())
        self.assertIn("hard.jsonl", output.getvalue())

    def test_prompt_difficulty_includes_all_difficulties_option(self):
        import main

        with patch("builtins.input", return_value="5"):
            selected = main.prompt_difficulty()

        self.assertEqual(selected, main.ALL_DIFFICULTIES_OPTION)


if __name__ == "__main__":
    unittest.main()
