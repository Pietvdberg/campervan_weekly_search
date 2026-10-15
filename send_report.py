#!/usr/bin/env python3
"""Send report using Gmail SMTP and verify the exact message in Gmail Sent via IMAP."""
import email
from email.message import EmailMessage
from email.utils import make_msgid, getaddresses
from datetime import datetime
import imaplib
import os
import smtplib
import ssl
import sys
import time

RECIPIENTS = ["piet.v.d.berg@hotmail.com", "hagenaars.danielle@gmail.com"]

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "report.txt"
    date = os.environ.get("REPORT_DATE", datetime.now().strftime("%Y-%m-%d"))
    subject = f"Weekly camper van search — {date}"
    sender = os.environ["GMAIL_SENDER"]
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(RECIPIENTS)
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    with open(path, encoding="utf-8") as f:
        message.set_content(f.read())
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(sender, password)
        refused = smtp.send_message(message)
        if refused:
            raise RuntimeError(f"SMTP refused recipients: {list(refused)}")
    print("SMTP accepted message; Message-ID:", message["Message-ID"], flush=True)

    # Gmail normally saves SMTP-submitted mail in Sent automatically.
    # Confirm that exact Message-ID and both recipient headers are present.
    for attempt in range(6):
        try:
            with imaplib.IMAP4_SSL("imap.gmail.com", 993) as imap:
                imap.login(sender, password)
                status, folders = imap.list()
                if status != "OK":
                    raise RuntimeError("Could not list Gmail folders")
                import re
                sent_folder = None
                for folder in folders:
                    line = folder.decode("utf-8", errors="replace")
                    if re.search(r"\\Sent\\b", line, re.IGNORECASE):
                        match = re.search(r'(?:"([^\"]+)"|([^ ]+))
                status, data = imap.uid("SEARCH", None, "HEADER", "Message-ID", message["Message-ID"])
                if status != "OK":
                    raise RuntimeError("IMAP search failed")
                for uid in data[0].split():
                    status, fetched = imap.uid("FETCH", uid, "(RFC822)")
                    if status != "OK":
                        continue
                    raw = next((part[1] for part in fetched if isinstance(part, tuple)), None)
                    if not raw:
                        continue
                    stored = email.message_from_bytes(raw)
                    actual = {addr.lower() for _, addr in getaddresses(stored.get_all("To", []))}
                    if (stored.get("Message-ID") == message["Message-ID"]
                            and str(email.header.make_header(email.header.decode_header(stored.get("Subject", "")))) == subject
                            and set(RECIPIENTS).issubset(actual)):
                        print("Verified exact subject and both recipients in Gmail Sent; Message-ID:", message["Message-ID"])
                        return 0
        except (imaplib.IMAP4.error, OSError) as exc:
            print("IMAP verification attempt failed:", str(exc), flush=True)
        time.sleep(5)
    raise RuntimeError("SMTP accepted mail but Gmail Sent verification failed for " + message["Message-ID"])

if __name__ == "__main__":
    sys.exit(main())
, line)
                        if match:
                            sent_folder = match.group(1) or match.group(2)
                            break
                if sent_folder is None:
                    raise RuntimeError("No folder marked with IMAP Sent special-use flag")
                mailbox = '"' + sent_folder.replace('\\', '\\\\').replace('"', '\\"') + '"'
                status, _ = imap.select(mailbox, readonly=True)
                if status != "OK":
                    raise RuntimeError("Cannot select Gmail Sent folder discovered via IMAP")
                status, data = imap.uid("SEARCH", None, "HEADER", "Message-ID", message["Message-ID"])
                if status != "OK":
                    raise RuntimeError("IMAP search failed")
                for uid in data[0].split():
                    status, fetched = imap.uid("FETCH", uid, "(RFC822)")
                    if status != "OK":
                        continue
                    raw = next((part[1] for part in fetched if isinstance(part, tuple)), None)
                    if not raw:
                        continue
                    stored = email.message_from_bytes(raw)
                    actual = {addr.lower() for _, addr in getaddresses(stored.get_all("To", []))}
                    if (stored.get("Message-ID") == message["Message-ID"]
                            and str(email.header.make_header(email.header.decode_header(stored.get("Subject", "")))) == subject
                            and set(RECIPIENTS).issubset(actual)):
                        print("Verified exact subject and both recipients in Gmail Sent; Message-ID:", message["Message-ID"])
                        return 0
        except (imaplib.IMAP4.error, OSError) as exc:
            print("IMAP verification attempt failed:", str(exc), flush=True)
        time.sleep(5)
    raise RuntimeError("SMTP accepted mail but Gmail Sent verification failed for " + message["Message-ID"])

if __name__ == "__main__":
    sys.exit(main())
