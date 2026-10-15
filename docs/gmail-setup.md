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
