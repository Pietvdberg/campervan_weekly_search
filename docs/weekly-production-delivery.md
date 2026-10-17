# Weekly delivery release — 17 October 2026

The user explicitly requested priorities 1–3: delivery-aware history, production
scheduling and a complete delivery/recovery acceptance run. This supersedes the
earlier instruction to leave production disabled once release acceptance passes.
Development/manual reports remain Hotmail-only; scheduled production reports go
to the two existing `PROD_RECIPIENTS`. Push CI never sends email.

## Delivery contract

Discovery observations and delivery acknowledgements are separate. The existing
`search-state` branch remains the integration audit; the new weekly workflow uses
`search-observations-development` and `search-observations-production` for its own
observations. A missed email cannot mark a lead as successfully reported.

`delivery-development` and `delivery-production` each contain one durable JSON
journal with acknowledged listing history, at most one pending report and the
last 60 confirmation receipts. A pending report contains its original date,
sender, recipients, exact text and rendered HTML, proposed acknowledgements and
submission status. No credentials or raw seller HTML are stored. These journals
are on isolated branches, not main. Git retains earlier branch commits; the
30-day audit artifact retention does not erase Git history.

Only listings actually shown in the digest advance delivery history after exact
Message-ID/subject/recipient confirmation in Gmail Sent. Leads outside the five
potential-advert slots remain eligible next time. This is SMTP/Sent confirmation,
not proof that a recipient read the message or that every inbox accepted it.

Before SMTP DATA, the journal checkpoints `submitting` using an optimistic,
non-force Git ref update. GitHub checkpoint failure prevents submission. An
ambiguous SMTP result is never automatically resubmitted: the original email is
checked in Sent on recovery. Explicit partial recipient refusal remains blocked
even if a Sent copy exists. If Sent is unavailable or no confirmation appears,
the workflow fails visibly and retains the pending report; a human must reconcile
an indefinitely ambiguous submission before resetting it. Do not delete delivery
branches or submission state as a routine retry strategy.

Every run recovers an older pending report before starting fresh discovery. The
confirmed reporting-period key suppresses duplicate reports across workflow IDs.
A rerun of an already confirmed period skips discovery and delivery. Development
and production histories cannot suppress each other's reports.

## Schedule and failure operations

The target is Thursday 15:00 Europe/Amsterdam. Two UTC cron entries (13:00 and
14:00 Thursday) are evaluated with Python `zoneinfo`; only the entry corresponding
to local 15:00 runs a production search. Tests cover both sides of the March and
October DST changes. The guard uses the triggering cron rather than requiring
the runner to start within a narrow hour. GitHub schedules are best effort and
can start late. The first planned production date is 22 October 2026, 15:00 CEST.
The guard uses the original workflow creation date, so rerunning all jobs on a
later day or after a DST change preserves the original reporting period.
The Pi RSS timer stays at Thursday 13:30 local and is unchanged.

Evidence validation, identity-bound discovery and core coverage checks all precede
new report submission. Optional AutoWereld RSS access does not block core health.
Zero matches remains a valid report, not a service failure.

Failed runs send an owner-only Hotmail alert with the run URL. If email is
unavailable, a deduplicated GitHub issue records the failure; GitHub notification
delivery depends on the owner's account/subscription settings. A workflow that
GitHub never starts cannot notify from within that workflow.

## Release acceptance

[PR #71](https://github.com/Pietvdberg/campervan_weekly_search/pull/71) merged
with scheduling disabled after 305 regression tests and artifact-restore CI passed.
The one-off release acceptance
[run 39043583754](https://github.com/Pietvdberg/campervan_weekly_search/actions/runs/39043583754)
then completed successfully on 17 October:

- 124 real adverts screened; evidence/core coverage validation and observation
  persistence passed. Zero purchase-qualified vehicles is a valid outcome.
- The Hotmail-only report was accepted by SMTP, followed by a deliberate
  interruption after the acceptance checkpoint was durably stored.
- A fresh journal object restored the original report and verified it in Gmail
  Sent with SMTP disabled. No second submission occurred, and the same reporting
  period could not be prepared again.
- Exactly five displayed adverts were acknowledged; the pending outbox was empty
  after recovery. Independent Gmail lookup found exactly one Sent message with
  the report's Message-ID.
- The explicitly labelled owner-notification test was also SMTP/Sent-confirmed;
  independent Gmail lookup found exactly one copy of that notification.
- The separate push-triggered integration
  [run 39043583671](https://github.com/Pietvdberg/campervan_weekly_search/actions/runs/39043583671)
  passed discovery, RDW, validation and history persistence; its mail job was
  skipped as required.

The activation change removes the one-off PR event and adds the production crons.
It adds direct CLI routing tests (308 total tests), including manual production
spoof prevention and a rerun after DST using the original reporting date. PR CI
also exercises the production planner against its real, read-only Actions metadata,
without sending email. IMAP connections now have an explicit 30-second timeout.

The complete live mail/recovery acceptance used the development recipient only.
Both production recipients are covered by routing tests; the first real scheduled
dual-recipient delivery remains due on 22 October. Neither a future cron firing
nor recipient receipt/read status is claimed as already observed.
