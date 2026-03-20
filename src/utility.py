import numpy as np
from sentence_transformers import SentenceTransformer

collection_urls = [
    # 1. Onboarding and Sign up (12 articles)
    "https://help.raenest.com/en/collections/3533693-onboarding-and-sign-up",
    # 2. US Bank Account for US Residents (2 articles)
    "https://help.raenest.com/en/collections/15733141-us-bank-account-for-us-residents",
    # 3. Bank Accounts (9 articles)
    "https://help.raenest.com/en/collections/3486985-bank-accounts",
    # 4. Employment Details (23 articles)
    "https://help.raenest.com/en/collections/15831197-employment-details",
    # 5. Invoicing and Employer Billing (1 article)
    "https://help.raenest.com/en/collections/3533698-invoicing-and-employer-billing",
    # 6. Raenest Fast Track (2 articles)
    "https://help.raenest.com/en/collections/16579670-raenest-fast-track",
    # 7. Transfer and Withdraw Fund (2 articles)
    "https://help.raenest.com/en/collections/3533863-transfer-and-withdraw-fund",
    # 8. Virtual cards (9 articles)
    "https://help.raenest.com/en/collections/3553353-virtual-cards",
    # 9. Wallets & Currencies (4 articles)
    "https://help.raenest.com/en/collections/5556772-wallets-currencies",
    # 10. Funding Your Wallet (2 articles)
    "https://help.raenest.com/en/collections/5556685-funding-your-wallet",
    # 11. Securing your Account (3 articles)
    "https://help.raenest.com/en/collections/3533702-securing-your-account",
    # 12. Fees and Charges (3 articles)
    "https://help.raenest.com/en/collections/3533699-fees-and-charges",
    # 13. Bill Payments (1 article)
    "https://help.raenest.com/en/collections/13716686-bill-payments",
    # 14. Raenest Perks (2 articles)
    "https://help.raenest.com/en/collections/14162840-raenest-perks",
    # 15. Add Money (3 articles)
    "https://help.raenest.com/en/collections/15731858-add-money",
    # 16. Stablecoins on Raenest (1 article)
    "https://help.raenest.com/en/collections/15732358-stablecoins-on-raenest",
    # 17. Payment Links (1 article)
    "https://help.raenest.com/en/collections/15877261-payment-links",
    # 18. U.S. Stocks (3 articles)
    "https://help.raenest.com/en/collections/15732786-u-s-stocks",
]


class ConfidenceCalculator:
    """Calculate semantic similarity for confidence scoring"""

    def __init__(self):
        # Load small, fast embedding model for similarity
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def calculate_similarity(self, query: str, context: str) -> float:
        """
        Calculate semantic similarity between query and context.

        Returns: float between 0-1 (1 = identical meaning)
        """
        query_embedding = self.model.encode(query)
        context_embedding = self.model.encode(context)

        similarity = np.dot(query_embedding, context_embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(context_embedding)
        )

        # Normalize to 0-1 range
        return float((similarity + 1) / 2)


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
