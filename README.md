# Intelligent Customer Support Ticket Router & Resolver

An advanced AI-powered customer support system that automatically classifies, resolves, and routes support tickets using multi-signal confidence scoring and LangGraph workflows.

## 🎯 Key Features

- **Multi-Signal Confidence Scoring**: Combines retrieval quality, semantic similarity, and LLM confidence
- **Smart Escalation Logic**: Auto-resolve (>85%), Human Review (60-85%), Escalate (<60%)
- **RAG-Powered Responses**: Vector search through Raenest Support documentation
- **Safety Overrides**: Critical keyword detection and priority-based routing
- **LangGraph Workflow**: State machine for reliable ticket processing
- **Real-time Demo**: Interactive UI showing all three escalation paths

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- NVIDIA API key OR Groq API key
- 2GB disk space (for vector embeddings)

### Installation

```bash
# 1. Clone repository
git clone <url>

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env

# 5. Run setup (scrape docs, create vector store)
# python setup.py
```

### Running the Demo

```bash
# Terminal 1: Start FastAPI backend
cd backend
uvicorn src:app --reload

# Terminal 2: Open frontend
cd frontend
npm run dev
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
| Frontend | React + Tailwind CSS | Demo interface |


### Key Challenges Solved

- **Hallucination Prevention**: Multi-signal confidence + semantic similarity validation
- **Calibrated Confidence**: Combined signals instead of trusting LLM self-assessment
- **Edge Case Handling**: Safety overrides for legal/critical tickets
- **Production Readiness**: Error handling, logging, API design

## 📈 Performance Metrics

From demo run with curated tickets:

| Metric | Target | Actual |
|--------|--------|--------|
| Auto-Resolution Rate | 60% | 33% (1/3) |
| Routing Accuracy | 90%+ | 100% (3/3) |
| Avg Processing Time | <3s | ~2.1s |
| False Escalations | <5% | 0% |

*Note: Demo uses curated tickets. Real-world performance varies.*

## 🔮 Future Enhancements
- [ ] User feedback loop for continuous improvement
- [ ] Analytics dashboard with Grafana

## 🐛 Troubleshooting

### Vector store not initialized
```bash
# TODO:
# python setup.py  # Re-run setup
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

**Built with ❤️ demonstrating advanced AI engineering**