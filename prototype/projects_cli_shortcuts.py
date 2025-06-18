import os
import shutil
from pathlib import Path
import winshell

PROJECTS_ROOT = Path(os.environ['PROJECTS_ROOT'])
assert(PROJECTS_ROOT is not None)
DOCUMENTS_ROOT = PROJECTS_ROOT.parent


def assert_valid_folder(path: Path):
    error_msg = f"You cannot perform this operation on the %s folder ({path})"
    if path == PROJECTS_ROOT:
        raise ValueError(error_msg.format("PROJECTS_ROOT"))
    elif path == DOCUMENTS_ROOT:
        raise ValueError(error_msg.format("DOCUMENTS_ROOT"))


def create_shortcut(src: Path, dst: Path):
    assert_valid_folder(src)
    rel_path = f"%PROJECTS_ROOT%\\{src.name}"
    print(f"Creating shortcut from {dst} to {rel_path}")
    with winshell.shortcut(str(dst)) as shortcut:
        shortcut.path = rel_path
        shortcut.working_directory = "%PROJECTS_ROOT%"


def move_and_link(src: Path, dst_dir: Path, shortcut_location: Path):
    assert(src != Path.cwd())  # TODO: find some workaround
    assert_valid_folder(src)
    dst = dst_dir / src.name
    print(f"Moving {src} to {dst}")
    shutil.move(str(src), dst)
    shortcut_path = shortcut_location / f"{src.name}.lnk"
    create_shortcut(dst, shortcut_path)


def convert():
    cwd = Path.cwd()
    assert_valid_folder(cwd)
    for item in cwd.iterdir():
        if item.is_dir():
            move_and_link(item, PROJECTS_ROOT, cwd)


def find():
    cwd = Path.cwd()
    assert_valid_folder(cwd)
    project_name = cwd.name
    for path in DOCUMENTS_ROOT.rglob(f"{project_name}.lnk"):
        if path.is_file():
            target = winshell.shortcut(str(path)).path
            if Path(target).name == project_name:
                print(path)


def rename(new_name: str):
    cwd = Path.cwd()
    assert_valid_folder(cwd)
    old_name = cwd.name
    for path in DOCUMENTS_ROOT.rglob(f"{old_name}.lnk"):
        sc = winshell.shortcut(str(path))
        if Path(sc.path).name == old_name:
            new_target = f"%PROJECTS_ROOT%\\{new_name}"
            with winshell.shortcut(str(path)) as shortcut:
                shortcut.path = new_target
                shortcut.working_directory = "%PROJECTS_ROOT%"
    new_path = PROJECTS_ROOT / new_name
    cwd.rename(new_path)


def create():
    cwd = Path.cwd()
    assert_valid_folder(cwd)
    if cwd.parent == PROJECTS_ROOT:
        shortcut_path = cwd.parent.parent / f"{cwd.name}.lnk"
        create_shortcut(cwd, shortcut_path)
    else:
        move_and_link(cwd, PROJECTS_ROOT, cwd.parent)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action")

    subparsers.add_parser("convert")
    subparsers.add_parser("find")
    subparsers.add_parser("create")

    rename_parser = subparsers.add_parser("rename")
    rename_parser.add_argument("new_name")

    args = parser.parse_args()

    match args.action:
        case "convert": convert()
        case "find": find()
        case "create": create()
        case "rename": rename(args.new_name)
        case _: parser.print_help()


if __name__ == "__main__":
    main()
