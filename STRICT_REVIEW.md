# Strict solution review

Reviewed upstream main `25e9105f9a2fae390de3f35bb38a857a6b179b74` on 2026-10-17.

## Scope and evidence

Read every Python module, test module, workflow, installer and documentation file,
plus the checked-in candidate, request, result and RSS data. Inspected the latest
15 GitHub Actions runs: mixed integration failures/successes; latest integration
run [38977667392](https://github.com/Pietvdberg/campervan_weekly_search/actions/runs/38977667392)
is green. That status does not establish complete discovery or qualified vehicles.

`context.md` (including `CONTEXT.md`) is absent from the repository and the
workspace. Requirements are inferred from the repository documentation and code:
high roof, cab A/C, conversion suitability, <=100 km driving distance from Bergen
op Zoom, <=EUR 8,000 inclusive of VAT, current individual listing and confirmed
registration. Full alignment with the missing context cannot be scored confidently.

Git clone failed because the configured network proxy was unreachable. Files were
retrieved through the GitHub connector using the reviewed revision. Local Git
history starts with a reconstructed snapshot; its local baseline commit is not
an upstream commit. No remote changes, workflow dispatches or emails were made.

## Scores before changes

Scores are out of 10; higher is better in all categories.

| Category | Score | Reason |
|---|---:|---|
| Complexity management | 4 | Small standard-library codebase, but a large discovery orchestrator, overlapping URL extractors, repeated source/model definitions, multiple handoffs and seven workflows make behavior harder to reason about than necessary. |
| Code quality | 5 | 110 passing offline tests, unknown-preserving fields, HTML escaping, recipient guards and audit artifacts are useful strengths. Dense formatting, broad exception handling, loose dictionaries, missing critical RDW tests and evidence identity problems undermine confidence. |
| Completeness | 3 | Useful development prototype. No production weekly schedule, no automatic conversion-suitability verification, incomplete marketplace/dealer discovery, no demonstrated qualification of a real candidate in this review. |

Verdict: retain as a development prototype; it does not yet meet the documented
weekly search goal. A passing workflow is weaker than successful end-to-end
operation. This score assesses the implementation, not the availability of
suitable vehicles in the market.

## Top 10 improvements, ordered by priority

### 1. Stop treating explicit feature denials as positive evidence — implemented initial fix

`discover_listings.extract` previously matched `airco` inside `geen airco`,
`zonder airco`, and `airco werkt niet`, as well as `hoog dak` inside `zonder hoog
dak`. This promoted unsuitable leads. Added an explicit negation/broken-feature
classifier, conflicting evidence becomes unknown, and directory titles no longer
supply roof/A/C evidence. Tests cover eight denial/conflict/positive cases.

Remaining limit: a phrase classifier is not a vehicle-specific evidence model.
Equipment in unrelated page cards can still contaminate extraction (see #4).
Seller declarations still do not prove working equipment.

### 2. Make RDW success mean a complete, matching lookup — implemented initial fix

`rdw_lookup.main` previously returned success for an empty registration result or
failed catalogue queries. `fetch` only checked that JSON was a list and silently
accepted a 1,000-row cap. A null defect date crashed summarization. The pipeline
accepted any nonempty registration record without matching the returned plate.

Added row/plate validation, exactly-one registration semantics, aggregate lookup
status, nonzero exit on catalogue failure/missing official description, cap
failure, null-date handling and a pipeline plate identity check. Audit output is
still written for failed batches. Empty defect history remains valid and carries
its existing caution. Tests exercise missing vehicles, empty/failed catalogues,
wrong/malformed/capped records, null dates and partial-batch exit behavior.

Remaining: implement bounded pagination and a catalogue selection rule for
multiple dated descriptions rather than taking the first description. Registration
identity does not establish current sale availability or mechanical condition.

### 3. Preserve every plate in multiline request files — implemented

`.github/workflows/rdw-check.yml` used `read -r -a plates <<< "$raw"`, which reads
one line, although README explicitly permits newline-separated registrations.
Added `rdw_lookup.py --input FILE`; commas and all whitespace are supported,
duplicates removed in input order and the entire input validated before network
access. The workflow now uses that parser. Tests verify multiline/comma/tab input,
whole-batch validation and preserved audit output on partial failure.

### 4. Bind listing evidence to one current vehicle

`is_vehicle_detail` returns true from URL shape alone on five source types.
`extract` then takes the first plate and feature words from page-wide text;
`listing_evidence` traverses all structured objects and takes the first offer and
coordinates. A removed advert, redirected inventory, or related-vehicle card can
therefore provide another vehicle's facts. `fetch` discards the final URL.

Require final/canonical URL agreement, one matching primary vehicle object,
availability evidence and per-field provenance (object identity, timestamp,
source/excerpt). Reject conflicting plates/offers/locations and associate VAT
labels with the selected offer. Test redirect-to-inventory and related-card
contamination. The viaBOVAG plate fallback also uses double-escaped regex tokens,
so that fallback does not match normal registration text.

### 5. Respect source-wide access failures consistently

In `discover`, `source_blocked` is initialized false but never assigned true;
`source_block_reason` stays null. Inventory seed/feed exceptions continue and
only detail-page 429 errors stop that loop. This makes block reporting inaccurate
and keeps contacting a source after access failures. Use typed HTTP exceptions,
a per-host stop state shared by inventory/feed/detail phases and a host request
budget. Test seed/feed 403 and 429, not only detail 429.

### 6. Finish the qualification path and define honest acceptance criteria

`extract` always leaves `conversion_suitable` unknown. All five checks must pass,
so automatic discovery cannot produce a qualified candidate, even with perfect
registration/price/route evidence. Define payload, dimensions and provenance
requirements; provide an explicit reviewed-evidence input where automated proof
is unavailable. Do not infer suitability from a model name.

The integration acceptance step currently only requires one candidate across all
six sources. Report separate discovery, evidence, RDW and delivery outcomes;
require the documented source coverage and qualification path in controlled
end-to-end fixtures. Zero real matches can be a legitimate result; it must not
mask a broken discovery system. Enable the weekly schedule only after this is
proved and the actual context requirements are available.

### 7. Make all critical regressions mandatory in CI — partially implemented

PR workflow path filters omitted RDW, mail, HTML, evidence and browser-only changes;
the explicit unittest list skipped several existing modules. It now triggers on
all Python/scripts/workflow changes and runs unittest discovery plus compilation.

Still add realistic captured/redacted page fixtures, mail verification tests,
cleanup boundary tests and collector upload tests. Mocked HTTP success is not a
live integration test. Existing live integration steps should stay distinct from
the deterministic PR suite. Pin the supported Python version for reproducibility.

### 8. Derive both report formats from one presentation model

`report_html.render_html` unconditionally says no vehicle meets all requirements,
even when it renders qualified vehicles. `item_card` uses missing check flags but
omits `item.reasons`, hiding failed registration/listing confirmation. Text uses
raw qualifier count while HTML uses deduplicated matches, and dedup keeps the
first item even if a later record is better supported. Centralize grouping,
ranking, counts and blockers; test both formats for zero, qualifying, duplicate
and RDW-failure cases.

### 9. Make delivery retries and retention reliable

`send_report` generates a new Message-ID on every execution, sends mail, then
raises if Sent-folder verification times out. Re-running the workflow can send
duplicates after SMTP already accepted the first message. Sent-folder presence
does not prove recipient delivery. Persist a run identity and acceptance state,
retry verification independently and distinguish accepted, Sent-confirmed and
recipient-delivered. Test SMTP refusal and delayed IMAP visibility without sending
real mail. Audit artifacts expire after 30 days, whereas repository retention only
handles dated RDW JSON; define retention for discovery/report evidence too.

### 10. Simplify configuration and restore accurate documentation

Source hosts, model patterns, link parsers, limits and selection logic are repeated
across discovery, inventory, RSS, browser and reporting modules. Extract a small
source configuration and adapter interface, keep shared evidence/report logic
central and format the dense one-line functions. Add schema validation at input
boundaries. Avoid replacing this small program with a large framework.

README presents only the RDW handoff; discovery docs still describe nine categories
and Bing-only behavior although code implements six source groups and direct
seeds. Recover the missing `context.md`, document the actual operational entry
point and deployment status, and state the per-source coverage limits. The Pi
timer only collects locally; upload is separate and data-only commits do not
trigger discovery. No end-to-end weekly automation exists today.

## Validation after changes

- Before: `python3 -m unittest discover -v` — 110 tests passed.
- After: `python3 -m unittest discover -q` — 120 tests passed.
- PR workflow now discovers the newly added regressions automatically.
- Live network verification was not possible through the broken local proxy.
- No production schedule enabled, no mail sent and no claim of end-to-end success.

The implemented changes address immediate false evidence, false RDW success and
silent batch loss. They do not close the larger source identity, conversion
verification or production operation gaps above.

## Autonomous follow-up

PR #46 merged after GitHub PR CI passed. The next change addresses finding #4:
redirect/canonical identity checks, URL-linked structured primary-vehicle or
canonical-main evidence scope, exclusion of unrelated cards, and explicit unbound
lead/provenance handling. Ten additional regressions bring the suite to 130 tests.
Availability and independent condition verification remain outstanding.

PR #47 merged after CI passed. Finding #5 now has a shared typed-HTTP access guard
and a 100-request per-host run budget across inventory, feeds, details and dealer
source groups. Other hosts continue independently; coverage records stop reasons
and host counts. Five regressions bring the suite to 135 passing offline tests.

PR #48 merged after CI passed. Finding #6 now has an explicit conversion evidence
input: caller-specified payload/dimension minima, one matching listing/plate
assessment, a named reviewer, evidence URLs and dated validity. No requirements
or measurements are fabricated. Passing and failing end-to-end fixtures prove
that qualification is reachable with reviewed evidence and blocked by failures.
The broader live-discovery acceptance and production operation gaps remain open.

PR #49 merged after CI passed. Finding #8 now uses one presentation selection
model for text and HTML, prefers stronger duplicate evidence, and reports unique
qualified counts consistently. HTML now shows RDW/listing blockers and no longer
claims zero qualifying vehicles unconditionally. Three additional regressions
bring the offline suite to 146 tests.

PR #50 merged after CI passed. Finding #9 now has a stable content-based Message-ID,
pre-submission Sent lookup and persisted submitting/accepted/confirmed state.
Workflow reruns restore state and verify rather than blindly resending. Seven
mocked delivery regressions bring the suite to 153 tests. The state artifact lasts
30 days; cross-run/concurrent exactly-once delivery and full audit retention still
need a persistent operational service.
