from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import RedirectResponse

from agents.confidence import ConfidenceCalculator
from agents.generator import LLMGenerator
from agents.workflow import TicketWorkflow
from custom_logging import setup_logging
from scripts.vector_store import VectorStoreManager
from .routes import router as api_router

version = "v1"

setup_logging()

app = FastAPI(
    title="Stripe Support AI",
    description="Intelligent customer support ticket router and resolver",
    version=version,
    docs_url=f"/api/{version}/docs",
)

origins = ["http://localhost:5173"]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # cross-origin for frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    # allowed_hosts=["localhost", "127.0.0.1", ".ngrok-free.app"],
    allowed_hosts=["*"]
)

app.include_router(api_router, prefix=f"/api/{version}")


# Custom OpenAPI schema to override 422 validation error response
def custom_openapi():
    """
    Customize the OpenAPI schema to show our custom validation error format
    in Swagger docs instead of FastAPI's default format.
    """
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    # Generate the default OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Define custom validation error schema
    custom_validation_error = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "example": "error",
                "description": "Status of the response",
            },
            "message": {
                "type": "string",
                "example": "Validation error",
                "description": "Error message",
            },
            "errors": {
                "type": "array",
                "description": "List of validation errors",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "string",
                            "example": "email",
                            "description": "Field that failed validation",
                        },
                        "message": {
                            "type": "string",
                            "example": "value is not a valid email address",
                            "description": "Validation error message",
                        },
                    },
                    "required": ["field", "message"],
                },
            },
        },
        "required": ["status", "message", "errors"],
    }

    # Override the HTTPValidationError schema
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}

    openapi_schema["components"]["schemas"][
        "HTTPValidationError"
    ] = custom_validation_error

    # Also remove the default ValidationError schema as it's no longer needed
    openapi_schema["components"]["schemas"].pop("ValidationError", None)

    # Cache the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Override FastAPI's openapi method
app.openapi = custom_openapi


def initialize_components():
    """Initialize AI components (only once)"""
    global vector_store, llm_generator, confidence_calc, workflow

    if workflow is None:
        print("Initializing AI components...")
        vector_store = VectorStoreManager()
        llm_generator = LLMGenerator()
        confidence_calc = ConfidenceCalculator()
        workflow = TicketWorkflow(vector_store, llm_generator, confidence_calc)
        print("✅ Components initialized")


@asynccontextmanager
async def life_span(app: FastAPI):
    await initialize_components()
    print("Server is starting...")
    yield
    print("Server has been stopped...")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url=f"/api/{version}/docs")


# Flow
# A customer sends an email
# A ticket is generated with an automatic message
# The AI responds or it is routed to human in the loop - the customer
# is informed if it is AI generated and if it is being routed to human
# See how Turing does theirs
# All the RAG stuff flow
# The fastapi stuff flow

# Gmail INBOX (unread)
#     │
#     ▼
# IMAP/Gmail API — fetch raw email
#     │
#     ▼
# Parser — IncomingEmail(external_id, sender, subject, body, timestamp)
#     │
#     ▼
# Mapper — TicketInput(ticket_id, subject, description, priority, category)
#     │
#     ▼
# workflow.process_ticket()  ──── ChromaDB (RAG)
#     │                      ──── LLM (Groq/NVIDIA)
#     ▼
# TicketResult { action, confidence, llm_response }
#     │
#     ├── auto_resolve  →  Send reply email back to sender
#     ├── human_review  →  Log + forward to human
#     └── escalate      →  Alert + log HIGH priority

# setup db