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
