import pytest
from decouple import config

from src.agents.classifier import TicketClassifier

hf_token = config("HF_TOKEN")
classifier = TicketClassifier(api_token=hf_token)

# pytest tests/unit/test_classifier.py::TestClassifier::test_urgency_high -v -s
# pytest src/tests/test_profiles.py::TestUpdateMyProfile::test_update_profile_success -v -s


class TestClassifier:
    """Test BART zero-shot classification"""

    def test_urgency_high(self):
        """High urgency tickets should be classified as 'high'"""
        result = classifier.classify(
            "URGENT: Withdrawal stuck for 8 hours\n\nI need this money NOW. Transaction failing.",
        )
        assert result["urgency"] == "high"

    def test_urgency_medium(self):
        """Medium urgency tickets"""
        result = classifier.classify(
            "KYC verification pending\n\nMy documents were submitted 2 days ago, still pending.",
        )
        assert result["urgency"] == "medium"

    def test_urgency_low(self):
        """Low urgency tickets"""
        result = classifier.classify(
            subject="Question about fees",
            description="How much does it cost to withdraw to local bank?",
        )
        assert result["urgency"] == "low"

    def test_issue_type_cards(self):
        """Card-related issues"""
        result = classifier.classify(
            "Card declined\n\nMy virtual card transaction failed on Netflix",
        )
        assert result["issue_type"] == "cards"

    def test_issue_type_verification(self):
        """Account verification issues"""
        result = classifier.classify(
            "KYC rejected\n\nMy documents were rejected, need to know why",
        )
        assert result["issue_type"] == "account_verification"

    def test_issue_type_transfers(self):
        """Transfer/withdrawal issues"""
        result = classifier.classify(
            "Withdrawal delayed\n\nMy withdrawal to GTBank is stuck on processing",
        )
        assert result["issue_type"] == "transfers"

    def test_issue_type_integrations(self):
        """Platform integration questions"""
        result = classifier.classify(
            "How to link Upwork\n\nI want to receive Upwork payments to my account",
        )
        assert result["issue_type"] == "integrations"

    def test_demo_tickets_classification(self, test_tickets):
        """
        Loop through all demo tickets and validate expected classification.
        """
        failed_tickets = []

        for ticket in test_tickets:
            # Get classification from classifier
            result = classifier.classify(
                f"{ticket["subject"]}\n\n{ticket["description"]}"
            )

            # Get expected classification
            expected = ticket["expected_classification"]

            # Track mismatches
            mismatches = []

            # Check issue_type
            if result["issue_type"] != expected["issue_type"]:
                mismatches.append(
                    f"issue_type: got '{result['issue_type']}', expected '{expected['issue_type']}'"
                )

            # Check urgency
            if result["urgency"] != expected["urgency"]:
                mismatches.append(
                    f"urgency: got '{result['urgency']}', expected '{expected['urgency']}'"
                )

            # If any mismatches, record this ticket
            if mismatches:
                failed_tickets.append(
                    {
                        "ticket_id": ticket["ticket_id"],
                        "subject": ticket["subject"],
                        "mismatches": mismatches,
                        "actual": result,
                        "expected": expected,
                    }
                )

        # Report failures
        if failed_tickets:
            error_msg = "\n\nClassification failures:\n"
            for failure in failed_tickets:
                error_msg += f"\n{failure['ticket_id']}: {failure['subject']}\n"
                for mismatch in failure["mismatches"]:
                    error_msg += f"  - {mismatch}\n"

            # Show summary
            error_msg += f"\n{len(failed_tickets)}/{len(test_tickets)} tickets failed classification"

            pytest.fail(error_msg)
