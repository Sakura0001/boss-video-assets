#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path

from sync_repo_copy import compare_trees, sync_tree


class SyncRepoCopyTest(unittest.TestCase):
    def test_sync_copies_source_removes_stale_and_excludes_runtime_files(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = root / "source"
            destination = root / "destination"
            (source / "references").mkdir(parents=True)
            (source / "scripts" / "__pycache__").mkdir(parents=True)
            destination.mkdir()

            (source / "SKILL.md").write_text("skill\n", encoding="utf-8")
            (source / "references" / "policy.md").write_text("policy\n", encoding="utf-8")
            (source / "scripts" / "runtime_store.py").write_text("pass\n", encoding="utf-8")
            (source / "scripts" / "__pycache__" / "runtime.pyc").write_bytes(b"cache")
            (source / "state.sqlite3").write_bytes(b"private")
            (source / ".DS_Store").write_bytes(b"metadata")
            (destination / "stale.md").write_text("stale\n", encoding="utf-8")

            self.assertTrue(compare_trees(source, destination))
            sync_tree(source, destination)

            self.assertEqual(compare_trees(source, destination), [])
            self.assertTrue((destination / "SKILL.md").exists())
            self.assertTrue((destination / "references" / "policy.md").exists())
            self.assertTrue((destination / "scripts" / "runtime_store.py").exists())
            self.assertFalse((destination / "stale.md").exists())
            self.assertFalse((destination / "state.sqlite3").exists())
            self.assertFalse((destination / ".DS_Store").exists())
            self.assertFalse((destination / "scripts" / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
