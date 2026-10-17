# Production search work: priorities 1–4

## Discovery relevance

AutoScout24 and AutoTrack are queried using their verified public `priceto=8000`
and ascending-price filters. The response must confirm the filter in its own
pageQuery; a URL parameter alone is not counted as success. Unsupported price
parameters on Marktplaats/viaBOVAG are not claimed to work.

Inventory card facts are used only to choose detail visits. Explicit expensive,
low-roof, auction or damaged/incompatible cards are retained as index rejections
in the audit, rather than consuming detail-page limits. Possibly affordable and
unknown-tax cards remain leads. Conflicting prices stay unknown. No index card
can establish a qualified match, working A/C, availability or gross price.

AutoTrack supports both legacy numeric advert URLs and its current UUID paths.
Its earlier numeric-only matcher missed relevant modern inventory. Unknown-price
links remain eligible after higher-interest leads; original records and source
limitations remain visible. `--max-per-source 1..50` supports bounded live checks.

Direct dealer coverage, evidence enrichment and repeated end-to-end verification
are being validated separately; this document is not production activation.

## Direct dealer coverage

`dealer_registry.json` independently lists BWCR Roosendaal, MANA and Van Mossel,
with public inventory/contact URLs, reviewed domain/detail patterns and a check
date. Public inventory/contact pages were checked on 17 October 2026. This is a
maintained starting catalogue, not a claim to cover every regional dealer.

Discovery samples each direct inventory independently of AutoWereld, records
per-dealer page counts/errors/index exclusions and bounds pagination. An
inaccessible dealer does not suppress another dealer. All three inventories
were reachable in the bounded check; 134 advert links were exposed, most clearly
expensive or incompatible. Branch towns are discovery hints only: a national or
multi-branch catalogue does not establish a vehicle's actual test-drive location.

BWCR detail pages have no JSON-LD/canonical URL. Its registered adapter requires
one main region, vehicle-specific car-details form actions matching the exact
requested advert, and matching gallery ID. Missing/conflicting identity stays
unbound. This exception is restricted to the reviewed registry strategy, not a
generic relaxation. Advertised facts remain seller claims; measurements,
working equipment, current availability and route need their own evidence.

AutoWereld consent/403 limits are preserved. Independent direct-dealer access is
not a consent bypass, and no public RSS lead is promoted to a verified advert.

## Candidate evidence and research

AutoScout24/AutoTrack detail state is read only when a single `listingDetails`
record's `webPage` matches the requested bound advert. Syndicated AutoTrack records
also require the exact UUID, native canonical controller and marketplace identity. Its explicit public gross
and net prices resolve VAT evidence without borrowing unrelated labels or guessing
rounding; conditional/incomplete prices stay unknown. Vehicle-specific exact
pickup addresses take precedence over generic seller coordinates and are matched
through PDOK before road routing. Hyphenated/unhyphenated labelled plates and
explicit vehicle licensePlate fields are supported; conflicts stay unconfirmed.
Only minimal selected facts are retained, not account/session/marketing data.

A bounded real-page recheck recovered the advertised EUR 5,748 gross price,
02-VGK-6 and a 136.1 km route, correctly outside the radius. Seller-reported
payload/dimensions/service history remain attributed research clues.

The pipeline exports research tasks and an unfilled review template, requires
dated independent A/C/availability/condition checks for qualification, and never
invents conversion minima or inspection outcomes. Read `conversion-evidence.md`
for the human review contract. Unknown physical facts still block a recommendation.

## Repeated end-to-end validation

`validate_search.py` checks identity preservation, gross-budget and routed-distance
claims, qualification evidence and RDW outcomes. CI runs it before any downstream
delivery. Zero qualified vehicles is a valid outcome; missing source coverage and
independent reviews remain visible. Bare conversion flags cannot replace reviewed
measurements. Explicit current mechanical failures exclude a listing; repaired or
conditional descriptions are handled separately.

Regional card hints rank discovery only and never establish road distance. Explicit
business-buyer index prices can exclude clearly expensive inventory but never prove
gross affordability. Four bounded live runs and paired-listing comparisons are
recorded in [the dated validation report](live-validation-2026-10-17.md). The final
run has 27 records, nine explicit gross prices, 17 routes, 17 plate confirmations
and zero qualified vehicles. Actual conversion minima and physical reviews remain
required; production scheduling and mail remain outside this release.

## Specification v2 supersedes earlier missing-minima status

The supplied [specification v2](camper_van_search_specification_v2.md) now provides
the conversion criteria. Earlier sections describing absent user minima record
the pre-v2 state. Actual physical evidence is still required. The implementation
now separates hard mattress/standing/layout/mass rules from preferred 186 cm height
and 250 kg payload; full [adoption and acceptance gaps](specification-v2-adoption.md)
include variant research, weighted ranking and persistent weekly change tracking.

## Weekly service follow-up

Search matches are now separate from inspected purchase readiness. Weighted
ranking, expiring sourced variant notes, durable cross-week identity/price tracking
and rolling source-health alerts are implemented in the
[weekly search design](useful-weekly-search.md). Earlier missing-feature statements
above describe prior review checkpoints. These changes do not enable production
mail or prove long-running scheduler reliability.
