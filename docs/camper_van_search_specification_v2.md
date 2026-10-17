---
title: Camper Van Search Specification
version: 2.0
updated: 2026-10-17
supersedes: 1.0
refinement_source: October 2026 campervan_weekly_search project handover
purpose: Weekly AI-assisted search for newly listed vans suitable for DIY camper conversion
language: en
country: Netherlands
search_origin: Bergen op Zoom
search_radius_km_preferred: 100
search_radius_km_max: 100
search_distance_basis: verified_driving_route_km
maximum_purchase_price_eur_including_vat: 8000
currency: EUR
target_completion_date: 2028-03-01
---


> **Version 2.0 amendment and precedence (17 October 2026):** This file preserves the original 54-section specification and adds the later operational requirements in Sections 55–68. Where an original rule differs, the explicit October 2026 amendment takes precedence. In particular, **100 km actual driving distance** is the hard routine inspection limit (not the earlier 125 km allowance); **€8,000 including VAT** is the purchase-price ceiling; and a verified/recommendable listing requires **≥90% supported evidence** with no overriding hard rejection. Do not infer that a 90% score proves a van is mechanically safe. The original preferences and weighted criteria remain useful after hard filters.

> **Operational release amendment (17 October 2026):** The user explicitly requested
> priorities 1–3, including production activation after live delivery acceptance.
> The release record in [weekly production delivery](weekly-production-delivery.md)
> supersedes the earlier “not yet approved” activation status in Sections 55–68.
> Production cadence is Thursday 15:00 Europe/Amsterdam with DST, using the two
> existing production recipients. Manual/development mail remains Hotmail-only;
> push CI sends no email. Advertised A/C remains sufficient for search screening.

# Camper Van Search Specification

## 1. Purpose

Use this document as the source of truth for an AI agent that searches Dutch vehicle marketplaces for newly listed vans suitable for conversion into a camper.

The AI should:

1. Search for newly listed vehicles that plausibly match the requirements below.
2. Apply hard filters before ranking.
3. Avoid excluding candidates solely because they are old, high-mileage, diesel, cosmetically rough, or less convenient to convert.
4. Evaluate specific **generation + engine + gearbox + body size**, not merely brand/model.
5. Prefer mechanical quality, reliability, maintainability, and European repairability over age, technology, appearance, or conversion convenience.
6. Highlight uncertainty rather than inventing missing information.
7. De-duplicate vehicles already seen in previous weekly searches when prior-result state is available.

---

# 2. Intended Use

## Occupants

- Primary use: 2 adults.
- Future possibility: children / 3–4 occupants years from now.
- Current required belted seats: 2.
- Current required sleeping places: 2.
- Future rear-seat expandability is a bonus, not a current hard requirement.

## Travel pattern

- Typical trips: weekends to 1 week.
- At least one planned trip of approximately 3 months.
- Expected annual distance: 6,000–10,000 km.
- Driving mix:
  - Mostly motorway.
  - Some mountain roads.
  - Some campsite roads and forest tracks.
- Main travel region: Europe.
- Example destinations:
  - Portugal
  - North Macedonia
  - Norway
  - Austria
- Expected relocation frequency: every 2–3 days.
- Overnight style:
  - Campsites
  - Camperplaatsen / aires
  - Occasional 1–2 night wild/off-grid stays
- Desired off-grid autonomy: approximately 3–4 days.
- Year-round use.
- Must tolerate occasional freezing nights.

---

# 3. Search Geography

## Hard search region

- Country: Netherlands only.
- Do not include imports from Germany, Belgium, or elsewhere.
- Preferred search radius: approximately 100 km from Bergen op Zoom.
- Maximum normal inspection radius: approximately 125 km from Bergen op Zoom.

## Exception

A candidate slightly outside the preferred radius may still be shown if it is an unusually strong match, but it should be clearly marked as outside the preferred search area.

---

# 4. Purchase Budget

## Base vehicle

- Target purchase price: <= €5,000.
- Stretch price: up to approximately €8,000.
- Vehicles above €5,000 should only rank highly when the extra cost buys a meaningful improvement such as:
  - better mechanical condition
  - much stronger service history
  - a substantially more reliable drivetrain
  - important expensive maintenance already completed
  - materially less corrosion
  - significantly better specification without compromising reliability

## Repair reserve

- Maintain at least approximately €2,000 after purchase for catch-up maintenance and unexpected repairs.

## Conversion budget

- Initial conversion budget: approximately €3,000–€4,000.
- The camper will be a long-term project and may be upgraded gradually.

---

# 5. Vehicle Size

Use actual dimensions where available rather than blindly trusting L1/L2/L3 labels because these vary by manufacturer.

## Preferred

- Approximate vehicle length: 5.3–5.6 m.
- Around 5.4 m is especially attractive.

## Acceptable

- Up to approximately 6.0 m if the additional space materially improves camper usability.

## Reject / major penalty

- Approximately 6.4 m or longer.
- Around 7 m is unacceptable.

## Height

- Standing room is required.
- Tallest regular occupant: 176 cm.
- Desired finished standing height: approximately 186 cm.
- H2 is likely sufficient.
- Pop-top / lift roof is acceptable.
- H3 is acceptable but unnecessary if H2 works.
- Fitting under 2.0 m barriers is nice to have, not a requirement.
- Parking-garage compatibility is not important.

---

# 6. Weight and Licence

## Hard requirement

- Must remain suitable for a Dutch category B driving licence.
- Completed camper must stay at or below 3,500 kg maximum authorised mass.

## Build target

- Prefer approximately 250 kg of usable payload remaining after the conversion is complete and loaded for normal travel.

## Evaluation rule

Penalize unusually heavy base vehicles if they make the final 3,500 kg target difficult.

Payload margin is more important than adding unnecessary equipment.

---

# 7. Age and Mileage

## Age

Do not use a simple age cut-off.

Potentially acceptable:

- Approximately 1996 onward for especially proven, mechanically simple, reliable models.
- Approximately 2006 onward as the normal search range.

## Mileage

Do not use a strict mileage maximum.

- 200,000–300,000 km can be acceptable.
- High mileage is not inherently negative when accompanied by:
  - good service history
  - a durable engine/gearbox
  - appropriate previous use
  - good mechanical condition
  - a healthy body

## Priority

When comparing otherwise similar vehicles:

1. Mechanical condition
2. Maintenance/service history
3. Known drivetrain durability
4. Mileage
5. Age

---

# 8. Reliability

## Priority

Reliability is the single most important criterion.

### Importance: 10/10

## Strong requirements

Prefer vehicles with:

- proven engine reliability
- proven gearbox reliability
- known high-mileage durability
- widespread fleet use
- no recurring catastrophic drivetrain weaknesses

## Reject or heavily penalize

