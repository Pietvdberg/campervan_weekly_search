# Camper van weekly search

The repository combines bounded six-source listing discovery, conservative
vehicle screening, RDW lookups and text/HTML email reports. The production workflow
starts each Thursday at 15:00 Europe/Amsterdam (including DST), with delivery to
the two configured production recipients. Manual searches email Hotmail only;
push CI sends no email. Delivery-aware history and a durable outbox preserve
unreported leads and recover the original email without blind resubmission. See
[production delivery and release evidence](docs/weekly-production-delivery.md),
[verification status](docs/verification-status.md) and the
[strict review](docs/strict-review.md) for scope and outstanding gaps.
The [weekly search design](docs/useful-weekly-search.md) distinguishes advertised
search fit from purchase readiness and documents ranking, durable history and
coverage monitoring.

## Installation and layout

Python 3.11 or newer is required. Install the package before running commands:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

```text
src/campervan_search/       Application modules
  resources/               Bundled registries and HTML report template
tests/                     Offline regression tests and fixtures
config/candidates.json     Empty manual-screening input
docs/                      Requirements, operations and review records
scripts/                   Development, CI and Pi installation helpers
.github/                   Workflows and local composite actions
data/                      External unverified RSS snapshot
requests/, results/        Existing RDW request/result handoff
archive/                   Retained older results
pyproject.toml             Packaging, CLI entry points and style settings
```

Two small root launchers, `autowereld_snapshot.py` and
`autowereld_upload.py`, preserve command paths already used by installed Pi
timers. Application code lives in `src/`; new installations use the declared
`campervan-rss-collect` and `campervan-rss-upload` commands. The installer creates
a virtual environment, without enabling or changing the timer's cadence.

Dealer and variant registries are bundled under
`src/campervan_search/resources/`. Runtime snapshots and generated reports
remain separate from the installed package.

## Development checks

```bash
python -m black --check .
python -m ruff check .
python -m unittest discover -s tests -t . -v
python -m build
```

Black and Ruff enforce 79-column code, 72-column comments/docstrings, import
ordering and the enabled
PEP 8/error checks in `pyproject.toml`. CI checks formatting, lint, regressions,
wheel installation outside the checkout and hidden-state artifact restoration.
See [the layout migration](docs/package-layout.md) for operational details.

## Local discovery and screening

```bash
campervan-discover --output discovered_candidates.json
campervan-screen --input discovered_candidates.json
campervan-verify-discovery discovered_candidates.json
campervan-validate --discovery discovered_candidates.json \
  --screening screening_results.json
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

If the results file is missing, failed, or late, never imply RDW verification succeeded. Use direct RDW queries as fallback where possible. This RDW request handoff is separate from the weekly search service; inspect its specific Actions run before claiming success.

## Local invocation

```bash
python3 -m campervan_search.rdw_lookup VL-034-B --output rdw_results.json
```

## Manual invocation

Go to **Actions → RDW vehicle and APK checks → Run workflow**, enter plates separated by commas or spaces, and download the resulting workflow artifact. Manual runs do not commit a result file.

**Limitations:** The script returns raw RDW records; the report must interpret the correct fields carefully. No defect records does not prove a fault-free vehicle, and APK approval does not establish service history. The repository is public, so requests and results are publicly visible; only submit public vehicle registration numbers and never secrets.

## Request parsing and success criteria

`python3 -m campervan_search.rdw_lookup --input requests/YYYY-MM-DD.txt --output rdw_results.json`
reads every comma/whitespace-separated plate, validates the full batch before
network access, and deduplicates registrations. A lookup succeeds only with one
matching registration, successful defect retrieval, and official descriptions
for every returned defect code. Empty defect history is valid but is not proof
of a fault-free vehicle. A capped response fails rather than claiming complete
history. Failed batches still write audit JSON and exit nonzero, preventing
publication as successful workflow results.

Run offline regressions with `python3 -m unittest discover -s tests -t . -v`.
