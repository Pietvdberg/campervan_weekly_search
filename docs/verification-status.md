# Pipeline verification scope

This repository remains a development search system, without a production weekly
schedule. The user has supplied `context.md` and specification v2; public requirements and operational
boundaries are reconciled in [requirements](requirements.md).

- PR CI runs syntax compilation and all offline unittest modules. The strict
  review follow-ups now have 256 tests, including vehicle identity,
  conversion review, source access stops, report consistency and mail retry state.
- The marketplace integration workflow performs bounded live discovery across
  six source groups. It records coverage gaps and requires identity-bound evidence
  for development acceptance. This does not demonstrate exhaustive coverage.
- `weekly-verification.yml` processes `candidates.json`, which is an empty manual
  candidate input. It does not run discovery and must not be interpreted as a
  production search.
- Controlled fixtures demonstrate passing and failing conversion review. No real
  vehicle measurements are supplied. Specification v2 now defines the criteria;
  the [adoption record](specification-v2-adoption.md) lists remaining acceptance gaps.
- Manual mail workflows address only the development recipient. SMTP acceptance
  and Gmail Sent confirmation do not prove recipient delivery. Retry state blocks
  blind resubmission after ambiguous or accepted SMTP submission.
- The external Pi timer collects RSS locally. Upload is separate; data-only pushes
  do not trigger marketplace discovery. This is not end-to-end weekly automation.

Search-versus-purchase separation, weighted scoring, a maintained initial variant
research registry and persistent weekly change tracking are implemented; see the
[weekly search design](useful-weekly-search.md).

Remaining production work: real reviewed candidates, expansion of cited variant research,
stable source access and maintained dealer coverage, an operational cadence,
durable mail/audit state, appropriate retention and independently demonstrated
live end-to-end outcomes. PR CI passing alone does not satisfy those conditions.
