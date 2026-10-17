# Live shortlist review — 17 October 2026

This review addresses shortlist usefulness, evidence/research, and a development
HTML delivery check. The baseline is [successful live run 39035369475](https://github.com/Pietvdberg/campervan_weekly_search/actions/runs/39035369475):
124 source records, six source groups, 64 rejected records, one distinct advertised
search match, and no purchase-ready vehicles. This is a bounded audit, not a
market-wide estimate of missed vehicles.

Seventeen exact public advert pages were re-extracted. Same-day RDW evidence from
the baseline was reused, with its original scope; no independent inspection or
seller contact was performed. Other records retain the baseline source evidence.
The [machine-readable review](validation/shortlist-review-2026-10-17.json) retains
paired URLs, price/route changes, research IDs, limitations, and mail check scope.
Raw marketplace session/account data is not committed.

## Findings and changes

| Actual vehicle | Finding | Result |
|---|---|---|
| Boxer VK273J | Own advert says `MOTOR NIET %100`; previous wording detection missed it | Excluded for explicit current engine trouble on both source records. Repaired, negated and conditional statements remain distinct. |
| Transit 4VVG77 | Seller writes both ex/incl VAT beside EUR 4,500, while public state previously supplied EUR 4,538 gross | Gross price and budget pass become unknown pending written clarification. Separate valid gross/net prices are not conflicts. |
| Jumper VRZ87R | EUR 7,805 gross, 97 km, L3H2, advertised A/C; APK expired; trade/export business wording | Remains the sole distinct advertised search match, with APK and Dutch consumer-sale questions. Official 2019 manufacturer source supports the engine family, not a reliability rating. |
| Transporter VSJ01P | RDW odometer assessment is Onlogisch; no usable standing-height evidence | Lower priority; discrepancy and pop-top feasibility need resolving. Sourced 1.9 TDI notes stay separate from CFCA/2.5 claims. |
| Ducato VH556N | KH1; EUR 5,748 gross, 87.2 km; expired APK | Conditional lead with explicit roof-conversion question. Haynes/RTA workshop catalogue supports family research; actual engine code and gearbox remain unconfirmed. |
| Transporter 20BRJX | 2.5 TDI, six-speed automatic, L1H1/DC; EUR 3,933 gross, 89.3 km; expired APK | Conditional lead with pop-top, remaining living-space, cooling and automatic-transmission questions. No rejection solely for age or mileage. |
| Master 53VKL8 | L1H2/automatic/A/C, EUR 3,570 gross; incomplete pickup address | Conditional lead; road distance stays unknown. No town-centre shortcut. |
| Boxer VB737J | L2H2/A/C, incomplete address, old leakage traces; platform labels EUR 5,000 inclusive but seller explicitly calls sale price exclusive without a gross/net pair | Gross price becomes unknown; retained as a conditional audit lead with attributed leakage caution. |
| Master VSG50K | L3H2, EUR 5,990 gross, 97 km; A/C not established by own advert | Remains outside the useful shortlist; no equipment inferred from other vans. |
| Transporter 62VVL9 | Promoted by route-based ranking; own description says the engine warning lamp is on | Excluded pending diagnosis on both independently re-extracted source records. No diagnosis or failure mechanism invented. |
| Transit VB421B | Own description explicitly says MARGE; EUR 2,999, 75.2 km, L2H1/seven seats | Explicit margin sale restores the consumer price without inventing a net amount; conditional lead with roof and living-space checks. |
| Transit 7VTJ12 | EUR 2,950 margin advert in Wouw; no verified full pickup address or roof solution | Retained in audit; plausible location does not establish the required route. |

The final audit rejects 68 source records: the original 64 plus two records for
the faulty Boxer and two for the Transporter's active engine warning. The final
shortlist contains Jumper VRZ87R, Transit VB421B, Ducato VH556N, Transporter 20BRJX
and Transit 4VVG77. All five have current matching source notes, with explicit
limits: manufacturer/catalogue identity information is not reliability research,
and a family-level inspection guide is not an exact engine-code assessment. No
vehicle receives an invented overall reliability score. Renault and unresolved
Boxer research remain future work; they are outside this final five.

Ranking now considers the odometer discrepancy before budget/route usefulness,
then paired budget/route evidence, a verified route, price, roof evidence and other unresolved RDW blockers. Missing address evidence
remains visible rather than displacing every actionable routed lead. A development
review may explicitly revisit known stock; normal weekly history suppression is
unchanged. Advertised A/C continues to satisfy the search criterion.

## HTML development delivery

One development email was sent to the Hotmail recipient on 17 October using the
authenticated Gmail connector. Its exact recipient, subject and plain/HTML bodies
were read back from Gmail Sent, with no CC/BCC. This demonstrates Gmail submission,
not Hotmail receipt or the Actions SMTP execution path.

Chromium checks at 800 and 390 pixels found no horizontal overflow. All 12 rendered
links use HTTPS and include the actual selected advert/research URLs. A MIME
round-trip preserves both alternatives; a CSS-stripped view retains readable
content. Mobile spacing and the viewport declaration were improved. These browser
checks do not emulate every Outlook client.

Actual Hotmail inbox receipt and desktop/mobile appearance await recipient
confirmation because no Hotmail inbox connection is available. The sent email is
an earlier rendering-test snapshot (65 rejected source records), before the final
VAT, engine-warning and margin-sale fixes. Its Renault/Boxer cards are replaced by
the two Transit leads in the final audit. It must not be treated as an updated
purchase recommendation. A duplicated RDW warning was removed from subsequent
HTML generation without sending another message.

Production scheduling and dual-recipient mail were not enabled.
