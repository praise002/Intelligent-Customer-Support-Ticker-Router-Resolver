import json
import logging
from datetime import datetime
from pathlib import Path

import pytest

from src.agents.classifier import TicketClassifier

# pytest tests/unit/test_classifier.py::TestClassifier::test_urgency_high -v -s
# pytest src/tests/test_profiles.py::TestUpdateMyProfile::test_update_profile_success -v -s


class TestClassifier:
    """Test classification"""

    def test_urgency_high(self):
        """High urgency tickets should be classified as 'high'"""

        result = TicketClassifier.classify(
            "URGENT: Withdrawal stuck for 8 hours",
            "I need this money NOW. Transaction failing.",
        )
        print(result)

        assert result.urgency == "high"

    def test_urgency_medium(self):
        """Medium urgency tickets"""
        result = TicketClassifier.classify(
            "KYC verification pending",
            "My documents were submitted 2 days ago, still pending.",
        )
        print(result)
        assert result.urgency == "medium"

    def test_urgency_low(self):
        """Low urgency tickets"""

        result = TicketClassifier.classify(
            "Question about fees",
            "How much does it cost to withdraw to local bank?",
        )

        print(result)

        assert result.urgency == "low"

    def test_issue_type_cards(self):
        """Card-related issues"""
        result = TicketClassifier.classify(
            "Card declined",
            "My virtual card transaction failed on Netflix",
        )
        print(result)
        assert result.issue_type == "cards"

    def test_issue_type_verification(self):
        """Account verification issues"""
        result = TicketClassifier.classify(
            "KYC rejected",
            "My documents were rejected, need to know why",
        )
        print(result)
        assert result.issue_type == "account_verification"

    def test_issue_type_transfers(self):
        """Transfer/withdrawal issues"""
        result = TicketClassifier.classify(
            "Withdrawal delayed",
            "My withdrawal to GTBank is stuck on processing",
        )
        print(result)
        assert result.issue_type == "transfers"

    def test_issue_type_integrations(self):
        """Platform integration questions"""
        result = TicketClassifier.classify(
            "How to link Upwork",
            "I want to receive Upwork payments to my account",
        )
        print(result)
        assert result.issue_type == "integrations"

    def test_demo_tickets_classification(self, test_tickets, tmp_path):
        """
        Loop through all demo tickets and validate expected classification.
        Expected classification can be a single value OR a list of acceptable values.
        """
        failed_tickets = []
        all_results = []  # store each result for later analysis

        for ticket in test_tickets:
            # Get classification from classifier
            result = TicketClassifier.classify(
                f"{ticket['subject']}", f"{ticket['description']}"
            )
            print(result)

            # Store result as serializable dict
            result_dict = {
                "ticket_id": ticket["ticket_id"],
                "subject": ticket["subject"],
                "actual_issue_type": result.issue_type,
                "actual_urgency": result.urgency,
                "expected_issue_type": ticket["expected_classification"]["issue_type"],
                "expected_urgency": ticket["expected_classification"]["urgency"],
            }
            all_results.append(result_dict)

            # Get expected values (may be string or list)
            expected_issue = ticket["expected_classification"]["issue_type"]
            expected_urgency = ticket["expected_classification"]["urgency"]

            # Convert single string to list for uniform handling
            expected_issue_list = (
                expected_issue if isinstance(expected_issue, list) else [expected_issue]
            )
            expected_urgency_list = (
                expected_urgency
                if isinstance(expected_urgency, list)
                else [expected_urgency]
            )

            # Track mismatches
            mismatches = []

            # Check issue_type
            if result.issue_type not in expected_issue_list:
                mismatches.append(
                    f"issue_type: got '{result.issue_type}', expected {expected_issue_list}"
                )

            # Check urgency
            if result.urgency not in expected_urgency_list:
                mismatches.append(
                    f"urgency: got '{result.urgency}', expected {expected_urgency_list}"
                )

            # If any mismatches, record this ticket
            if mismatches:
                failed_tickets.append(
                    {
                        "ticket_id": ticket["ticket_id"],
                        "subject": ticket["subject"],
                        "mismatches": mismatches,
                        "actual": result_dict,
                        "expected": {
                            "issue_type": expected_issue_list,
                            "urgency": expected_urgency_list,
                        },
                    }
                )
            logging.info(mismatches)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(__file__).parent / f"classification_results_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            all_results.extend(failed_tickets)
            json.dump(all_results, f, indent=2)

        logging.info(
            f"\nSaved {len(all_results)} classification results to {output_file}"
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


# TODO: TO BE Fixed

# File saying in root instead of in test file
# File saying in root instead of in test file
