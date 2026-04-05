from typing import Dict, List

import httpx
from decouple import config

ZENDESK_SUBDOMAIN = config("ZENDESK_SUBDOMAIN")
ZENDESK_EMAIL = config("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = config("ZENDESK_API_TOKEN")

BASE_URL = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2"
AUTH = (f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)

CUSTOM_FIELD_URGENCY_ID = config("ZENDESK_CUSTOM_FIELD_URGENCY")
CUSTOM_FIELD_ISSUE_TYPE_ID = config("ZENDESK_CUSTOM_FIELD_ISSUE_TYPE")


# It always go to default group so we can update it

# Map issue type to Zendesk group ID
group_map = {
    "account_verification": config("VERIFICATION_TEAM_GROUP_ID"),  # KYC specialists
    "cards": config("CARDS_TEAM_GROUP_ID"),  # Card support team
    "transfers": config("TRANSFERS_TEAM_GROUP_ID"),  # Payments team
    "integrations": config("INTEGRATIONS_TEAM_GROUP_ID"),  # Integration specialists
    "fees": config("GENERAL_SUPPORT_GROUP_ID"),  # General support (FAQ)
    "account_access": config("SECURITY_TEAM_GROUP_ID"),  # Security/access team
    "technical": config("TECHNICAL_TEAM_GROUP_ID"),
    "general": config("GENERAL_SUPPORT_GROUP_ID"),  # Catch-all
}

# Set priority based on urgency
priority_map = {"high": "urgent", "medium": "normal", "low": "low"}
# url = "https://example.zendesk.com/api/v2/tickets?include=users%2Cgroups%2Corganizations"

async def create_single_ticket(ticket_data: Dict):
    """Create a single ticket"""

    url = f"{BASE_URL}/tickets.json?include=users"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json={"ticket": ticket_data},
            auth=AUTH,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()["ticket"]

async def update_single_ticket(ticket_id: str, update_data: Dict):
    """Update a single ticket"""

    url = f"{BASE_URL}/tickets/{ticket_id}.json"

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.put(
            url,
            json={"ticket": update_data},
            auth=AUTH,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def batch_update_tickets(updates: List[Dict]):
    """
    Update multiple tickets in one API call.

    Args:
        updates: List of ticket updates
        Example: [
            {"id": "123", "status": "pending", "comment": {...}},
            {"id": "456", "status": "solved", "comment": {...}}
        ]
    """

    url = f"{BASE_URL}/tickets/update_many.json"

    async with httpx.AsyncClient() as client:
        response = await client.put(
            url,
            json={"tickets": updates},
            auth=AUTH,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def bulk_update_tickets(ticket_ids: List[str], updates: Dict):
    """
    Make the same change to multiple tickets using their IDs.

    Args:
        ticket_ids: List of ticket IDs to update.
        update_data: The data to update for the tickets.
            Example: {"status": "solved"}
    """
    ids_param = ",".join(ticket_ids)
    url = f"{BASE_URL}/tickets/update_many.json?ids={ids_param}"

    async with httpx.AsyncClient() as client:
        response = await client.put(
            url,
            json={"tickets": updates},
            auth=AUTH,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def send_response_to_customer(
    ticket_id: str, response: str, urgency: str, issue_type: str
):
    """Send auto-resolved response to customer"""

    update_data = {
        "status": "pending",
        "group_id": group_map.get(issue_type),
        "custom_fields": [
            {"id": CUSTOM_FIELD_URGENCY_ID, "value": urgency},
            {"id": CUSTOM_FIELD_ISSUE_TYPE_ID, "value": issue_type},
        ],
        "comment": {"body": response, "public": True},  # Customer receives email
    }

    return await update_single_ticket(ticket_id, update_data)


async def assign_for_review(
    ticket_id: str,
    draft_response: str,
    confidence: float,
    issue_type: str,
    urgency: str,
):
    """Assign ticket to specialist team for human review."""

    update_data = {
        "status": "open",
        "group_id": group_map.get(issue_type),
        "custom_fields": [
            {"id": CUSTOM_FIELD_URGENCY_ID, "value": urgency},
            {"id": CUSTOM_FIELD_ISSUE_TYPE_ID, "value": issue_type},
        ],
        "comment": {
            "body": f"""[AI DRAFT - Review before sending]

            Confidence: {confidence:.0%}  
            Urgency: {urgency}
            Issue Type: {issue_type}

            ---
            Suggested Response:
            {draft_response}
            ---

            Please review and edit before sending to customer.""",
            "public": False,  # Private note - only agents see
        },  # confidence: 0.952 will produce 95%
    }

    return await update_single_ticket(ticket_id, update_data)


async def escalate_ticket(
    ticket_id: str,
    issue_type: str,
    attempted_response: str,
    confidence: float,
    urgency: str,
):
    """Escalate ticket to specialist team."""

    update_data = {
        "status": "open",
        "custom_fields": [
            {"id": CUSTOM_FIELD_URGENCY_ID, "value": urgency},
            {"id": CUSTOM_FIELD_ISSUE_TYPE_ID, "value": issue_type},
        ],
        "group_id": group_map.get(issue_type),
        "priority": priority_map.get(urgency, "normal"),
        "comment": {
            "body": f"""[AI ESCALATION - Low Confidence]

            Confidence: {confidence:.0%}
            Issue Type: {issue_type}
            Urgency: {urgency}

            AI attempted to generate a response but confidence is too low.

            ---
            AI Attempted Response:
            {attempted_response}
            ---

            This ticket requires specialist review.""",
            "public": False,  # Private note
        },
    }

    return await update_single_ticket(ticket_id, update_data)


# BATCH EXAMPLE


async def batch_auto_resolve(tickets: List[Dict]):
    """
    Auto-resolve multiple tickets in one API call.

    Args:
        tickets: [
            {"id": "123", "response": "AI response 1"},
            {"id": "456", "response": "AI response 2"}
        ]
    """

    updates = [
        {
            "id": ticket["id"],
            "status": "pending",
            "group_id": group_map.get(ticket["issue_type"]),
            "custom_fields": [
                {"id": CUSTOM_FIELD_URGENCY_ID, "value": ticket["urgency"]},
                {"id": CUSTOM_FIELD_ISSUE_TYPE_ID, "value": ticket["issue_type"]},
            ],
            "comment": {"body": ticket["response"], "public": True},
        }
        for ticket in tickets
    ]

    return await batch_update_tickets(updates)


async def batch_assign_for_review(tickets: List[Dict]):
    """
    Assign ticket to specialist team for human review.
    Args:
        tickets: [
            {
                "id": "123",
                "issue_type": "billing",
                "urgency": "high",
                "confidence": 0.75,
                "draft_response": "AI response..."
            }
        ]
    """

    updates = [
        {
            "id": ticket["id"],
            "status": "open",
            "group_id": group_map.get(ticket["issue_type"]),
            "custom_fields": [
                {"id": CUSTOM_FIELD_URGENCY_ID, "value": ticket["urgency"]},
                {"id": CUSTOM_FIELD_ISSUE_TYPE_ID, "value": ticket["issue_type"]},
            ],
            "comment": {
                "body": f"""[AI DRAFT - Review before sending]

            Confidence: {ticket["confidence"]:.0%}  
            Urgency: {ticket["urgency"]}
            Issue Type: {ticket["issue_type"]}

            ---
            Suggested Response:
            {ticket["draft_response"]}
            ---

            Please review and edit before sending to customer.""",
                "public": False,  # Private note - only agents see
            },
        }
        for ticket in tickets
    ]

    return await batch_update_tickets(updates)


async def batch_escalate_ticket(tickets: List[Dict]):
    """
    Escalate ticket to specialist team.
    Args:
        tickets: [
            {
                "id": "123",
                "issue_type": "billing",
                "urgency": "high",
                "confidence": 0.45,
                "attempted_response": "AI tried..."
            }
        ]
    """

    updates = [
        {
            "id": ticket["id"],
            "status": "open",
            "group_id": group_map.get(ticket["issue_type"]),
            "priority": priority_map.get(ticket["urgency"], "normal"),
            "custom_fields": [
                {"id": CUSTOM_FIELD_URGENCY_ID, "value": ticket["urgency"]},
                {"id": CUSTOM_FIELD_ISSUE_TYPE_ID, "value": ticket["issue_type"]},
            ],
            "comment": {
                "body": f"""[AI ESCALATION - Low Confidence]

            Confidence: {ticket["confidence"]:.0%}
            Issue Type: {ticket["issue_type"]}
            Urgency: {ticket["urgency"]}

            AI attempted to generate a response but confidence is too low.

            ---
            AI Attempted Response:
            {ticket["attempted_response"]}
            ---

            This ticket requires specialist review.""",
                "public": False,  # Private note
            },
        }
        for ticket in tickets
    ]

    return await batch_update_tickets(updates)
