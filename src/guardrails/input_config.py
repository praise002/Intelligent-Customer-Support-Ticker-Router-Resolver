from typing import Dict, List

INJECTION_PATTERNS = [
    r"ignore (all|previous|above) (instructions|prompts|rules)",
    r"system prompt",
    r"developer mode",
    r"</?SYSTEM>",
    r"you are now",
    r"forget (your|the) (role|instructions)",
    r"pretend (you|to) (are|be)",
    r"translate to .+: ?\[ignore",
    r"new instructions:",
    r"disregard (all|previous)",
]


JAILBREAK_PATTERNS = [
    r"DAN mode",
    r"do anything now",
    r"without (ethics|restrictions|rules|limitations)",
    r"hypothetical (world|scenario)",
    r"in a world where",
    r"evil AI",
    r"unethical mode",
]


SPAM_PATTERNS = [
    r"[A-Z\s]{30,}",  # Excessive caps
    r"(.)\1{15,}",  # Repeated characters (15+ times)
    r"http[s]?://.*http[s]?://",  # Multiple URLs
    r"[!?]{5,}",  # Excessive punctuation
    r"(click here|buy now|limited time|free money|act now)",
]

# Guardrail configuration
INPUT_GUARDRAIL_CONFIG = {
    "prompt_injection": {
        "enabled": True,
        "patterns": INJECTION_PATTERNS,
        "action": "block",
    },
    "jailbreak": {
        "enabled": True,
        "patterns": JAILBREAK_PATTERNS,
        "action": "block",
    },
    "toxicity": {
        "enabled": True,
        "threshold": 0.7,  # 0.0 (allow all) to 1.0 (block all)
        "action": "block",
    },
    "spam": {
        "enabled": True,
        "patterns": SPAM_PATTERNS,
        "action": "block",
    },
}
