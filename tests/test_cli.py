import json
import os
os.environ["PROJECTS_CONFIG"] = "tests/.documents_cli.yaml"

from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_filesystem_unittest import Patcher
import yaml
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

# project.json not checked because that is an implementation detail, not important behavior
def read_tree(fs: FakeFilesystem, root=ROOT):
    return {
        name: read_tree(fs, fs.joinpaths(root, name)) if fs.isdir(fs.joinpaths(root, name)) else None
        for name in fs.listdir(root)
    }

def load_case(path):
    with open(path) as f:
        return yaml.safe_load(f)

def test_load():
    data = load_case("tests/test_load.yaml")

    with Patcher() as patcher:
        # Importing projects_cli here causes recursion error (https://github.com/pytest-dev/pyfakefs/issues/1096)
        # Suggested workaround can't find 'pywintypes' (related to PEP 582 mode?)
        # This means I can't test config file creation (oh well)
        fs = patcher.fs
        create_tree(fs, data["start"])
        fs.create_file(ROOT + "/PROJECTS_ROOT/projects.json", contents=json.dumps(data["projects"]))

        projects_cli.cmd_load()

        actual = read_tree(fs)
        assert actual == data["end"]