- known major engine defects
- engines with frequent catastrophic failure modes
- gearboxes with expensive systemic failure problems
- variants with meaningful risk of €5,000+ engine or gearbox failure
- vehicles where major €2,000–€3,000 repairs are expected as normal ownership

## Repair tolerance

- Roughly €1,500 is the preferred upper limit for a single unexpected repair.
- Occasional larger repairs are not automatically disqualifying, but must be genuinely unusual rather than common for the model.

---

# 9. Maintainability

### Importance: very high

The van should:

- be serviceable by normal independent garages
- not require frequent dealer-only intervention
- not be excessively dependent on proprietary diagnostics
- allow straightforward owner maintenance
- have good workshop information and parts availability
- be mechanically understandable

Owner is comfortable with basic mechanical work up to roughly spark-plug-replacement complexity.

## Hard rejection / major penalty

- poor independent-garage support
- specialist-only maintenance for routine work
- excessive electronic complexity for the vehicle's age/value
- difficult parts sourcing
- poor diagnostic accessibility

Mechanical simplicity is preferred over modern technology.

---

# 10. Parts and European Repairability

## Importance

- European repairability: 9/10
- Parts availability: 8/10

Prefer:

- common European platforms
- large dealer and independent-garage networks
- engines shared across many vehicles
- multiple aftermarket parts suppliers
- easy sourcing of used and new parts
- platforms commonly understood outside the Netherlands

Shared-platform vans are a positive because they improve long-term parts supply.

---

# 11. Rust and Body Condition

## Importance

Corrosion resistance: approximately 8/10.

## Reject

- serious structural rust
- widespread corrosion
- shell requiring major restoration
- rust likely to compromise a camper conversion

## Accept

- minor localized rust
- professional body repairs
- dents
- scratches
- faded paint
- worn commercial cargo interior

Exterior appearance itself has low importance.

---

# 12. Previous Use and History

## Strong preference

- documented maintenance history
- fleet vehicle with good records is acceptable
- high-mileage fleet use may be preferable to low-mileage poor-history private use

## Avoid

- former rental vehicles are undesirable

## Not automatic rejection

- commercial fleet
- trades vehicle
- previous camper
- private vehicle

Judge the individual vehicle and usage pattern.

---

# 13. Interior Camper Requirements

## Bed

### Required

- sleeping space for 2 adults
- real mattress, not merely seat cushions
- minimum mattress size: approximately 170 x 120 cm
- bed setup must not require unloading luggage

### Preferred

- permanent bed
- transverse or longitudinal both acceptable
- convertible, lifting, sliding, or extending bed acceptable if it preserves a real mattress
- side flares acceptable

Permanent bed is preferred over maximum parking convenience.

## Living space

Must support:

- 2 adults spending a full rainy day inside
- comfortable sitting
- indoor cooking
- reasonable movement past each other
- access to storage without dismantling the camper

Separate seating from the bed is preferred but not mandatory.

Interior space importance: 7/10.

---

# 14. Kitchen

### Importance: 8/10

## Required

- permanent indoor kitchen
- proper sink
- 2-burner cooking capability
- moderate worktop space
- approximately 30–50 L refrigerator
- enough food storage for several days

## Preferred energy source

- gas cooking

## Nice to have

- ability to cook outside when weather permits

## Not needed

- freezer
- induction cooking
- large domestic-style kitchen

---

# 15. Toilet and Bathroom

## Toilet

### Mandatory

An indoor toilet must be possible.

Acceptable solution:

- compact portable/chemical toilet stored away when not in use

A fixed cassette toilet is not required.

## Shower

Not required.

Do not give meaningful ranking credit for:

- indoor shower
- wet room
- permanent bathroom

Living and storage space are preferred over a bathroom.

---

# 16. Water System

## Target

- fresh water: approximately 50–75 L
- cold running water
- pump-fed sink
- ability to protect the system from freezing

## Not required

- hot running water
- shower supply
- large grey-water tank
- underslung grey-water tank

Water autonomy importance: 7/10.

---

# 17. Storage

### Importance: 7.5/10

Need storage for:

- normal luggage
- climbing equipment
- SUP-related equipment
- camping chairs/table
- some hiking equipment
- occasional ski equipment
- roadside maintenance tools
- other sports gear

## Preferred

- useful rear garage/storage area
- storage that remains accessible without rearranging the whole camper

## Bicycles

- bicycles can remain outside
- preferred solution: towbar-mounted bike rack

---

# 18. Towbar

## Strong preference

A towbar is desirable.

Primary short-term purpose:

- bicycle rack

Future trailer use is a bonus, not a current requirement.

---

# 19. Cab Comfort

Long driving days of approximately 8–10 hours are realistic.

## Mandatory

- cab air conditioning

## Strong preference

- cruise control
- comfortable seats
- good driving position
- acceptable motorway refinement

## Nice to have

- Android Auto / Apple CarPlay

Factory infotainment is low priority because an aftermarket head unit can be installed.

## Low value

Do not pay much extra for:

- adaptive cruise control
- heated seats
- premium factory infotainment
- extensive driver-assistance systems

---

# 20. Driving and Performance

## Performance importance: 8/10
## Driving comfort importance: 7/10

The vehicle must:

- climb steep roads in Austria/Norway comfortably when converted and loaded
- maintain reasonable speed in mountains
- have adequate overtaking performance
- cruise comfortably around 100 km/h
- remain stable on motorways

Regular 120–130 km/h cruising is not required.

Avoid severely underpowered engine variants.

---

# 21. Drivetrain

No inherent preference for:

- FWD
- RWD
- AWD

Choose based on:

1. reliability
2. maintenance
3. loaded mountain performance
4. year-round traction
5. total cost

## AWD

Not required.

Expected unpaved use:

- campsite roads
- gravel roads
- forest tracks

No serious off-roading planned.

AWD should not justify a large premium.

Maximum plausible AWD premium: approximately 20%, and only if it brings meaningful practical value.

---

# 22. Fuel Economy and Range

## Fuel economy

Importance: 6/10.

Acceptable diesel consumption target:

- approximately 9–10 L/100 km

Interpretation:

- 1 L/100 km difference: minor
- 2 L/100 km difference: meaningful

Fuel economy may be sacrificed for:

- reliability
- better interior layout
- better mechanical condition
- larger fuel tank / longer range

## Fuel range

Long real-world range is very important.

For each candidate, estimate:

- tank size
- realistic loaded consumption
- approximate real touring range

A less efficient van with a much larger tank may outrank a more efficient vehicle with poor range.

---

# 23. Fuel Type

## Preference, all else being equal

1. Petrol
2. Electric
3. Diesel

Do not search for LPG.

## Important rule

Fuel type is subordinate to:

