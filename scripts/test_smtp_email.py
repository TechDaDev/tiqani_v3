#!/usr/bin/env python3
"""Send a small SMTP test email and report whether delivery was accepted."""

from __future__ import annotations

import argparse
import getpass
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test whether an SMTP account can authenticate and send email."
    )
    parser.add_argument("--host", default=os.environ.get("SMTP_HOST") or os.environ.get("EMAIL_HOST") or "premium86.web-hosting.com")
    parser.add_argument("--port", type=int, default=int(os.environ.get("SMTP_PORT") or os.environ.get("EMAIL_PORT") or "465"))
    parser.add_argument("--user", default=os.environ.get("SMTP_USER") or os.environ.get("EMAIL_HOST_USER") or "otp@iqtiqani.com")
    parser.add_argument("--password", default=os.environ.get("SMTP_PASSWORD") or os.environ.get("EMAIL_HOST_PASSWORD"))
    parser.add_argument("--to", default=os.environ.get("SMTP_TEST_TO"))
    parser.add_argument("--from-email", default=os.environ.get("SMTP_FROM") or os.environ.get("DEFAULT_FROM_EMAIL"))
    parser.add_argument("--subject", default="Tiqani SMTP test")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("SMTP_TIMEOUT", "20")))
    parser.add_argument(
        "--security",
        choices=("ssl", "starttls", "none"),
        default=os.environ.get("SMTP_SECURITY") or ("ssl" if env_bool("EMAIL_USE_SSL", True) else "starttls"),
        help="Use implicit SSL on 465, STARTTLS on 587, or no transport encryption.",
    )
    parser.add_argument(
        "--login-only",
        action="store_true",
        help="Only authenticate; do not send a test message.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print SMTP protocol debug output. Do not use this in shared logs.",
    )
    return parser.parse_args()


def build_message(sender: str, recipient: str, subject: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    message.set_content(
        "This is a Tiqani SMTP test message.\n\n"
        "If you received this, the SMTP account authenticated and the server accepted delivery.\n"
    )
    return message


def connect(args: argparse.Namespace) -> smtplib.SMTP:
    if args.security == "ssl":
        context = ssl.create_default_context()
        return smtplib.SMTP_SSL(args.host, args.port, timeout=args.timeout, context=context)

    client = smtplib.SMTP(args.host, args.port, timeout=args.timeout)
    if args.security == "starttls":
        context = ssl.create_default_context()
        client.ehlo()
        client.starttls(context=context)
        client.ehlo()
    return client


def main() -> int:
    args = parse_args()

    password = args.password or getpass.getpass(f"SMTP password for {args.user}: ")
    sender = args.from_email or args.user
    recipient = args.to or sender

    print(f"Connecting to {args.host}:{args.port} with {args.security} as {args.user}", flush=True)
    try:
        with connect(args) as client:
            if args.debug:
                client.set_debuglevel(1)
            client.login(args.user, password)
            print("Authentication: OK", flush=True)

            if args.login_only:
                print("Send: skipped (--login-only)", flush=True)
                return 0

            message = build_message(sender, recipient, args.subject)
            refused = client.send_message(message)
            if refused:
                print(f"Send: refused recipients: {', '.join(refused.keys())}", file=sys.stderr)
                return 2

            print(f"Send: OK, server accepted message for {recipient}", flush=True)
            return 0
    except smtplib.SMTPAuthenticationError as exc:
        print(f"Authentication failed: {exc.smtp_code} {exc.smtp_error!r}", file=sys.stderr)
        return 1
    except smtplib.SMTPRecipientsRefused as exc:
        refused = ", ".join(
            f"{address} ({code} {message!r})"
            for address, (code, message) in exc.recipients.items()
        )
        print(f"Send failed: recipient refused: {refused}", file=sys.stderr)
        return 2
    except smtplib.SMTPException as exc:
        print(f"SMTP failed: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Connection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
