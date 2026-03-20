from decouple import config
import pytest

from agents.classifier import TicketClassifier
from src.tickets.tasks import classify_ticket_task

hf_token = config("HF_TOKEN")
classifier = TicketClassifier(api_token=hf_token)


class TestClassifier:
    """Test BART zero-shot classification"""

    def test_urgency_high(self):
        """High urgency tickets should be classified as 'high'"""
        result = classify_ticket_task(
            subject="URGENT: Withdrawal stuck for 8 hours",
            description="I need this money NOW. Transaction failing.",
        )
        assert result["urgency"] == "high"

    def test_urgency_medium(self):
        """Medium urgency tickets"""
        result = classifier.classify_ticket(
            subject="KYC verification pending",
            description="My documents were submitted 2 days ago, still pending.",
        )
        assert result["urgency"] == "medium"

    def test_urgency_low(self):
        """Low urgency tickets"""
        result = classifier.classify_ticket(
            subject="Question about fees",
            description="How much does it cost to withdraw to local bank?",
        )
        assert result["urgency"] == "low"

    def test_issue_type_cards(self):
        """Card-related issues"""
        result = classifier.classify_ticket(
            subject="Card declined",
            description="My virtual card transaction failed on Netflix",
        )
        assert result["issue_type"] == "cards"

    def test_issue_type_verification(self):
        """Account verification issues"""
        result = classifier.classify_ticket(
            subject="KYC rejected",
            description="My documents were rejected, need to know why",
        )
        assert result["issue_type"] == "account_verification"

    def test_issue_type_transfers(self):
        """Transfer/withdrawal issues"""
        result = classifier.classify_ticket(
            subject="Withdrawal delayed",
            description="My withdrawal to GTBank is stuck on processing",
        )
        assert result["issue_type"] == "transfers"

    def test_issue_type_integrations(self):
        """Platform integration questions"""
        result = classifier.classify_ticket(
            subject="How to link Upwork",
            description="I want to receive Upwork payments to my account",
        )
        assert result["issue_type"] == "integrations"

    def test_classification_has_confidence_scores(self):
        """Classification should include confidence scores"""
        result = classifier.classify_ticket(
            subject="Test ticket", description="Test description"
        )
        assert "confidence_scores" in result
        assert isinstance(result["confidence_scores"], dict)
        
    def test_demo_tickets_classification(self, test_tickets):
        """
        Loop through all demo tickets and validate expected classification.
        """
        failed_tickets = []
        
        for ticket in test_tickets:
            # Get classification from classifier
            result = classifier.classify_ticket(
                subject=ticket["subject"],
                description=ticket["description"]
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
                failed_tickets.append({
                    "ticket_id": ticket["ticket_id"],
                    "subject": ticket["subject"],
                    "mismatches": mismatches,
                    "actual": result,
                    "expected": expected
                })
        
        # Report failures
        if failed_tickets:
            error_msg = "\n\nClassification failures:\n"
            for failure in failed_tickets:
                error_msg += f"\n{failure['ticket_id']}: {failure['subject']}\n"
                for mismatch in failure['mismatches']:
                    error_msg += f"  - {mismatch}\n"
            
            # Show summary
            error_msg += f"\n{len(failed_tickets)}/{len(test_tickets)} tickets failed classification"
            
            pytest.fail(error_msg)

class TestClassifierEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_subject(self):
        """Should handle empty subject"""
        result = classifier.classify_ticket(
            subject="", description="Card declined on payment"
        )
        assert result["issue_type"] in ["cards", "general"]

    def test_empty_description(self):
        """Should handle empty description"""
        result = classifier.classify_ticket(subject="Card declined", description="")
        assert result["issue_type"] in ["cards", "general"]

    def test_very_short_text(self):
        """Should handle very short text"""
        result = classifier.classify_ticket(subject="Help", description="Urgent")
        assert result["urgency"] in ["high", "medium", "low"]
        assert result["issue_type"] is not None
