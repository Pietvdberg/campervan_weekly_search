"""Separate usable development discovery from complete source coverage."""
import argparse
import json
from pathlib import Path

from source_catalog import SOURCE_NAMES


def summarize(data):
    coverage = data.get("source_coverage", {})
    candidates = data.get("candidates", [])
    bound = [candidate for candidate in candidates if candidate.get("individual_listing_confirmed") is True]
    bound_sources = {candidate.get("source") for candidate in bound}
    missing = [source for source in SOURCE_NAMES if source not in bound_sources]
    coverage_recorded = isinstance(coverage, dict) and all(isinstance(coverage.get(source), dict) for source in SOURCE_NAMES)
    return {"candidate_pages": len(candidates), "identity_bound_candidates": len(bound),
            "coverage_recorded_for_all_sources": coverage_recorded,
            "sources_without_identity_bound_candidates": missing,
            "development_discovery_verified": bool(bound) and coverage_recorded,
            "all_source_groups_have_bound_candidates": not missing and coverage_recorded,
            "production_ready": False,
            "note": "Source coverage is a bounded sample, not exhaustive inventory or independent availability verification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    args = parser.parse_args()
    result = summarize(json.loads(Path(args.input).read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2))
    return 0 if result["development_discovery_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
