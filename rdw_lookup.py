#!/usr/bin/env python3
"""Fetch public RDW vehicle registration and recorded APK defects.

Usage: python rdw_lookup.py VL-034-B [OTHER-PLATE ...] [--output results.json]
"""
import argparse
import json
import os
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://opendata.rdw.nl/resource"
DATASETS = {"vehicle": "m9d7-ebf2", "defects": "a34c-vvps"}


def normalize_plate(plate):
    value = re.sub(r"[-\s]", "", plate.upper())
    if not re.fullmatch(r"[A-Z0-9]{6}", value):
        raise ValueError(f"Invalid Dutch registration: {plate!r}")
    return value


def fetch(dataset, plate, attempts=3):
    url = f"{BASE}/{DATASETS[dataset]}.json?" + urlencode({"kenteken": plate, "$limit": 1000})
    headers = {"Accept": "application/json", "User-Agent": "campervan-weekly-search/1.0"}
    token = os.environ.get("SOCRATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    for attempt in range(attempts):
        try:
            with urlopen(Request(url, headers=headers), timeout=20) as response:
                records = json.load(response)
            if not isinstance(records, list):
                raise ValueError("Unexpected RDW response")
            return {"status": "ok", "records": records, "source": url}
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                return {"status": "error", "error": f"HTTP {exc.code}", "source": url}
        except (URLError, TimeoutError, ValueError) as exc:
            if attempt == attempts - 1:
                return {"status": "error", "error": str(exc), "source": url}
        time.sleep(2 ** attempt)


def lookup(plate):
    plate = normalize_plate(plate)
    return {"kenteken": plate, **{name: fetch(name, plate) for name in DATASETS}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plates", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        results = [lookup(plate) for plate in args.plates]
    except ValueError as exc:
        parser.error(str(exc))
    data = json.dumps({"results": results}, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(data + "\n")
    else:
        print(data)
    return int(any(entry[name]["status"] != "ok" for entry in results for name in DATASETS))


if __name__ == "__main__":
    sys.exit(main())
