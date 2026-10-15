#!/usr/bin/env python3
"""Send an existing weekly report via Gmail OAuth2 and verify the Sent copy."""
import base64
from datetime import datetime
from email.message import EmailMessage
import json
import os
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

RECIPIENTS = ["piet.v.d.berg@hotmail.com", "hagenaars.danielle@gmail.com"]

def request_json(url, payload=None, token=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    else:
        data = None
    with urlopen(Request(url, data=data, headers=headers), timeout=30) as response:
        return json.load(response)

def access_token():
    body = urlencode({
        "client_id": os.environ["GMAIL_CLIENT_ID"],
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    with urlopen(Request("https://oauth2.googleapis.com/token", data=body), timeout=30) as response:
        return json.load(response)["access_token"]

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "report.txt"
    date = os.environ.get("REPORT_DATE", datetime.now().strftime("%Y-%m-%d"))
    subject = f"Weekly camper van search — {date}"
    sender = os.environ["GMAIL_SENDER"]
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(RECIPIENTS)
    message["Subject"] = subject
    with open(path, encoding="utf-8") as f:
        message.set_content(f.read())
    token = access_token()
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
    sent = request_json("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", {"raw": raw}, token)
    message_id = sent["id"]
    print("Gmail API accepted message ID:", message_id)
    for attempt in range(5):
        record = request_json(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=metadata",
            token=token,
        )
        headers = {h["name"].lower(): h["value"] for h in record.get("payload", {}).get("headers", [])}
        actual_recipients = headers.get("to", "").lower()
        if ("SENT" in record.get("labelIds", [])
                and headers.get("subject") == subject
                and all(addr in actual_recipients for addr in RECIPIENTS)):
            print("Verified Sent copy, subject and both recipients:", message_id)
            return 0
        time.sleep(3)
    raise RuntimeError("Message was accepted but Sent-copy verification failed: " + message_id)

if __name__ == "__main__":
    sys.exit(main())
