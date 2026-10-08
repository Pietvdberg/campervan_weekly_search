#!/usr/bin/env python3
"""Archive result JSON after one calendar month; delete after nine.

Age is based on the leading YYYY-MM-DD in the filename, not Git timestamps.
Only results/*.json and archive/*.json are managed.
"""
import argparse
import calendar
import re
import subprocess
from datetime import date
from pathlib import Path

DATE_PREFIX = re.compile(r"^(\\d{4}-\\d{2}-\\d{2})(?:-|\\.json$)")
ROOT = Path(__file__).resolve().parent


def months_after(day: date, count: int) -> date:
    month_index = day.year * 12 + day.month - 1 + count
    year, month_index = divmod(month_index, 12)
    month = month_index + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def file_date(path: Path):
    match = DATE_PREFIX.match(path.name)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--apply", action="store_true", help="Perform git mv/rm (default: dry run)")
    args = parser.parse_args()
    results, archive = ROOT / "results", ROOT / "archive"
    archive.mkdir(exist_ok=True)
    actions = []
    for folder in (results, archive):
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.json")):
            born = file_date(path)
            if born is None:
                print(f"SKIP unrecognized filename: {path.relative_to(ROOT)}")
                continue
            if born > args.today:
                print(f"SKIP future-dated filename: {path.relative_to(ROOT)}")
                continue
            relative = path.relative_to(ROOT)
            if args.today >= months_after(born, 9):
                actions.append(("DELETE", relative, None))
            elif folder == results and args.today >= months_after(born, 1):
                target = Path("archive") / path.name
                if (ROOT / target).exists():
                    print(f"SKIP destination already exists: {target}")
                    continue
                actions.append(("ARCHIVE", relative, target))

    for action, source, target in actions:
        print(f"{action}: {source}" + (f" -> {target}" if target else ""))
        if args.apply:
            cmd = ["git", "rm", "--", str(source)] if action == "DELETE" else ["git", "mv", "--", str(source), str(target)]
            subprocess.run(cmd, cwd=ROOT, check=True)
    print(f"{'Applied' if args.apply else 'Dry run:'} {len(actions)} change(s)")


if __name__ == "__main__":
    main()
