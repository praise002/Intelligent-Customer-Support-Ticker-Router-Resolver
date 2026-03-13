import httpx
from decouple import config
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
# from google_recaptcha_flask import ReCaptcha

# --- Configuration ---
# In production, store credentials in environment variables
ZENDESK_SUBDOMAIN = config("ZENDESK_SUBDOMAIN", default="YOUR_ZENDESK_SUBDOMAIN")
ZENDESK_USER_EMAIL = config("ZENDESK_USER_EMAIL", default="YOUR_ZENDESK_EMAIL_ADDRESS")
ZENDESK_API_TOKEN = config("ZENDESK_API_TOKEN")
RECAPTCHA_SITE_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
RECAPTCHA_SECRET_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"

# recaptcha = ReCaptcha(app)
# app.config.update(
#     dict(
#         GOOGLE_RECAPTCHA_ENABLED=True,
#         GOOGLE_RECAPTCHA_SITE_KEY=RECAPTCHA_SITE_KEY,
#         GOOGLE_RECAPTCHA_SECRET_KEY=RECAPTCHA_SECRET_KEY,
#         GOOGLE_RECAPTCHA_LANGUAGE="en",
#     )
# )
# recaptcha.init_app(app)


# --- FastAPI App ---
app = FastAPI(
    title="Stripe Support AI Backend",
    description="Handles support ticket creation via a web form.",
    version="1.0.0",
)

# --- HTML Form ---
# This is a simple HTML form for the frontend.
# In a real application, you would serve this from a separate file or a frontend framework.
HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Submit a Support Request</title>
    <style>
        body { font-family: sans-serif; margin: 2em; }
        label { display: block; margin-top: 1em; }
        input, textarea { width: 300px; padding: 0.5em; }
        button { margin-top: 1em; padding: 0.5em 1em; }
    </style>
</head>
<body>
    <h1>Submit a Support Request</h1>
    <form action="/submit" method="post">
        <div>
            <label for="subject">Subject</label>
            <input type="text" id="subject" name="subject" required>
        </div>
        <div>
            <label for="description">Description</label>
            <textarea id="description" name="description" rows="6" required></textarea>
        </div>
        <div>
            <label for="name">Name</label>
            <input type="text" id="name" name="name" required>
        </div>
        <div>
            <label for="email">Email</label>
            <input type="email" id="email" name="email" required>
            
        </div>
        <div>
            <button type="submit">Submit</button>
        </div>
    </form>
</body>
</html>
"""

# --- API Endpoints ---


@app.get("/", response_class=HTMLResponse)
async def get_form():
    """Serves the HTML form to the user."""
    return HTML_FORM


@app.post("/submit")
async def submit_form(
    subject: str = Form(),
    description: str = Form(),
    name: str = Form(),
    email: str = Form(),
):
    """
    Handles form submission, creates a Zendesk ticket, and returns the result.
    """
    zendesk_url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/requests.json"

    # Prepare the data for the Zendesk API
    data = {
        "request": {
            "subject": subject,
            "comment": {"body": description},
            "requester": {"name": name, "email": email},
        }
    }

    auth = (f"{ZENDESK_USER_EMAIL}/token", ZENDESK_API_TOKEN)

    # Use an async HTTP client for non-blocking requests
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(zendesk_url, json=data, auth=auth)
            response.raise_for_status()  # Raise an exception for bad responses (4xx or 5xx)

            return {
                "message": "Form submitted successfully",
                "ticket_data": response.json(),
            }

        except httpx.HTTPStatusError as e:
            # More specific error for client/server issues
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error submitting to Zendesk: {e.response.text}",
            )
        except httpx.RequestError as e:
            # More specific error for network issues
            raise HTTPException(
                status_code=500,
                detail=f"Network error while contacting Zendesk: {str(e)}",
            )


# To run this application:
# 1. Install FastAPI and an ASGI server: pip install fastapi "uvicorn[standard]" httpx python-decouple
# 2. Save the code as main.py
# 3. Run the server: uvicorn main:app --reload --port 3000
