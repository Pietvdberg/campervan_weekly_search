"""Verify layout-sensitive resources and command compatibility."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from campervan_search.report_html import render_html


class PackageLayoutTests(unittest.TestCase):
    def test_html_matches_the_pre_refactor_output(self):
        fixtures = Path(__file__).with_name("fixtures")
        data = json.loads((fixtures / "report_case.json").read_text())
        expected = (fixtures / "report.html").read_text()
        self.assertEqual(render_html(data), expected)

    def test_module_command_works_outside_repository(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "campervan_search.discover_listings",
                    "--help",
                ],
                cwd=folder,
                capture_output=True,
                text=True,
                check=True,
            )
        self.assertIn("--output", result.stdout)

    def test_existing_pi_command_paths_remain_usable(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            for script in ("autowereld_snapshot.py", "autowereld_upload.py"):
                result = subprocess.run(
                    [sys.executable, str(root / script), "--help"],
                    cwd=folder,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertIn("usage:", result.stdout)

    def test_empty_manual_input_creates_reports_outside_repository(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "campervan_search.camper_pipeline",
                    "--input",
                    str(root / "config/candidates.json"),
                ],
                cwd=folder,
                capture_output=True,
                text=True,
                check=True,
            )
            result = json.loads(
                Path(folder, "screening_results.json").read_text()
            )
            self.assertEqual(result["results"], [])
            self.assertTrue(Path(folder, "report.txt").is_file())
