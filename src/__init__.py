import logging
from contextlib import asynccontextmanager

from decouple import config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import RedirectResponse

from agents.classifier import TicketClassifier
from agents.llm_config import get_llm_client
from agents.workflow_graph import create_ticket_workflow
from custom_logging import setup_logging
from scripts.vector_store import VectorStoreManager
from src.tickets.routes import router as api_router
from src.utility import ConfidenceCalculator

version = "v1"

setup_logging()

app_state = {}

def initialize_components():
    """Initialize AI components (only once)"""
    # Initialize all heavy components once
    logging.info("Initializing AI components...")
    app_state["llm_client"] = get_llm_client()
    app_state["vector_store"] = VectorStoreManager()
    app_state["confidence_calculator"] = ConfidenceCalculator()
    app_state["ticket_classifier"] = TicketClassifier(
        api_token=config("NVIDIA_API_KEY_2")
    )
    app_state["workflow"] = create_ticket_workflow()
    logging.info("AI components initialized successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_components()
    print("Server is starting...")
    yield
    app_state.clear()
    print("Server has been stopped...")


app = FastAPI(
    title="Raenest Support AI",
    description="Intelligent customer support ticket router and resolver",
    version=version,
    docs_url=f"/api/{version}/docs",
    lifespan=lifespan,
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
    allowed_hosts=["*"],
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


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url=f"/api/{version}/docs")
