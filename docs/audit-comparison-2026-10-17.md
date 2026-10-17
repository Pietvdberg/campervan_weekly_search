# Audit comparison after context reconciliation

Compared run 38977667392 (2026-10-16) with run 39013660683 (2026-10-17).
These runs sampled different changing adverts; changes are not a controlled measure of parser accuracy.

| Source | VAT prices before → after | Routes before → after | Plates before → after |
|---|---:|---:|---:|
| Marktplaats | 3 → 0 | 0 → 0 | 8 → 0 |
| AutoScout24 | 2 → 0 | 50 → 0 | 6 → 0 |
| AutoTrack | 49 → 50 | 1 → 0 | 44 → 45 |
| viaBOVAG | 44 → 44 | 46 → 46 | 0 → 0 |
| AutoWereld | 0 → 0 | 0 → 0 | 0 → 0 |
| Local dealers | 12 → 0 | 12 → 0 | 12 → 0 |

Totals: reported VAT prices 110 → 94 (−16); reported routes 109 → 46 (−63).
Both runs found zero qualified vehicles. Record counts were 210 → 198.

The identity guard introduced in PR #47 incorrectly required a root Vehicle/Product URL.
Actual Marktplaats and AutoScout24 pages identify the primary vehicle through its own
`offers.url`. The context follow-up accepts that exact identity link while rejecting
conflicting root/offer identities. No unbound page-wide fallback is restored.

A bounded three-page recheck uses one real page from each of Marktplaats, AutoScout24
and AutoTrack, retrieved on 17 October. It restores identity binding on the first two;
the sampled AutoScout24 address produces a route greater than 100 km and is rejected.
The sampled AutoTrack title explicitly says L1H1, which now overrides unrelated H2
mentions in the page. Full-run post-fix counts require the subsequent live CI artifact.

PDOK matching now preserves a house letter (e.g. 12B) instead of silently routing to 12.
Evidence counts indicate what the extractor reported, not independently verified
mechanical condition, complete inventory or current availability.

HTML generation is unit-tested. Its rendering in a received Hotmail message remains
unverified; no manual mail workflow was dispatched for this comparison.

The local-dealer decline is not evidence of zero stock: a bounded current request
to an AutoWereld dealer inventory redirected to an external DPG consent host.
That content is not a validated dealer inventory and must not be bypassed. The
follow-up classifies external-origin redirects as source stops and records the
reason. Configured inventory seeds may follow HTTPS path changes on the same
host; advert responses retain strict URL identity. This does not establish that
all historically reported dealer records were false; the two runs differ.

## Follow-up runs supplied by the user

| Run | Result | Screened records | Qualified matches |
|---|---|---:|---:|
| [39014586903](https://github.com/Pietvdberg/campervan_weekly_search/actions/runs/39014586903) | Success | 195 | 0 |
| [39014733473](https://github.com/Pietvdberg/campervan_weekly_search/actions/runs/39014733473) | Cancelled before any job started; no artifact | — | — |
| [39014829289](https://github.com/Pietvdberg/campervan_weekly_search/actions/runs/39014829289) | Success | 193 | 0 |

The latest successful run includes the context reconciliation, risk gates and
consent-redirect reporting. All 193 screened records have bound listing identity.
Its development acceptance reports `production_ready: false`, and no mail step ran.

| Source | Records | Confirmed VAT prices | Road routes | Listing plates |
|---|---:|---:|---:|---:|
| Marktplaats | 50 | 3 | 0 | 8 |
| AutoScout24 | 50 | 2 | 39 | 5 |
| AutoTrack | 45 | 45 | 0 | 41 |
| viaBOVAG | 48 | 44 | 45 | 0 |
| AutoWereld | 0 | 0 | 0 | 0 |
| Local dealers | 0 | 0 | 0 | 0 |
| Total | 193 | 94 | 84 | 54 |

Compared with the broken identity-gate run 39013660683, Marktplaats recovered
3 VAT prices and 8 plates, AutoScout24 recovered 2 VAT prices, 39 routes and 5
plates. Across the changing samples, total reported prices remain 94 and routes
increase from 46 to 84 (+38). This is recovery of lost evidence, not proof that
all source coverage is restored to the original 210-record baseline.

AutoWereld has 75 fresh RSS-only leads and no independently validated advert
pages. Its external consent redirect is now explicitly recorded for both the
marketplace and local-dealer source group. Independent local dealer retrieval
also found no validated details; this does not establish zero stock. One expired
APK concern appears in the latest audit. Conversion suitability is unknown for
all 193 records; there are no purchase-ready recommendations.

A further budget correction rejects a bound EUR offer explicitly above EUR 8,000
without inventing its VAT-inclusive price. An amount at or below the ceiling
remains unknown until VAT treatment is supported. That correction is validated
by offline regressions; it is not included in the three run counts above.
