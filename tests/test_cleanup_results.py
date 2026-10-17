"""Retention must use the requested checkout, not the installed
package.
"""

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from campervan_search.cleanup_results import main


class CleanupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "results").mkdir()
        for day in ("2026-08-01", "2025-01-01", "2026-10-01"):
            (self.root / "results" / (day + ".json")).write_text("{}\n")

    def run_cleanup(self, apply=False):
        args = [
            "campervan-cleanup",
            "--root",
            str(self.root),
            "--today",
            "2026-10-17",
        ]
        if apply:
            args.append("--apply")
        with (
            patch.object(sys, "argv", args),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            main()

    def test_dry_run_does_not_create_or_move_files(self):
        self.run_cleanup()
        self.assertFalse((self.root / "archive").exists())
        self.assertEqual(len(list((self.root / "results").iterdir())), 3)

    def test_installed_cleanup_uses_explicit_checkout_root(self):
        for command in (
            ["git", "init", "-q"],
            ["git", "add", "results"],
            [
                "git",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.test",
                "commit",
                "-qm",
                "Initial retention fixtures",
            ],
        ):
            subprocess.run(command, cwd=self.root, check=True)
        with tempfile.TemporaryDirectory() as other:
            with contextlib.chdir(other):
                self.run_cleanup(apply=True)
        self.assertTrue((self.root / "archive/2026-08-01.json").exists())
        self.assertFalse((self.root / "results/2025-01-01.json").exists())
        self.assertTrue((self.root / "results/2026-10-01.json").exists())

    def test_apply_requires_a_checkout(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.run_cleanup(apply=True)
        self.assertFalse((self.root / "archive").exists())
