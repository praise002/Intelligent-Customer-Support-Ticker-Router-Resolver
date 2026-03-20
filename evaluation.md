# Evaluation Strategy
## Ticket Router & Resolver

---

## Overview

Evaluating an AI system is fundamentally different from evaluating regular code. Regular code is deterministic — same input always gives same output. LLM responses are non-deterministic — the same ticket can produce different responses every time.

This means you cannot use simple assertions to test LLM output. Instead, evaluation happens across three layers:

```
Layer 1: Unit Tests       → does the code work?
Layer 2: LLM as a Judge   → does the AI produce good outputs?
Layer 3: Performance Metrics → does the system perform well?
```

---

## Layer 1: Unit Tests

Unit tests cover all deterministic parts of the pipeline — components that always return the same output given the same input.

### What to Test

**Classify Component**
```python
# Urgency classification
input  = "My payment is failing right now, losing money"
expect = urgency == "high"

input  = "Hey, just wondering how to update my logo. No rush!"
expect = urgency == "low"

# Issue type classification
input  = "I can't process transactions"
expect = issue_type == "billing"

input  = "My API integration keeps throwing errors"
expect = issue_type == "technical"
```

**Confidence Router**
```python
# Routing thresholds
input  = confidence_score = 0.90
expect = routing_decision == "auto_resolve"

input  = confidence_score = 0.70
expect = routing_decision == "human_review"

input  = confidence_score = 0.50
expect = routing_decision == "escalate"

# Boundary edge cases
input  = confidence_score = 0.85  # exactly on boundary
expect = routing_decision in ["auto_resolve", "human_review"]

# Escalation routing by issue type
input  = confidence_score = 0.50, issue_type = "billing"
expect = assigned_to == "#billing-support"

input  = confidence_score = 0.50, issue_type = "technical"
expect = assigned_to == "#tech-support"
```

### When to Run
Unit tests run on every GitHub push via GitHub Actions CI/CD pipeline. They are fast (milliseconds) and cheap.

---

## Layer 2: LLM as a Judge

Since LLM responses are non-deterministic, a second LLM evaluates the first LLM's response against defined quality criteria before it is sent to the customer.

### Evaluation Criteria

| Criterion | Description | Target Score |
|-----------|-------------|--------------|
| **Tone & Empathy** | Sounds like a real support agent, warm and professional, not robotic | > 0.75 |
| **Response Quality** | Clear, actionable, not vague or rude, ends with a next step | > 0.75 |
| **Faithfulness** | Answer comes from retrieved documents, not from LLM training data | > 0.75 |
| **Groundedness** | No hallucinations, all facts exist in source documents | > 0.75 |

### Judge Prompt

```python
JUDGE_PROMPT = """
You are an expert customer support quality evaluator.

Evaluate the following support response using these criteria.
Return ONLY a JSON object, no preamble.

ORIGINAL TICKET:
{ticket_content}

RETRIEVED DOCUMENTS:
{retrieved_docs}

LLM RESPONSE:
{llm_response}

Score each criterion from 0.0 to 1.0:

1. tone_empathy      - sounds like real support agent, warm and professional
2. response_quality  - clear, actionable, not vague or rude
3. faithfulness      - answer comes from retrieved documents only
4. groundedness      - no hallucinations, facts exist in source documents

Return this exact JSON:
{{
    "tone_empathy":      <score>,
    "response_quality":  <score>,
    "faithfulness":      <score>,
    "groundedness":      <score>,
    "overall":           <average score>,
    "reason":            "<one sentence explanation>",
    "pass":              <true if overall > 7, else false>
}}
"""
```

**Why retrieved documents are passed to the judge:** The judge needs the source documents as a reference point to evaluate faithfulness and groundedness. Without them, it cannot verify whether the LLM's response is grounded in the actual knowledge base or hallucinated.

### Using Judge Scores to Improve the System

Judge scores accumulate over time and reveal systematic weaknesses:

