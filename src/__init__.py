import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import RedirectResponse

from custom_logging import setup_logging
from src.agents.registry import get_registry
from src.tickets.routes import router as api_router

version = "v1"

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Server is starting...")

    registry = get_registry()  # first call → builds everything
    # subsequent reloads → returns cache instantly
    app.state.llm_client = registry["llm_client"]
    app.state.vector_store = registry["vector_store"]
    app.state.confidence_calculator = registry["confidence_calculator"]
    app.state.ticket_classifier = registry["ticket_classifier"]
    app.state.workflow = registry["workflow"]

    logging.info("Server is ready.")
    yield
    logging.info("Server has been stopped.")


app = FastAPI(
    title="Raenest Support AI",
    description="Intelligent customer support ticket router and resolver",
    version=version,
    docs_url=f"/api/{version}/docs",
    lifespan=lifespan,
)

origins = ["http://localhost:5173", "http://127.0.0.1:5500"]

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

app.include_router(api_router, prefix=f"/api/{version}", tags=["Tickets"])


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
