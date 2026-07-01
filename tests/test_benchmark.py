import contextlib
import csv
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from benchmark import runner as benchmark_module
from benchmark import visualization as benchmark_visualization
from generator import generate_dataset_records, write_dataset_records
from solvers.metrics import SolverResult
from tests.config_helpers import temporary_config


def slow_solver(_puzzle):
    time.sleep(1)
    return SolverResult(solution=None, status="failed", runtime_seconds=1.0)


def crashing_solver(_puzzle):
    raise RuntimeError("boom")


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_result_paths_use_stable_dataset_names(self):
        with tempfile.TemporaryDirectory() as root:
            with temporary_config(root, benchmark_results_dir=root):
                csv_path, summary_path = benchmark_module.result_paths(
                    "data/datasets/9x9_medium_100.jsonl",
                )
                csv_path.touch()
                summary_path.touch()
                next_csv_path, next_summary_path = benchmark_module.result_paths(
                    "data/datasets/9x9_medium_100.jsonl",
                )

        self.assertEqual(csv_path, Path(root) / "data" / "9x9_medium_100_results.csv")
        self.assertEqual(
            summary_path,
            Path(root) / "summary" / "9x9_medium_100_summary.csv",
        )
        self.assertEqual(next_csv_path, csv_path)
        self.assertEqual(next_summary_path, summary_path)

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
                "benchmark.runner.SOLVERS",
                {"naive": fake_solver},
            ):
                benchmark_module.benchmark_dataset(
                    Path("data/datasets/16x16_easy_1.jsonl"),
                    16,
                    write_csv=False,
                )

    def test_benchmark_dataset_runs_selected_records(self):
        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        with tempfile.TemporaryDirectory() as root:
            with temporary_config(root, datasets_dir=root):
                path = write_dataset_records(
                    [record],
                    size=4,
                    difficulty="easy",
                )

                def fake_solver(_puzzle):
                    return SolverResult(
                        solution=record["solution"],
                        status="solved",
                        runtime_seconds=0.001,
                    )

                output = io.StringIO()
                with patch(
                    "benchmark.runner.SOLVERS",
                    {"fake": fake_solver},
                ):
                    with contextlib.redirect_stdout(output):
                        result = benchmark_module.benchmark_dataset(path, 4, write_csv=False)

        self.assertIn("Puzzles Tested: 1", output.getvalue())
        self.assertIn("fake=0.0010s", output.getvalue())
        self.assertEqual(result["puzzle_index"].nunique(), 1)
        self.assertEqual(result["solver"].tolist(), ["fake"])
        self.assertEqual(result["runtime_seconds"].tolist(), [0.001])

    def test_benchmark_dataset_can_run_csp_only(self):
        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        with tempfile.TemporaryDirectory() as root:
            with temporary_config(root, datasets_dir=root):
                dataset_path_for_test = write_dataset_records(
                    [record],
                    size=4,
                    difficulty="easy",
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
                    "benchmark.runner.SOLVERS",
                    {"csp": fake_csp, "sat": fake_sat},
                ):
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
            with temporary_config(root, datasets_dir=root, solver_timeout_seconds=0.05):
                dataset_path_for_test = write_dataset_records(
                    [record],
                    size=4,
                    difficulty="easy",
                )

                output = io.StringIO()
                with patch(
                    "benchmark.runner.SOLVERS",
                    {"slow": slow_solver},
                ):
                    with contextlib.redirect_stdout(output):
                        benchmark_module.benchmark_dataset(
                            dataset_path_for_test,
                            4,
                            write_csv=False,
                        )

        self.assertIn("slow=TIMEOUT", output.getvalue())
        self.assertIn("0/1", output.getvalue())

    def test_benchmark_dataset_reports_solver_process_crash(self):
        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        with tempfile.TemporaryDirectory() as root:
            with temporary_config(root, datasets_dir=root):
                dataset_path_for_test = write_dataset_records(
                    [record],
                    size=4,
                    difficulty="easy",
                )

                output = io.StringIO()
                with patch("benchmark.runner.SOLVERS", {"crash": crashing_solver}):
                    with contextlib.redirect_stdout(output):
                        result = benchmark_module.benchmark_dataset(
                            dataset_path_for_test,
                            4,
                            write_csv=False,
                        )

        self.assertIn("crash=ERROR", output.getvalue())
        self.assertEqual(result["status"].tolist(), ["error"])
        self.assertIn("without a result", result["error"].tolist()[0])

    def test_benchmark_dataset_writes_csv_data_and_summary(self):
        record = generate_dataset_records(4, "easy", 1, seed=123, verify=False)[0]

        with tempfile.TemporaryDirectory() as root:
            with temporary_config(
                root,
                datasets_dir=root,
                benchmark_results_dir=Path(root) / "results",
            ):
                dataset_path_for_test = write_dataset_records(
                    [record],
                    size=4,
                    difficulty="easy",
                )

                def fake_solver(_puzzle):
                    return SolverResult(
                        solution=record["solution"],
                        status="solved",
                        runtime_seconds=0.001,
                    )

                output = io.StringIO()
                with patch(
                    "benchmark.runner.SOLVERS",
                    {"fake": fake_solver},
                ):
                    with contextlib.redirect_stdout(output):
                        benchmark_module.benchmark_dataset(
                            dataset_path_for_test,
                            4,
                            write_csv=True,
                        )

            csv_path = Path(root) / "results" / "data" / "4x4_easy_1_results.csv"
            summary_path = Path(root) / "results" / "summary" / "4x4_easy_1_summary.csv"
            self.assertTrue(csv_path.exists())
            self.assertTrue(summary_path.exists())
            with open(summary_path, newline="", encoding="utf-8") as f:
                summary_rows = list(csv.DictReader(f))

        self.assertEqual(summary_rows[0]["solver"], "fake")
        self.assertEqual(summary_rows[0]["solved"], "1")
        self.assertEqual(summary_rows[0]["tested"], "1")

    def test_visualization_menu_uses_returned_benchmark_data(self):
        result = benchmark_module.results_dataframe(
            [
                {
                    "puzzle_index": 1,
                    "solver_name": "naive",
                    "result": SolverResult(
                        solution="1234",
                        status="solved",
                        runtime_seconds=0.001,
                    ),
                }
            ]
        )

        with patch("builtins.input", side_effect=["y", "n"]):
            with patch("benchmark.visualization.visualize_benchmark") as visualize:
                benchmark_visualization.visualization_menu(result)

        visualize.assert_called_once_with(
            {"naive": [0.001]},
            1,
            {"naive": 0.001},
            show_naive=False,
        )

    def test_benchmark_menu_passes_selected_solver_filter(self):
        import main

        selected_path = Path("data/datasets/4x4_easy_1.jsonl")
        results_table = object()

        with patch("benchmark.runner.select_dataset", return_value=selected_path) as select:
            with patch(
                "benchmark.runner.prompt_choice",
                return_value="csp",
            ) as prompt:
                with patch("builtins.input", return_value="n"):
                    with patch(
                        "benchmark.runner.benchmark_dataset",
                        return_value=results_table,
                    ) as run_benchmark:
                        result = main.benchmark_menu()

        select.assert_called_once_with()
        prompt.assert_called_once_with(
            "\nSelect benchmark solver mode:",
            ["all", "naive", "csp", "sat", "smt", "dlx"],
        )
        run_benchmark.assert_called_once_with(
            selected_path,
            4,
            write_csv=False,
            solver_names=["csp"],
        )
        self.assertIs(result, results_table)

    def test_main_runs_visualization_after_benchmark(self):
        import main

        results_table = object()

        with patch("builtins.input", side_effect=["4", "5"]):
            with patch("main.os.system"):
                with patch("main.benchmark_menu", return_value=results_table):
                    with patch("main.visualization_menu") as visualization:
                        main.main()

        visualization.assert_called_once_with(results_table)


if __name__ == "__main__":
    unittest.main()