- reliability
- maintainability
- price
- interior suitability
- parts support

A very good diesel should outrank a mediocre petrol van.

---

# 24. Electric-Van Threshold

Electric vans may be considered only if they genuinely meet the use case.

Preferred minimum:

- approximately 500 km real motorway range

Acceptable charging stop:

- up to approximately 2 hours

Reliability and load capacity must still be suitable.

Do not award extra points merely because a vehicle is electric.

---

# 25. Emissions and Future-Proofing

### Importance: 6/10

Preferred:

- Euro 5 or better

Not a strict rule.

The camper will mostly avoid major city centres, so low-emission-zone access should not override reliability or value.

A good older Euro 5 diesel may rank above a newer but less reliable Euro 6 model.

---

# 26. Electrical Conversion Requirements

## Initial system

Target:

- 100–200 Ah lithium camper battery
- around 200 W solar
- 230 V outlets
- USB/device charging
- lights
- refrigerator
- water pump
- powered roof fan
- small heater/cooling equipment
- occasional laptop use
- kettle
- coffee maker

## Cooking

- gas, not induction

## Future

The layout should allow later expansion toward greater off-grid capability.

---

# 27. Off-Grid Capability

### Importance: 7/10

Initial build should support approximately 3–4 days without campsite electricity while keeping essential systems operational.

Future expansion toward fuller off-grid capability is desirable.

---

# 28. Roof

## Preferred

- H2 fixed roof or pop-top/lift roof
- one powered roof fan
- awning
- approximately 200 W solar

## Ideal

- pop-top/lift roof with solar mounted on top, if practical

## Conditional

Roof rack / roof box are only useful if they do not conflict with the lift-roof solution.

---

# 29. Heating and Winter Use

## Requirements

- good insulation
- reasonable thermal-bridge treatment
- water system protected from occasional freezing
- living-area heating possible

### Insulation importance: 8/10
### Thermal-bridge importance: 7/10

Electric heating is currently preferred, but this should not be a base-vehicle filter.

---

# 30. Ventilation

Required:

- at least 1 powered roof fan

Preferred:

- mosquito screening

Opening side/rear camper windows are not mandatory.

---

# 31. Seating

## Current

- 2 belted occupants
- preferably two individual front seats rather than a passenger bench

## Living area

Prefer at least 2 usable living-area seats.

Swivel front seats are optional.

## Future

Potential to add approved rear travel seats later is a bonus.

Do not reject an otherwise excellent two-seat van solely because future four-person conversion would require significant work.

---

# 32. Safety

### Importance: 5/10

Preferred baseline:

- ABS
- driver airbag
- passenger airbag

Not required:

- adaptive cruise control
- lane keeping
- AEB
- blind-spot monitoring
- traffic-sign recognition

Reversing camera is preferred but can be retrofitted.

Parking sensors are not required.

---

# 33. Security

### Importance: 8/10

Platform should allow effective aftermarket security such as:

- deadlocks
- alarm
- GPS tracker
- additional window security if useful

Penalize platforms with a severe known theft vulnerability.

---

# 34. Doors

Preferred:

- one sliding side door
- rear barn doors

Not required:

- second sliding door
- 270-degree rear doors

Not preferred:

- tailgate

---

# 35. Conversion Philosophy

The conversion will be mostly DIY.

Likely outsourced:

- kitchen
- electrical work

Owner:

- limited camper-building experience
- some woodworking experience
- generally good with hands
- willing to fabricate custom components

## Evaluation rule

Mechanical quality outranks ease of conversion.

Do not reject a mechanically excellent van merely because:

- walls are curved
- fewer premade camper components exist
- some custom fabrication is required

---

# 36. Camper Ecosystem

### Importance: 5/10

Useful but not decisive.

Positive factors:

- windows available
- pop-top available
- swivel bases available
- roof accessories
- mosquito screens
- water tanks
- conversion examples/community knowledge

Do not over-weight furniture kits or model-specific conversion products.

---

# 37. Appearance and Stealth

## Appearance importance: 3/10
## Stealth importance: 5/10

Accept:

- commercial appearance
- dents
- scratches
- tired paint
- visible camper windows
- awning

Do not pay a meaningful premium for appearance.

---

# 38. Resale

### Importance: 4/10

Expected ownership:

- approximately 7–10 years

Likely future sale:

- complete camper

Common platforms are useful for resale, but resale value should not drive the purchase.

---

# 39. Brand and Model Bias

Currently attractive:

- Volkswagen
- Toyota
- Ford

Current lower-confidence brand:

- Renault

Models already of interest:

- Volkswagen Transporter
- Toyota HiAce
- Ford Transit
- Mercedes-Benz Sprinter if compact enough

## Critical instruction

Do not blindly favor or reject a brand.

Always evaluate the exact:

- generation
- engine
- gearbox
- body size
- year
- known failure modes

A strong Renault variant may outrank a weak Volkswagen variant if the evidence supports it.

---

# 40. Hard Rejection Criteria

Normally reject a listing if any of the following is true:

1. Serious or widespread structural rust.
2. Known major engine defect with unacceptable failure risk.
3. Known gearbox with unacceptable catastrophic-failure risk.
4. Poor independent-garage maintainability.
5. Weak parts availability in Europe.
6. Insufficient interior room for the intended conversion.
7. Cannot realistically provide a >= 170 x 120 cm real mattress.
8. Cannot provide practical standing height through fixed roof or viable pop-top.
9. No cab air conditioning.
10. Completed conversion is unlikely to remain practical below 3,500 kg.
11. Vehicle length is approximately 6.4 m or more.
12. Vehicle is LPG-only.
13. Vehicle is an import requiring purchase outside the Netherlands.
14. Listing shows major corrosion or obvious structural damage.
15. Drivetrain's common major failure risk is incompatible with long-distance European travel.

---

# 41. Strong Preferences

Prefer vehicles with:

- purchase price around €5,000
- price no higher than approximately €8,000
- approximately 5.3–5.6 m length
- H2 or practical pop-top
- Euro 5+
- complete maintenance history
- common European platform
- independent-garage friendliness
- strong parts availability
- proven high-mileage reliability
- adequate loaded mountain performance
- comfortable 100 km/h cruising
- long fuel range
- around 9–10 L/100 km or better
- useful payload margin
- towbar
- cruise control
- good cab comfort
- good corrosion resistance
- practical rear storage
- suitable roof for fan + solar
- future upgrade potential
- security-upgrade options

---

# 42. Nice-to-Haves

Use mainly to distinguish between otherwise similar candidates:

- pop-top roof
- solar on pop-top
- reversing camera
- swivelling passenger seat
- roof rack
- roof box
- exterior ladder
- especially square cargo area
- large DIY camper community
- strong aftermarket ecosystem
- more powerful engine version
- petrol drivetrain
- electric drivetrain if fully suitable
- better-than-required fuel economy
- attractive appearance
- easy future rear-seat conversion

