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
