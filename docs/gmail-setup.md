# Gmail OAuth setup
This workflow sends from your Gmail account to both configured recipients.
Create an OAuth client in Google Cloud, enable Gmail API, and authorize the account with the
`https://www.googleapis.com/auth/gmail.send` and
`https://www.googleapis.com/auth/gmail.readonly` scopes.
Store these four values as GitHub Actions repository secrets:
`GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, `GMAIL_SENDER`.
Never commit the refresh token or client secret. Use an OAuth consent configuration
appropriate for your Google account; testing-mode refresh tokens can expire after seven days.
Run **Gmail delivery smoke test** manually after configuring secrets.
A successful Gmail Sent verification confirms submission and Sent placement, not inbox delivery.
