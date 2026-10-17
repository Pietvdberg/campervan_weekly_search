"""Separate usable development discovery from complete source coverage."""
import argparse
import json
from pathlib import Path

from source_catalog import SOURCE_NAMES, CORE_SOURCE_NAMES, OPTIONAL_RSS_SOURCES


def summarize(data):
    coverage = data.get("source_coverage", {})
    candidates = data.get("candidates", [])
    bound = [candidate for candidate in candidates if candidate.get("individual_listing_confirmed") is True]
    bound_sources = {candidate.get("source") for candidate in bound}
    missing = [source for source in SOURCE_NAMES if source not in bound_sources]
    coverage_recorded = isinstance(coverage, dict) and all(isinstance(coverage.get(source), dict) for source in SOURCE_NAMES)
    core_recorded = isinstance(coverage, dict) and all(isinstance(coverage.get(source), dict) for source in CORE_SOURCE_NAMES)
    core_bound = [candidate for candidate in bound if candidate.get("source") in CORE_SOURCE_NAMES]
    core_missing = [source for source in CORE_SOURCE_NAMES if source not in bound_sources]
    return {"candidate_pages": len(candidates), "identity_bound_candidates": len(bound),
            "coverage_recorded_for_all_sources": coverage_recorded,
            "sources_without_identity_bound_candidates": missing,
            "coverage_recorded_for_core_sources": core_recorded,
            "optional_rss_sources": list(OPTIONAL_RSS_SOURCES),
            "core_sources_without_identity_bound_candidates": core_missing,
            "development_discovery_verified": bool(core_bound) and core_recorded,
            "all_core_source_groups_have_bound_candidates": not core_missing and core_recorded,
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
