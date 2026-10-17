#!/usr/bin/env python3
"""Send report using Gmail SMTP and verify the exact message in Gmail Sent via IMAP."""
import email
import hashlib
import json
from pathlib import Path
from report_html import render_html
from email.message import EmailMessage
from email.utils import getaddresses
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
    with imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=30) as imap:
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

def save_delivery_state(path, message_id, status):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"message_id": message_id, "status": status}) + "\n", encoding="utf-8")
    temporary.replace(path)


def compose_message(text, html, date, sender, mode, recipients):
    subject = f"Weekly camper van search — {date}"
    if mode == "development":
        subject += " [SMOKE TEST / DEVELOPMENT]"
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(text)
    if html is not None:
        message.add_alternative(html, subtype="html")
    content_identity = json.dumps([sender.lower(), recipients, subject,
        [(part.get_content_type(), part.get_content()) for part in message.walk()
         if part.get_content_maintype() != "multipart"]], ensure_ascii=False)
    fingerprint = hashlib.sha256(content_identity.encode("utf-8")).hexdigest()
    message["Message-ID"] = "<camper-" + fingerprint + "@" + sender.split("@")[-1] + ">"
    return message


def deliver(message, sender, password, recipients, state=None, checkpoint=None):
    """Checkpoint remotely before SMTP DATA; ambiguous submissions only recheck Sent."""
    subject = str(message["Subject"])
    def save(status):
        if checkpoint is not None:
            checkpoint({"message_id": message["Message-ID"], "status": status})

    if state is not None and state.get("message_id") != message["Message-ID"]:
        raise RuntimeError("Restored delivery state belongs to different report content; refusing an ambiguous retry")
    if state is not None and state.get("status") == "recipients_refused":
        raise RuntimeError("SMTP refused one or more recipients; resolve partial delivery before acknowledging this report")
    # IMAP failure must not be treated as proof that no earlier delivery exists.
    if verify_sent(sender, password, message["Message-ID"], subject, recipients):
        save("sent_confirmed")
        print("Existing exact message verified in Gmail Sent; no resend", flush=True)
        return 0
    if state is None:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
            smtp.login(sender, password)
            # Persist before DATA: an interrupted/ambiguous submission is never blindly retried.
            save("submitting")
            refused = smtp.send_message(message)
            if refused:
                save("recipients_refused")
                raise RuntimeError(f"SMTP refused recipients: {list(refused)}; no automatic resend")
            save("smtp_accepted")
        print("SMTP accepted message; Message-ID:", message["Message-ID"], flush=True)
    else:
        print("Prior submission state restored; retrying Sent verification only", flush=True)
    for attempt in range(6):
        try:
            if verify_sent(sender, password, message["Message-ID"], subject, recipients):
                save("sent_confirmed")
                print("Verified exact subject and intended recipients in Gmail Sent; Message-ID:", message["Message-ID"])
                return 0
        except (imaplib.IMAP4.error, OSError, RuntimeError) as exc:
            print("IMAP verification attempt failed:", str(exc), flush=True)
        time.sleep(5)
    raise RuntimeError("Submission not confirmed in Gmail Sent; automatic resend is blocked for " + message["Message-ID"])


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "report.txt")
    date = os.environ.get("REPORT_DATE", datetime.now().strftime("%Y-%m-%d"))
    mode, recipients = configured_recipients()
    sender = os.environ["GMAIL_SENDER"]
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    audit = path.with_name("screening_results.json")
    html = render_html(json.loads(audit.read_text(encoding="utf-8"))) if audit.is_file() else None
    message = compose_message(path.read_text(encoding="utf-8"), html, date, sender, mode, recipients)
    state_path = Path(os.environ.get("MAIL_DELIVERY_STATE", str(path.with_name("mail_delivery_state.json"))))
    state = json.loads(state_path.read_text()) if state_path.exists() else None
    print("Mail mode:", mode, "Recipients:", ", ".join(recipients), flush=True)
    return deliver(message, sender, password, recipients, state,
                   lambda value: save_delivery_state(state_path, value["message_id"], value["status"]))

if __name__ == "__main__":
    sys.exit(main())
