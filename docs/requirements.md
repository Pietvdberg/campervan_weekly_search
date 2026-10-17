# Search requirements and operational boundaries

Reconciled on 17 October 2026 with the user-supplied session handover `context.md`.
The full private handover is not committed here; this file records the public
project requirements and distinguishes historical observations from current proof.

- Origin: Bergen op Zoom. Maximum 100 km actual road-driving route, not a
  straight-line distance or assumed distance to a named city.
- Purchase budget: EUR 8,000 including VAT. Unknown tax treatment stays unknown.
- Target: high-roof conversion vans, especially L2H2/L3H2, with working cab A/C,
  usable dimensions and legal payload for the planned conversion. The handover
  does not specify numeric dimension/payload minima; these must be supplied for
  an actual conversion review rather than invented.
- A qualified recommendation needs at least 90% of required evidence under strict
  evaluation. Unknowns do not pass; seller claims do not establish working
  equipment, availability or mechanical condition. The five equal-weight hard
  checks currently require all five passes to exceed 90%.
- Keep service invoices, odometer assessment, APK status/history, rust/drivetrain,
  actual mass/payload, realistic conversion costs and independent inspection visible
  as evidence or outstanding risks. APK approval is not an inspection substitute.
- Sources: Marktplaats, AutoScout24, AutoTrack, viaBOVAG, AutoWereld and local dealers.
  Auctions, Gaspedaal, TrucksNL, wijkopenautos and Bedrijfsauto.nl are excluded.
- Keep the digest short: confirmed matches, up to five unverified individual leads
  and up to five separate RSS tips. Retain full audit records and source limits.
  Zero verified matches never means exhaustive proof of no stock.
- Development/manual mail goes only to the agreed Hotmail development address.
  Push CI sends no email. Actual HTML inbox rendering is still unverified.
- Production weekly search/email remains disabled pending explicit activation
  authorization. The intended cadence is Thursday 15:00 Europe/Amsterdam with DST.
  General authorization to improve and merge code does not activate production.
- The separate Pi RSS collector/upload timer was already enabled and user-approved:
  Thursday 13:30 Europe/Amsterdam, linger enabled, last verified in the handover on
  16 October. That is a historical user-reported operational observation, not a
  remote Pi health check performed during this review. Preserve that setup.
- Pi uploads are index-only, do not dispatch workflows and do not send mail.
  AutoWereld 403 detail pages stay unverified; no access-control bypass is allowed.

The historical handover's code SHA, 110-test count and run statistics describe
pre-review code. Consult current GitHub CI and dated audit comparisons for newer
observations. Do not copy credentials, private correspondence or machine access
information into this public repository.

## Explicit adverse evidence

An expired RDW APK date (assessed on the Netherlands local calendar date) or an
`Onlogisch` odometer assessment prevents a qualified recommendation until resolved.
A registered maximum mass above 3,500 kg produces a licence/mass review warning;
it does not infer the user's licence or prove actual conversion payload. Missing
or malformed RDW facts do not establish a clean inspection. These concerns appear
in both report formats and remain in the audit. Historical APK defects remain
historical; they are not automatically labelled current unrepaired faults.

Auction sale evidence and the explicitly excluded marketplace domains are rejected
before candidate RDW work. RSS auction tips are excluded from the digest as well.
