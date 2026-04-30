import contextlib
import io
import tempfile
import unittest
from unittest.mock import patch

from solvers.metrics import SolverResult
from sudoku_datasets import (
    clue_count,
    dataset_filename,
    expand_difficulties,
    generate_dataset_records,
    read_dataset,
    write_dataset_records,
)
from sudoku_generator import generate_puzzle


class SudokuDatasetTests(unittest.TestCase):
    def test_clue_count_uses_difficulty_percentages(self):
        self.assertEqual(clue_count(9, "easy"), 49)
        self.assertEqual(clue_count(9, "medium"), 36)
        self.assertEqual(clue_count(9, "hard"), 24)

    def test_mixed_difficulty_distribution_assigns_remainders_in_order(self):
        self.assertEqual(
            expand_difficulties("mixed", 5),
            ["easy", "easy", "medium", "medium", "hard"],
        )

    def test_dataset_jsonl_roundtrip(self):
        records = generate_dataset_records(36, "hard", 1, seed=123, verify=False)

        with tempfile.TemporaryDirectory() as root:
            path = write_dataset_records(
                records,
                size=36,
                difficulty="hard",
                count=1,
                root=root,
            )
            loaded = read_dataset(path, expected_size=36)

        self.assertEqual(len(loaded), 1)
        self.assertEqual(path.name, "36x36_hard_1_0.jsonl")
        self.assertEqual(loaded[0]["size"], 36)
        self.assertEqual(loaded[0]["difficulty"], "hard")
        self.assertEqual(loaded[0]["verification_mode"], "solvable")
        self.assertFalse(loaded[0]["unique"])

    def test_dataset_reader_rejects_wrong_size(self):
        records = generate_dataset_records(36, "easy", 1, seed=123, verify=False)

        with tempfile.TemporaryDirectory() as root:
            path = write_dataset_records(
                records,
                size=36,
                difficulty="easy",
                count=1,
                root=root,
            )
            with self.assertRaises(ValueError):
                read_dataset(path, expected_size=9)

    def test_dataset_filename_uses_size_difficulty_count_and_index(self):
        self.assertEqual(dataset_filename(9, "medium", 100, 0), "9x9_medium_100_0.jsonl")

    def test_dataset_writer_uses_next_available_index(self):
        records = generate_dataset_records(4, "easy", 1, seed=123, verify=False)

        with tempfile.TemporaryDirectory() as root:
            first = write_dataset_records(records, 4, "easy", 1, root=root)
            second = write_dataset_records(records, 4, "easy", 1, root=root)

        self.assertEqual(first.name, "4x4_easy_1_0.jsonl")
        self.assertEqual(second.name, "4x4_easy_1_1.jsonl")

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
    def test_generate_puzzle_only_verifies_solvability_once(self):
        with patch("sudoku_generator.verify_puzzle") as verify:
            verify.return_value.valid = True
            verify.return_value.error = None
            generated = generate_puzzle(size=4, clues=6, seed=123, verify=True)

        self.assertEqual(generated.actual_clues, 6)
        self.assertEqual(verify.call_count, 1)
        self.assertEqual(verify.call_args.kwargs["mode"], "solvable")

    def test_small_dataset_records_are_solvable_only(self):
        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        self.assertEqual(record["verification_mode"], "solvable")
        self.assertFalse(record["unique"])

    def test_dataset_generation_verifies_each_puzzle_by_default(self):
        with patch("sudoku_generator.verify_puzzle") as verify:
            verify.return_value.valid = True
            verify.return_value.error = None
            records = generate_dataset_records(4, "easy", 2, seed=123)

        self.assertEqual(len(records), 2)
        self.assertEqual(verify.call_count, 2)

    def test_skipped_verification_does_not_claim_solution_count(self):
        generated = generate_puzzle(size=4, clues=6, seed=123, verify=False)

        self.assertIsNone(generated.verification.solution_count)


class BenchmarkDatasetSmokeTests(unittest.TestCase):
    def test_benchmark_csv_path_uses_dataset_name_and_next_index(self):
        import main

        with tempfile.TemporaryDirectory() as root:
            dataset = "datasets/9x9/9x9_medium_100_0.jsonl"
            first = main.benchmark_csv_path(dataset, results_dir=root)
            first.touch()
            second = main.benchmark_csv_path(dataset, results_dir=root)

        self.assertEqual(first.name, "9x9_medium_100_0_results_0.csv")
        self.assertEqual(second.name, "9x9_medium_100_0_results_1.csv")

    def test_benchmark_dataset_runs_selected_records(self):
        import main

        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        with tempfile.TemporaryDirectory() as root:
            path = write_dataset_records(
                [record],
                size=4,
                difficulty="easy",
                count=1,
                root=root,
            )

            def fake_solver(_puzzle):
                return SolverResult(
                    solution=record["solution"],
                    status="solved",
                    runtime_seconds=0.001,
                )

            output = io.StringIO()
            with patch("main.solvers_for_size", return_value={"fake": fake_solver}):
                with patch("builtins.input", return_value="n"):
                    with contextlib.redirect_stdout(output):
                        main.benchmark_dataset(path, 4, write_csv=False)

        self.assertIn("Puzzles Tested: 1", output.getvalue())
        self.assertIn("fake=0.0010s", output.getvalue())


if __name__ == "__main__":
    unittest.main()
