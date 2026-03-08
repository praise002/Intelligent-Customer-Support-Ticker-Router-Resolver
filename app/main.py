from fastapi.responses import RedirectResponse
import jinja2
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.templating import Jinja2Templates
from starlette_admin.contrib.sqla import Admin, ModelView

from src.auth.routes import router as auth_router
from src.custom_logging import setup_logging
from src.profiles.routes import router as profile_router
from src.projects.routes import router as project_router
from src.messaging.routes import router as message_router
from src.db.main import async_engine
from src.db.models import User
from src.errors import register_all_errors
from src.middleware import register_middleware

description = """
## Overview
DEVSEARCH API is a powerful platform designed to connect developers around the world.

## Features
- **Collaboration**: Connect with other developers worldwide
- **Skill-sharing**: Showcase and discover technical skills
- **Project discovery**: Find interesting projects to contribute to
- **Profile management**: Create and manage developer profiles
- **Project listings**: Search and browse through projects
- **Ratings & Reviews**: Rate and review projects

## Technical Details
The API is built using modern best practices and RESTful principles, ensuring that it is intuitive and easy to integrate into your applications.
"""

version = "v1"

setup_logging()

app = FastAPI(
    title="DevSearch",
    description=description,
    version=version,
    docs_url=f"/api/{version}/docs",
    redoc_url=f"/api/{version}/redoc",
    contact={
        "name": "Devsearch admin",
        "email": "devsearch@gmail.com",
    },
    # lifespan=life_span
)

register_all_errors(app)

register_middleware(app)


env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
templates = Jinja2Templates(env=env)

# templates = Jinja2Templates(directory="templates")


app.mount("/static", StaticFiles(directory="static"), name="static")

# Create admin
admin = Admin(async_engine, title="Devsearch")

# Add view
# admin.add_view(ModelView(User, icon="fas fa-user"))

# Mount admin to your app
# admin.mount_to(app)

app.include_router(auth_router, prefix=f"/api/{version}/auth", tags=["Auth"])
app.include_router(profile_router, prefix=f"/api/{version}/profiles", tags=["Profiles"])
app.include_router(project_router, prefix=f"/api/{version}/projects", tags=["Projects"])
app.include_router(message_router, prefix=f"/api/{version}/messages", tags=["Messages"])

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
                "description": "Status of the response"
            },
            "message": {
                "type": "string",
                "example": "Validation error",
                "description": "Error message"
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
                            "description": "Field that failed validation"
                        },
                        "message": {
                            "type": "string",
                            "example": "value is not a valid email address",
                            "description": "Validation error message"
                        }
                    },
                    "required": ["field", "message"]
                }
            }
        },
        "required": ["status", "message", "errors"]
    }
    
    # Override the HTTPValidationError schema
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
    
    openapi_schema["components"]["schemas"]["HTTPValidationError"] = custom_validation_error
    
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

