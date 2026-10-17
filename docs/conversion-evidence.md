# Reviewed conversion suitability — specification v2

This contract establishes purchase readiness. Advertised search matches and
conditional research leads can be shortlisted before these physical reviews; see
[weekly search stages](useful-weekly-search.md). Known failed hard requirements
still exclude a vehicle.

The [user specification](camper_van_search_specification_v2.md) supplies the project
criteria. No additional arbitrary interior-length minimum is needed. A van's model,
H2 label or nominal payload cannot prove conversion suitability.

Run `python3 camper_pipeline.py --input discovered_candidates.json
--reviewed-evidence reviewed_evidence.json` on one shell command line. The pipeline
exports an unfilled `reviewed_evidence_template.json` and a bounded
`research_pack.json`. Template generation never verifies or contacts a vehicle.

## Review contract

The JSON contains `assessments` and optional `requirements` (default `{}`). Each
assessment needs the exact confirmed `listing_url` and `plate`, named `reviewer`,
timezone-aware `observed_at` and `expires_at`. Exactly one current matching review
is accepted. This is trusted human evidence input, not reviewer authentication or
an independent inspection service.

Every `measurements` entry needs numeric `value`, an HTTPS `source_url` and
`independently_checked: true`:

| Measurement | Hard rule |
|---|---|
| `finished_standing_height_cm` | At least 176 cm, plus a positive practical-standing review |
| `bed_length_cm` / `bed_width_cm` | At least 170 / 120 cm for the planned real mattress |
| `external_length_cm` | Below 640 cm |
| `maximum_authorised_mass_kg` | At most 3,500 kg |
| `completed_loaded_mass_kg` | Within the legal maximum, including the planned conversion and normal travel loading |
| `available_payload_kg` | Nonnegative remaining legal margin after those loads |
| `belted_seats` | At least two, integer count |

Completed travel mass plus remaining payload must not exceed authorised mass.
Establish actual base-vehicle mass and account for build components, people, water,
fuel and normal equipment; a brochure payload is insufficient. A projected build
requires a corroborated weight plan, not an assertion that a finished van was weighed.
The 176 cm figure is the occupant-height floor, **not proof of practical clearance**:
`practical_standing_room` is separately required. Approximately 186 cm finished
height and 250 kg remaining payload are recorded preferences, not hard failures.
Raw cargo height is not finished height. A reviewed viable pop-top is acceptable.

Every `conversion_checks` entry needs boolean `confirmed`, HTTPS `source_url` and
`independently_checked: true`. The generated research pack supplies descriptions:

- `practical_standing_room`: usable standing solution for the 176 cm occupant.
- `two_person_layout`: indoor living, a real mattress without unloading luggage,
  movement and accessible storage for two adults.
- `indoor_kitchen_and_toilet`: sink, two burners, worktop, fridge and portable toilet.
- `year_round_systems`: insulation, heating, freeze protection, ventilation, water
  and initial off-grid systems are feasible.
- `drivetrain_and_support`: review the exact generation, engine, gearbox and body
  for major-failure risk, loaded mountain performance, parts and European garage support.
- `netherlands_purchase`: purchase and inspection in the Netherlands without a
  foreign-purchase import requirement.
- `fuel_eligible`: not LPG-only; any electric candidate has corroborated touring
  range/charging suitability.

Availability and condition checks remain required. The A/C physical check is optional:

| Check | Accepted methods |
|---|---|
| `cab_ac_working` | `physical_test`, `independent_inspection` |
| `available_for_sale` | `seller_confirmation`, `independent_inspection` |
| `condition_acceptable` | `independent_inspection` |

Advertised cab A/C on the bound individual listing satisfies the search A/C rule.
A physical test is a pre-purchase action, not a search qualification gate. Explicit
evidence of absent or broken A/C still rejects. A blank optional `cab_ac_working`
field does not assert that operation has been tested.

These use boolean `confirmed`, accepted `method` and HTTPS `source_url` under the
same reviewer/identity/date header. Include rust, structural condition, drivetrain
and service records in the inspection. Seller equipment lists establish advertised equipment, not physically tested operation.

Missing, stale, malformed or wrong-vehicle evidence is unknown. A supported failed
hard requirement rejects, even when other fields are missing. Legacy reviews with
only payload, internal height and internal length cannot establish v2 compliance.
Optional legacy `requirements` may still add all three positive numeric minima
(`available_payload_kg`, `internal_height_cm`, `internal_length_cm`); they can only
add constraints, never override v2. No actual inspection facts are supplied here.
