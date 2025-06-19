# Abandoning automated testing for now due to lack of understanding and fear for my files

from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_filesystem_unittest import Patcher
import yaml
from pathlib import Path

ROOT = "test_root"

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
        import projects_cli
        fs = patcher.fs
        create_tree(fs, data["start"])

        # projects_cli

        actual = read_tree(fs)
        print(actual)
        assert actual == data["end"]
