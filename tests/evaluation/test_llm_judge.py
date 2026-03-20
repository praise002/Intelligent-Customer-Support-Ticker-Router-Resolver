import pytest

from tests.evaluation.judge import LLMJudge


class TestLLMJudge:
    """Test LLM judge evaluator"""

    @pytest.fixture
    def judge(self):
        return LLMJudge()

    def test_judge_evaluates_good_response(self, judge):
        """Judge should give high scores to good response"""

        retrieved_docs = [
            type(
                "Document",
                (),
                {
                    "page_content": "To link Upwork: Go to Settings > Payment Methods > Add Direct Deposit. Use your Raenest USD account details. No fees for receiving."
                },
            )()
        ]

        result = judge.evaluate_response(
            ticket_subject="How to link Upwork",
            ticket_description="I want to receive Upwork payments to my Raenest account",
            retrieved_docs=retrieved_docs,
            llm_response="To link your Upwork account:\n\n1. Log into Upwork\n2. Go to Settings > Payment Methods\n3. Add Direct Deposit (US)\n4. Enter your Raenest USD account details\n5. There are no fees for receiving Upwork payments\n\nLet me know if you need the specific account details!",
        )

        assert result["pass"] is True
        assert result["overall"] >= 0.75
        assert result["tone_empathy"] > 0.7
        assert result["response_quality"] > 0.7

    def test_judge_evaluates_bad_response(self, judge):
        """Judge should give low scores to bad response"""

        retrieved_docs = [
            type(
                "Document",
                (),
                {
                    "page_content": "Card declines happen due to: insufficient funds, merchant restrictions, or card limits."
                },
            )()
        ]

        result = judge.evaluate_response(
            ticket_subject="Card declined",
            ticket_description="My card was declined on Netflix",
            retrieved_docs=retrieved_docs,
            llm_response="Your card was declined. Contact your bank.",  # Vague, unhelpful
        )

        assert result["pass"] is False
        assert result["overall"] < 0.75
        assert result["response_quality"] < 0.6

    def test_judge_detects_hallucination(self, judge):
        """Judge should detect hallucinated information"""

        retrieved_docs = [
            type(
                "Document",
                (),
                {
                    "page_content": "Withdrawal processing time: 5 minutes to 2 hours for Nigerian banks."
                },
            )()
        ]

        result = judge.evaluate_response(
            ticket_subject="Withdrawal delay",
            ticket_description="My withdrawal is taking too long",
            retrieved_docs=retrieved_docs,
            llm_response="Withdrawals are processed instantly within 30 seconds. If delayed, your account is probably flagged for fraud.",  # Hallucinated fraud claim
        )

        assert result["groundedness"] < 0.5  # Should detect hallucination
        assert result["faithfulness"] < 0.5

    def test_judge_return_structure(self, judge):
        """Judge should return correct structure"""

        result = judge.evaluate_response(
            ticket_subject="Test",
            ticket_description="Test ticket",
            retrieved_docs=[],
            llm_response="Test response",
        )

        required_keys = [
            "tone_empathy",
            "response_quality",
            "faithfulness",
            "groundedness",
            "overall",
            "reason",
            "pass",
        ]

        for key in required_keys:
            assert key in result

        assert isinstance(result["tone_empathy"], float)
        assert isinstance(result["pass"], bool)
