# Reviewed conversion suitability

Discovery cannot infer conversion suitability from a model name. Use an explicit
review file with `python3 camper_pipeline.py --input discovered_candidates.json
--conversion-evidence reviewed_conversion.json` (on one shell command line).

The JSON object has two keys:

- `requirements`: positive numeric minima for `available_payload_kg`,
  `internal_height_cm` and `internal_length_cm`. These are user/project criteria;
  there are deliberately no default numbers.
- `assessments`: a list of reviewed vehicle records. Each has `listing_url`,
  `plate`, a nonempty `reviewer`, timezone-aware ISO `observed_at` and `expires_at`,
  and a `measurements` object with the same three measurement keys. Every
  measurement contains a positive numeric `value`, an HTTPS `source_url` for its
  supporting evidence and `independently_checked: true`.

The assessment must identify the same confirmed listing URL and registration.
Exactly one assessment must match; conflicting, expired, future-dated or
incomplete reviews remain unknown. A reviewed measurement below its minimum is
an explicit failure. The complete assessment and comparison are retained in the
candidate's audit record. This is a contract for reviewed evidence, not an
independent measurement service or authentication of the reviewer's identity.

Available payload must account for the planned conversion and loading; nominal
payload from a model brochure is insufficient. Reviewers choose expiry based on
the evidence. New plate/listing evidence is still required and RDW registration
must match before a candidate can qualify. Mechanical condition, actual A/C
operation and current availability need their own verification.

No real measurements or project minima were available in this session. The test
suite uses explicitly fictional measurements to prove that both passing and
failing reviewed evidence reach the correct pipeline outcome. Production
qualification remains blocked until actual requirements and evidence exist.

## Complete vehicle review and research input

`camper_pipeline.py` now also writes `research_pack.json` (up to ten promising,
unrejected vehicles with remaining actions) and `reviewed_evidence_template.json`.
The template is deliberately unfilled; generation is not verification. The same
input can be supplied through `--reviewed-evidence FILE` (the older
`--conversion-evidence` option remains an alias).

Each matching assessment can contain `checks` alongside `measurements`:

| Check | Accepted methods |
|---|---|
| `cab_ac_working` | `physical_test`, `independent_inspection` |
| `available_for_sale` | `seller_confirmation`, `independent_inspection` |
| `condition_acceptable` | `independent_inspection` |

Each check needs boolean `confirmed`, accepted `method` and an HTTPS `source_url`.
The named reviewer, exact listing/plate and valid observation/expiry timestamps
apply to the entire assessment. Missing, stale, wrong-vehicle or unsupported
claims remain unknown; an explicitly failed current independent check rejects
the candidate. All three independent checks are required for qualification, in
addition to the five scored criteria and matching successful RDW evidence.
Seller equipment lists, an Active marketplace flag and service-history claims
are kept as attributed statements and cannot satisfy physical review gates.

Set actual minimum dimensions and available conversion payload before completing
a real assessment. They remain unset in a generated template when no project
requirements were supplied. No physical measurement/inspection or seller contact
is performed automatically. Review input is a trusted human evidence contract,
not authentication of a reviewer's identity or an inspection service.
