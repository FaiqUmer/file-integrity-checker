import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import file_integrity_checker as fic


def write(folder, name, text):
    path = os.path.join(folder, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self._quiet = contextlib.redirect_stdout(io.StringIO())
        self._quiet.__enter__()
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = os.path.join(self.tmp.name, "data")
        os.makedirs(self.folder)
        self.baseline = os.path.join(self.tmp.name, "baseline.json")
        write(self.folder, "a.txt", "hello")
        write(self.folder, "b.txt", "world")
        write(self.folder, "sub/c.txt", "nested")

    def tearDown(self):
        self._quiet.__exit__(None, None, None)
        self.tmp.cleanup()

    def test_hash_matches_hashlib(self):
        p = os.path.join(self.folder, "a.txt")
        self.assertEqual(fic.hash_file(p), hashlib.sha256(b"hello").hexdigest())

    def test_baseline_contains_all_files_including_subfolders(self):
        fic.create_baseline(self.folder, self.baseline)
        with open(self.baseline) as f:
            data = json.load(f)
        self.assertEqual(set(data), {"a.txt", "b.txt", os.path.join("sub", "c.txt")})

    def test_unchanged_folder_is_ok(self):
        fic.create_baseline(self.folder, self.baseline)
        self.assertEqual(fic.main(["check", self.folder, "--baseline", self.baseline]), 0)

    def test_detects_modified_added_deleted(self):
        fic.create_baseline(self.folder, self.baseline)
        write(self.folder, "a.txt", "tampered")
        os.remove(os.path.join(self.folder, "b.txt"))
        write(self.folder, "d.txt", "new")
        with open(self.baseline) as f:
            old = json.load(f)
        new = fic.scan_folder(self.folder)
        modified, added, deleted = fic.compare(old, new)
        self.assertEqual(modified, ["a.txt"])
        self.assertEqual(added, ["d.txt"])
        self.assertEqual(deleted, ["b.txt"])
        self.assertEqual(fic.main(["check", self.folder, "--baseline", self.baseline]), 1)

    def test_missing_baseline_returns_error(self):
        self.assertEqual(fic.main(["check", self.folder, "--baseline", self.baseline]), 2)

    def test_missing_folder_returns_error(self):
        self.assertEqual(fic.main(["init", os.path.join(self.tmp.name, "nope")]), 2)

    def test_baseline_inside_folder_is_ignored(self):
        inside = os.path.join(self.folder, "baseline.json")
        fic.create_baseline(self.folder, inside)
        self.assertEqual(fic.main(["check", self.folder, "--baseline", inside]), 0)


if __name__ == "__main__":
    unittest.main()
