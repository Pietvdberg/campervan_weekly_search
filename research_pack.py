"""Produce bounded research tasks and an unfilled review input; never fake facts."""
from conversion_evidence import MEASUREMENTS
from vehicle_review import REVIEW_CHECKS
from search_requirements import MEASUREMENT_RULES, REVIEW_RULES, PREFERENCES, SPEC_VERSION


def build(data, requirements=None, limit=10):
    # Import locally so screening can also generate this artifact without a cycle.
    from camper_pipeline import candidate_state, unique_report_items, report_priority
    leads = [item for item in unique_report_items(data.get("results", [])) if candidate_state(item) == "POTENTIAL MATCH — UNVERIFIED"]
    leads.sort(key=report_priority, reverse=True)
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
        tasks += ["Before purchase, physically test cab A/C; listing-specific advertised cab A/C is sufficient for search qualification.",
                  "Confirm the vehicle is still for sale and where it can be inspected.",
                  "Obtain an independent inspection of rust, drivetrain, brakes and service invoices.",
                  "Measure finished standing height, mattress, exterior length and legal completed travel mass; review the two-person layout and exact drivetrain against specification v2."]
        research = item.get("suitability", {}).get("research", {})
        tasks += [question for entry in research.get("notes", []) for question in entry.get("seller_questions", [])]
        if not research.get("exact_variant_identified"):
            tasks.append("Confirm exact generation, engine code/family, gearbox and body; obtain cited reliability/support evidence before assigning suitability scores.")
        records.append({"search_assessment": item.get("search_assessment"), "suitability": item.get("suitability"), "history": item.get("history"), "listing_url": candidate.get("listing_url"), "plate": item.get("plate"),
                        "name": candidate.get("name"), "source": candidate.get("source"),
                        "observed_at": candidate.get("observed_at"), "checks": candidate.get("checks"),
                        "verified_price_incl_vat": candidate.get("price_incl_vat"), "road_distance_km": candidate.get("distance_km"),
                        "field_evidence": candidate.get("field_evidence", {}), "rdw_concerns": item.get("rdw_risks", []),
                        "blockers": item.get("reasons", []), "next_actions": tasks})
        assessments.append({"listing_url": candidate.get("listing_url"), "plate": item.get("plate"),
                            "reviewer": None, "observed_at": None, "expires_at": None,
                            "measurements": {key: {"value": None, "source_url": None, "independently_checked": False} for key in dict.fromkeys((*MEASUREMENT_RULES, *MEASUREMENTS))},
                            "conversion_checks": {key: {"confirmed": None, "source_url": None, "independently_checked": False} for key in REVIEW_RULES},
                            "checks": {key: {"confirmed": None, "method": None, "source_url": None} for key in REVIEW_CHECKS}})
    return {"generated_on": data.get("generated_on"), "requirements": requirements or {},
            "required_review_measurements": list(MEASUREMENT_RULES),
            "required_conversion_checks": REVIEW_RULES,
            "leads": records, "specification_version": SPEC_VERSION, "preferences": PREFERENCES,
            "review_template": {"requirements": requirements or {}, "specification_version": SPEC_VERSION, "assessments": assessments},
            "qualification_note": "This is a research queue. Blank fields are not verified and no seller is contacted automatically."}
