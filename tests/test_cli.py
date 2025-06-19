import json
from pathlib import Path
import shutil

# Silly me didn't realize I made calls dependent on the real system (mklink), thus pyfakefs won't work
import yaml
from projview_cli import ProjviewController, NAME_PROJECTS, NAME_VIEW

def create_tree(root: Path, tree: dict):
    for name, subtree in tree.items():
        path = root / name
        if subtree is None:
            path.touch()
        else:
            path.mkdir()
            create_tree(path, subtree)

# project.json not checked because that is an implementation detail, not important behavior
def read_tree(root: Path):
    return {
        p.name: read_tree(p) if p.is_dir() else None
        for p in sorted(root.iterdir(), key=lambda x: x.name)
    }

def load_case(path):
    with open(path) as f:
        return yaml.safe_load(f)

def controller(tmp_path: Path, data: dict):
    projects_root = tmp_path / NAME_PROJECTS
    views_root = tmp_path / NAME_VIEW

    create_tree(tmp_path, data["start"])
    (projects_root / "projects.json").write_text(json.dumps(data["projects"]))

    return ProjviewController(projects_root, views_root)

def test_load(tmp_path: Path):
    data = load_case("tests/test_load.yaml")
    controller(tmp_path, data).cmd_load()

    actual = read_tree(tmp_path)
    assert actual == data["end"]

def test_save(tmp_path: Path):
    data = load_case("tests/test_save.yaml")
    c = controller(tmp_path, data)
    c.cmd_save()
    views_root = tmp_path / NAME_VIEW
    shutil.rmtree(views_root)
    views_root.mkdir()
    c.cmd_load()

    actual = read_tree(tmp_path)
    assert actual == data["end"]
