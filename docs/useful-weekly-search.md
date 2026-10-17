# Weekly search priorities 1–4

> **17 October release update:** Production activation and live delivery/recovery
> acceptance are recorded in [weekly production delivery](weekly-production-delivery.md).
> The earlier review checkpoints below describe implementation history. Physical
> inspections remain purchase checks, not a blocker for the weekly digest.


## 1. Search fit and purchase readiness are different

`search_assessment` checks only bound individual-advert evidence: advertised roof
solution, advertised cab A/C, supported gross purchase price <= EUR 8,000 and an
actual driving route <= 100 km. All four must pass for `SEARCH_MATCH`. An unknown
conversion measurement, uncontacted seller or missing inspection does not remove
that search match. A useful partial advert is `CONDITIONAL`, never a verified pass.
RSS-only tips remain separate. Known failed hard requirements still reject.

The original five-check percentage and `qualified` field now explicitly represent
purchase readiness. They retain the reviewed layout, weights, availability,
condition and matching RDW requirements. Search matches are not mechanically safe
purchase recommendations. The digest shows search status, tailored follow-up
questions and outstanding pre-purchase actions separately.

## 2. Sourced research and weighted ranking

`suitability.py` implements all 32 weights from specification section 44. Supported
0–10 criterion scores need a source URL, rationale and medium/high confidence.
Drivetrain reliability/support/performance scores additionally require exact
make/model/generation/engine/gearbox/body identity and current matching research.
A price preference is calculated reproducibly from the EUR 5,000 target and
EUR 8,000 ceiling. Unknown criteria receive no invented score. Weighted coverage,
partial score and the four-check search percentage are separate fields.

A/B categories require complete advertised search fit, critical mechanical/support
criteria and sufficient weighted coverage. Unsupported variants remain C; known
hard failures are D, regardless of cosmetic scores. The digest withholds a total
judgement when support is too sparse. Exact identity inferred from a year is
labeled and cannot unlock an exact-variant reliability score.

`variant_research.json` is a maintained, expiring source registry. Initial entries
cover Boxer 2.2 HDi/manual concerns, Boxer 3.0 HDi timing guidance, CFCA-specific
Transporter risk and Transit 2.2 TDCi 115 injector concerns. These are focused
findings, not statistical reliability ratings. Supplier interests and source type
are retained, with questions and inspection priorities. No guide is treated as a
diagnosis of a particular advert; unsupported engine variants remain unresearched.
Review the registry by its `review_by` dates and add cited exact-variant evidence
for serious leads. No automated general-purpose mechanical research service is
claimed. Sources were read on 17 October 2026:

- [Haynes Transit buyer guide](https://uk.haynes.com/blogs/tips-tutorials/ford-transit-diesel-2006-2013-buyer-s-guide)
- [Transit Center Boxer guide](https://www.transitcenter.uk/peugeot-boxer-common-faults-t-96.html)
- [Deutsche Parts CFCA discussion](https://www.deutsche-parts.co.uk/blog/post/vw-transporter-t5-1-t6-bitdi-180-cfca-oil-consumption-problems.html)
- [Willemsbrug timing guidance](https://www.allemerkengarage.nl/distributieriem-fiat-ducato-boxer-jumper)

## 3. Durable weekly history

`search_history.py` stores minimal first/last-seen observations, per-source URLs,
prices and relevant facts. Confirmed plates join cross-site adverts; URL-only
identities can be promoted without resetting their age. Conflicting plates and
source prices remain visible in audit. Missing stock in a partial crawl is not
marked sold. A material price move is at least EUR 250 and 5%; minor price edits
remain recorded without filling the weekly digest. Changed extraction across code
versions is labeled evidence enrichment, not an assumed seller-side edit.

Newly observed means first observed by this system, not newly posted by a seller.
Unchanged and newly syndicated/relisted vehicles stay in audit but are suppressed
from the digest. New observations, material changes and useful newly enriched
facts may be shown. Stable run IDs make reruns idempotent. The last 30 runs and
275 days of listing identity state are retained; this state is separate from
result-file and Actions-artifact retention.

`state_store.py` restores/persists `search_state.json` on the dedicated
`search-state` branch. It never writes main or dispatches a workflow. Reads fail
on corrupt/missing data on an existing branch. Persistence rejects an advanced
head and uses a non-forced ref update; a concurrent writer cannot silently erase
history. Git blob reads avoid the small Contents API response limit.

The integration job has read permission; a separate job alone receives contents
write permission to persist the computed state. Reruns do not add market or
failure-streak observations. Recovery from an actual persistence conflict means
restoring the latest state and starting a new run; do not force-push stale state.

## 4. Source health across runs

`coverage_health.json` and the GitHub job summary expose each source's discovered
and bound adverts, verified prices/routes, access restrictions, sampling limit,
consecutive zero runs and individual dealer diagnostics. Zero usable bound
inventory fails the integration job. A previously productive source going to
zero, sustained missing inventory and sharp evidence-yield drops raise explicit
alerts. Different sample caps are not treated as comparable count regressions.
Failed zero-inventory observations are still persisted when invariant validation
completed, so the next run can see the failure streak.

AutoWereld is an optional RSS discovery channel under the user's 17 October
decision. Its separately displayed health checks snapshot freshness and complete
item assessment. Blocked direct-page access and zero bound counts stay in the
audit but do not cause a critical core-source alert. Optional feed problems emit
notices; failures of core sources retain their normal alerts and acceptance gates.
RSS-only leads never become verified matches through this policy change.
Direct dealer inventory is checked independently. Public Louwman pages were
reviewed during this work, but absent reliable bound detail identity meant no new
validated adapter was claimed or added. Existing access controls are preserved.

Repeated bounded runs demonstrate the monitoring and history path, not exhaustive
market coverage or weeks of unattended reliability. Real weekly operation, received
Hotmail rendering, approved production scheduling and real vehicle inspections
remain acceptance tasks. No new production timer, recipient, email or Pi change
is part of this release.

## Local run with history

```bash
python3 state_store.py pull --repo Pietvdberg/campervan_weekly_search
python3 discover_listings.py --max-per-source 8 --output discovered_candidates.json
python3 camper_pipeline.py --input discovered_candidates.json --history .search-state/search_state.json --run-id UNIQUE_RUN_ID
python3 validate_search.py --discovery discovered_candidates.json --screening screening_results.json
python3 coverage_report.py
```

State-store commands use `GH_TOKEN`; keep it in the environment/secret storage.
Use the same run ID only for an actual rerun. No command above sends email.

## Validation on 17 October 2026

All 256 offline tests and syntax checks pass. Two bounded live runs each screened
32 adverts; the first showed two conditional leads with source-backed questions,
and the repeat suppressed unchanged/relisted vehicles. Neither run established a
complete advertised search match or a purchase-ready vehicle. Missing physical
inspection no longer prevents search matches; the live samples still had unresolved
advertised price/roof/route combinations. A deterministic complete advert fixture
passes the search stage without any physical review.

The final live run's code/registry fingerprint matches this release. Replaying its
run ID leaves state unchanged. The durable seed retains four actual observations
(two earlier dated baselines plus these two runs); all occurred on one date, so
this is not evidence of weeks of reliability. AutoWereld remains a visible coverage
gap. See [the retained validation](validation/2026-10-17-weekly-priorities.json).
