# Marketplace discovery and RDW integration

The development workflow runs on selected code changes to main and on manual
dispatch. It uses direct seeds for six source groups: Marktplaats, AutoScout24,
AutoTrack, viaBOVAG, AutoWereld and local dealers. viaBOVAG has bounded inventory
pagination. Public Bing RSS provides fallback links; a validated external
AutoWereld RSS snapshot supplies separate unverified leads.

Discovery attempts individual pages, scopes evidence to the requested vehicle,
screens conservative facts and queries RDW only for confirmed listing plates.
It also probes RDW with historical plate V-706-SG; that probe does not imply the
vehicle is for sale. A returned page without bound identity is an unverified
lead, not confirmed registration/equipment evidence.

A shared per-host guard stops HTTP 403/429 requests and limits each host to 100
requests per run across inventory/feed/detail phases and source groups. Coverage
records restriction reasons and host counts; independent dealer hosts continue.

`verify_discovery.py discovered_candidates.json` requires at least one
identity-bound candidate plus coverage records for all six source groups to pass
**development discovery verification**. It reports groups without bound candidates
and never declares production readiness. This is not exhaustive inventory or a
claim that empty sources have no vehicles. A blocked source is an operational gap.

Unknown road distance, VAT, actual A/C operation, mechanical condition and payload
remain unverified. Conversion review requires explicit requirements and dated,
independently checked evidence; see [conversion evidence](conversion-evidence.md).

Push runs do not send mail. Manual development dispatch sends only to the Hotmail
test recipient. Mail retry state is preserved as a separate artifact. No production
weekly schedule is enabled. Passing PR tests establishes offline regression
behavior; development discovery acceptance and actual delivery are separate.
