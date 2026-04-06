**CASE STUDY - AI Engineering**

**CLIENT/PROJECT:**
Raenest (formerly Geegpay) — Nigerian cross-border fintech serving 700,000+ users | DevCareer × Raenest Hackathon Project

---

**THE PROBLEM**

Raenest has processed over $1 billion in payments and supports over 700,000 individuals and 500 businesses but growth created a support problem their team couldn't keep up with.

Their Play Store reviews tell the real story. Users reporting 24-48 hour response times on urgent transfer issues. Customers waiting 72+ hours with funds stuck and no reply. One user described waiting two weeks for an issue that should take 10 minutes to resolve. Raenest's own support team repeatedly acknowledged being overwhelmed citing "high volume of inbound requests" across dozens of complaints.

The ticket categories were consistent and predictable: transfer failures, KYC verification delays, account suspensions, card issues, and login problems. These were repetitive, classifiable issues, exactly the kind a well-designed AI system could handle. The business cost was real. Slow support was driving 1-star reviews, damaging trust, and pushing users toward competitors.

---

**MY APPROACH**

Built for the DevCareer × Raenest Hackathon, the goal was to design a production-ready intelligent support system — not a chatbot, but a full routing and resolution engine.

The key design decisions:

**Use Claude Haiku for classification — not a traditional classifier.**
The initial approach used `facebook/bart-large-mnli`, a lightweight zero-shot classifier. It was fast but kept misclassifying tickets because it lacked domain knowledge of fintech support contexts, it couldn't reliably distinguish a KYC delay from an account suspension, or a transfer failure from a general complaint.
I initially tried a fine-tuned text classifier, but the misclassification issues persisted. Even after exploring more advanced models like `knowledgator/gliclass-small-v1.0` and `gliclass-base-v2.0-rac-init`—which offered capabilities like few-shot examples, descriptive prompts, and Retrieval-Augmented Classification—the core problem remained unsolved.

The switch to Claude Haiku solved this. Haiku excels in structured classification, scoring as high as 98% in email categorization and is designed for high-volume customer service scenarios where speed and accuracy interact. Unlike generic classifiers, Haiku understands the nuance and language patterns of real fintech support tickets, making classification both faster and more accurate for this specific domain. Claude Haiku 4.5 runs up to 4-5 times faster than Sonnet 4.5 at a fraction of the cost, keeping classification fast without becoming a bottleneck.

**Build confidence-based routing**
Instead of a simple auto-resolve or escalate decision, designed a three-tier confidence system. High confidence resolves automatically. Medium confidence drafts a response for human review. Low confidence escalates to the right specialist team. This protects users from bad AI responses while still automating the majority of tickets.

**Use RAG for context-aware responses.**
Rather than relying purely on LLM knowledge, built a retrieval layer using Raenest's actual help center documentation, FAQs, and past resolved tickets stored in ChromaDB. Every response is grounded in Raenest's own knowledge.

**Design for scale from day one.**
At 700,000 users, ticket spikes are inevitable. Used Redis priority queues to buffer incoming tickets and ensure urgent issues jump the queue, with 3 LLM workers running at ~54% utilization to handle up to 1,000 tickets per hour with headroom.

---

**THE SOLUTION**

An intelligent support ticket router and resolver built with FastAPI, LangChain, LangGraph, ChromaDB, PostgreSQL, and Redis, deployed on DigitalOcean with Docker Compose, Nginx, and CI/CD via GitHub Actions.

**How it works:**

A ticket arrives via Zendesk webhook → passes through input guardrails that block prompt injection, spam → classified by Claude Haiku by issue type (KYC, cards, transfers, integrations, fees, account access, general) and urgency (high, medium, low) → enters a Redis priority queue with urgent tickets processed first → LLM workers retrieve relevant context from the RAG knowledge base → generate a response with a confidence score calculated from three signals: retrieval similarity, semantic match, and LLM self-confidence → routed based on score:

- Above 85% → auto-resolved, response sent directly to customer
- 60-85% → human review queue, AI draft ready for agent
- Below 60% → escalated to the right specialist team via Zendesk

The system gets smarter over time, every successfully resolved ticket feeds back into the knowledge base.

**Live at:** support-agent.praizdev.com

---

**THE RESULT**

| Metric | Before | Target |
|---|---|---|
| Auto-resolution rate | 0% | 60-70% of tickets |
| Average response time | 24-48 hours | Under 10 minutes |
| Agent efficiency | Manual review of all tickets | Agents handle only complex cases |
| Customer satisfaction | 4.3/5 with recurring support complaints | 4.5/5 target |

**Tech Stack:** FastAPI · React · LangChain · LangGraph · ChromaDB · PostgreSQL · Redis · Claude Haiku · Groq · Zendesk · Docker · GitHub Actions · DigitalOcean

