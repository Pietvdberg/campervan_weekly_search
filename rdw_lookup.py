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
from datetime import datetime
from urllib.request import Request, urlopen

BASE = "https://opendata.rdw.nl/resource"
DATASETS = {"vehicle": "m9d7-ebf2", "defects": "a34c-vvps", "catalogue": "hx2c-gt7k"}


def normalize_plate(plate):
    value = re.sub(r"[-\s]", "", plate.upper())
    if not re.fullmatch(r"[A-Z0-9]{6}", value):
        raise ValueError(f"Invalid Dutch registration: {plate!r}")
    return value


def fetch(dataset, plate, attempts=3):
    field = "gebrek_identificatie" if dataset == "catalogue" else "kenteken"
    url = f"{BASE}/{DATASETS[dataset]}.json?" + urlencode({field: plate, "$limit": 1000})
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


def summarize_defects(response, catalogue_by_code=None):
    """Summarize recorded APK defects without inventing code descriptions."""
    if response["status"] != "ok":
        return {
            "status": "unavailable",
            "entries": [],
            "caution": "RDW defect records could not be retrieved; no conclusion about defect history is possible.",
        }

    catalogue_by_code = catalogue_by_code or {}
    entries = []
    for record in response["records"]:
        raw_date = record.get("meld_datum_door_keuringsinstantie", "")
        try:
            inspection_date = datetime.strptime(raw_date, "%Y%m%d").date().isoformat()
        except ValueError:
            inspection_date = None
        raw_quantity = record.get("aantal_gebreken_geconstateerd")
        try:
            quantity = int(raw_quantity) if raw_quantity is not None else None
        except (ValueError, TypeError):
            quantity = None
        code = record.get("gebrek_identificatie")
        catalogue = catalogue_by_code.get(code, {})
        description = catalogue.get("gebrek_omschrijving")
        entries.append({
            "inspection_date": inspection_date,
            "inspection_date_raw": raw_date or None,
            "defect_code": code,
            "quantity": quantity,
            "description": description,
            "description_status": "official_rdw_catalogue" if description else "not_found_in_official_catalogue",
            "description_source": catalogue.get("_source"),
        })

    return {
        "status": "ok",
        "recorded_entry_count": len(entries),
        "entries": entries,
        "caution": (
            "RDW public APK defect entries are not a complete maintenance history "
            "and do not establish current mechanical condition. Descriptions are "
            "retrieved from the official RDW defect catalogue where available. "
            "No entries returned does not prove a vehicle has never had defects."
        ),
    }


def lookup(plate):
    plate = normalize_plate(plate)
    data = {name: fetch(name, plate) for name in ("vehicle", "defects")}
    catalogue_by_code = {}
    catalogue_errors = []
    if data["defects"]["status"] == "ok":
        codes = sorted({record.get("gebrek_identificatie") for record in data["defects"]["records"] if record.get("gebrek_identificatie")})
        for code in codes:
            catalogue = fetch("catalogue", code)
            if catalogue["status"] != "ok":
                catalogue_errors.append({"code": code, "error": catalogue["error"]})
                continue
            descriptions = [item for item in catalogue["records"] if item.get("gebrek_omschrijving")]
            if descriptions:
                selected = descriptions[0]
                catalogue_by_code[code] = {**selected, "_source": catalogue["source"]}
    return {
        "kenteken": plate,
        **data,
        "defect_catalogue_errors": catalogue_errors,
        "apk_defect_summary": summarize_defects(data["defects"], catalogue_by_code),
    }


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
    return int(any(entry[name]["status"] != "ok" for entry in results for name in ("vehicle", "defects")))


if __name__ == "__main__":
    sys.exit(main())