---

# 43. Low-Priority / Do-Not-Overweight

Do not allow these to eliminate a much stronger mechanical candidate:

- cosmetic appearance
- modern infotainment
- adaptive cruise control
- lane assist
- heated seats
- automatic transmission
- AWD
- 4x4 styling
- shower potential
- wet room
- freezer
- hot water
- fixed cassette toilet
- huge solar array
- factory camper furniture
- perfect standing height without modification
- factory parking sensors
- high maximum speed
- resale value
- stealth styling
- fashionable camper brand

---

# 44. Weighted Scoring Model

Use the following weights after applying hard filters.

| Criterion | Weight /10 |
|---|---:|
| Reliability | 10 |
| European repairability | 9 |
| Performance | 8 |
| Parts availability | 8 |
| Low running costs | 8 |
| Kitchen suitability | 8 |
| Storage | 7.5 |
| Purchase price | 7 |
| Maintenance cost | 7 |
| Vehicle availability | 7 |
| Interior space | 7 |
| Payload | 7 |
| Driving comfort | 7 |
| Off-grid capability | 7 |
| Conversion ease | 7 |
| Water capability | 7 |
| Winter capability | 7 |
| Rough-road capability | 7 |
| Fuel economy | 6 |
| Electrical capability | 6 |
| Emissions/future-proofing | 6 |
| Toilet integration | 6 |
| Exterior compactness | 5 |
| Safety | 5 |
| Camper aftermarket | 5 |
| Stealth | 5 |
| Road tax | 5 |
| Insurance | 5 |
| Modern technology | 4 |
| Resale value | 4 |
| Appearance | 3 |
| Automatic transmission | 2 |

## Scoring method

For every surviving candidate:

1. Score each applicable criterion from 0–10.
2. Multiply score by its weight.
3. Sum weighted scores.
4. Normalize to 0–100 if useful.
5. Do not let a high weighted score override a hard rejection criterion.

---

# 45. Candidate Evaluation Checklist

For every serious listing, determine as much of the following as possible:

1. Asking price.
2. Distance from Bergen op Zoom.
3. Exact model.
4. Generation.
5. Year.
6. Engine code or engine family if identifiable.
7. Power output.
8. Gearbox type.
9. Body length.
10. Roof height.
11. External dimensions.
12. Internal cargo dimensions.
13. Odometer reading.
14. Fuel type.
15. Euro emissions class.
16. Gross vehicle weight.
17. Empty/kerb weight if available.
18. Estimated usable camper payload.
19. Cab air conditioning.
20. Cruise control.
21. ABS.
22. Driver airbag.
23. Passenger airbag.
24. Towbar.
25. Service history.
26. Timing belt/chain status.
27. Major recent repairs.
28. Known engine weaknesses.
29. Known gearbox weaknesses.
30. Known rust areas.
31. Visible rust/body concerns in listing photos.
32. Realistic fuel consumption.
33. Fuel tank capacity.
34. Approximate touring range.
35. European parts availability.
36. Independent-garage support.
37. Ease of owner servicing.
38. Theft/security weaknesses.
39. Pop-top availability if needed.
40. Roof fan/solar feasibility.
41. Rear-seat retrofit possibility.
42. Camper aftermarket/community support.
43. Seller type.
44. Previous use where known.
45. APK expiry.
46. Number of owners where known.
47. Signs of suspiciously incomplete listing information.
48. Overall confidence in the data.

---

# 46. Weekly Search Rules

The AI performing a weekly search should:

1. Search major Dutch used-vehicle marketplaces and dealer listings.
2. Focus on listings posted since the previous search.
3. Include older listings only if:
   - price dropped materially
   - listing changed materially
   - it was missed previously
4. De-duplicate the same vehicle advertised on multiple sites.
5. Avoid showing clearly unsuitable vehicles simply to fill a quota.
6. Prefer 5 strong matches over 20 mediocre matches.
7. Clearly distinguish:
   - confirmed facts from the listing
   - known model-generation information
   - reasonable inference
   - unknown information
8. Flag suspiciously low prices.
9. Flag likely VAT-excluded commercial prices.
10. Flag vehicles whose stated price appears to be ex-BTW / excl. BTW.
11. Flag obvious export-only listings.
12. Flag vehicles substantially outside the geographic preference.
13. Flag listings where the vehicle appears to be a crew cab/double cab that materially reduces camper space.
14. Flag listings where cargo/body dimensions are uncertain.

---

# 47. Weekly Result Categories

Classify each candidate as one of:

## A — Excellent Match

- Passes all hard filters.
- Strong drivetrain/reliability fit.
- Good price.
- Good camper dimensions.
- Worth contacting quickly.

## B — Good Match

- Passes hard filters.
- Some compromises but still a credible candidate.
- Worth investigating.

## C — Conditional Match

- Potentially suitable.
- Important information missing or one notable compromise.
- Only pursue if the issue can be resolved.

## D — Reject

- Fails one or more hard requirements.
- Mention only when useful to explain why a seemingly attractive listing should be avoided.

---

# 48. Weekly Result Format

Return a concise summary first, followed by a comparison table.

## Summary

Include:

- number of new relevant listings found
- number of A/B/C candidates
- best new candidate
- notable market changes
- whether this week is stronger or weaker than recent weeks if history is available

## Candidate Table

Use columns:

| Rank | Match | Vehicle | Year | Engine | Gearbox | Body | KM | Price | Distance | Reliability | Repairability | Camper Fit | Main Positives | Main Risks | Verdict |
|---|---|---|---|---|---|---|---:|---:|---:|---|---|---|---|---|---|

Then provide a short section for each A or B candidate with:

### Why it fits

### Known mechanical concerns

### Camper-conversion fit

### Questions to ask the seller

### Inspection priorities

### Estimated value assessment

Use:

- `good value`
- `fair`
- `expensive`
- `suspiciously cheap`

where enough market context exists.

---

# 49. Seller Questions for Strong Candidates

For A/B candidates, generate a tailored seller-question list based on missing information.

Default questions should cover:

- maintenance history available?
- timing belt/chain history?
- clutch / dual-mass flywheel history?
- gearbox service history where relevant?
- injector/turbo/EGR/DPF/AdBlue work?
- rust repairs?
- accident/bodywork history?
- current faults or dashboard warnings?
- air conditioning working correctly?
- oil or coolant consumption?
- cold-start behaviour?
- reason for sale?
- previous use?
- towbar fitted and approved?
- APK advisories?
- any known water leaks?
- tyre age/condition?
- brakes/suspension recently serviced?

Only include questions relevant to that specific drivetrain and listing.

---

