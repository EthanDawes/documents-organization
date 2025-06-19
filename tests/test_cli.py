import os
os.environ["PROJECTS_CONFIG"] = "tests/.documents_cli.yaml"

from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_filesystem_unittest import Patcher
import yaml
from pathlib import Path
import projects_cli

ROOT = "/test_root"

def create_tree(fs: FakeFilesystem, tree, root=ROOT):
    for name, subtree in tree.items():
        path = fs.joinpaths(root, name)
        if subtree is None:
            fs.create_file(path)
        else:
            fs.create_dir(path)
            create_tree(fs, subtree, path)

def read_tree(fs: FakeFilesystem, root=ROOT):
    return {
        name: read_tree(fs, fs.joinpaths(root, name)) if fs.isdir(fs.joinpaths(root, name)) else None
        for name in fs.listdir(root)
    }

def create_config(fs: FakeFilesystem):
    config_path = Path("/.documents_cli.yaml")
    fs.create_file(config_path, contents="debug: true\nlog_level: INFO")

def load_case(path):
    with open(path) as f:
        return yaml.safe_load(f)

def test_file_structure_transformation():
    data = load_case("tests/case1.yaml")

    with Patcher() as patcher:
        # Importing projects_cli here causes recursion error (https://github.com/pytest-dev/pyfakefs/issues/1096)
        # Suggested workaround can't find 'pywintypes' (related to PEP 582 mode?)
        # This means I can't test config file creation (oh well)
        fs = patcher.fs
        create_tree(fs, data["start"])

        projects_cli.where()

        actual = read_tree(fs)
        assert actual == data["end"]
