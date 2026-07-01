from pathlib import Path

import pandas as pd

from config import load_config


CSV_FIELDS = [
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
BENCHMARK_RESULTS_DIR = load_config()["paths"]["benchmark_results_dir"]


def result_paths(dataset_path):
    root = Path(load_config()["paths"]["benchmark_results_dir"])
    dataset_stem = Path(dataset_path).stem
    data_dir = root / "data"
    summary_dir = root / "summary"
    data_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    csv_path = data_dir / f"{dataset_stem}_results.csv"
    summary_path = summary_dir / f"{dataset_stem}_summary.csv"
    return csv_path, summary_path


def _result_row(puzzle_index, solver_name, result, metadata=None):
    metadata = metadata or {}
    return {
        "size": metadata.get("size", ""),
        "difficulty": metadata.get("difficulty", ""),
        "clues": metadata.get("clues", ""),
        "puzzle_index": puzzle_index,
        "solver": solver_name,
        "status": result.status,
        "runtime_seconds": result.runtime_seconds,
        "setup_seconds": 0.0 if result.setup_seconds is None else result.setup_seconds,
        "solve_seconds": result.solve_seconds,
        "backtracks": result.backtracks,
        "assignments": result.assignments,
        "recursive_calls": result.recursive_calls,
        "solution_found": result.solved,
        "error": result.error or "",
    }


def results_dataframe(csv_rows):
    result_rows = [_result_row(**row) for row in csv_rows]
    table = pd.DataFrame(result_rows, columns=CSV_FIELDS)
    table["solution_found"] = table["solution_found"].fillna(False).astype(bool)
    return table


def summary_dataframe(table, tested=None):
    if table.empty:
        return pd.DataFrame()

    total_tested = tested if tested is not None else table["puzzle_index"].nunique()
    rows = [
        _summary_row(name, solver_results, total_tested)
        for name, solver_results in table.groupby("solver", sort=False)
    ]
    return pd.DataFrame(rows)


def print_summary_table(table):
    if not table.empty:
        display = table.copy()
        display["solved"] = (
            display["solved"].astype(str) + "/" + display["tested"].astype(str)
        )
        display = display.drop(columns=["tested"])
        print(
            display.to_string(
                index=False,
                na_rep="-",
                formatters={
                    "success_rate": "{:.1f}%".format,
                    "total_runtime_s": _format_number,
                    "avg_runtime_s": _format_number,
                    "setup_avg_s": _format_number,
                    "solve_avg_s": _format_number,
                    "backtracks_avg": _format_number,
                    "assignments_avg": _format_number,
                    "recursive_calls_avg": _format_number,
                },
            )
        )


def write_csv(table, csv_path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(csv_path, index=False)
    return csv_path


def _summary_row(name, table, tested):
    average_fields = [
        "setup_seconds",
        "solve_seconds",
        "backtracks",
        "assignments",
        "recursive_calls",
    ]
    solved = int(table["solution_found"].sum()) if not table.empty else 0
    total_runtime = table["runtime_seconds"].sum() if not table.empty else 0.0
    avg_runtime = total_runtime / tested if tested else 0.0
    success_rate = (solved / tested * 100) if tested else 0.0
    averages = table[average_fields].mean()
    solve_average = averages["solve_seconds"]

    if pd.isna(solve_average) and (
        not table.empty and table["status"].ne("error").any()
    ):
        solve_average = avg_runtime

    return {
        "solver": name,
        "solved": solved,
        "tested": tested,
        "success_rate": success_rate,
        "total_runtime_s": total_runtime,
        "avg_runtime_s": avg_runtime,
        "setup_avg_s": averages["setup_seconds"],
        "solve_avg_s": solve_average,
        "backtracks_avg": averages["backtracks"],
        "assignments_avg": averages["assignments"],
        "recursive_calls_avg": averages["recursive_calls"],
    }


def _format_number(value, decimals=6):
    return "-" if pd.isna(value) else f"{value:.{decimals}f}"