# 50. AI Research Rules for Mechanical Reliability

When evaluating a model:

1. Research the exact generation.
2. Research the exact engine family/code where possible.
3. Research the exact gearbox.
4. Separate anecdotal owner complaints from documented recurring failure patterns.
5. Distinguish:
   - common minor issues
   - common expensive issues
   - rare catastrophic failures
6. Consider whether failures typically occur at the listed mileage.
7. Prefer evidence from:
   - specialist forums
   - owner communities
   - workshop/service information
   - recall/service campaign data
   - long-term reliability reports
   - mechanics/specialists
8. Avoid generic statements such as "Transporters are reliable."
9. State uncertainty when the exact drivetrain cannot be confirmed.

---

# 51. Ranking Philosophy

The search should prioritize, in order:

1. Reliability
2. Maintainability
3. European repairability
4. Camper suitability
5. Loaded mountain performance
6. Mechanical condition
7. Service history
8. Purchase price / total ownership value
9. Parts availability
10. Payload
11. Driving comfort
12. Fuel range
13. Fuel economy
14. Age/mileage
15. Appearance and technology

A candidate should never win simply because it is newer or has lower mileage.

---

# 52. Search Prompt Template

Use the following prompt for a weekly search.

```text
Search Dutch used-vehicle marketplaces for newly listed vans suitable for my DIY camper conversion.

Use the attached Camper Van Search Specification as the source of truth.

SEARCH PRIORITIES
- Reliability is the highest priority.
- Prioritize mechanically simple, independently repairable vehicles with excellent parts availability throughout Europe.
- Evaluate exact generation + engine + gearbox + body size, not merely brand/model.
- Mechanical condition and maintenance history matter more than age or mileage.
- Do not exclude high-mileage vans automatically.
- Do not exclude diesel automatically.
- Do not favor a vehicle merely because it is newer, lower-mileage, automatic, AWD, or cosmetically cleaner.

CORE SEARCH PARAMETERS
- Netherlands only.
- Prefer within 100 km of Bergen op Zoom.
- Normally do not exceed 125 km.
- Target price <= €5,000.
- Stretch to approximately €8,000 only for materially better candidates.
- Prefer approximately 5.3–5.6 m long.
- Approximately 6.0 m is acceptable.
- Approximately 6.4 m or longer is unsuitable.
- Completed camper must remain <= 3,500 kg.
- Cab air conditioning is mandatory.
- Need room for a real mattress of at least 170 x 120 cm.
- Need practical standing height via H2/fixed high roof or viable pop-top.
- Need enough interior room for two adults to comfortably spend a rainy day inside.
- Need adequate loaded mountain performance for countries such as Austria and Norway.
- Need strong European parts and garage support.
- Serious rust, known major engine problems, poor maintainability, or catastrophic drivetrain risk are deal-breakers.

PREFERRED PLATFORMS CURRENTLY INCLUDE
- Volkswagen Transporter
- Toyota HiAce
- Ford Transit
- Compact Mercedes-Benz Sprinter variants

But do not limit the search to these. Find less-obvious alternatives that satisfy the requirements better.

For every new candidate:
1. Verify the exact generation, engine, gearbox and approximate body dimensions.
2. Research known engine/gearbox failure modes.
3. Judge European repairability and parts availability.
4. Estimate whether it can work as the intended camper.
5. Flag likely payload/3,500 kg concerns.
6. Flag rust risks.
7. Flag VAT-exclusive prices, export listings, suspiciously cheap vehicles or misleading ads.
8. State which facts are confirmed, inferred or unknown.
9. Score the vehicle using the weighting model in the specification.
10. Classify it A, B, C or D.

Return:
- a short weekly market summary
- a ranked comparison table
- detailed notes for A and B candidates
- tailored seller questions
- inspection priorities
- links to the listings
- a section called "Best candidate this week"

If a listing was already shown in a previous weekly update, do not present it as new unless its price or details changed materially.
```

---

# 53. Short Search-Agent Instruction

For systems that work better with a shorter standing instruction:

```text
Find newly listed Dutch vans that match the Camper Van Search Specification. Apply hard filters first, then rank surviving candidates using the weighted criteria. Reliability, maintainability, European repairability and camper suitability dominate the ranking. Evaluate exact generation + engine + gearbox + body size. Prefer mechanical condition and service history over age or mileage. Return only genuinely relevant new listings and clearly flag uncertainty, mechanical risks, rust, payload concerns and suspicious pricing.
```

---

# 54. Search State to Preserve Between Weeks

If the AI system supports memory/state, retain:

```yaml
search_state:
  previous_search_date: null
  seen_listing_ids: []
  seen_listing_urls: []
  rejected_vehicles: []
  contacted_vehicles: []
  shortlisted_vehicles: []
  historical_price_changes: {}
```

Use this to identify:

- genuinely new listings
- relisted vehicles
- price reductions
- previously rejected vans
- previously shortlisted vans

---

# 55. Definition of a Successful Search Result

A successful weekly search does **not** mean finding many vans.

It means identifying any newly available vehicle that materially increases the chance of finding:

> A reliable, mechanically understandable, commonly supported European van around 5.3–6.0 m long, preferably around €5,000 and no more than approximately €8,000, capable of becoming a comfortable two-person year-round camper below 3,500 kg, with enough performance for mountain travel, cab air conditioning, useful storage, a proper bed, indoor cooking and several days of basic off-grid independence.

---

# 55. Version 2.0 — Refinement Requirements and Authority

These amendments reflect requirements agreed during the later `Pietvdberg/campervan_weekly_search` project refinement through 17 October 2026. They supplement—not replace—the original vehicle-choice specification. Requirements in Sections 55–68 govern the **live discovery, validation, reporting, scheduling, security and retention implementation**. Historical observations, sample listings, and pending work are identified separately and **are not themselves purchase recommendations or verified implementation claims**.

**Precedence:** (1) latest explicit user instruction; (2) these dated refinements for conflicting rules; (3) original Sections 1–54. Preserve unmodified original sections for provenance. If a new requirement cannot be corroborated, keep it a proposed improvement instead of silently making it a hard rule.

## 55.1 Changes overriding earlier parameters

