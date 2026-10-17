# Pipeline verification scope

This repository remains a development search system, without a production weekly
schedule. The user has supplied `context.md` and specification v2; public requirements and operational
boundaries are reconciled in [requirements](requirements.md).

- PR CI runs syntax compilation and all offline unittest modules. The strict
  review follow-ups now have 305 tests, including vehicle identity,
  conversion review, source access stops, report consistency and mail retry state.
- The marketplace integration workflow performs bounded live discovery across
  six source groups. It records coverage gaps and requires identity-bound evidence
  for development acceptance. This does not demonstrate exhaustive coverage.
- `weekly-verification.yml` processes `candidates.json`, which is an empty manual
  candidate input. It does not run discovery and must not be interpreted as a
  production search.
- Controlled fixtures demonstrate passing and failing conversion review. No real
  vehicle measurements are supplied. Specification v2 now defines the criteria;
  the [adoption record](specification-v2-adoption.md) lists remaining acceptance gaps.
- Manual mail workflows address only the development recipient. SMTP acceptance
  and Gmail Sent confirmation do not prove recipient delivery. Retry state blocks
  blind resubmission after ambiguous or accepted SMTP submission.
- The external Pi timer collects RSS locally. Upload is separate; data-only pushes
  do not trigger marketplace discovery. This is not end-to-end weekly automation.

Search-versus-purchase separation, weighted scoring, a maintained initial variant
research registry and persistent weekly change tracking are implemented; see the
[weekly search design](useful-weekly-search.md).

The weekly digest does not require physical vehicle inspections or a qualifying
vehicle before launch. Those remain purchase decisions. The final release work
is delivery-aware history, timezone-aware scheduling and a complete live
SMTP/recovery acceptance check, recorded in [weekly production delivery](weekly-production-delivery.md).
Coverage, dealer maintenance and additional variant research remain ongoing
quality improvements rather than blanket release blockers.

The [17 October live-shortlist audit](shortlist-review-2026-10-17.md) reviews the
124-record successful Actions run, re-extracts 17 exact public pages, and records
current fault/VAT corrections and matching research for the final five leads.
One development HTML/plain-text message was sent and read back from Gmail Sent;
local desktop/mobile rendering passed. On 17 October the recipient confirmed
receipt and readable appearance on both phone and PC, with screenshots. The
[post-merge live run](https://github.com/Pietvdberg/campervan_weekly_search/actions/runs/39037474619)
also succeeded on the merged commit, including discovery, RDW screening, invariant
validation, artifact upload and durable history restoration/persistence. Its mail
step was skipped as intended for a push-triggered run. This closes the remaining
recipient-side check for priorities 1–3; production activation remains separate.

The [RSS assessment and artifact extraction follow-up](rss-evaluation-and-artifact-extraction.md)
adds a dedicated all-item Pi feed screening stage and keeps its research leads
separate from verified adverts. AutoWereld's external-consent access gap remains
visible alongside successful RSS screening. Artifact restores retain official
checksum validation and use Python ZIP extraction to avoid upstream DEP0005.

AutoWereld now has the explicit `optional_rss` role requested by the user. Healthy
RSS assessment and blocked advert follow-up are reported separately. Missing or
stale optional feeds generate notices rather than critical core-source alerts;
core outages and data-integrity failures still fail the relevant checks.
