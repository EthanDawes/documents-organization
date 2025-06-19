import json
from pathlib import Path

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

def test_load(tmp_path: Path):
    data = load_case("tests/test_load.yaml")

    projects_root = tmp_path / NAME_PROJECTS
    views_root = tmp_path / NAME_VIEW

    create_tree(tmp_path, data["start"])
    (projects_root / "projects.json").write_text(json.dumps(data["projects"]))

    ProjviewController(projects_root, views_root).cmd_load()

    actual = read_tree(tmp_path)
    assert actual == data["end"]
