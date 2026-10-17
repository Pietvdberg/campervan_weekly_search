# Camper van weekly search — development pipeline

The repository combines bounded six-source listing discovery, conservative
vehicle screening, RDW lookups, text/HTML reports and development email delivery.
It is not yet an automated production weekly search. See
[verification status](docs/verification-status.md) and the
[strict review](STRICT_REVIEW.md) for scope and outstanding gaps.

## Local discovery and screening

```bash
python3 discover_listings.py --output discovered_candidates.json
python3 camper_pipeline.py --input discovered_candidates.json
python3 verify_discovery.py discovered_candidates.json
python3 validate_search.py --discovery discovered_candidates.json --screening screening_results.json
```

The outputs include `screening_results.json`, `report.txt`, `research_pack.json` and
`reviewed_evidence_template.json`. Validation writes `validation_summary.json`.
See the [dated live validation](docs/live-validation-2026-10-17.md). No mail is sent by these
commands. Optional reviewed conversion evidence has a separate documented
[contract](docs/conversion-evidence.md). Source groups, inventory seeds and model
patterns are centralized in `source_catalog.py`. The supplied handover is reconciled in [requirements](docs/requirements.md);
the [v2 specification](docs/camper_van_search_specification_v2.md) now supplies
conversion criteria. Actual reviewed vehicle evidence remains outstanding. See
[v2 adoption and acceptance gaps](docs/specification-v2-adoption.md).

## RDW request handoff

`rdw_lookup.py` retrieves actual official RDW registration records (`m9d7-ebf2`) and recorded APK defects (`a34c-vvps`) for Dutch number plates.

## Automated handoff from ChatGPT

1. During the Thursday camper search, find candidates and independently confirm their number plates.
2. Create a new GitHub file `requests/YYYY-MM-DD.txt` containing those plates separated by spaces or newlines. If a retry is needed, use a unique suffix, such as `requests/YYYY-MM-DD-retry1.txt`.
3. A push-triggered GitHub Action runs `rdw_lookup.py`, uploads a JSON artifact, and, **only when the entire lookup succeeds**, commits `results/YYYY-MM-DD.json` (or matching suffixed filename) to the repository.
4. Read that exact results file through the GitHub connector and match records to the corresponding listing plates. Incorporate verified fields into the camper report and email.

If the results file is missing, failed, or late, never imply RDW verification succeeded. Use direct RDW queries as fallback where possible. **The GitHub workflow has not yet been verified end-to-end.**

## Local invocation

```bash
python3 rdw_lookup.py VL-034-B --output rdw_results.json
```

## Manual invocation

Go to **Actions → RDW vehicle and APK checks → Run workflow**, enter plates separated by commas or spaces, and download the resulting workflow artifact. Manual runs do not commit a result file.

**Limitations:** The script returns raw RDW records; the report must interpret the correct fields carefully. No defect records does not prove a fault-free vehicle, and APK approval does not establish service history. The repository is public, so requests and results are publicly visible; only submit public vehicle registration numbers and never secrets.

## Request parsing and success criteria

`python3 rdw_lookup.py --input requests/YYYY-MM-DD.txt --output rdw_results.json`
reads every comma/whitespace-separated plate, validates the full batch before
network access, and deduplicates registrations. A lookup succeeds only with one
matching registration, successful defect retrieval, and official descriptions
for every returned defect code. Empty defect history is valid but is not proof
of a fault-free vehicle. A capped response fails rather than claiming complete
history. Failed batches still write audit JSON and exit nonzero, preventing
publication as successful workflow results.

Run offline regressions with `python3 -m unittest discover -v`.
