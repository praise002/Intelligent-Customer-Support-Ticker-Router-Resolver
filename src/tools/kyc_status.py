from pydantic import BaseModel, Field

# ---------- Mock data (simulates Raenest's internal DB) ----------
# In reality, this would be a database table synced via Veriff webhooks.
MOCK_KYC_STATUSES = {
    "ada.nnamdi@yahoo.com": {
        "status": "pending_review",  # pending_review, approved, declined, resubmission_requested
        "last_updated": "2026-03-19T10:15:00Z",
        "veriff_session_id": "vs_abc123",
        "notes": "User uploaded passport and utility bill. Awaiting manual review.",
    },
    "chidi.okafor@gmail.com": {
        "status": "approved",
        "last_updated": "2026-03-15T08:30:00Z",
        "veriff_session_id": "vs_xyz789",
        "notes": "Auto-approved via Veriff.",
    },
    "blessing.trade@gmail.com": {
        "status": "declined",
        "last_updated": "2026-03-10T14:20:00Z",
        "veriff_session_id": "vs_def456",
        "notes": "Identity document could not be verified.",
    },
}


class KYCStatusInput(BaseModel):
    email: str = Field(description="Customer's email address (as stored in Raenest).")
    refresh_from_veriff: bool = Field(
        default=False,
        description="If True, pretend to call Veriff API to get the latest status (still mocks).",
    )


def check_kyc_status(email: str, refresh_from_veriff: bool = False) -> dict:
    """
    Returns the current KYC verification status for a given user.
    If `refresh_from_veriff` is True, simulates a real-time call to Veriff.
    """
    # Simulate calling Veriff API if requested
    if refresh_from_veriff:
        # In real code: response = veriff_client.get_session(session_id)
        # Here we just pretend to get fresh data
        if email in MOCK_KYC_STATUSES:
            # No actual change for the mock
            pass
        else:
            return {"error": f"No KYC record found for {email}."}

    # Fetch from mock DB
    record = MOCK_KYC_STATUSES.get(email)
    if not record:
        return {"error": f"No KYC record found for {email}."}

    return {
        "status": record["status"],
        "last_updated": record["last_updated"],
        "source": (
            "veriff_webhook_sync" if not refresh_from_veriff else "veriff_api_realtime"
        ),
        "notes": record["notes"],
    }
