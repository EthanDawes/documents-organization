import argparse
import json
import os
import shutil
from abc import abstractmethod, ABC
from json import JSONDecodeError
from pathlib import Path
from subprocess import run
import yaml

import winshell
from InquirerPy import inquirer

NAME_PROJECTS = "PROJECTS_ROOT"
NAME_VIEW = "DOCS_VIEW_ROOT"


def get_config():
    PROFILE_INFO_FILE = Path(os.environ["PROJECTS_CONFIG"] or (Path.home() / ".projview_cli.yaml"))
    try:
        with PROFILE_INFO_FILE.open() as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        with PROFILE_INFO_FILE.open("w") as file:
            config = {
                "profile": "projects",
                NAME_PROJECTS: None,
                NAME_VIEW: None,
            }
            yaml.safe_dump(config, file)
            raise ValueError(f"Must configure {NAME_PROJECTS} and {NAME_VIEW} in {PROFILE_INFO_FILE}")
    return config


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
        print(f"Creating shortcut from %{NAME_PROJECTS}%\\{src.name} to {dst}")
        with winshell.shortcut(str(dst.absolute())) as shortcut:
            shortcut.path = str(src.absolute())


class ProjviewController:
    def __init__(self, projects_root: Path, docs_view_root: Path, profile: str="projects", implementation: ViewBackend=ShortcutBackend()):
        self.implementation = implementation
        self.PROJECTS_ROOT = projects_root
        assert self.PROJECTS_ROOT
        self.DOCS_VIEW_ROOT = docs_view_root
        assert self.DOCS_VIEW_ROOT
        self.PROJECTS_FILE = self.PROJECTS_ROOT / (profile + '.json')

    def assert_valid_folder(self, path: Path):
        assert path.exists()
        assert path.is_dir()
        error_msg = f"You cannot perform this operation on the %s folder ({path})"
        if path == self.PROJECTS_ROOT:
            raise ValueError(error_msg % NAME_PROJECTS)
        elif path == self.DOCS_VIEW_ROOT:
            raise ValueError(error_msg % NAME_VIEW)

    def load_projects(self) -> ProjectsSpec:
        try:
            with self.PROJECTS_FILE.open() as f:
                return json.load(f)
        except (JSONDecodeError, FileNotFoundError):
            return {}

    def save_projects(self, projects: ProjectsSpec):
        with self.PROJECTS_FILE.open('w') as f:
            json.dump(projects, f, indent=2)

    def append_projects(self, name: str, path: str):
        projects = self.load_projects()
        projects.setdefault(name, []).append(path)
        self.save_projects(projects)
        self.cmd_load()

    def delete_project_view(self, path: Path):
        if path.is_junction() or path.is_file():
            path.unlink()
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                print(f'Directory "{path.relative_to(self.DOCS_VIEW_ROOT)}" is not empty!')
        else:
            raise NotImplementedError('This should not happen!')

    def mklink(self, src: Path, dst: Path):
        self.assert_valid_folder(src)
        if isinstance(self.implementation, ShortcutBackend):
            dst = dst.with_suffix(".lnk")
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            self.implementation.mklink(src, dst)

    def cmd_save(self):
        projects: ProjectsSpec = {}
        for folder in self.iter_folders(self.DOCS_VIEW_ROOT):
            if folder.is_junction() or folder.is_file():
                rel = str(folder.parent.relative_to(self.DOCS_VIEW_ROOT))
                projects.setdefault(folder.stem, []).append(rel)
        self.save_projects(projects)

    def iter_folders(self, path: PathLike):
        """Iterate bottom-up all folders. Won't recurse into project folders"""
        projects = list(self.load_projects().keys())
        for dir_entry in os.scandir(path):
            if dir_entry.is_file() and not dir_entry.name.endswith(".lnk"):
                continue
            if dir_entry.name not in projects and dir_entry.is_dir():
                yield from self.iter_folders(dir_entry.path)
            yield Path(dir_entry.path)

    def cmd_load(self):
        projects = self.load_projects()
        paths: list[str] = []
        for project, view_dirs in projects.items():
            for view_dir in view_dirs:
                target = self.PROJECTS_ROOT / project
                link = self.DOCS_VIEW_ROOT / view_dir / project
                paths.append(str(link))
                self.mklink(target, link)

        for existing in self.iter_folders(self.DOCS_VIEW_ROOT):
            if not any(path.startswith(str(existing.with_suffix(""))) for path in paths):
                print(f"Will delete {existing.relative_to(self.DOCS_VIEW_ROOT)}")
                self.delete_project_view(existing)

    def cmd_link(self, project: str = None):
        all_projects = [f.name for f in os.scandir(self.PROJECTS_ROOT) if f.is_dir()]
        if not project:
            project = inquirer.fuzzy(
                message="Select project:",
                choices=all_projects,
            ).execute()
        path = Path.cwd().relative_to(self.DOCS_VIEW_ROOT)
        self.append_projects(project, str(path))

    def cmd_link_to(self, target_path: str):
        cwd = Path.cwd()
        project = cwd.name
        self.assert_valid_folder(cwd)
        self.append_projects(project, target_path)

    def move_and_link(self, src: Path, dst_view: str):
        self.assert_valid_folder(src)
        print(f"Moving {src.name} to self.DOCS_VIEW_ROOT & creating junction {dst_view}")
        project = src.name
        shutil.move(src, self.PROJECTS_ROOT)
        self.append_projects(project, dst_view)

    def cmd_convert(self, project: str):
        convert_path = Path.cwd()
        if project != "*":
            convert_path = convert_path / project
        self.assert_valid_folder(convert_path)
        items = convert_path.iterdir() if project == "*" else [convert_path]
        for item in items:
            if item.is_dir():
                try:
                    dst_view = item.relative_to(self.PROJECTS_ROOT).parent
                except ValueError:
                    dst_view = item.relative_to(self.DOCS_VIEW_ROOT).parent
                self.move_and_link(item, str(dst_view))
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

    config = get_config()
    controller = ProjviewController(
        Path(config[NAME_PROJECTS]),
        Path(config[NAME_VIEW]),
        config["profile"]
    )

    match args.cmd:
        case 'save': controller.cmd_save()
        case 'load': controller.cmd_load()
        case 'link': controller.cmd_link(args.project)
        case 'link-to': controller.cmd_link_to(args.path)
        case 'convert': controller.cmd_convert(args.project)


if __name__ == '__main__':
    main()
