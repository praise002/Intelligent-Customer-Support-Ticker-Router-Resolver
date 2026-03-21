import re
from dataclasses import dataclass


# from guardrails import Guard
# from guardrails.hub import ToxicLanguage
from src.guardrails.input_config import INPUT_GUARDRAIL_CONFIG


@dataclass
class InputValidation:
    """Result of input validation"""

    safe: bool
    reason: str | None = None
    category: str | None = None  # "injection", "jailbreak", "toxicity", "spam"
    confidence: float = 1.0


class InputGuardrails:
    """Input guardrails validator"""

    def __init__(self):
        self.config = INPUT_GUARDRAIL_CONFIG

        # Initialize Guardrails AI for toxicity
        if self.config["toxicity"]["enabled"]:
            # self.toxicity_guard = Guard().use(
            #     ToxicLanguage(
            #         threshold=self.config["toxicity"]["threshold"],
            #         validation_method="sentence",
            #         on_fail="exception",
            #     )
            # )
            pass

    def validate_input(self, subject: str, description: str) -> InputValidation:
        """
        Validate ticket input against all guardrails.

        Args:
            subject: Ticket subject line
            description: Ticket description/body

        Returns:
            InputValidation with safe=True if passes all checks
        """

        # Combine subject and description for validation
        full_text = f"{subject}\n{description}"

        # Check 1: Prompt Injection
        if self.config["prompt_injection"]["enabled"]:
            result = self._check_prompt_injection(full_text)
            if not result.safe:
                return result

        # Check 2: Jailbreak Attempts
        if self.config["jailbreak"]["enabled"]:
            result = self._check_jailbreak(full_text)
            if not result.safe:
                return result

        # Check 3: Toxicity
        if self.config["toxicity"]["enabled"]:
            result = self._check_toxicity(full_text)
            if not result.safe:
                return result

        # Check 4: Spam
        if self.config["spam"]["enabled"]:
            result = self._check_spam(full_text)
            if not result.safe:
                return result

        # All checks passed
        return InputValidation(safe=True)

    def _check_prompt_injection(self, text: str) -> InputValidation:
        """Check for prompt injection patterns"""

        patterns = self.config["prompt_injection"]["patterns"]
        text_lower = text.lower()

        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return InputValidation(
                    safe=False,
                    reason=f"Prompt injection detected: matched pattern '{pattern}'",
                    category="injection",
                    confidence=0.95,
                )

        return InputValidation(safe=True)

    def _check_jailbreak(self, text: str) -> InputValidation:
        """Check for jailbreak attempt patterns"""

        patterns = self.config["jailbreak"]["patterns"]
        text_lower = text.lower()

        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return InputValidation(
                    safe=False,
                    reason=f"Jailbreak attempt detected: matched pattern '{pattern}'",
                    category="jailbreak",
                    confidence=0.95,
                )

        return InputValidation(safe=True)

    def _check_toxicity(self, text: str) -> InputValidation:
        """Check for toxic/abusive language using Guardrails AI"""

        try:
            # Guardrails AI validation
            self.toxicity_guard.validate(text)
            return InputValidation(safe=True)

        except Exception as e:
            # Toxicity detected
            return InputValidation(
                safe=False,
                reason="Toxic or abusive language detected",
                category="toxicity",
                confidence=0.85,
            )

    def _check_spam(self, text: str) -> InputValidation:
        """Check for spam patterns"""

        patterns = self.config["spam"]["patterns"]

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return InputValidation(
                    safe=False,
                    reason=f"Spam detected: matched pattern '{pattern}'",
                    category="spam",
                    confidence=0.90,
                )

        return InputValidation(safe=True)


# Singleton instance
input_guardrails = InputGuardrails()


def validate_input(subject: str, description: str) -> InputValidation:
    """
    Convenience function to validate input.

    Usage:
        result = validate_input(subject, description)
        if not result.safe:
            # Block ticket
    """
    return input_guardrails.validate_input(subject, description)
