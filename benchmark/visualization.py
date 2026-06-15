def visualization_menu(benchmark_result):
    if benchmark_result is None:
        return

    visual = input("\nVisualize data? (y/n): ").strip().lower()
    if visual != "y":
        return

    times_by_solver = benchmark_result["times_by_solver"]
    results_by_solver = benchmark_result["results_by_solver"]
    tested = benchmark_result["tested"]
    show_naive = True
    if "naive" in times_by_solver:
        show_naive = input("Show naive solver on graph? (y/n): ").strip().lower() == "y"
    avgs = {
        name: (sum(result.runtime_seconds for result in results) / tested)
        if tested
        else 0.0
        for name, results in results_by_solver.items()
    }
    visualize_benchmark(times_by_solver, tested, avgs, show_naive=show_naive)


def visualize_benchmark(times_by_solver, tested, avgs, show_naive=True):
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("TkAgg")

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