```
tone_empathy consistently low
→ Add to prompt: "Always acknowledge the customer's frustration first"

faithfulness consistently low
→ Retrieve more documents (top 5 instead of top 3)
→ Or improve the embedding model

groundedness consistently low
→ Add to prompt: "Only use information from the provided context"
→ "If unsure, say: I don't have enough information to answer this"

response_quality consistently low
→ Add response format instructions
→ "Always end with a clear next step for the customer"
```

This creates a continuous improvement loop:

```
Collect judge scores
        ↓
Identify weakest criterion
        ↓
Fix prompt or RAG configuration
        ↓
Deploy
        ↓
Scores improve
        ↓
repeat
```

---

## Layer 3: Performance Metrics

Performance metrics answer business and system health questions that unit tests and the judge cannot.

### Category 1: Business Metrics

These answer: *"Is the system delivering value?"*

| Metric | Description | Target |
|--------|-------------|--------|
| **Resolution Rate** | % of tickets auto-resolved without human involvement | > 60% |
| **Escalation Rate** | % of tickets routed to human agents | < 40% |
| **Reopen Rate** | % of auto-resolved tickets the customer replied to again | < 10% |

A high reopen rate is a strong signal that auto-resolved responses did not actually solve the customer's problem.

### Category 2: Quality Metrics

These answer: *"Are AI responses actually good?"*

| Metric | Description | Target |
|--------|-------------|--------|
| **Average Judge Scores** | Mean score per criterion across all judged tickets | > 0.75 |
| **Confidence Score Distribution** | Breakdown of high/medium/low confidence tickets | Monitor for shifts |
| **Hallucination Rate** | % of responses with groundedness score < 0.5 | < 5% |

### Category 3: System Performance Metrics

These answer: *"Is the system fast and reliable?"*

| Metric | Description | Target |
|--------|-------------|--------|
| **End-to-End Latency** | Time from webhook received to response sent | < 10 seconds |
| **Queue Depth** | Number of tickets waiting in priority queue | Monitor for spikes |
| **Worker Utilization** | % of LLM worker capacity in use | < 70-80% |
| **Uptime** | % of time system is available | 99.9% |

### Primary Alert Metric

The single most important metric to monitor is **auto-resolution rate.** A sudden drop signals a systemic failure:

```
Normal:    65% auto-resolved
Overnight: 10% auto-resolved
     ↓
Possible causes:
→ ChromaDB down (RAG returning no results)
→ Confidence scores all tanked
→ LLM prompt regression
→ Embedding model issue
```

Set an alert threshold:
```python
if auto_resolution_rate < 50%:
    → page engineer immediately
```

### Feedback Signals from Customers

Beyond system metrics, customer behaviour provides implicit quality signals:

```
Satisfied customer:
→ No follow-up reply
→ Closes the ticket
→ Short reply like "thanks, fixed!"

Unsatisfied customer:
→ Replies with more questions
→ Long frustrated follow-up
→ Requests human agent
```

These signals feed back into reopen rate and help identify which ticket categories the AI handles poorly.

---

## Stats API Endpoint

The `GET /api/v1/stats` endpoint exposes all metrics to the React dashboard:

```json
{
  "business": {
    "resolution_rate": 0.65,
    "escalation_rate": 0.35,
    "reopen_rate": 0.08
  },
  "quality": {
    "avg_tone_empathy": 0.82,
    "avg_response_quality": 0.79,
    "avg_faithfulness": 0.85,
    "avg_groundedness": 0.88,
    "hallucination_rate": 0.03
  },
  "performance": {
    "avg_latency_seconds": 7.2,
    "queue_depth": 12,
    "worker_utilization": 0.54,
    "uptime": 0.999
  }
}
```

Stats are pre-computed every 1 hour via a cron job (materialized view). Real-time accuracy is not required for dashboard statistics.

---

## Summary

| Layer | What it tests | When it runs | Cost |
|-------|--------------|--------------|------|
| Unit Tests | Code correctness, routing logic, edge cases | Every GitHub push | Free, milliseconds |
| LLM as Judge | Response tone, quality, faithfulness, groundedness | Sampled on stored ticket, most concern is auto-resolve tickets | LLM API cost, ~5s |
| Performance Metrics | Business value, system health, AI quality over time | Continuously, aggregated every 1 hour | Negligible |