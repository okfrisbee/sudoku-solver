from generator import SUPPORTED_SIZES, list_datasets


def prompt_choice(title, options):
    print(title)
    for index, option in enumerate(options, start=1):
        print(f"{index}. {option}")

    choice = input().strip()
    if not choice.isdigit():
        return None

    index = int(choice)
    if index < 1 or index > len(options):
        return None
    return options[index - 1]


def prompt_size():
    options = [f"{size}x{size}" for size in SUPPORTED_SIZES]
    selected = prompt_choice("\nSelect puzzle size:", options)
    if selected is None:
        print("Invalid size.")
        return None
    return int(selected.split("x", 1)[0])


def select_dataset(size):
    datasets = list_datasets(size)
    if not datasets:
        print(f"\nNo datasets found for {size}x{size}. Generate a dataset first.")
        return None

    options = [path.name for path in datasets]
    selected = prompt_choice("\nSelect dataset:", options)
    if selected is None:
        print("Invalid dataset.")
        return None

    return datasets[options.index(selected)]