| Parameter | Earlier v1.0 | Controlling v2.0 requirement |
|---|---|---|
| Inspection distance | Prefer 100 km; normally up to 125 km; exceptions possible | **Maximum 100 km verified actual driving route from Bergen op Zoom** for normal candidates; do not claim an unverified route satisfies this |
| Price | Prefer ≤€5,000, stretch ~€8,000 | Keep €5,000 preference, but enforce **€8,000 maximum including VAT**; advertised ex-VAT prices cannot be assumed within budget |
| Roof/body | Prefer workable standing room, H2 or pop-top | Discovery emphasis on **L2H2/L3H2 or genuinely equivalent internal dimensions**; reject obvious insufficient-height variants such as L1H1/L2H1 unless independently proven viable under original conversion requirements |
| Confidence | Original weighted 0–100 ranking and A/B/C/D | Additionally impose **≥90% evidence qualification threshold** before verified recommendation; not a mechanical quality probability and not a substitute for hard filters |
| Reporting | Broad ranked search output | **Concise, human-readable, preferably HTML email digest**, full detail retained in audit artifact; no irrelevant or out-of-budget vehicles among recommended/potential showcase cards |
| Scheduled run | Weekly AI search | **Thursday 15:00 Europe/Amsterdam is the intended production schedule, not permission to enable it**; Raspberry Pi RSS collection is a separate approved Thursday 13:30 schedule |

# 56. Strict Vehicle and Listing Eligibility

1. Dutch-located sale listings only; no Belgian/German import search or auction sources. Marktplaats is **allowed** (it is not an auction exclusion).
2. A vehicle must be physically within **100 km road-driving distance** of Bergen op Zoom for the intended test drive. An estimated straight-line distance, city centroid, short GPS distance or unspecified dealer address must remain **unknown**. Do not count it as a distance pass. Clearly disclose unresolved routing rather than fabricating a number.
3. Budget ceiling is **€8,000 incl. applicable VAT**. Keep **€5,000** as target purchase price; reserve approximately €2,000 for repairs and approximately €3,000–€4,000 for the initial conversion, as already specified. Do not include a known price above €8,000 in a candidate showcase merely because its VAT regime is unknown.
4. Cab air conditioning **must be present and functional**, subject to seller demonstration/inspection. A title saying “Airco” proves only an advertised claim, not operation.
5. Prioritize L2H2/L3H2 or equivalent physical length/standing room; **actual interior/exterior dimensions outrank inconsistent manufacturer length labels**. Exclude obviously wrong body styles (open pickups, chassis cabs, tippers, cranes, and impractical box trucks) from candidate recommendations.
6. Remain within **3,500 kg authorized mass**, with realistic loaded finished-camper margin; try to retain approximately 250 kg useful payload under the original v1 requirements. An official empty weight is not a measured ready-to-travel weight.
7. Serious structural rust, catastrophic drivetrain risks, insufficient usable living/bed space, and demonstrably unsuitable conversion configurations remain hard rejections. Do not indiscriminately reject older, diesel or high-mileage vans: compare exact engine, gearbox, generation, service evidence and condition. Extraordinarily high mileage is a material review flag, not an invented absolute cap.
8. Already converted vans may be considered if they meet the same price, road-distance, legal-mass, mechanical and camper-usability requirements.
9. Report what is **advertised**, **officially verified**, **inferred**, or **unknown**; never turn a sales claim into a mechanical inspection finding.

# 57. Source Inventory, Access Rules and Coverage

## 57.1 In-scope sources

- **Marktplaats** — van adverts and individual detail pages.
- **AutoScout24** — individual adverts.
- **AutoTrack** — individual adverts.
- **viaBOVAG** — individual adverts.
- **AutoWereld** — public RSS discovery only when individual pages are inaccessible; see Section 59.
- **Local Dutch dealerships** — real individual vehicle pages, with source attribution.

## 57.2 Explicit source exclusions

Exclude **auction platforms, Gaspedaal, TrucksNL, wijkopenautos and Bedrijfsauto.nl** from this implementation unless a later explicit user requirement reverses the decision. Do not present a newly discovered platform as approved by default.

## 57.3 Discovery and access controls

- Discover inventory and inspect **individual advert detail pages** before counting them as validated candidates. Search-result cards, site inventory counts and RSS feed entries are not equivalent to individual-page validation.
- Keep **per-source discovered vs. successfully fetched/validated** counts and status. Limits such as a 50-page source sample must be disclosed as sampling, **never exhaustive market coverage**.
- Distinguish site-level failures, missing listing details, stale/expired adverts, blocked access, and rejected vehicle eligibility.
- Respect site access conditions and anti-bot controls. An HTTP **403 is not permission to circumvent restrictions**; do not invent page data.
- Normalize direct first-party advert URLs, strip known tracking parameters where safe, and avoid Outlook Safe Links wrapping in authored email links; HTML escaping and safe link handling are mandatory.
- Deduplicate repeated inventory and cross-site re-adverts in the **human-readable digest** when backed by reliable identity evidence. Preserve separate raw URLs, seller claims and all conflicting records in the audit trail.

# 58. Evidence Model, Qualification and Rejection

## 58.1 Evidence status

Evaluate hard rules and the current qualification checks as **pass / fail / unknown** with per-field provenance. Critical pipeline checks include:

- `high_roof`
- `cab_ac`
- `conversion_suitable`
- `distance_within_100km`
- `price_incl_vat_within_8000`

Maintain additional source, advertised/verified price, route, plate, RDW/APK, dimensions, GVW, payload, air-conditioning operation, repair and history evidence where supported.

## 58.2 Qualification criteria

- Only classify a listing as **verified ≥90% qualified** if the pipeline's required evidence checks yield at least **90% explicitly supported passes** and **no hard rejection**. A failed required condition is not cured by other passed checks. Unknown is **not** pass.
- Treat an evidence percentage as **coverage of supported checklist conditions**, not a probability of safe purchase, probability of mechanical soundness or an overall numerical valuation of the van.
- Apply original **weighted suitability scoring** only after hard filtering and with explicit unknown/confidence annotations. Do not conflate the v1.0 weighted ranking score and the later evidence-completeness percentage.
- Unverified but plausible records may appear in a **clearly labeled research-leads** section, not as qualified recommendations, if they have no known disqualifier and potentially useful follow-up checks. An explicitly **€19,999** listing is not a budget-eligible potential match even if its VAT basis is missing.
- Do not lower the 90% threshold to manufacture candidates. Some checks, notably `conversion_suitable`, may require manual inspection, dimensions or seller-provided corroboration.
- **No matches** means none verified from the searches performed, **not** proof that no fitting vans are on sale.

# 59. AutoWereld RSS — Strict Unverified Boundary

AutoWereld individual advert pages were returning HTTP 403 from the GitHub environment. Public RSS feeds are a useful **discovery index only**, not detail-page verification.