---

---

**CASE STUDY — AI Automation (No-Code)**

**CLIENT/PROJECT:**
Raenest (formerly Geegpay) — Nigerian cross-border fintech serving 700,000+ users | Spec Project

---

**THE PROBLEM**

Raenest serves over 700,000 users processing cross-border payments across Africa. As their user base grew, their support team faced a problem that couldn't be solved by hiring more people.

Their Play Store reviews tell the real story. Customers waiting 24-48 hours for responses on urgent transfer issues. Funds stuck in pending with no reply for days. One user described waiting two weeks for an issue that could be resolved in 10 minutes. Raenest's own team repeatedly cited "high volume of inbound requests" as the reason, a clear signal their manual support process had hit its ceiling.

The ticket types were consistent and predictable: transfer failures, KYC verification delays, account suspensions, card issues, and login problems. The same questions, asked thousands of times, handled one by one by human agents.

The business cost was real, slow support was driving 1-star reviews, damaging user trust, and pushing customers toward competitors like Grey and Cleva. The problem wasn't the support team. It was the system.

---

**MY APPROACH**

The goal was to build the same intelligent support outcome as a fully coded system — automatic classification, priority routing, AI-generated responses, and confidence-based decisions but using n8n so the system is faster to deploy, easier to maintain, and requires no engineering team to operate after handoff.

Key design decisions:

**Multi-channel entry from day one.**
Support tickets come from three sources: Zendesk, a web support form via webhook, and WhatsApp Business Cloud API. Each channel feeds into the same n8n workflow, normalised into a consistent ticket format before processing begins. WhatsApp works through Meta's Business Cloud API — when a customer messages Raenest's WhatsApp number, Meta instantly sends the message payload to an n8n webhook, triggering the workflow automatically.

**Separate classification from resolution.**
Two AI node calls, not one. The first call classifies the ticket — determining urgency (high, medium, low) and issue type (KYC, cards, transfers, account access, fees, general). The second call generates the actual response using Raenest's support knowledge as context. Keeping these separate means classification stays fast and the response generation has a clean, focused prompt.

**Priority handling via workflow separation.**
High urgency tickets immediately trigger a separate n8n sub-workflow via an Execute Workflow node which is processed instantly without queuing. Medium and low urgency tickets are saved to Google Sheets and a scheduled workflow picks them up and resolves them sequentially. This mirrors a priority queue without needing Redis or any infrastructure.

**Confidence-based routing via Switch node.**
After response generation, a three-signal confidence score determines routing — above 85% auto-resolves, 60-85% goes to human review, below 60% escalates to the right specialist team by issue type. The Switch node handles all routing logic cleanly without any code.

**Airtable as the central ticket database.**
Every ticket creates a record in Airtable on arrival. As it moves through the workflow — classified, scored, routed, resolved, the same record updates. Full audit trail, no duplicate rows, queryable views for the support team without touching a spreadsheet formula.

---

**THE SOLUTION**

A fully automated support ticket system built entirely in n8n — no code, no infrastructure management, no developer needed to maintain it.

**How it works:**

Ticket arrives via Zendesk webhook, web form webhook, or WhatsApp Business Cloud API → normalised into a standard format → record created in Airtable → AI node 1 classifies urgency and issue type → Switch node routes high urgency tickets to an immediate sub-workflow, medium and low urgency tickets saved to Google Sheets queue → scheduled workflow processes queued tickets one by one → AI node 2 generates a response using Raenest's support knowledge → confidence score calculated → Switch node routes based on score:

- **Above 85%** → auto-resolved, response sent to Zendesk, Zendesk delivers to customer automatically. WhatsApp tickets replied to directly via WhatsApp Business Cloud node.
- **60-85%** → routed to human review queue in Zendesk with AI draft attached
- **Below 60%** → escalated to specialist team by issue type via Zendesk. Gmail notification sent to the relevant team.

Airtable record updated at every stage — urgency, issue type, AI response, confidence score, routing decision, and final status all tracked in one place.

---

**THE RESULT**

| Metric | Before | Target |
|---|---|---|
| Auto-resolution rate | 0% | 60-70% of tickets |
| Average response time | 24-48 hours | Under 10 minutes |
| Agent efficiency | Manual review of all tickets | Agents handle only complex cases |
| Deployment time | N/A | Days, not weeks |
| Maintenance | Requires engineering team | Manageable by ops team |

**The core advantage over a coded system:** Same intelligent outcome. Zero infrastructure to manage. No Docker, no Redis, no CI/CD pipeline. A non-technical support manager can modify routing rules, update the AI prompt, or add a new integration directly in n8n — without filing a ticket to engineering.

**Tools Used:** n8n · Claude Haiku · WhatsApp Business Cloud API · Zendesk · Gmail · Airtable · Google Sheets

---