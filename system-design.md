# Intelligent Customer Support Ticket Router & Resolver
## System Design Document

---

## Table of Contents
1. [Problem Statement](#problem-statement)
2. [Requirements & Assumptions](#requirements--assumptions)
3. [High Level Design](#high-level-design)
4. [Core Components](#core-components)
5. [Database Schema](#database-schema)
6. [API Design](#api-design)
7. [Scaling & Bottlenecks](#scaling--bottlenecks)
8. [Deployment](#deployment)

---

## Problem Statement

Customer support teams are overwhelmed with tickets that could be automatically resolved or properly routed, leading to slow response times and poor customer satisfaction.

The solution is an AI agent that analyzes incoming support tickets, extracts key information, checks a knowledge base, and either resolves the ticket automatically or routes it to the appropriate specialist with context.

---

## Requirements & Assumptions

### Users
- **Customers** — submit support tickets via Zendesk
- **Support Agents** — handle escalated tickets requiring human review

### System Behaviour
- Incoming tickets are classified, processed through a RAG pipeline, and either auto-resolved or escalated to the right department
- Every resolved ticket is stored back into the knowledge base (feedback loop)

### Scale Assumptions
| Metric | Value |
|--------|-------|
| Baseline load | ~100 tickets/day |
| Peak spike | ~1,000 tickets/hour |
| Read/write ratio | ~10:1 (read-heavy) |

---

## High Level Design

```
Incoming Ticket (Zendesk Webhook)
            ↓
       [Load Balancer]
      ↙      ↓      ↘
   [C1]    [C2]    [C3]
         (Classify)
      ↘      ↓      ↙
    [Priority Queue]
    ┌──────────────────┐
    │ 🔴 HIGH urgency  │
    │ 🟡 MEDIUM        │
    │ 🟢 LOW           │
    └──────────────────┘
            ↓
   [LLM Workers: W1 W2 W3]
         ↓           ↓
   [RAG Search]  [Customer DB]
         ↓
   [Vector Database]
   ┌─────────────────────┐
   │ - Stripe Docs       │
   │ - FAQs              │
   │ - Past Tickets      │
   └─────────────────────┘
         ↓
   [LLM Response]
         ↓
   [Confidence Router]
   ↙         ↓          ↘
>0.85     0.6-0.85      <0.6
  ↓           ↓           ↓
Auto      Human        Escalate
Resolve   Review    (by issue type)
  ↓                      ↓
Send to            billing   → #billing-support
Customer           technical → #tech-support
  ↓                account   → #account-team
Store in           feature   → #product-team
database           general   → #support-team
```

---

## Core Components

### 1. Classify

Determines urgency and issue type for each incoming ticket.

| Property | Decision |
|----------|----------|
| **Inputs** | Email subject, body, sender identity |
| **DB Lookup** | Customer plan type, payment history, previous tickets |
| **Outputs** | Urgency label (high/medium/low), Issue type (billing/technical/account/feature/general) |
| **Method** | Zero-shot text classifier (`facebook/bart-large-mnli`) — no LLM call needed |

**Why lightweight?** Classify runs before the queue and is a potential single point of failure. It must be fast (milliseconds) to avoid becoming a bottleneck.

---

### 2. Priority Queue (Redis)

Buffers incoming tickets during traffic spikes and ensures urgent tickets are processed first.

```
Spike of 1,000 tickets
        ↓
   Priority Queue
  ┌──────────────────┐
  │ 🔴 HIGH → first  │
  │ 🟡 MEDIUM        │
  │ 🟢 LOW → last    │
  └──────────────────┘
        ↓
  LLM Workers pull
  from queue
```

---

### 3. RAG Search (ChromaDB)

Retrieves relevant context from the knowledge base before LLM response generation.

| Property | Decision |
|----------|----------|
| **Knowledge Base** | Stripe docs, FAQs, past resolved tickets |
| **Pre-computed** | All KB documents embedded at startup and stored in ChromaDB |
| **On demand** | Incoming ticket converted to embedding at runtime |
| **Output** | Top N similar documents passed as context to LLM |

**Feedback Loop:** Every successfully resolved ticket is stored back into the knowledge base, making the system smarter over time.

---

### 4. LLM Response

Generates a response and confidence score for each ticket.

**Confidence Formula:**
```
confidence = (
    0.4 * retrieval_score      # how similar are retrieved docs?
    0.3 * semantic_similarity  # how well do docs match the question?
    0.3 * llm_self_score       # how confident is the LLM itself?
)
```

**Worker Capacity Calculation:**
```
1 LLM call = ~5 seconds
1 worker   = 720 tickets/hour
Target     = 1,000 tickets/hour
Required   = 2 workers minimum
Deployed   = 3 workers (headroom buffer ~54% utilization)
```

---

### 5. Confidence Router

Routes tickets based on confidence score and issue type.

| Score | Action |
|-------|--------|
| > 0.85 | Auto resolve → send response to customer |
| 0.6 – 0.85 | Human review → support team checks before sending |
| < 0.6 | Escalate → route to specialist by issue type |

**Escalation Routing by Issue Type:**
| Issue Type | Destination |
|------------|-------------|
| Billing | #billing-support (Zendesk) |
| Technical | #tech-support (Zendesk) |
| Account | #security-team (Zendesk) |
| Feature | #product-team (Zendesk) |
| General | #support-team (Zendesk) |

---

## Database Schema

### PostgreSQL (Relational Data)

**Customers Table**
```sql
CREATE TABLE customers (
    customer_id   UUID PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    plan_type     ENUM('free', 'premium', 'enterprise'),
    created_at    TIMESTAMP DEFAULT NOW()
);
```

**Tickets Table**
```sql
CREATE TABLE tickets (
    ticket_id     UUID PRIMARY KEY,
    subject       TEXT NOT NULL,
    content       TEXT NOT NULL,
    sender        UUID REFERENCES customers(customer_id),
    priority      ENUM('high', 'medium', 'low'),
    issue_type    ENUM('billing', 'technical', 'account', 'feature', 'general'),
    created_at    TIMESTAMP DEFAULT NOW()
);
# POST priority and issue type to zendesk
# Can be done in customize ticket
```

**Responses Table**
```sql
CREATE TABLE responses (
    response_id       UUID PRIMARY KEY,
    ticket_id         UUID REFERENCES tickets(ticket_id),
    message           TEXT NOT NULL,
    confidence_score  FLOAT NOT NULL,
    routing_decision  ENUM('auto_resolve', 'human_review', 'escalate'),  # update to zendesk
    assigned_to       TEXT,  -- Group assigned to e.g billing-support
    created_at        TIMESTAMP DEFAULT NOW()
);
```

### ChromaDB (Vector Data)
```
Collections:
├── stripe_docs        → Stripe documentation embeddings
├── faqs               → FAQ embeddings
└── resolved_tickets   → Past resolved ticket embeddings
```

**Why two databases?**
- PostgreSQL → structured data, exact lookups, relationships
- ChromaDB → semantic search, similarity matching, embeddings

---

## API Design

### Webhook (Event Driven)
```
POST /api/v1/webhooks/zendesk
→ Receives new ticket from Zendesk instantly
→ Returns 200 OK immediately (async processing)
→ Ticket added to priority queue in background
```

**Why async acknowledgement?**
Returning 200 immediately prevents Zendesk from timing out during the 5-10 second LLM processing time, which would cause duplicate ticket submissions.

### REST Endpoints
```
GET   /api/v1/health
→ Check the health of the API

PATCH /api/v1/tickets/{ticket_id}
→ Agent resolves or updates a ticket
→ Triggers knowledge base update on resolution

GET   /api/v1/tickets
→ Retrieve all tickets (React dashboard)

GET   /api/v1/tickets/{ticket_id}
→ Check specific ticket status

GET   /api/v1/stats
→ Pre-computed dashboard statistics
  (resolved count, escalated count, pending count)
```

**Stats endpoint** uses a cron job every 5 minutes to pre-compute counts (materialized view). Real-time accuracy not required for dashboard statistics.

---

## Scaling & Bottlenecks

| Bottleneck | Problem | Solution | Trade-off |
|------------|---------|----------|-----------|
| **LLM Response** | Slowest step, 5s per call | Priority queue + 3 workers | Higher API cost |
| **Customer DB** | 1,000 simultaneous lookups during spike | Redis caching with event-driven invalidation | Cache staleness on plan upgrades |
| **Classify** | Single point of failure, first component every ticket hits | Multiple instances + load balancer (least connection) | Infrastructure cost |
| **Vector DB (speed)** | 1,000 simultaneous RAG searches | Replication across multiple instances | Eventual consistency on new documents |
| **Vector DB (storage)** | Knowledge base grows over time | Sharding across multiple databases | Complex routing to correct shard |

### Key Scaling Principles Applied
- **Never run above 70-80% capacity** — 3 workers at ~54% utilization
- **Replication** solves speed problems
- **Sharding** solves storage problems
- **Caching** reduces repeated database hits
- **YAGNI** — complexity added only when justified

---

## Deployment

### Stack
```
DigitalOcean Droplet (Ubuntu 24)
├── Nginx (reverse proxy)
├── Certbot / Let's Encrypt (SSL)
├── Docker Compose
│   ├── FastAPI backend
│   ├── React dashboard
│   ├── ChromaDB
│   ├── Redis (priority queue)
│   └── LLM Workers (3 instances)
└── DigitalOcean Managed PostgreSQL (separate)
```

**Why Managed PostgreSQL?** Automated backups, failover, and patching handled by DigitalOcean — no manual database administration needed.


### CI/CD Pipeline
```
Push to GitHub
      ↓
GitHub Actions
      ↓
Run tests
      ↓
Build Docker images
      ↓
Push to DigitalOcean Container Registry
      ↓
Deploy to Droplet
```

### Domain
```
support-agent.praizdev.com
→ Nginx reverse proxy
→ Let's Encrypt SSL via Certbot
```

---

## Tech Stack Summary

| Component | Technology |
|-----------|------------|
| Backend API | FastAPI |
| Frontend | React |
| AI Orchestration | LangChain + LangGraph |
| Vector Database | ChromaDB |
| Relational Database | PostgreSQL |
| Queue | Redis |
| Text Classifier | facebook/bart-large-mnli (zero-shot) |
| Ticket Ingestion | Zendesk Webhooks |
| Escalation Notifications | Slack API |
| Deployment | DigitalOcean + Docker Compose |
| Reverse Proxy | Nginx |
| SSL | Let's Encrypt (Certbot) |
| CI/CD | GitHub Actions |