# Specification v2 adoption — 17 October 2026

The supplied [v2 specification](camper_van_search_specification_v2.md) is preserved
verbatim. Latest explicit user instructions take precedence, followed by the dated
amendments, then the original vehicle preferences. Historical run counts in the
specification remain historical and are not updated inside that source document.

## Corrected implementation

- Existing EUR 8,000 VAT-inclusive and 100 km actual-road limits remain hard rules.
  The original 125 km exception is superseded.
- Standing room, mattress, exterior length, legal loaded mass, seats and a reviewed
  two-person layout now gate conversion suitability. The review includes exact
  drivetrain/support, Dutch purchase and fuel suitability. Missing facts remain unknown.
- Desired 186 cm finished height and 250 kg payload are preferences, not invented
  hard minima. There is no arbitrary full cargo-length minimum. See the
  [review contract](conversion-evidence.md) for numeric interpretation and evidence.
- An H1 label alone cannot establish that a viable pop-top is impossible. Such
  adverts stay unverified and rank below high-roof/roof-solution clues. A complete
  reviewed roof solution is needed for qualification. Advertised pop-tops are clues.
- HiAce is an accepted target model; bounded Transporter/HiAce public inventories
  are added. No age, mileage, diesel or cosmetic exclusion is introduced.
- RDW registered maximum mass above 3,500 kg now blocks qualification until legal
  registration is resolved, regardless of other evidence.
- Bare or legacy conversion flags are reassessed under v2 before scoring; a failed
  review rejects, and an incomplete review cannot retain a misleading 100% score.
- Research outputs carry the specification version, targets, required measurements
  and unfilled review fields. Numeric criteria no longer require an invented user reply.

## Remaining acceptance work

| Requirement | Current limit / next acceptance |
|---|---|
| Variant reliability research (§50) | Human review contract captures required assessment; no automatic documented mechanical research service exists. Collect cited generation/engine/gearbox findings for actual leads. |
| Weighted suitability and A/B/C categories (§44–48) | Current percentage measures five-check evidence coverage. Full 32-criterion suitability scoring and A/B comparisons remain unimplemented; never treat evidence percentage as mechanical quality. |
| New/changed weekly inventory (§46, §54, §67) | Within-digest plate/URL deduplication exists. Persistent cross-week state and material-change tracking remain needed before claiming results are newly listed. |
| Real candidate review | No real vehicle has complete independent measurements, layout, drivetrain, A/C, availability and condition evidence. A green test does not qualify one. |
| Source coverage | Bounded samples and access gaps remain; AutoWereld RSS is index-only. Added seed URLs do not prove those marketplaces applied every filter or exposed their entire stock. |
| Received email | HTML/plain-text generation is tested; actual Hotmail/mobile appearance still needs inspection. No email was sent for this adoption. |
| Retention | Current workflow declares `17 3 1 * *` (03:17 UTC on the first monthly day); dry-run defaults true for manual dispatch. Actual scheduler execution and historical archiving/deletion need operational verification. Artifact retention remains separate at 30 days. |
| Production | Thursday 15:00 Europe/Amsterdam and the second recipient remain unactivated pending explicit authorization. The approved Pi RSS setup is unchanged and was not remotely inspected here. |

These gaps remain visible rather than representing adoption as complete production
acceptance. Existing development workflows, recipient controls and access boundaries
are preserved.

## Verification

All 232 offline tests pass, including v2 boundary failures, independently reviewed
pop-top suitability, malformed evidence, soft targets and RDW mass contradictions.
The canonical specification's SHA-256 is
`8c593a300c461ead3e4ceb2c03dc289ddd54f5828877f191cfa9ab4e52d5a615`,
identical to the supplied attachment. A local retention dry run found zero eligible
changes; no archive or deletion was applied. No monthly-cleanup run appeared among
the 100 most recent repository workflow runs inspected; this bounded check does
not establish whether the scheduler is disabled.

The final bounded live run sampled up to eight detail attempts per source and
produced 31 identity-bound records: 8 gross prices, 18 actual road routes,
22 confirmed plates and 0 qualified vehicles. Validation passed with no
invariant errors. The discovery fingerprint matches the final Python/registry
snapshot. AutoWereld remains an access-limited RSS index; no real physical reviews
were provided. Changing live samples do not establish extraction accuracy.
See the [minimal live manifest](validation/2026-10-17-spec-v2-summary.json).
