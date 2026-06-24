import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("TkAgg")

def visualization_menu(results_table):
    if results_table is None or results_table.empty:
        return

    visual = input("\nVisualize data? (y/n): ").strip().lower()
    if visual != "y":
        return

    times_by_solver = {
        name: solver_results["runtime_seconds"].tolist()
        for name, solver_results in results_table.groupby("solver", sort=False)
    }
    tested = results_table["puzzle_index"].nunique()
    show_naive = True
    if "naive" in times_by_solver:
        show_naive = input("Show naive solver on graph? (y/n): ").strip().lower() == "y"
    avgs = results_table.groupby("solver", sort=False)["runtime_seconds"].mean().to_dict()
    visualize_benchmark(times_by_solver, tested, avgs, show_naive=show_naive)


def visualize_benchmark(times_by_solver, tested, avgs, show_naive=True):
    plt.figure()
    for name, ts in times_by_solver.items():
        if name == "naive" and not show_naive:
            continue
        xs = range(1, len(ts) + 1)
        ys = ts
        plt.plot(xs, ys, label=name)
    plt.title(f"Sudoku Benchmark: Per-puzzle solve times (n={tested})")
    plt.xlabel("Puzzle #")
    plt.ylabel("Time (seconds)")
    plt.legend()
    plt.tight_layout()

    plt.figure()
    names, values = list(avgs.keys()), list(avgs.values())
    plt.bar(names, values)
    plt.title("Average solve time")
    plt.xlabel("Solver")
    plt.ylabel("Avg time (seconds)")
    plt.tight_layout()

    plt.show()
