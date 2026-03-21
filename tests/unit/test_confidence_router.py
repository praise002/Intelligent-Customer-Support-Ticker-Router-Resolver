from src.agents.workflow_nodes import route_by_confidence

# pytest tests/unit/test_confidence_router.py::TestConfidenceRouter -v -s

class TestConfidenceRouter:
    """Test routing logic based on confidence scores"""

    def test_high_confidence_auto_resolve(self):
        """Confidence > 0.85 should auto-resolve"""
        state = {"final_confidence": 0.90}
        decision = route_by_confidence(state)
        assert decision == "auto_resolve"

    def test_boundary_high_confidence(self):
        """Confidence at 0.86 (just above threshold)"""
        state = {"final_confidence": 0.86}
        decision = route_by_confidence(state)
        assert decision == "auto_resolve"

    def test_medium_confidence_human_review(self):
        """Confidence 0.6-0.85 should go to human review"""
        state = {"final_confidence": 0.75}
        decision = route_by_confidence(state)
        assert decision == "human_review"

    def test_boundary_medium_confidence_lower(self):
        """Confidence exactly at 0.6 (lower boundary)"""
        state = {"final_confidence": 0.60}
        decision = route_by_confidence(state)
        assert decision == "human_review"

    def test_boundary_medium_confidence_upper(self):
        """Confidence exactly at 0.85 (upper boundary)"""
        state = {"final_confidence": 0.85}
        decision = route_by_confidence(state)
        assert decision == "human_review"

    def test_low_confidence_escalate(self):
        """Confidence < 0.6 should escalate"""
        state = {"final_confidence": 0.45}
        decision = route_by_confidence(state)
        assert decision == "escalate"

    def test_boundary_low_confidence(self):
        """Confidence at 0.59 (just below threshold)"""
        state = {"final_confidence": 0.59}
        decision = route_by_confidence(state)
        assert decision == "escalate"

    def test_extreme_high_confidence(self):
        """Very high confidence (near 1.0)"""
        state = {"final_confidence": 0.99}
        decision = route_by_confidence(state)
        assert decision == "auto_resolve"

    def test_extreme_low_confidence(self):
        """Very low confidence (near 0.0)"""
        state = {"final_confidence": 0.05}
        decision = route_by_confidence(state)
        assert decision == "escalate"


class TestRouterEdgeCases:
    """Test edge cases"""

    def test_confidence_zero(self):
        """Confidence = 0 should escalate"""
        state = {"final_confidence": 0.0}
        decision = route_by_confidence(state)
        assert decision == "escalate"

    def test_confidence_one(self):
        """Confidence = 1.0 should auto-resolve"""
        state = {"final_confidence": 1.0}
        decision = route_by_confidence(state)
        assert decision == "auto_resolve"
