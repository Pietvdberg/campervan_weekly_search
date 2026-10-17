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
