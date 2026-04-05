from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from src.tickets.schemas import LLMProvider, TicketClassification


def _get_llm():
    """Lazy load LLM — only when first node runs, not at import time"""
    from src.agents.llm_config import get_llm_client

    return get_llm_client(LLMProvider.GROQ, output_model=TicketClassification)


# Cache at module level after first call
llm = None


def get_llm():
    global llm
    if llm is None:
        llm = _get_llm()
    return llm


class TicketClassifier:
    def __init__(self, api_token):
        self.api_token = api_token

    def classify_local(self, model):
        pass

    def classify(subject: str, description: str) -> Dict:
        llm = get_llm()
        system_prompt = f"""
            You are a support ticket classifier for Raenest, a Nigerian fintech. Classify into issue_type and urgency.
            Ignore customer emotions (frustration, disappointment, urgency words like "urgently" unless tied to real financial harm). Focus only on factual intent and what action is needed.
            
            Issue types:
            - account_verification: KYC, document uploads, account approval delays, approval status (not account lock).
            - cards: virtual card declines, creation failures, funding, limits, failed card payments where money was deducted but the merchant was not credited.
            - transfers: withdrawals stuck in processing, failed transfers, wrong recipient, missing funds after credit alert.
            - integrations: linking Upwork, Fiverr, or other platforms for payouts.
            - fees: pricing, conversion rates, withdrawal charges, hidden costs.
            - technical — app crashes, outdated version errors, device or platform issues unrelated to account or payment
            - account_access: login failure, 2FA, locked accounts, missing account details.
            - general: anything else (e.g., feature questions not covered above).

            Urgency:
            - high: customer cannot transact, money is missing/stuck, account locked, cannot transact at all, immediate deadline.
            - medium: process waiting (KYC review, card delivery) but no immediate financial loss.
            - low: general questions about fees, how-to guides, feature requests, non-critical info.
            
            PRIORITY HIERARCHY (highest to lowest): If the customer ticket has more than one issue type, prioritize the most critical one.

            Domain hints:
            - GTBank, Access, Opay = Nigerian bank transfers.
            - "Processing" on withdrawal = transfers issue.
            - Fee questions are always low urgency unless customer explicitly states urgency.

            Return JSON only: {{"issue_type": "...", "urgency": "...", "reasoning": "short justification"}}
            
        """
        user_message = f"""Subject: {subject}
        
        Question: {description}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        response: TicketClassification = llm.invoke(messages)

        return response
