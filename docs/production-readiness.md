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
