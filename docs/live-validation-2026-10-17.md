# Bounded live-search validation — 17 October 2026

These are local live observations, not GitHub Actions run IDs. Sources and adverts
change between requests; counts are not a controlled parser-accuracy experiment.

| Observation | Detail cap per source | Records | Gross-price evidence | Road routes | Plates | Qualified | Validation |
|---|---:|---:|---:|---:|---:|---:|---|
| run-1 | 5 | 20 | 6 | 13 | 3 | 0 | early observation only |
| run-2 | 5 | 22 | 3 | 12 | 13 | 0 | passed |
| run-3 | 8 | 28 | 5 | 17 | 15 | 0 | passed |
| run-4 | 8 | 27 | 9 | 17 | 17 | 0 | passed |

Runs 2 and 3 share an identical code fingerprint and retain all 22 common records
when widening the detail cap. The final run contains 27 records, including three
bound direct-dealer adverts. It passes all screening invariants with no errors.
On 25 identical source/listing URLs compared with run 3, the final corrections
recover five gross prices and three plate confirmations. Other count changes
include changed selections and must not be described as accuracy gains.

The final inventory prefilter audited 274 index exclusions rather than fetching
those adverts as candidate details. Source coverage remains a bounded sample;
AutoWereld is still RSS-only behind an external consent gate.

## Spot checks

- A public AutoScout24 advert explicitly reports EUR 5,748 gross and EUR 4,750 net,
  registration 02-VGK-6 and a route of 136.1 km. It is outside the road-distance limit.
- Its AutoTrack mirror identifies the same UUID under its own page controller;
  the adapter requires that exact identity evidence before sharing the facts.
- A cheap Roosendaal advert says it does not start. Its own description causes an
  explicit mechanical-failure exclusion instead of promoting it as a cheap match.
- BWCR detail-form/gallery identity and unhyphenated plates were checked against
  a real public detail page. Missing VAT/pickup evidence remains unknown.
- The final research queue contains eight unqualified leads, including a refrigerated
  Crafter whose expired APK is prominently retained as a blocker. It is not recommended.

## What this proves and what remains

All 222 offline tests pass, including deterministic detail → gross price → exact
address/route → reviewed measurements/physical checks → RDW → report → validation
fixtures. The fixtures use clearly fictional criteria and inspection evidence.
Live runs demonstrate functional discovery and conservative evidence handling;
they do not establish that a real vehicle has passed an independent inspection.

Actual conversion minima, physical measurements, working A/C, current availability
and acceptable inspected condition still need real evidence. Generated review
templates leave those fields unfilled. No email was sent, no seller contacted, no
production schedule enabled and no Pi configuration changed.

The machine-readable counts, source diagnostics and code fingerprints are retained
in [the validation manifest](validation/2026-10-17-live-summary.json).