- Collect public feeds for **Peugeot Boxer, Ford Transit, Citroën Jumper, Fiat Ducato and Renault Master** on the Raspberry Pi; the current implementation collected up to **15 per feed** (roughly 75 index records). This is a collection configuration, not a guarantee of live availability.
- Maintain a separate, timestamped `data/autowereld_rss_snapshot.json` with validation and safeguards: **48-hour freshness TTL, maximum 250 items, maximum 300 KB** under the established implementation. Invalid/stale data must not be silently trusted.
- Pass snapshot entries via `unverified_rss_leads`, apart from confirmed individual candidate records. A **fresh_index_only** status confirms only snapshot freshness; it does not mean any advert was successfully opened or checked.
- **Never score, qualify, recommend or count RSS-only leads as validated individual pages**. Their headline, advertised price and timestamp are unverified seller/index claims; VAT regime, distance, registration, availability, conversion suitability and technical condition remain unresolved.
- Clearly label any optional digest section **“AutoWereld — unverified RSS tips”**; show at most five informative leads, with explicit missing checks and direct listing URLs. Their apparent low price must not be converted into a purchase recommendation.
- The local collector may upload the snapshot to the repository but **must not dispatch a search workflow or send email**.

# 60. Price, VAT and Driving-Route Verification

## 60.1 Prices

1. Record **seller-advertised price** separately from **verified buyer price including VAT**.
2. Accept inclusive VAT status only if the amount's **own label / adjacent first-party context** explicitly says `incl. btw`, a correctly interpreted margin scheme, or another supportable gross-price basis. Explicit `excl. btw` must be handled and converted as appropriate only when the association to **that amount** is clear.
3. Use precise decimal money arithmetic rather than float rounding for VAT conversions and comparisons.
4. Unlabeled JSON-LD `price` or a label attached to another page component **does not** establish VAT status. Contradictory labels mean **unknown** until resolved.
5. Do **not** assume all advertised prices include VAT and do **not** blindly multiply an unidentified price by **1.21**. Do not call an unknown-price record within budget without evidence.
6. A **clearly advertised amount >€8,000** is an effective early budget exclusion for a comparable normal Dutch listing; do not elevate a €19,999 van because inclusive/exclusive VAT tagging is unresolved. Preserve context for genuine pricing anomalies/discounts and do not assert an impossible net-to-gross inference.

## 60.2 Driving distance

1. Prefer a **same-listing, verified full seller address**. Site structured data may supply a valid Dutch postcode plus house number.
2. Resolve an exact address using **PDOK BAG/Locationsserver** and verify the returned postcode/house number match before routing.
3. Obtain **actual road-driving distance** from Bergen op Zoom via a routing service such as **OSRM**; record route evidence and not merely coordinates.
4. If the page provides only town, approximate coordinate, a partial address, an untrusted location or failed/mismatched PDOK lookup, set route to **unknown**. Do not infer a ≤100 km pass.
5. External routing service failures are **unknown**, not a rejection or positive route match.

# 61. RDW Registration, APK History and Inspection Evidence

- Where the **correct plate is independently linked to an individual listing**, query RDW records for registration, inspection expiry, odometer assessment, maximum vehicle mass and empty vehicle mass. Avoid borrowing a plate from a different vehicle, generic inventory page or historical demo record.
- Retain source and timestamp for RDW and seller evidence; treat RDW as authoritative for recorded administrative fields, **not** a guarantee of working mechanics.
- Decode APK defect codes using RDW's defect catalogue into **human-readable Dutch descriptions** where available; never invent a description for an unknown code. Preserve code, date and source when the decoding is missing.
- Historical defects (e.g. `AC1`, `205`, `RA2`) are **historical registered findings**; neither prove a fault remains today nor establish it was repaired. Deduplicate repeated entries carefully without erasing distinct dated events.
- An expired APK, odometer assessment **Onlogisch**, suspicious mass/payload or defect record is a meaningful caution/verification prompt, not an automatic claim about current roadworthiness without context.
- The development RDW probe **`V-706-SG` is a historical test plate, not a live listing**. Report it only as a diagnostic test and never in recommended candidate cards.
- For serious leads request service invoices, timing-belt/chain or clutch history when relevant, technical inspection of drivetrain, rust and AC, measurement/weight of actual vehicle, and an **independent pre-purchase inspection**. APK approval alone is insufficient.

# 62. Human-Readable Email and Weekly Report Contract

The user explicitly preferred the earlier **AI-quality narrative readability**, and rejected giant dumps of listings and an overly terse plain-text report. The required communication is an actionable **curated digest** with real evidence, not a raw scrape.

## 62.1 Presentation

- **HTML email** with graceful **plain-text fallback**, clear visual hierarchy and Dutch-friendly wording (current template title: **“Camperzoektocht · [datum]”**). Keep reasonably readable on mobile and in Outlook/Hotmail.
- Opening snapshot: run date, explicitly verified ≥90% qualifiers, number of **individual adverts screened**, number rejected, incomplete-source caveat.
- **Verified candidates** first; **interesting but not yet verified** research leads second (up to five); **AutoWereld RSS-only tips** in their own explicitly nonqualifying section (up to five).
- Show concise, scannable **vehicle cards**: make/model/body, market source, seller-advertised price, confirmed price incl. VAT or **not confirmed**, actual driving km or **unverified**, qualification evidence status, outstanding checks, and **clickable direct advert URL**.
- Provide source coverage summary/table (discovered, validated individual pages, verified price/route, RSS-only status). Clarify that source gaps limit discovery.
- Provide a short editorial explanation of **why each interesting candidate matters**, the decisive uncertainties, seller questions and next inspection steps. Do not imply AI research where only deterministic extraction was performed; label such narratives as evidence-based interpretation.
- Avoid long encoded Safe Links, repetition, 200+ vehicle dumps, boilerplate RDW history for irrelevant vehicles, cluttered machine fields and large explicit-rejection lists in the **email body**.
- Clearly disclose **no verified candidates** without claiming market exhaustiveness. Never hide adverse facts or turn unknowns into confident prose.
- HTML-escape all untrusted scraped text and use safe first-party URL validation. Maintain accessible plain text if recipient has HTML disabled.

## 62.2 Audit output (not email body)

- Preserve **`discovered_candidates.json`**, full **`screening_results.json`**, concise **`report.txt`**, RDW probe evidence where applicable, exact rejection reasons, source failures and `pass/fail/unknown` provenance as downloadable GitHub Actions audit artifact(s).
- Historical build configured **30-day artifact retention**; do not describe historical artifacts as permanently available.
- The email must distinguish **developer test output** from approved live weekly output.

# 63. Scheduling, Emails and Explicit Authorization

