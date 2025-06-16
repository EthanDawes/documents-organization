import argparse
import json
import os
import shutil
from abc import abstractmethod, ABC
from json import JSONDecodeError
from pathlib import Path
from subprocess import run

import winshell
from InquirerPy import inquirer

PROJECTS_ROOT = Path(os.environ['PROJECTS_ROOT'])
assert PROJECTS_ROOT
DOCS_VIEW_ROOT = Path(os.environ['DOCS_VIEW_ROOT'])
assert DOCS_VIEW_ROOT
PROJECTS_FILE = PROJECTS_ROOT / 'projects.json'

PathLike = str | bytes | os.PathLike
ProjectsSpec = dict[str, list[str]]


class ViewBackend(ABC):
    @staticmethod
    @abstractmethod
    def mklink(src: Path, dst: Path) -> None:
        ...


class JunctionBackend(ViewBackend):
    @staticmethod
    def mklink(src: Path, dst: Path) -> None:
        run(['cmd', '/c', 'mklink', '/J', str(dst), str(src)], check=True)


class ShortcutBackend(ViewBackend):
    @staticmethod
    def mklink(src: Path, dst: Path) -> None:
        rel_path = f"%PROJECTS_ROOT%\\{src.name}"
        print(f"Creating shortcut from {rel_path} to {dst}")
        with winshell.shortcut(str(dst)) as shortcut:
            shortcut.path = rel_path
            shortcut.working_directory = "%PROJECTS_ROOT%"


implementation = ShortcutBackend()


def assert_valid_folder(path: Path):
    assert path.exists()
    assert path.is_dir()
    error_msg = f"You cannot perform this operation on the %s folder ({path})"
    if path == PROJECTS_ROOT:
        raise ValueError(error_msg % "PROJECTS_ROOT")
    elif path == DOCS_VIEW_ROOT:
        raise ValueError(error_msg % "DOCS_VIEW_ROOT")


def load_projects() -> ProjectsSpec:
    try:
        with PROJECTS_FILE.open() as f:
            return json.load(f)
    except (JSONDecodeError, FileNotFoundError):
        return {}


def save_projects(projects: ProjectsSpec):
    with PROJECTS_FILE.open('w') as f:
        json.dump(projects, f, indent=2)


def append_projects(name: str, path: str):
    projects = load_projects()
    projects.setdefault(name, []).append(path)
    save_projects(projects)
    cmd_load()


def delete_project_view(path: Path):
    if path.is_junction() or path.is_file():
        path.unlink()
    elif path.is_dir():
        try:
            path.rmdir()
        except OSError:
            print(f'Directory "{path.relative_to(DOCS_VIEW_ROOT)}" is not empty!')
    else:
        raise NotImplementedError('This should not happen!')


def mklink(src: Path, dst: Path):
    assert_valid_folder(src)
    if isinstance(implementation, ShortcutBackend):
        dst = dst.with_suffix(".lnk")
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        implementation.mklink(src, dst)


def cmd_save():
    projects: ProjectsSpec = {}
    for folder in iter_folders(DOCS_VIEW_ROOT):
        if folder.is_junction() or folder.is_file():
            rel = str(folder.parent.relative_to(DOCS_VIEW_ROOT))
            projects.setdefault(folder.stem, []).append(rel)
    save_projects(projects)


def iter_folders(path: PathLike):
    """Iterate bottom-up all folders. Won't recurse into project folders"""
    projects = list(load_projects().keys())
    for dir_entry in os.scandir(path):
        if dir_entry.is_file() and not dir_entry.name.endswith(".lnk"):
            continue
        if dir_entry.name not in projects and dir_entry.is_dir():
            yield from iter_folders(dir_entry.path)
        yield Path(dir_entry.path)


def cmd_load():
    projects = load_projects()
    paths: list[str] = []
    for project, view_dirs in projects.items():
        for view_dir in view_dirs:
            target = PROJECTS_ROOT / project
            link = DOCS_VIEW_ROOT / view_dir / project
            paths.append(str(link))
            mklink(target, link)

    for existing in iter_folders(DOCS_VIEW_ROOT):
        if not any(path.startswith(str(existing.with_suffix(""))) for path in paths):
            print(f"Will delete {existing.relative_to(DOCS_VIEW_ROOT)}")
            delete_project_view(existing)


def cmd_link(project: str = None):
    all_projects = [f.name for f in os.scandir(PROJECTS_ROOT) if f.is_dir()]
    if not project:
        project = inquirer.fuzzy(
            message="Select project:",
            choices=all_projects,
        ).execute()
    path = Path.cwd().relative_to(DOCS_VIEW_ROOT)
    append_projects(project, str(path))


def cmd_link_to(target_path: str):
    cwd = Path.cwd()
    project = cwd.name
    assert_valid_folder(cwd)
    append_projects(project, target_path)


def move_and_link(src: Path, dst_view: str):
    assert_valid_folder(src)
    print(f"Moving {src.name} to DOCS_VIEW_ROOT & creating junction {dst_view}")
    project = src.name
    shutil.move(src, PROJECTS_ROOT)
    append_projects(project, dst_view)


def cmd_convert(project: str):
    convert_path = Path.cwd()
    if project != "*":
        convert_path = convert_path / project
    assert_valid_folder(convert_path)
    items = convert_path.iterdir() if project == "*" else [convert_path]
    for item in items:
        if item.is_dir():
            try:
                dst_view = item.relative_to(PROJECTS_ROOT).parent
            except ValueError:
                dst_view = item.relative_to(DOCS_VIEW_ROOT).parent
            move_and_link(item, str(dst_view))
    print(f'Must manually delete "{convert_path.name}"')


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='cmd', required=True)

    subparsers.add_parser('save')
    subparsers.add_parser('load')

    convert_parser = subparsers.add_parser('convert')
    convert_parser.add_argument('project', help="* will treat all dirs in cwd as project. Pass folder name to only convert 1")

    link_parser = subparsers.add_parser('link')
    link_parser.add_argument('project', nargs='?', default=None)

    link_to_parser = subparsers.add_parser('link-to')
    link_to_parser.add_argument('path')

    args = parser.parse_args()

    match args.cmd:
        case 'save': cmd_save()
        case 'load': cmd_load()
        case 'link': cmd_link(args.project)
        case 'link-to': cmd_link_to(args.path)
        case 'convert': cmd_convert(args.project)


if __name__ == '__main__':
    main()
