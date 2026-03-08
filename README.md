# 🤖 Stripe Support AI - Intelligent Ticket Router & Resolver

An advanced AI-powered customer support system that automatically classifies, resolves, and routes support tickets using multi-signal confidence scoring and LangGraph workflows.

## 🎯 Key Features

- **Multi-Signal Confidence Scoring**: Combines retrieval quality, semantic similarity, and LLM confidence
- **Smart Escalation Logic**: Auto-resolve (>85%), Human Review (60-85%), Escalate (<60%)
- **RAG-Powered Responses**: Vector search through Stripe API documentation
- **Safety Overrides**: Critical keyword detection and priority-based routing
- **LangGraph Workflow**: State machine for reliable ticket processing
- **Real-time Demo**: Interactive UI showing all three escalation paths

## 📊 Architecture

```
Incoming Ticket
     ↓
┌────────────────────┐
│  1. Retrieve       │  → ChromaDB vector search (top-5 docs)
└────────────────────┘
     ↓
┌────────────────────┐
│  2. Generate       │  → LLM creates response (NVIDIA/Groq)
└────────────────────┘
     ↓
┌────────────────────┐
│  3. Calculate      │  → Multi-signal confidence:
│     Confidence     │     • Retrieval Quality (40%)
│                    │     • Semantic Similarity (40%)
│                    │     • LLM Confidence (20%)
└────────────────────┘
     ↓
┌────────────────────┐
│  4. Safety         │  → Override rules:
│     Overrides      │     • Critical keywords → escalate
│                    │     • High priority → review minimum
└────────────────────┘
     ↓
  ┌──────┴──────┐
  │   ROUTER    │
  └──┬───┬────┬─┘
     │   │    │
  Auto Review Escalate
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- NVIDIA API key OR Groq API key
- 2GB disk space (for vector embeddings)

### Installation

```bash
# 1. Clone or create project directory
mkdir stripe-support-ai
cd stripe-support-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Set up environment variables
echo "NVIDIA_API_KEY=your_key_here" > .env
echo "GROQ_API_KEY=your_groq_key_here" >> .env

# 5. Run setup (scrape docs, create vector store)
python setup.py
```

### Running the Demo

```bash
# Terminal 1: Start FastAPI backend
cd backend
python main.py

# Terminal 2: Open frontend
# Simply open frontend/index.html in your browser
# Or use a simple HTTP server:
cd frontend
python -m http.server 8080
# Then navigate to http://localhost:8080
```

## 🎬 Demo Scenarios

The demo includes 3 curated tickets that showcase the escalation intelligence:

### Ticket 1: High Confidence (Auto-Resolve) ✅
- **Subject**: "API Key Not Working After Regeneration"
- **Issue**: Common authentication problem
- **Confidence**: ~0.94
- **Action**: Auto-resolved with step-by-step solution
- **Why**: Exact match in documentation, clear resolution path

### Ticket 2: Medium Confidence (Human Review) ⚠️
- **Subject**: "Intermittent 500 Errors on Webhook Endpoint"
- **Issue**: Complex debugging scenario
- **Confidence**: ~0.68
- **Action**: Draft response created, flagged for human review
- **Why**: Multiple possible causes, requires investigation

### Ticket 3: Low Confidence (Escalate) 🚨
- **Subject**: "Customer Claims Data Loss, Legal Involved"
- **Issue**: Critical severity + legal implications
- **Confidence**: ~0.15
- **Action**: Immediate escalation to senior support
- **Why**: Critical keywords detected, out of AI scope

## 🔧 Technical Implementation

### Confidence Calculation

```python
final_confidence = (
    0.4 * retrieval_quality +      # How relevant are retrieved docs?
    0.4 * semantic_similarity +    # Does response match docs?
    0.2 * llm_confidence          # LLM's self-assessment
)
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Vector Store | ChromaDB + sentence-transformers | Document retrieval |
| LLM | NVIDIA AI / Groq (Llama 3.1 70B) | Response generation |
| Workflow | LangGraph | State machine orchestration |
| API | FastAPI | RESTful backend |
| Frontend | HTML + Tailwind CSS | Demo interface |

