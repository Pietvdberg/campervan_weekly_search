# Gmail SMTP setup (no GCP billing)
Enable two-step verification on the sending Gmail account and create an app password at
https://myaccount.google.com/apppasswords

Store exactly these two GitHub Actions repository secrets:
- `GMAIL_SENDER`: Gmail address used for SMTP login.
- `GMAIL_APP_PASSWORD`: 16-character Google app password (spaces optional).

The workflow sends to both configured recipients via smtp.gmail.com:465 with TLS.
It then checks Gmail Sent over IMAP for the exact Message-ID, subject and both recipient addresses.
If Gmail IMAP is unavailable or the Sent copy cannot be verified, the workflow fails even if SMTP accepted the message.
Enable IMAP access on the account if applicable. Never commit the app password.
Run the manual Gmail delivery smoke test after merging the pull request.

## Submission state and retries

The sender derives a stable Message-ID from the sender, recipients, subject and
both report bodies. It checks Gmail Sent before submitting. IMAP failures stop
submission rather than being interpreted as proof that no earlier message exists.

`mail_delivery_state.json` records only Message-ID and submission status. State
is written before SMTP DATA, after acceptance and after Sent confirmation. When
state exists, retries only verify Sent; they never resubmit an ambiguous or
accepted message. Different report content with restored state is rejected.

Mail workflows preserve the state as a 30-day Actions artifact and require that
artifact on reruns. A rerun without recoverable state fails closed; start a new
run only after inspecting whether a submission occurred. Cross-run/concurrent
exactly-once delivery is not guaranteed: there is no transactional SMTP/Sent
service. Sent presence confirms storage in the sender account, not delivery to
every recipient. No real email was sent during these regression tests.
