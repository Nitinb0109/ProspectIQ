
import asyncio
import logging
import os

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import Optional

from workflow.graph import run_prospect_workflow
from backend.history import (
    create_campaign,
    delete_campaign,
    get_campaign,
    get_conversation,
    get_oauth_return_to,
    list_inbox,
    list_campaigns,
    set_approval,
)
from backend.gmail import (
    disconnect,
    finish_oauth,
    gmail_status,
    process_pubsub,
    send_campaign_email,
    start_oauth,
    start_watch,
    sync_mailbox,
)

app = FastAPI(
    title="ProspectIQ API",
    description="AI-powered personalized B2B outreach",
    version="1.0.0"
)

logger = logging.getLogger("prospectiq.api")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = [{"loc": error.get("loc", []), "msg": error.get("msg", "Invalid request"), "type": error.get("type", "value_error")} for error in exc.errors()]
    logger.warning("Request validation failed: method=%s path=%s errors=%s", request.method, request.url.path, errors)
    return JSONResponse(status_code=422, content={"detail": errors})

# Allow requests from React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://prospect-iq-ruby.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def start_gmail_polling():
    async def poll():
        while True:
            await asyncio.sleep(300)
            try:
                sync_mailbox()
            except Exception as error:
                print(f"Gmail sync failed: {error}")

    asyncio.create_task(poll())


class OutreachRequest(BaseModel):
    prospect_name: str = Field(min_length=1, max_length=150)
    designation: str = Field(min_length=1, max_length=150)
    company: str = Field(min_length=1, max_length=150)
    company_website: Optional[str] = None
    prospect_email: str = Field(min_length=3, max_length=320)

    sender_company: str = Field(min_length=1, max_length=150)
    product_or_service: str = Field(min_length=1, max_length=500)
    value_proposition: str = Field(min_length=1, max_length=1000)


class ApprovalRequest(BaseModel):
    approved: bool


class SendEmailRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)
    idempotency_key: str = Field(min_length=16, max_length=120)


@app.get("/")
def home():
    return {"message": "Welcome to ProspectIQ API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/outreach/generate")
def generate_outreach(request: OutreachRequest):
    try:
        prospect_data = request.model_dump()

        result = run_prospect_workflow(prospect_data)

        response = {
            "success": True,
            "research": result["research_data"],
            "signals": result["analyzed_data"],
            "email": result["email_data"],
            "review": result["review_result"]
        }
        response["history_id"] = create_campaign(response, prospect_data)
        return response

    except Exception as e:
        print(f"Outreach generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Outreach generation failed. Please check the backend logs."
        )


@app.get("/api/history")
def history_list(
    search: str = Query(default="", max_length=150),
    status: str = Query(default="all", pattern="^(all|sent|failed|replied|awaiting_approval|ai_review_failed|approved)$"),
):
    items = list_campaigns(search=search, status=status)
    return {"items": items, "total": len(items)}


@app.get("/api/history/{campaign_id}")
def history_detail(campaign_id: int):
    campaign = get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


@app.patch("/api/history/{campaign_id}/approval")
def update_history_approval(campaign_id: int, request: ApprovalRequest):
    if not request.approved:
        raise HTTPException(status_code=400, detail="Only explicit approval is supported.")
    if not set_approval(campaign_id, request.approved):
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return {"success": True, "approval_status": "approved"}


@app.delete("/api/history/{campaign_id}")
def remove_history_campaign(campaign_id: int):
    if not delete_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return {"success": True}


@app.post("/api/history/{campaign_id}/send")
def send_history_campaign(campaign_id: int, request: SendEmailRequest):
    try:
        result = send_campaign_email(campaign_id, request.subject, request.body, request.idempotency_key)
        return {"success": True, **result}
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except Exception as error:
        logger.exception("Gmail send failed: campaign_id=%s type=%s", campaign_id, type(error).__name__)
        raise HTTPException(status_code=502, detail="Gmail could not send this message.") from error


@app.get("/api/gmail/status")
def gmail_connection_status():
    return gmail_status()


@app.get("/api/gmail/connect")
def gmail_connect(return_to: Optional[str] = Query(default=None)):
    try:
        return RedirectResponse(start_oauth(return_to))
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/api/gmail/callback")
def gmail_callback(code: str = "", state: str = "", error: str = "", error_description: str = "", error_uri: str = ""):
    frontend = get_oauth_return_to(state) or os.getenv("FRONTEND_URL", "http://localhost:5173/")
    frontend = frontend.rstrip("/")
    if error:
        logger.warning("Gmail OAuth was declined by Google: error=%s description=%s uri=%s", error, error_description[:500], error_uri[:500])
        return RedirectResponse(f"{frontend}/?gmail=denied#new")
    try:
        finish_oauth(code, state)
        logger.info("Gmail OAuth callback returned success to frontend=%s", frontend)
        return RedirectResponse(f"{frontend}/?gmail=connected#new")
    except Exception as callback_error:
        logger.error("Gmail OAuth callback failed after the detailed Gmail error above: type=%s", type(callback_error).__name__)
        return RedirectResponse(f"{frontend}/?gmail=error#new")


@app.delete("/api/gmail/connection")
def gmail_disconnect():
    disconnect()
    return {"success": True}


@app.post("/api/gmail/watch")
def gmail_watch():
    try:
        return {"success": True, **start_watch()}
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/api/gmail/sync")
def gmail_sync():
    try:
        return sync_mailbox()
    except Exception as error:
        raise HTTPException(status_code=502, detail="Gmail synchronization failed.") from error


@app.post("/api/gmail/webhook")
def gmail_webhook(payload: dict, x_gmail_webhook_token: Optional[str] = Header(default=None), token: Optional[str] = Query(default=None)):
    configured_token = os.getenv("GMAIL_PUBSUB_TOKEN")
    if configured_token and configured_token not in {x_gmail_webhook_token, token}:
        raise HTTPException(status_code=401, detail="Invalid webhook token.")
    try:
        return process_pubsub(payload)
    except Exception as error:
        raise HTTPException(status_code=502, detail="Gmail notification processing failed.") from error


@app.get("/api/inbox")
def inbox():
    return {"items": list_inbox()}


@app.get("/api/history/{campaign_id}/conversation")
def conversation(campaign_id: int):
    return {"items": get_conversation(campaign_id)}
