# RSS follow-up and artifact extraction — 17 October 2026

## Every Pi feed item gets a separate assessment

The Pi supplies unverified first-party RSS leads. `rss_evaluation.py` now evaluates
all supplied items in a dedicated Actions step after discovery, before RDW
screening, rather than just applying a narrow L2H2/L3H2 display filter.
It records one outcome per item: interesting, needs information, excluded,
already evaluated through its own advert, or duplicate. The audit retains all
outcomes and the email presents up to five prioritized follow-up tasks.

The assessment uses each item's own advertised price/VAT wording, roof and
advertised A/C, body incompatibilities, explicit current defects, and regional
place hints. H1 can remain a conditional lead requiring a viable pop-top;
age and mileage alone do not exclude a vehicle. Unknown VAT stays unknown, with
a clearly hypothetical 21% scenario where that would exceed the budget. A town
mention never supplies road distance. No RSS assessment creates a verified
advert, confirmed gross-price/route count, search match, or purchase recommendation.

The report states why a lead is interesting, the missing checks, and whether
individual-advert follow-up is blocked. `rss_evaluation.json` contains all
assessments and is uploaded with the discovery audit. `research_pack.json` also
includes the selected RSS follow-up queue. No seller is contacted automatically.

A real replay of the repository's fresh 75-item Pi snapshot collected on
16 October 2026 at 21:43 UTC produced **10 interesting, 8 needing information,
and 57 excluded** on 17 October. These are triage results, not confirmed vehicles.
The revised ranking starts with the advertised EUR 3,750 Renault Master L3H2
A/C; its VAT, road distance, current availability and technical condition remain
unverified. Results will change with later snapshots.

## AutoWereld health reflects two separate stages

A fresh bounded public detail request on 17 October still redirected from
AutoWereld to `myprivacy.dpgmedia.nl`. The existing host access stop was respected;
no consent workaround or further retries were attempted. The previous Pi
handover also records HTTP 403 on individual pages. This is a genuine access gap,
not proof of zero stock and not repaired by successful RSS collection.

Health output now distinguishes external redirects, HTTP 403, HTTP 429 and
request-budget stops. It shows separately how many RSS items were assessed and
found interesting, the exact access diagnostic, and the next action. The
zero-validated-advert streak and critical status remain until permitted primary
advert access is restored. Independently fetched dealer adverts remain useful
alternatives; they do not count as validated AutoWereld stock.

## Remove the deprecated ZIP extraction path

The current official download action still has the upstream
[DEP0005 issue](https://github.com/actions/download-artifact/issues/484): its ZIP
extraction chain uses `unzip-stream` / `binary` / `buffers`, which invokes the old
Buffer constructor. The repository now uses a small local composite action:

1. `actions/download-artifact@v8` downloads the ZIP with `skip-decompress: true`
   and `digest-mismatch: error`, retaining the official authenticated transfer and
   strict SHA-256 validation.
2. Python's standard ZIP reader extracts the archive, preserving hidden history
   files. It rejects traversal, links, conflicting paths, encrypted files and
   oversized archives; a corrupt file does not replace existing state.
3. Temporary archives are removed even on a failed transfer/extraction.

The wrapper intentionally supports one named ZIP artifact from the current run,
which is exactly what the repository's existing history/mail-state restores use.
It does not suppress warnings, downgrade Node, vendor the upstream JavaScript,
or disable checksums. PR CI runs the real artifact round trip with
`NODE_OPTIONS=--throw-deprecation` so the old warning would fail validation.
