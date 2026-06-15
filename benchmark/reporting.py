import csv
import json
from pathlib import Path


CSV_FIELDS = [
    "benchmark_type",
    "dataset",
    "size",
    "difficulty",
    "clues",
    "puzzle_index",
    "solver",
    "status",
    "runtime_seconds",
    "setup_seconds",
    "solve_seconds",
    "backtracks",
    "assignments",
    "recursive_calls",
    "solution_found",
    "error",
]
BENCHMARK_RESULTS_DIR = "data/results"


def format_seconds(value):
    return "" if value is None else f"{value:.6f}"


def format_metric(value):
    return "" if value is None else str(value)


def csv_row(benchmark_type, puzzle_index, solver_name, result, metadata=None):
    metadata = metadata or {}
    return {
        "benchmark_type": benchmark_type,
        "dataset": metadata.get("dataset", ""),
        "size": metadata.get("size", ""),
        "difficulty": metadata.get("difficulty", ""),
        "clues": metadata.get("clues", ""),
        "puzzle_index": puzzle_index,
        "solver": solver_name,
        "status": result.status,
        "runtime_seconds": format_seconds(result.runtime_seconds),
        "setup_seconds": format_seconds(result.setup_seconds),
        "solve_seconds": format_seconds(result.solve_seconds),
        "backtracks": format_metric(result.backtracks),
        "assignments": format_metric(result.assignments),
        "recursive_calls": format_metric(result.recursive_calls),
        "solution_found": result.solved,
        "error": result.error or "",
    }


def benchmark_data_directory(size, difficulty, results_dir=None):
    if results_dir is None:
        results_dir = BENCHMARK_RESULTS_DIR
    return Path(results_dir) / f"{size}x{size}" / difficulty / "data"


def benchmark_summary_directory(size, difficulty, results_dir=None):
    if results_dir is None:
        results_dir = BENCHMARK_RESULTS_DIR
    return Path(results_dir) / f"{size}x{size}" / difficulty / "summary"


def next_benchmark_run_paths(size, difficulty, results_dir=None):
    data_dir = benchmark_data_directory(size, difficulty, results_dir)
    summary_dir = benchmark_summary_directory(size, difficulty, results_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    index = 0
    while True:
        csv_path = data_dir / f"run_{index}.csv"
        json_path = summary_dir / f"run_{index}.json"
        if not csv_path.exists() and not json_path.exists():
            return csv_path, json_path
        index += 1


def write_benchmark_csv(rows, csv_path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def write_benchmark_summary_json(summary, json_path):
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    return json_path


def average_present(results, attr):
    values = [
        getattr(result, attr)
        for result in results
        if getattr(result, attr) is not None
    ]
    if not values:
        return None
    return sum(values) / len(values)


def format_summary_seconds(value):
    return "-" if value is None else f"{value:.6f}"


def format_summary_average(value):
    return "-" if value is None else f"{value:.2f}"


def benchmark_summary_rows(results_by_solver, tested):
    rows = []

    for name, results in results_by_solver.items():
        solved = sum(1 for result in results if result.solved)
        total_runtime = sum(result.runtime_seconds for result in results)
        avg_runtime = total_runtime / tested if tested else 0.0
        success_rate = (solved / tested * 100) if tested else 0.0
        solve_average = average_present(results, "solve_seconds")
        if solve_average is None and any(result.status != "error" for result in results):
            solve_average = avg_runtime

        rows.append(
            {
                "solver": name,
                "solved": f"{solved}/{tested}",
                "success_rate": f"{success_rate:.1f}%",
                "total_runtime_s": f"{total_runtime:.4f}",
                "avg_runtime_s": f"{avg_runtime:.6f}",
                "setup_avg_s": format_summary_seconds(
                    average_present(results, "setup_seconds")
                ),
                "solve_avg_s": format_summary_seconds(solve_average),
                "backtracks_avg": format_summary_average(
                    average_present(results, "backtracks")
                ),
                "assignments_avg": format_summary_average(
                    average_present(results, "assignments")
                ),
                "recursive_calls_avg": format_summary_average(
                    average_present(results, "recursive_calls")
                ),
            }
        )

    return rows


def print_plain_summary_table(rows):
    if not rows:
        return

    headers = list(rows[0].keys())
    widths = {
        header: max(len(header), *(len(str(row[header])) for row in rows))
        for header in headers
    }
    header_row = "  ".join(header.ljust(widths[header]) for header in headers)
    divider = "  ".join("-" * widths[header] for header in headers)

    print(header_row)
    print(divider)
    for row in rows:
        print("  ".join(str(row[header]).ljust(widths[header]) for header in headers))


def print_summary_table(rows):
    try:
        import pandas as pd
    except ImportError:
        print_plain_summary_table(rows)
        return

    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
