#!/usr/bin/env python3
"""Send report using Gmail SMTP and verify the exact message in Gmail Sent via IMAP."""
import email
from email.message import EmailMessage
from email.utils import make_msgid, getaddresses
from datetime import datetime
import imaplib
import os
import re
import smtplib
import ssl
import sys
import time

DEV_RECIPIENTS = ("piet.v.d.berg@hotmail.com",)
PROD_RECIPIENTS = ("piet.v.d.berg@hotmail.com", "hagenaars.danielle@gmail.com")

def configured_recipients():
    mode = os.environ.get("MAIL_MODE", "development").strip().lower()
    if mode == "development":
        return mode, DEV_RECIPIENTS
    if mode == "production":
        return mode, PROD_RECIPIENTS
    raise ValueError("MAIL_MODE must be 'development' or 'production'")

def sent_folder_from_list(folders):
    for folder in folders:
        line = folder.decode("utf-8", errors="replace")
        if not re.search(r"\\Sent\b", line, re.IGNORECASE):
            continue
        quoted = re.search(r'"([^"]+)"$', line)
        return quoted.group(1) if quoted else line.rsplit(" ", 1)[-1]
    raise RuntimeError("No IMAP folder with Sent special-use flag was found")

def verify_sent(sender, password, message_id, subject, recipients):
    with imaplib.IMAP4_SSL("imap.gmail.com", 993) as imap:
        imap.login(sender, password)
        status, folders = imap.list()
        if status != "OK":
            raise RuntimeError("Could not list Gmail IMAP folders")
        name = sent_folder_from_list(folders)
        mailbox = '"' + name.replace('\\', '\\\\').replace('"', '\\"') + '"'
        status, _ = imap.select(mailbox, readonly=True)
        if status != "OK":
            raise RuntimeError("Could not select discovered Gmail Sent folder")
        status, data = imap.uid("SEARCH", None, "HEADER", "Message-ID", message_id)
        if status != "OK":
            raise RuntimeError("Could not search Gmail Sent")
        for uid in data[0].split():
            status, fetched = imap.uid("FETCH", uid, "(RFC822)")
            if status != "OK":
                continue
            raw = next((part[1] for part in fetched if isinstance(part, tuple)), None)
            if not raw:
                continue
            stored = email.message_from_bytes(raw)
            actual = {addr.lower() for _, addr in getaddresses(stored.get_all("To", []))}
            decoded_subject = str(email.header.make_header(email.header.decode_header(stored.get("Subject", ""))))
            if (stored.get("Message-ID") == message_id and decoded_subject == subject
                    and actual == set(recipients)):
                return True
    return False

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "report.txt"
    date = os.environ.get("REPORT_DATE", datetime.now().strftime("%Y-%m-%d"))
    mode, recipients = configured_recipients()
    subject = f"Weekly camper van search — {date}"
    if mode == "development":
        subject += " [SMOKE TEST / DEVELOPMENT]"
    sender = os.environ["GMAIL_SENDER"]
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    with open(path, encoding="utf-8") as f:
        message.set_content(f.read())
    print("Mail mode:", mode, "Recipients:", ", ".join(recipients), flush=True)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(sender, password)
        refused = smtp.send_message(message)
        if refused:
            raise RuntimeError(f"SMTP refused recipients: {list(refused)}")
    print("SMTP accepted message; Message-ID:", message["Message-ID"], flush=True)
    for attempt in range(6):
        try:
            if verify_sent(sender, password, message["Message-ID"], subject, recipients):
                print("Verified exact subject and intended recipients in Gmail Sent; Message-ID:", message["Message-ID"])
                return 0
        except (imaplib.IMAP4.error, OSError, RuntimeError) as exc:
            print("IMAP verification attempt failed:", str(exc), flush=True)
        time.sleep(5)
    raise RuntimeError("SMTP accepted mail but Gmail Sent verification failed for " + message["Message-ID"])

if __name__ == "__main__":
    sys.exit(main())
