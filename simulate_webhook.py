#!/usr/bin/env python3
"""
simulate_webhook.py
===================
Simulates real Zendesk webhook POSTs to your local FastAPI server.

Requires: pip install httpx

Usage:
    python simulate_webhook.py --quick          # one hardcoded ticket (fastest smoke test)
    python simulate_webhook.py --id 101         # single ticket by id
    python simulate_webhook.py --all            # all 10 tickets, 2s apart
    python simulate_webhook.py --all --delay 5  # custom delay (seconds)

Prerequisites (must all be running):
    1. Redis:         docker run -d --name redis -p 6379:6379 redis
    2. FastAPI:       uvicorn src:app --reload
    3. Celery worker: celery -A src.tickets.celery_config.celery_app worker --loglevel=info -Q classification,processing
"""

import argparse
import json
import time
from pathlib import Path

import httpx

# ── Configuration ────────────────────────────────────────────────────────────

WEBHOOK_URL = "http://localhost:8000/api/v1/webhook/ticket-created"
FIXTURES_FILE = Path(__file__).parent / "tests" / "fixtures" / "webhook_payloads.json"

PRIORITY_EMOJI = {
    "urgent": "🔴",
    "high": "🟠",
    "normal": "🟡",
    "low": "🟢",
}

# ── Helpers ──────────────────────────────────────────────────────────────────


def load_fixtures() -> list[dict]:
    with open(FIXTURES_FILE) as f:
        return json.load(f)


def send(ticket: dict, url: str) -> None:
    priority = ticket.get("priority", "Normal").lower()
    emoji = PRIORITY_EMOJI.get(priority, "⬜")
    print(
        f"\n{emoji} Ticket #{ticket['id']}  [{ticket['priority']}]  {ticket['subject'][:55]}..."
    )
    print(f"   From: {ticket['requester_email']}")

    try:
        r = httpx.post(url, json=ticket, timeout=15.0)
        if r.status_code == 200:
            print(f"   ✅  {r.json()}")
        else:
            print(f"   ❌  HTTP {r.status_code} → {r.text[:300]}")

    except httpx.ConnectError:
        print(
            "   🚫 Connection refused.\n"
            "      Make sure FastAPI is running:  uvicorn src:app --reload"
        )
        raise SystemExit(1)

    except httpx.TimeoutException:
        print("   ⏰ Request timed out.")


def send_all(url: str, delay: float) -> None:
    tickets = load_fixtures()
    print(f"📦  Loaded {len(tickets)} tickets from {FIXTURES_FILE.name}")
    print(f"🎯  Target: {url}")
    print(f"⏱   Delay between tickets: {delay}s\n")

    for i, ticket in enumerate(tickets, 1):
        print(f"── [{i}/{len(tickets)}] " + "─" * 45)
        send(ticket, url)
        if i < len(tickets):
            time.sleep(delay)

    print("\n✅  All tickets sent!")


def send_by_id(ticket_id: str, url: str) -> None:
    tickets = load_fixtures()
    match = next((t for t in tickets if str(t["id"]) == ticket_id), None)
    if not match:
        ids = [t["id"] for t in tickets]
        print(f"❌  No ticket with id='{ticket_id}'.\n   Available IDs: {ids}")
        raise SystemExit(1)
    send(match, url)


def send_quick(url: str) -> None:
    """Hardcoded single ticket — no fixture file needed."""
    ticket = {
        "id": "9",
        "subject": "KYC Verification Pending for 48 Hours",
        "description": (
            "----------------------------------------------\n\n"
            "praise idowu, Mar 21, 2026, 21:38\n\n"
            "Hello,\n\n"
            "I submitted my documents for verification two days ago using Veriff, "
            'but the status still shows "pending review." I uploaded my international '
            "passport and a utility bill, both of which are clear and valid.\n\n"
            "I need my account approved urgently as I am expecting a payment from a client.\n\n"
            "Thank you.\n\nBest regards,\npraise idowu"
        ),
        "status": "New",
        "priority": "Normal",
        "requester_email": "praizthecoder@gmail.com",
        "created_at": "March 21, 2026",
    }
    print(f"🎯  Target: {url}")
    print("🚀  Sending quick smoke-test ticket (id=9)...")
    send(ticket, url)


# ── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate Zendesk webhook POSTs to a FastAPI server."
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--quick", action="store_true", help="Send a single hardcoded test ticket"
    )
    mode.add_argument("--all", action="store_true", help="Send all fixture tickets")
    mode.add_argument("--id", metavar="ID", help="Send one fixture ticket by its id")

    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds between tickets when using --all (default: 2.0)",
    )
    parser.add_argument(
        "--url",
        default=WEBHOOK_URL,
        help=f"Override the target URL (default: {WEBHOOK_URL})",
    )

    args = parser.parse_args()

    if args.quick:
        send_quick(args.url)
    elif args.all:
        send_all(args.url, args.delay)
    elif args.id:
        send_by_id(args.id, args.url)


if __name__ == "__main__":
    main()
