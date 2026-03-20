import requests
from decouple import config
from transformers import pipeline

API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"
ISSUE_LABELS = [
    "account_verification",  # KYC, document issues, account approval
    "cards",  # All card issues (declined, funding, limits, creation)
    "transfers",  # Withdrawals, transfers, delays, failed transactions
    "integrations",  # Upwork, Fiverr, platform linking
    "fees",  # Pricing, charges, costs
    "account_access",  # Login, password, 2FA, security
    "general",  # Everything else
]
URGENCY_LABELS = ["high", "medium", "low"]


class TicketClassifier:
    """
    A client for the Hugging Face Inference API to perform zero-shot classification.
    """

    def __init__(self, api_token: str = None, use_pipeline: bool = False):
        """
        Initialize the classifier.

        Args:
            api_token: Your Hugging Face API token (required if use_pipeline=False)
            use_pipeline: If True, uses local pipeline. If False, uses HF API.
        """
        self.use_pipeline = use_pipeline

        if use_pipeline:
            print("Loading local pipeline...")
            self.classifier = pipeline(
                "zero-shot-classification", model="facebook/bart-large-mnli"
            )
            print("✅ Pipeline loaded successfully")
        else:
            if not api_token:
                raise ValueError(
                    "Hugging Face API token is required when use_pipeline=False"
                )
            self.headers = {"Authorization": f"Bearer {api_token}"}

    def _query_hf_api(self, payload: dict) -> dict:
        """Sends a request to the Hugging Face API and returns the JSON response."""
        response = requests.post(API_URL, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def _query_local_pipeline(self, text: str, candidate_labels: list) -> dict:
        """
        Uses the local pipeline to classify text.
        """
        result = self.classifier(text, candidate_labels)
        print(result)

        # Pipeline returns: {'labels': [...], 'scores': [...]}
        # We convert to: [{'label': 'billing', 'score': 0.94}, ...]
        formatted = [
            {"label": label, "score": score}
            for label, score in zip(result["labels"], result["scores"])
        ]
        return formatted

    def classify(self, ticket_text: str) -> dict:
        """
        Classifies a support ticket to determine its issue type and urgency.

        Args:
            ticket_text: The combined subject and description of the ticket.

        Returns:
            A dictionary containing the predicted issue type, urgency, and their
            respective confidence scores.
            Example:
            {
                "issue_type": "billing",
                "urgency": "high",
                "issue_score": 0.9412,
                "urgency_score": 0.8231
            }
        """
        if self.use_pipeline:
            print("Classifying with local pipeline...")
            issue_output = self._query_local_pipeline(ticket_text, ISSUE_LABELS)
            urgency_output = self._query_local_pipeline(ticket_text, URGENCY_LABELS)
        else:
            print("Classifying with HF API...")
            issue_output = self._query_hf_api(
                {
                    "inputs": ticket_text,
                    "parameters": {"candidate_labels": ISSUE_LABELS},
                }
            )
            urgency_output = self._query_hf_api(
                {
                    "inputs": ticket_text,
                    "parameters": {"candidate_labels": URGENCY_LABELS},
                }
            )

        return {
            "issue_type": issue_output[0]["label"],
            "urgency": urgency_output[0]["label"],
            "issue_score": round(issue_output[0]["score"], 4),
            "urgency_score": round(urgency_output[0]["score"], 4),
        }


if __name__ == "__main__":
    hf_token = config("HF_TOKEN")
    classifier = TicketClassifier(api_token=hf_token)

    test_ticket = "My credit card was charged twice for the same subscription. Please refund immediately."

    result = classifier.classify(test_ticket)
    print(result)
