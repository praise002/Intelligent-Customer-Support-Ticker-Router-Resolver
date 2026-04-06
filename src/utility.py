import httpx
from decouple import config


def get_priority_score(urgency: str) -> int:
    """
    Convert urgency to Celery priority (10=highest, 1=lowest)

    Priority Queue Logic:
    🔴 HIGH urgency    → Priority 10 (processed first)
    🟡 MEDIUM urgency  → Priority 5
    🟢 LOW urgency     → Priority 1 (processed last)
    """
    priority_map = {"high": 10, "medium": 5, "low": 1}
    return priority_map.get(urgency.lower(), 5)


def send_slack_alert(message: str):
    """
    Sends a message to a Slack channel using a webhook URL.
    """
    slack_webhook_url = config("SLACK_WEBHOOK_URL", default=None)
    if not slack_webhook_url:
        print("SLACK_WEBHOOK_URL not set. Skipping Slack notification.")
        return

    try:
        with httpx.Client() as client:
            response = client.post(
                slack_webhook_url,
                json={"text": message},
            )
            response.raise_for_status()
        print("Slack alert sent successfully.")
    except httpx.RequestError as e:
        print(f"Error sending Slack alert: {e}")
