from decouple import config

ZENDESK_SUBDOMAIN = config("ZENDESK_SUBDOMAIN")
BASE_URL = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2"


async def send_response_to_customer(ticket_id: str, response: str):
    """Send auto-resolved response to customer"""
    pass


async def assign_for_review(
    ticket_id: str, draft_response: str, confidence: float, queue: str
):
    """Assign ticket to human review queue with draft response"""

    url = f"{BASE_URL}/tickets/{ticket_id}.json"

    # Map queue to Zendesk group ID
    queue_map = {
        "billing-review": "34670629763741",
        "technical-review": "34670765117085",
        "product-review": "34670810496029",
        "security-review": "34670772576541",
        "support-review": "34512695547421",
    }
