"""Evidence-based editorial interpretation, not invented mechanical research."""

def details(item):
    c = item["candidate"]
    why = []
    if c.get("checks", {}).get("high_roof") is True:
        why.append("Dakoplossing staat in de advertentie")
    if c.get("checks", {}).get("cab_ac") is True:
        why.append("cabine-airco geadverteerd")
    if c.get("price_incl_vat") is not None:
        why.append("prijs past binnen het aankoopbudget" if c["price_incl_vat"] <= 8000 else "prijs boven budget")
    if c.get("checks", {}).get("distance_within_100km") is True:
        why.append("ophaaladres binnen 100 km rijden")
    research = item.get("suitability", {}).get("research", {})
    notes = research.get("notes", [])
    questions = []
    for risk in item.get("rdw_risks", []):
        if risk.get("code") == "odometer_inconsistent":
            questions.append("RDW meldt Onlogisch: welke facturen en kilometerhistorie verklaren de afwijking?")
        elif risk.get("code") == "apk_expired":
            questions.append("APK is verlopen: wordt de bus geleverd met een nieuwe APK en welke herstelkosten zijn bekend?")
    if c.get("checks", {}).get("high_roof") is not True:
        questions.append("Geen bruikbare stahoogte bevestigd: meet de laadruimte en controleer haalbaarheid, kosten en toelating van een hefdak vóór aankoop.")
    if c.get("field_evidence", {}).get("price", {}).get("conflicts"):
        questions.insert(0, "Btw-prijsinformatie spreekt zichzelf tegen; bevestig schriftelijk de totale consumentenprijs inclusief btw en verplichte kosten.")
    questions.extend(question for entry in notes for question in entry.get("seller_questions", []))
    if not research.get("exact_variant_identified"):
        questions.append("Bevestig bouwjaar/generatie, motorcode, versnellingsbak en carrosseriemaat; de exacte aandrijflijn is nog niet vastgesteld.")
    if c.get("price_incl_vat") is None:
        questions.append("Wat is de totale consumentenprijs inclusief btw en verplichte kosten?")
    if c.get("distance_km") is None:
        questions.append("Wat is het volledige adres waar deze bus kan worden bekeken?")
    questions.append("Is de bus nog te koop en zijn onderhoudsfacturen beschikbaar?")
    suitability = item.get("suitability", {})
    coverage = suitability.get("weighted_coverage_percent", 0)
    score = suitability.get("weighted_score_known_criteria")
    ranking = (f"{score}/100 over onderbouwde criteria; {coverage}% van het gewogen totaal ingevuld"
               if suitability.get("critical_research_supported") and coverage >= 50 else
               f"Nog onvoldoende bewijs voor een totaaloordeel; {coverage}% van het gewogen totaal ingevuld")
    history = item.get("history", {})
    changes = {"newly_observed": "Voor het eerst door deze zoekdienst gezien", "material_price_drop": "Duidelijke prijsverlaging",
               "material_details_changed": "Belangrijke advertentiewijziging", "relisted_or_new_source": "Bekende bus, andere advertentie", "unchanged": "Ongewijzigd bekend", "evidence_updated": "Onderbouwing aangevuld; wijziging door verkoper niet vastgesteld"}
    conflicts = history.get("conflicting_source_prices", [])
    if conflicts:
        questions.insert(0, "Eerder waargenomen bronprijzen verschillen (EUR " + ", ".join(str(value) for value in conflicts) + "); bevestig de actuele totale prijs.")
    return {"why": "; ".join(why) or "Nog onvoldoende advertentiegegevens voor een overtuigende zoekmatch",
            "questions": list(dict.fromkeys(questions))[:5], "research_notes": notes, "ranking": ranking,
            "category": suitability.get("category", "C"), "history": changes.get(history.get("status"), "Geen eerdere zoekhistorie beschikbaar"),
            "conflicts": history.get("conflicting_source_prices", []),
            "purchase_actions": "Voor aankoop: beschikbaarheid bevestigen, onafhankelijke technische keuring, airco testen en inrichting/gewichten controleren."}
