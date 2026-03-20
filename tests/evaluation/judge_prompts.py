JUDGE_SYSTEM_PROMPT = """You are an expert customer support quality evaluator for Raenest (fintech payment platform).

Your job is to evaluate AI-generated support responses against specific quality criteria.

Be strict but fair. A response should only score high if it genuinely meets the criterion."""


JUDGE_EVALUATION_PROMPT = """Evaluate the following support response using these criteria.
Return ONLY a JSON object, no preamble or explanation.

ORIGINAL TICKET:
Subject: {subject}
Description: {description}

RETRIEVED DOCUMENTS (Source material):
{retrieved_docs}

AI-GENERATED RESPONSE:
{llm_response}

---

Score each criterion from 0.0 to 1.0:

1. **tone_empathy** (0.0 - 1.0)
   - Sounds like a real support agent, warm and professional
   - Acknowledges customer's frustration/concern
   - Not robotic or generic
   - Uses natural language

2. **response_quality** (0.0 - 1.0)
   - Clear and actionable
   - Provides specific next steps
   - Not vague or unhelpful
   - Addresses the customer's actual question
   - Well-structured and easy to follow

3. **faithfulness** (0.0 - 1.0)
   - Answer comes ONLY from retrieved documents
   - Does not add information from outside sources
   - Does not make up facts
   - Stays within provided context

4. **groundedness** (0.0 - 1.0)
   - No hallucinations
   - All facts mentioned exist in source documents
   - Can trace every claim back to retrieved docs
   - Does not contradict source material

---

Return this EXACT JSON structure (no markdown, no backticks):
{{
    "tone_empathy": <float between 0.0 and 1.0>,
    "response_quality": <float between 0.0 and 1.0>,
    "faithfulness": <float between 0.0 and 1.0>,
    "groundedness": <float between 0.0 and 1.0>,
    "overall": <average of the 4 scores>,
    "reason": "<one sentence explaining the overall score>",
    "pass": <true if overall >= 0.75, else false>
}}
"""


def format_retrieved_docs(documents: list) -> str:
    """Format retrieved documents for judge prompt"""
    if not documents:
        return "No documents retrieved."

    formatted = []
    for i, doc in enumerate(documents, 1):
        formatted.append(f"Document {i}:\n{doc.page_content}\n")

    return "\n".join(formatted)
