"""Read-only workflow probes; these commands never send email."""

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def check_planner():
    """Exercise the installed planner against real Actions metadata."""
    with tempfile.TemporaryDirectory() as folder:
        event = Path(folder, "schedule.json")
        output = Path(folder, "outputs")
        event.write_text(json.dumps({"schedule": "0 13 * * 4"}))
        probe_env = dict(
            os.environ,
            GITHUB_EVENT_NAME="schedule",
            GITHUB_EVENT_PATH=str(event),
            GITHUB_OUTPUT=str(output),
        )
        subprocess.run(
            [sys.executable, "-m", "campervan_search.weekly_schedule"],
            env=probe_env,
            check=True,
        )
        plan = dict(
            line.split("=", 1) for line in output.read_text().splitlines()
        )
        if plan["mode"] != "production":
            raise RuntimeError("Scheduled planner chose the wrong audience")
        if plan["enabled"] not in ("true", "false"):
            raise RuntimeError("Planner did not return a valid decision")


def check_artifact():
    """Verify hidden-state restoration in a different Actions job."""
    path = (
        Path(os.environ["RUNNER_TEMP"])
        / "camper-history-restore/.search-state/history.json"
    )
    if json.loads(path.read_text()) != {"probe": "node24-artifact-roundtrip"}:
        raise RuntimeError("Restored history differs from the uploaded data")


def check_source_distribution():
    """Ensure the source archive includes offline test prerequisites."""
    archives = list(Path("dist").glob("*.tar.gz"))
    if len(archives) != 1:
        raise RuntimeError("Expected one source distribution")
    required = {
        "pyproject.toml",
        "config/candidates.json",
        "autowereld_snapshot.py",
        "autowereld_upload.py",
        "tests/__init__.py",
        "tests/helpers.py",
        "tests/fixtures/report.html",
        "tests/fixtures/report_case.json",
        ".github/actions/download-artifact/extract.py",
        "src/campervan_search/resources/dealer_registry.json",
        "src/campervan_search/resources/variant_research.json",
        "src/campervan_search/resources/report.html",
    }
    with tarfile.open(archives[0]) as archive:
        files = {name.split("/", 1)[-1] for name in archive.getnames()}
    missing = required - files
    if missing:
        raise RuntimeError(
            "Source distribution is incomplete: " + str(missing)
        )
    print("Source distribution contains test fixtures and runtime resources")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=("planner", "artifact", "sdist"))
    args = parser.parse_args()
    if args.check == "planner":
        check_planner()
    elif args.check == "artifact":
        check_artifact()
    else:
        check_source_distribution()


if __name__ == "__main__":
    main()
