from board_utils import validate_size


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
    print("\nEnter puzzle size:")
    value = input().strip()
    if not value.isdigit():
        print("Invalid size.")
        return None

    size = int(value)
    try:
        validate_size(size)
    except ValueError:
        print("Invalid size.")
        return None
    return size


def prompt_positive_int(message):
    print(message)
    value = input().strip()
    if not value.isdigit() or int(value) <= 0:
        print("Invalid count.")
        return None
    return int(value)

