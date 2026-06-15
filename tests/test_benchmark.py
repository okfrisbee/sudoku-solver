import contextlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from benchmark import runner as benchmark_module
from benchmark import visualization as benchmark_visualization
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
                benchmark_module.benchmark_dataset(
                    Path("data/datasets/16x16_easy_1.jsonl"),
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
                with contextlib.redirect_stdout(output):
                    result = benchmark_module.benchmark_dataset(path, 4, write_csv=False)

        self.assertIn("Puzzles Tested: 1", output.getvalue())
        self.assertIn("fake=0.0010s", output.getvalue())
        self.assertEqual(result["tested"], 1)
        self.assertEqual(result["solvers"], ["fake"])
        self.assertEqual(result["times_by_solver"], {"fake": [0.001]})

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

    def test_visualization_menu_uses_returned_benchmark_data(self):
        result = {
            "tested": 1,
            "times_by_solver": {"naive": [0.001]},
            "results_by_solver": {
                "naive": [
                    SolverResult(
                        solution="1234",
                        status="solved",
                        runtime_seconds=0.001,
                    )
                ],
            },
        }

        with patch("builtins.input", side_effect=["y", "n"]):
            with patch("benchmark.visualization.visualize_benchmark") as visualize:
                benchmark_visualization.visualization_menu(result)

        visualize.assert_called_once_with(
            {"naive": [0.001]},
            1,
            {"naive": 0.001},
            show_naive=False,
        )

    def test_benchmark_menu_passes_csp_only_filter(self):
        import main

        selected_path = Path("data/datasets/4x4_easy_1.jsonl")
        benchmark_result = {"tested": 1}

        with patch("benchmark.runner.select_dataset", return_value=selected_path) as select:
            with patch(
                "benchmark.runner.prompt_choice",
                return_value="csp only",
            ):
                with patch("builtins.input", return_value="n"):
                    with patch(
                        "benchmark.runner.benchmark_dataset",
                        return_value=benchmark_result,
                    ) as run_benchmark:
                        result = main.benchmark_menu()

        select.assert_called_once_with()
        run_benchmark.assert_called_once_with(
            selected_path,
            4,
            write_csv=False,
            solver_names=["csp"],
        )
        self.assertIs(result, benchmark_result)

    def test_main_runs_visualization_after_benchmark(self):
        import main

        benchmark_result = {"tested": 1}

        with patch("builtins.input", side_effect=["4", "5"]):
            with patch("main.os.system"):
                with patch("main.benchmark_menu", return_value=benchmark_result):
                    with patch("main.visualization_menu") as visualization:
                        main.main()

        visualization.assert_called_once_with(benchmark_result)


if __name__ == "__main__":
    unittest.main()