1. Desired **production search** cadence: **every Thursday at 15:00 Europe/Amsterdam local time**, including DST transitions. **Production GitHub schedule/automatic weekly mailing is not yet approved to enable**; no repo change, test success or prior discussion implies permission.
2. Intended **production email** recipients: **both previously agreed addresses**, after explicit approval. The second address is intentionally **not specified here** and must not be invented.
3. **All development, test and manually triggered search emails** go **only to `piet.v.d.berg@hotmail.com`**. Do not include production's second recipient in development mode.
4. A **push or pull request CI run must not send email**. Manual workflow dispatch may send a development-only Hotmail report when that dispatch was explicitly requested or approved; avoid unnecessary repeated test emails.
5. Separate, approved **Raspberry Pi RSS timer**: **Thursday 13:30 Europe/Amsterdam** with `systemd --user`, and user lingering enabled to keep it operational after SSH logout. This local collection may update the GitHub snapshot but **must not trigger an email or workflow dispatch**.
6. Validate timezone and DST semantics on both schedulers independently. Never mistake enabled RSS collection for permission to activate scheduled GitHub mail.

# 64. Repository, CI and Functional Acceptance

- Repository: `https://github.com/Pietvdberg/campervan_weekly_search`.
- Maintain offline regression tests for discovery, RSS parsing/snapshots, source adapters, listing evidence/VAT/PDOK parsing, routes, RDW semantics, candidate qualification, digest rendering and email recipients.
- **Tests must isolate fixture discovery from a real committed RSS snapshot**. Synthetic AutoWereld tests should not ingest 75 real snapshot links (the cause of a previous five-test regression).
- CI should fail clearly on compilation/test error and on a live discovery producing **zero usable individual vehicle records**, rather than falsely green-lighting no discovery. A green run means the pipeline executed, **not** that a van is qualified.
- Preserve separation: **CI push tests and integration without email**, explicitly manual **development report with Hotmail email**, future **production schedule only when authorized**.
- Maintain reproducible artifacts and job logs with source counts, errors, candidate counts, rejected numbers and explicit verification gaps.
- Do not log or commit tokens, email passwords or GitHub secrets. GitHub workflows must use secret storage and least-privilege permissions.
- Repo architecture currently includes `discover_listings.py`, `camper_pipeline.py`, `listing_evidence.py`, `report_html.py`, `send_report.py`, `rdw_lookup.py`, and the AutoWereld helpers. Names are *implementation references*, not hard constraints on future refactoring.

# 65. Raspberry Pi Collection and GitHub Data Handoff

- Raspberry Pi is the approved separate AutoWereld RSS acquisition surface. A public `curl`-based collector can ingest five public feeds into the bounded snapshot; **no attempt to bypass blocked detail pages**.
- Upload to `data/autowereld_rss_snapshot.json` in GitHub via **opt-in GitHub Contents API**, using a minimally scoped credential stored locally with owner-only permissions in a dedicated configuration file. Never embed credential values in docs, logs or source code.
- Preserve snapshot integrity: schema and URL validation, creation timestamp, TTL/max count/max size bounds, content freshness and integrity checks. Reject malformed/off-domain URLs and stale/corrupt snapshots.
- Do **not** call `workflow_dispatch`, send email or promote RSS links to candidates from the Pi upload action.
- Set up proper timing and user lingering for unattended collection; check the running status and logs rather than assuming a timer's presence guarantees the data uploaded.

# 66. Results Retention and Monthly Cleanup

User requested a separate **monthly cleanup GitHub Action** with lifecycle behavior:

- After **one month**, move eligible result files into an **archive folder**.
- After **nine months**, **delete result files** under the agreed retention scheme (count from original creation date; clearly document handling of archived results).
- Never delete source code, specifications, the live RSS snapshot or required current state by interpreting them as expired result files.
- Test age and path matching, dry-run behavior, and GitHub permissions; log archival/deletion actions for audit. Confirm schedule/implementation before describing this as operational: the workflow exists, but its effective schedule was not revalidated in the 17 October handover.
- Distinguish repository result retention from GitHub Actions artifact retention, which was 30 days in the inspected integration workflow.

# 67. Uncertainty, Provenance and User Safety Principles

- Keep evidence **listing-specific**; information extracted from a different vehicle/listing must never fill missing requirements.
- First-party seller HTML/structured data establishes **claims by that seller**, not independently verified operational condition.
- RDW confirms the **recorded official fields** only. Historical defects must have correct code-description linkage and dates.
- Respect marketplace scraping/access restrictions and avoid technological bypasses.
- Do not classify a speculative lead as a purchase recommendation; prominently identify unknown VAT, sales address/route, legal mass, mechanical condition, availability, rust, air-conditioning operation and conversion fit.
- Track previously seen listing IDs and material listing/price changes to avoid presenting old adverts as new. Retain provenance even when the concise email deduplicates duplicates.
- Reject explicit nonmatches early for digest quality without destroying the raw audit trail. Missing evidence alone can be **unverified**, whereas a demonstrably failed hard criterion is **rejected**.
- When historical development totals are quoted, include date/run and avoid representing them as current market truth.

# 68. Validation Status and Open Acceptance Tests (as of 17 October 2026)

The latest recorded inspected GitHub Actions run was [38977667392](https://github.com/Pietvdberg/campervan_weekly_search/actions/runs/38977667392), with **110 passing tests**, **210 individual pages screened**, and **zero ≥90% qualified vehicles**. This is **project status**, not a standing search requirement or evidence that no suitable vehicle exists.

**Already observed / implemented at last check:** six-source discovery framework (five direct-page sources plus AutoWereld RSS index), Pi Thursday 13:30 RSS collection/upload, RDW live historical probe, GitHub test/audit workflow, plain-text report and HTML rendering code, 30-day Action artifacts, development-only email routing on manual dispatch.

**Not established as validated:** human visual appearance of the new HTML email in Hotmail, net improvement to VAT and road-distance evidence across sources, complete technical/physical verification of promising listings, current calendar trigger for monthly cleanup, and an enabled Thursday 15:00 production search. These require explicit acceptance and, for live production activation, user permission.

**Maintainer acceptance checklist:**

- [ ] Confirm every shown verified candidate has supported ≤€8,000 VAT-inclusive price, ≤100 km verified road route, correct roof/AC/conversion dimensions and ≥90% supported evidence with no hard fail.
- [ ] Confirm apparent over-budget adverts (including missing VAT status) do not appear as interesting budget-eligible matches.
- [ ] Confirm `conversion_suitable` remains unknown unless vehicle-specific evidence justifies a pass.
- [ ] Inspect per-source verified VAT, address and road-route counts against earlier baselines rather than assuming extractor improvements worked.
- [ ] Inspect a **received HTML** development email in Hotmail (including mobile view), plus MIME plain-text fallback, before approving report formatting.
- [ ] Confirm RSS-only links never enter scoring/recommendation or validated-page counts.
- [ ] Confirm 30-day audit-artifact retention and monthly archive/deletion lifecycle independently.
- [ ] Obtain explicit approval before enabling 15:00 production scheduling or dual-recipient production mail.

---

**Companion historical handover:** `context.md` (compiled 17 October 2026). This specification describes what the system **must do**; the handover describes what was **implemented and observed**, with commit and run references.
