"""Produce bounded research tasks and an unfilled review input; never fake facts."""
from conversion_evidence import MEASUREMENTS
from vehicle_review import REVIEW_CHECKS


def build(data, requirements=None, limit=10):
    # Import locally so screening can also generate this artifact without a cycle.
    from camper_pipeline import candidate_state, unique_report_items, report_priority
    leads = [item for item in unique_report_items(data.get("results", [])) if candidate_state(item) == "POTENTIAL MATCH — UNVERIFIED"]
    leads.sort(key=report_priority, reverse=True)
    minimums = {key: (requirements or {}).get(key) for key in MEASUREMENTS}
    records = []
    assessments = []
    for item in leads[:limit]:
        candidate = item["candidate"]
        tasks = []
        if not item.get("plate"):
            tasks.append("Obtain the registration from this vehicle's listing or seller; verify against RDW.")
        if candidate.get("price_incl_vat") is None:
            tasks.append("Confirm the total purchase price including VAT and obligatory charges.")
        if candidate.get("distance_km") is None:
            tasks.append("Confirm the vehicle's full pickup address and calculate the road-driving route from Bergen op Zoom.")
        tasks += ["Physically test cab A/C; an advertised equipment list does not confirm operation.",
                  "Confirm the vehicle is still for sale and where it can be inspected.",
                  "Obtain an independent inspection of rust, drivetrain, brakes and service invoices.",
                  "Measure usable interior height/length and establish legal remaining payload for the planned conversion."]
        records.append({"listing_url": candidate.get("listing_url"), "plate": item.get("plate"),
                        "name": candidate.get("name"), "source": candidate.get("source"),
                        "observed_at": candidate.get("observed_at"), "checks": candidate.get("checks"),
                        "verified_price_incl_vat": candidate.get("price_incl_vat"), "road_distance_km": candidate.get("distance_km"),
                        "field_evidence": candidate.get("field_evidence", {}), "rdw_concerns": item.get("rdw_risks", []),
                        "blockers": item.get("reasons", []), "next_actions": tasks})
        assessments.append({"listing_url": candidate.get("listing_url"), "plate": item.get("plate"),
                            "reviewer": None, "observed_at": None, "expires_at": None,
                            "measurements": {key: {"value": None, "source_url": None, "independently_checked": False} for key in MEASUREMENTS},
                            "checks": {key: {"confirmed": None, "method": None, "source_url": None} for key in REVIEW_CHECKS}})
    return {"generated_on": data.get("generated_on"), "requirements": minimums,
            "unset_requirements": [key for key, value in minimums.items() if value is None],
            "leads": records, "review_template": {"requirements": minimums, "assessments": assessments},
            "qualification_note": "This is a research queue. Blank fields are not verified and no seller is contacted automatically."}
