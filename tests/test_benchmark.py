import contextlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from benchmark import runner as benchmark_module
from generator import generate_dataset_records, write_dataset_records
from solvers.metrics import SolverResult


def slow_solver(_puzzle):
    time.sleep(1)
    return SolverResult(solution=None, status="failed", runtime_seconds=1.0)


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_run_paths_split_artifacts_and_share_index(self):
        with tempfile.TemporaryDirectory() as root:
            csv_path, json_path = benchmark_module.next_benchmark_run_paths(
                9,
                "medium",
                results_dir=root,
            )
            csv_path.touch()
            next_csv_path, next_json_path = benchmark_module.next_benchmark_run_paths(
                9,
                "medium",
                results_dir=root,
            )

        self.assertEqual(csv_path, Path(root) / "9x9" / "medium" / "data" / "run_0.csv")
        self.assertEqual(
            json_path,
            Path(root) / "9x9" / "medium" / "summary" / "run_0.json",
        )
        self.assertEqual(next_csv_path.name, "run_1.csv")
        self.assertEqual(next_json_path.name, "run_1.json")

    def test_benchmark_run_paths_check_existing_summary_files(self):
        with tempfile.TemporaryDirectory() as root:
            csv_path, json_path = benchmark_module.next_benchmark_run_paths(
                9,
                "medium",
                results_dir=root,
            )
            json_path.touch()
            next_csv_path, next_json_path = benchmark_module.next_benchmark_run_paths(
                9,
                "medium",
                results_dir=root,
            )

        self.assertEqual(csv_path.name, "run_0.csv")
        self.assertEqual(next_csv_path.name, "run_1.csv")
        self.assertEqual(next_json_path.name, "run_1.json")

    def test_naive_benchmark_keeps_tokenized_multi_digit_values(self):
        record = {
            "puzzle": "1 10 0 16",
            "solution": "1 10 11 16",
            "difficulty": "easy",
            "actual_clues": 3,
        }

        def fake_solver(puzzle):
            self.assertEqual(puzzle, "1 10 0 16")
            return SolverResult(
                solution=record["solution"],
                status="solved",
                runtime_seconds=0.001,
            )

        with patch("benchmark.runner.read_dataset", return_value=[record]):
            with patch(
                "benchmark.runner.solvers_for_size",
                return_value={"naive": fake_solver},
            ):
                with patch("builtins.input", return_value="n"):
                    benchmark_module.benchmark_dataset(
                        Path("data/datasets/16x16/easy.jsonl"),
                        16,
                        write_csv=False,
                    )

    def test_benchmark_dataset_runs_selected_records(self):
        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        with tempfile.TemporaryDirectory() as root:
            path = write_dataset_records(
                [record],
                size=4,
                difficulty="easy",
                root=root,
            )

            def fake_solver(_puzzle):
                return SolverResult(
                    solution=record["solution"],
                    status="solved",
                    runtime_seconds=0.001,
                )

            output = io.StringIO()
            with patch(
                "benchmark.runner.solvers_for_size",
                return_value={"fake": fake_solver},
            ):
                with patch("builtins.input", return_value="n"):
                    with contextlib.redirect_stdout(output):
                        benchmark_module.benchmark_dataset(path, 4, write_csv=False)

        self.assertIn("Puzzles Tested: 1", output.getvalue())
        self.assertIn("fake=0.0010s", output.getvalue())

    def test_benchmark_dataset_can_run_csp_only(self):
        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        with tempfile.TemporaryDirectory() as root:
            dataset_path_for_test = write_dataset_records(
                [record],
                size=4,
                difficulty="easy",
                root=root,
            )

            def fake_csp(_puzzle):
                return SolverResult(
                    solution=record["solution"],
                    status="solved",
                    runtime_seconds=0.001,
                )

            def fake_sat(_puzzle):
                return SolverResult(
                    solution=record["solution"],
                    status="solved",
                    runtime_seconds=0.001,
                )

            output = io.StringIO()
            with patch(
                "benchmark.runner.solvers_for_size",
                return_value={"csp": fake_csp, "sat": fake_sat},
            ):
                with patch("builtins.input", return_value="n"):
                    with contextlib.redirect_stdout(output):
                        benchmark_module.benchmark_dataset(
                            dataset_path_for_test,
                            4,
                            write_csv=False,
                            solver_names=["csp"],
                        )

        self.assertIn("csp=0.0010s", output.getvalue())
        self.assertNotIn("sat=", output.getvalue())

    def test_benchmark_dataset_times_out_slow_solver(self):
        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        with tempfile.TemporaryDirectory() as root:
            dataset_path_for_test = write_dataset_records(
                [record],
                size=4,
                difficulty="easy",
                root=root,
            )

            output = io.StringIO()
            with patch(
                "benchmark.runner.solvers_for_size",
                return_value={"slow": slow_solver},
            ):
                with patch("builtins.input", return_value="n"):
                    with contextlib.redirect_stdout(output):
                        benchmark_module.benchmark_dataset(
                            dataset_path_for_test,
                            4,
                            write_csv=False,
                            timeout_seconds=0.05,
                        )

        self.assertIn("slow=TIMEOUT", output.getvalue())
        self.assertIn("0/1", output.getvalue())

    def test_benchmark_dataset_writes_csv_data_and_json_summary(self):
        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        with tempfile.TemporaryDirectory() as root:
            dataset_path_for_test = write_dataset_records(
                [record],
                size=4,
                difficulty="easy",
                root=root,
            )

            def fake_solver(_puzzle):
                return SolverResult(
                    solution=record["solution"],
                    status="solved",
                    runtime_seconds=0.001,
                )

            output = io.StringIO()
            with patch(
                "benchmark.reporting.BENCHMARK_RESULTS_DIR",
                str(Path(root) / "results"),
            ):
                with patch(
                    "benchmark.runner.solvers_for_size",
                    return_value={"fake": fake_solver},
                ):
                    with patch("builtins.input", return_value="n"):
                        with contextlib.redirect_stdout(output):
                            benchmark_module.benchmark_dataset(
                                dataset_path_for_test,
                                4,
                                write_csv=True,
                            )

            csv_path = Path(root) / "results" / "4x4" / "easy" / "data" / "run_0.csv"
            json_path = Path(root) / "results" / "4x4" / "easy" / "summary" / "run_0.json"
            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            with open(json_path, encoding="utf-8") as f:
                summary = json.load(f)

        self.assertEqual(summary["dataset"]["difficulty"], "easy")
        self.assertEqual(summary["dataset"]["puzzle_count"], 1)
        self.assertEqual(summary["tested"], 1)
        self.assertEqual(summary["solvers"], ["fake"])
        self.assertEqual(summary["summary_rows"][0]["solver"], "fake")

    def test_benchmark_menu_passes_csp_only_filter(self):
        import main

        selected_path = Path("data/datasets/4x4/easy.jsonl")

        with patch("main.prompt_size", return_value=4):
            with patch("main.select_dataset", return_value=selected_path):
                with patch("main.prompt_benchmark_solver_mode", return_value="csp only"):
                    with patch("main.prompt_write_csv", return_value=False):
                        with patch("main.benchmark_dataset") as run_benchmark:
                            main.benchmark_menu()

        run_benchmark.assert_called_once_with(
            selected_path,
            4,
            write_csv=False,
            solver_names=["csp"],
        )


if __name__ == "__main__":
    unittest.main()
