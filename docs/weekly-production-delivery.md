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
The Pi RSS timer stays at Thursday 13:30 local and is unchanged.

Evidence validation, identity-bound discovery and core coverage checks all precede
new report submission. Optional AutoWereld RSS access does not block core health.
Zero matches remains a valid report, not a service failure.

Failed runs send an owner-only Hotmail alert with the run URL. If email is
unavailable, a deduplicated GitHub issue records the failure; GitHub notification
delivery depends on the owner's account/subscription settings. A workflow that
GitHub never starts cannot notify from within that workflow.

## Release acceptance

First merge the delivery implementation with scheduling disabled. A one-off,
merged-release-PR event runs the full discovery/validation workflow and sends a
development report only to Hotmail. The acceptance harness deliberately interrupts
after SMTP accepts the message and the remote journal records that acceptance.
It reloads the journal and verifies the original Sent message with SMTP resending
disabled, then verifies the same reporting period cannot be prepared again.
It also sends an explicitly labelled owner-notification test.

Only after this live acceptance succeeds will the follow-up activation PR remove
the one-off event and add the production schedule. Results and run links will be
recorded here; no successful live acceptance is claimed by this document yet.