### API Endpoints

```
GET  /                    # Health check
GET  /health              # Detailed system status
POST /tickets             # Process single ticket
POST /tickets/batch       # Batch processing
POST /demo/run            # Run curated demo
GET  /metrics             # System metrics
```

## 📁 Project Structure

```
stripe-support-ai/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── agents/
│   │   ├── retriever.py        # (implicit in workflow)
│   │   ├── generator.py        # LLM response generation
│   │   ├── confidence.py       # Multi-signal scoring
│   │   └── workflow.py         # LangGraph state machine
│   ├── data/
│   │   ├── scraper.py          # Stripe docs scraper
│   │   ├── tickets.py          # Demo ticket generator
│   │   └── vector_store.py     # ChromaDB manager
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   └── requirements.txt
├── frontend/
│   └── index.html              # Demo interface
├── data/
│   ├── stripe_docs/            # Scraped documentation
│   ├── demo_tickets.json       # Curated tickets
│   ├── test_tickets.json       # Test suite
│   └── chroma_db/              # Vector embeddings
├── setup.py                    # Initialization script
└── README.md
```

## 🎓 Learning Highlights

### What Makes This Portfolio-Worthy

1. **Production-Grade Architecture**: Multi-signal confidence scoring prevents hallucination
2. **Real-World Problem**: Solves actual customer support bottleneck (50% auto-resolution target)
3. **Sophisticated AI**: Beyond basic RAG - confidence calculation, safety overrides, LangGraph
4. **Measurable Impact**: Clear metrics (auto-resolve rate, accuracy, processing time)
5. **Safety-First Design**: Critical keyword detection, priority-based overrides

### Key Challenges Solved

- **Hallucination Prevention**: Multi-signal confidence + semantic similarity validation
- **Calibrated Confidence**: Combined signals instead of trusting LLM self-assessment
- **Edge Case Handling**: Safety overrides for legal/critical tickets
- **Production Readiness**: Error handling, logging, API design

## 📈 Performance Metrics

From demo run with curated tickets:

| Metric | Target | Actual |
|--------|--------|--------|
| Auto-Resolution Rate | 50% | 33% (1/3) |
| Routing Accuracy | 90%+ | 100% (3/3) |
| Avg Processing Time | <3s | ~2.1s |
| False Escalations | <5% | 0% |

*Note: Demo uses curated tickets. Real-world performance varies.*

## 🔮 Future Enhancements

- [ ] Fine-tuned classifier for faster ticket categorization
- [ ] Integration with Zendesk/Intercom webhooks
- [ ] A/B testing framework for confidence thresholds
- [ ] User feedback loop for continuous improvement
- [ ] Multilingual support
- [ ] Analytics dashboard with Grafana

## 📝 Interview Talking Points

When presenting this project:

1. **Problem**: "Support teams drown in repetitive tickets; 40% could be auto-resolved but companies fear AI errors"
   
2. **Solution**: "Multi-signal confidence scoring catches when LLM is uncertain - safer than pure LLM"

3. **Technical Depth**: "Combines retrieval quality, semantic similarity, and LLM confidence - not just trusting the model"

4. **Business Impact**: "50% auto-resolution means 20 hours/week saved for a team handling 200 tickets/week"

5. **Lessons Learned**: "LLMs will confidently hallucinate - you need validation layers like semantic similarity"

## 🐛 Troubleshooting

### Vector store not initialized
```bash
python setup.py  # Re-run setup
```

### LLM API errors
- Check `.env` file has valid API keys
- Verify internet connection
- Check API quota/credits

### Frontend can't connect to backend
- Ensure backend is running on port 8000
- Check CORS settings in main.py
- Try accessing http://localhost:8000/health directly

## 📄 License

MIT License - feel free to use for your portfolio!

## 🙏 Acknowledgments

- Stripe API Documentation
- LangChain & LangGraph communities
- NVIDIA & Groq for LLM APIs

---

**Built with ❤️ as a portfolio project demonstrating advanced AI engineering**

For questions or feedback, feel free to reach out!