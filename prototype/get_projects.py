from pathlib import Path

def get_second_level_dirs(root: Path) -> list[tuple[str, str]]:
    return [
        p.parts[-2] + "/" + p.parts[-1]
        for p in root.glob('*/*/')
        if p.is_dir()
    ]

if __name__ == "__main__":
    user_input = input("Enter the root directory path: ").strip()
    root_dir = Path(user_input).expanduser().resolve()

    if not root_dir.is_dir():
        print(f"Invalid directory: {root_dir}")
        exit(1)

    second_level_names = get_second_level_dirs(root_dir)
    print(*second_level_names, sep="\n")
