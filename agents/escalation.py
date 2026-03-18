# src/escalation.py

from typing import Dict

import httpx
from decouple import config

ZENDESK_SUBDOMAIN = config("ZENDESK_SUBDOMAIN")
BASE_URL = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2"


async def escalate_to_specialist(
    ticket_id: str,
    team: str,
    classification: Dict,
    attempted_response: str,
    confidence: float,
):
    """Escalate ticket to specialist team via Zendesk + Slack"""

    team_map = {
        "billing-review": "34670629763741",
        "technical-review": "34670765117085",
        "product-review": "34670810496029",
        "security-review": "34670772576541",
        "support-review": "34512695547421",
    }

    url = f"{BASE_URL}/tickets/{ticket_id}.json"

    # TODO: LOGIC

    # Notify on zendesk
    # await notify_zendesk(ticket_id, team, classification)
