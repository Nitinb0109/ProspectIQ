"""Server-side Gmail OAuth, sending, and reply synchronization."""

import base64
import json
import logging
import os
import re
import secrets
from email import message_from_bytes
from email.header import decode_header, make_header
from email.mime.text import MIMEText
from typing import Any

import requests
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.history import (
    claim_send,
    complete_send,
    fail_send,
    find_campaign_by_thread,
    get_campaign_row,
    get_gmail_account,
    now_iso,
    save_gmail_account,
    save_incoming_message,
    save_oauth_state,
    save_outgoing_message,
    consume_oauth_state,
    update_gmail_sync,
    delete_gmail_account,
)

load_dotenv()

logger = logging.getLogger("prospectiq.gmail")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def _setting(name: str) -> str:
    return os.getenv(name, "").strip()


def _safe_error(error: Exception) -> str:
    """Return useful OAuth diagnostics without logging credentials or codes."""
    message = str(error)
    message = re.sub(r"(?i)(access_token|refresh_token|client_secret|authorization_code|code)=([^&\s]+)", r"\1=[redacted]", message)
    message = re.sub(r"(?i)(['\"](access_token|refresh_token|client_secret|authorization_code|code)['\"]\s*:\s*)['\"][^'\"]+['\"]", r"\1[redacted]", message)
    return message[:1000] or error.__class__.__name__


def _client_config() -> dict[str, Any]:
    client_id = _setting("GOOGLE_CLIENT_ID")
    client_secret = _setting("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
    return {"web": {"client_id": client_id, "client_secret": client_secret, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "redirect_uris": [_setting("GOOGLE_REDIRECT_URI")]}}


def _encryption() -> Fernet:
    key = _setting("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY must be configured before connecting Gmail.")
    return Fernet(key.encode())


def _frontend_redirect(result: str) -> str:
    base = _setting("FRONTEND_URL") or "http://localhost:5173/"
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}gmail={result}#new"


def _allowed_frontend_origin(origin: str | None) -> str:
    configured = (_setting("FRONTEND_URL") or "http://localhost:5173/").rstrip("/")
    allowed = {configured, "http://localhost:5173", "http://127.0.0.1:5173"}
    return origin.rstrip("/") if origin and origin.rstrip("/") in allowed else configured


def start_oauth(return_to: str | None = None) -> str:
    redirect_uri = _setting("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        raise RuntimeError("GOOGLE_REDIRECT_URI must be configured before connecting Gmail.")
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=secrets.token_urlsafe(32))
    flow.redirect_uri = redirect_uri
    authorization_url, state = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
    save_oauth_state(state, _allowed_frontend_origin(return_to), flow.code_verifier or "")
    logger.info("Gmail OAuth authorization URL created: redirect_uri=%s scopes=%s", redirect_uri, ",".join(SCOPES))
    return authorization_url


def finish_oauth(code: str, state: str) -> tuple[str, str | None]:
    oauth_state = consume_oauth_state(state)
    if oauth_state is None:
        logger.error("Gmail OAuth failed at state validation: state was missing or expired")
        raise RuntimeError("The Gmail authorization state is invalid or expired.")
    return_to = oauth_state["return_to"]
    code_verifier = oauth_state["code_verifier"]
    redirect_uri = _setting("GOOGLE_REDIRECT_URI")
    try:
        flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=state)
        flow.redirect_uri = redirect_uri
        if code_verifier:
            flow.code_verifier = code_verifier
        logger.info("Gmail OAuth callback accepted; exchanging authorization code: redirect_uri=%s pkce_verifier_restored=%s", redirect_uri, bool(code_verifier))
        flow.fetch_token(code=code)
    except Exception as error:
        logger.error("Gmail OAuth token exchange failed: type=%s message=%s", type(error).__name__, _safe_error(error))
        raise

    try:
        credentials = flow.credentials
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        profile = service.users().getProfile(userId="me").execute()
    except Exception as error:
        logger.error("Gmail OAuth token exchange succeeded but Gmail profile lookup failed: type=%s message=%s", type(error).__name__, _safe_error(error))
        raise

    try:
        encrypted = _encryption().encrypt(credentials.to_json().encode()).decode()
        save_gmail_account(profile["emailAddress"], encrypted, profile.get("historyId"))
    except Exception as error:
        logger.error("Gmail credentials were retrieved but could not be stored: type=%s message=%s", type(error).__name__, _safe_error(error))
        raise
    if _setting("GMAIL_PUBSUB_TOPIC"):
        try:
            start_watch()
        except Exception as watch_error:
            print(f"Gmail watch setup skipped: {watch_error}")
    logger.info("Gmail OAuth completed successfully for account=%s", profile["emailAddress"])
    return profile["emailAddress"], return_to


def _credentials() -> tuple[Credentials, dict[str, Any]]:
    account = get_gmail_account()
    if not account:
        raise RuntimeError("Connect a Gmail account before using email features.")
    token_data = json.loads(_encryption().decrypt(account["encrypted_credentials"].encode()).decode())
    credentials = Credentials.from_authorized_user_info(token_data, SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        refreshed = credentials.to_json()
        encrypted = _encryption().encrypt(refreshed.encode()).decode()
        save_gmail_account(account["email"], encrypted, account["history_id"], account["watch_expiration"])
    return credentials, account


def gmail_status() -> dict[str, Any]:
    account = get_gmail_account()
    return {"connected": bool(account), "email": account["email"] if account else None, "last_sync_at": account.get("last_sync_at") if account else None}


def disconnect() -> None:
    account = get_gmail_account()
    if account:
        try:
            credentials, _ = _credentials()
            if credentials.token:
                requests.post("https://oauth2.googleapis.com/revoke", params={"token": credentials.token}, timeout=10)
        except Exception:
            pass
    delete_gmail_account()


def send_campaign_email(campaign_id: int, subject: str, body: str, idempotency_key: str) -> dict[str, Any]:
    row = get_campaign_row(campaign_id)
    if row is None:
        raise LookupError("Campaign not found.")
    if not row["review_approved"]:
        raise PermissionError("The campaign must pass AI review before it can be sent.")
    if row["approval_status"] != "approved":
        raise PermissionError("Explicit human approval is required before sending.")
    if not row["prospect_email"]:
        raise ValueError("Add a prospect email address before sending.")
    claim = claim_send(campaign_id, idempotency_key, subject.strip(), body.strip())
    if claim is None: raise LookupError("Campaign not found.")
    if claim.get("already_sent"): return {"sent": True, **claim}
    if claim.get("in_progress"): raise RuntimeError("This campaign is already being sent.")
    try:
        credentials, account = _credentials()
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        message = MIMEText(body.strip(), "plain", "utf-8")
        message["to"] = row["prospect_email"]
        message["subject"] = subject.strip()
        message["from"] = account["email"]
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        message_id = sent["id"]
        thread_id = sent.get("threadId", "")
        complete_send(campaign_id, message_id, thread_id)
        save_outgoing_message(campaign_id, message_id, thread_id, account["email"], row["prospect_email"], subject.strip(), body.strip())
        return {"sent": True, "message_id": message_id, "thread_id": thread_id, "sent_at": now_iso()}
    except Exception:
        fail_send(campaign_id)
        raise


def _decode_header(value: str) -> str:
    try: return str(make_header(decode_header(value or "")))
    except Exception: return value or ""


def _message_body(payload: dict[str, Any]) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"] + "===").decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            return _message_body(part)
        nested = _message_body(part)
        if nested: return nested
    return ""


def _sync_one_account() -> int:
    credentials, account = _credentials()
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    start_history_id = account.get("history_id")
    if not start_history_id:
        profile = service.users().getProfile(userId="me").execute()
        update_gmail_sync(profile.get("historyId"))
        return 0
    try:
        response = service.users().history().list(userId="me", startHistoryId=start_history_id, historyTypes=["messageAdded"], labelId="INBOX").execute()
    except HttpError as error:
        if error.resp.status == 404:
            profile = service.users().getProfile(userId="me").execute()
            update_gmail_sync(profile.get("historyId"))
            return 0
        raise
    message_ids = []
    for record in response.get("history", []):
        for added in record.get("messagesAdded", []): message_ids.append(added.get("message", {}).get("id"))
        for message in record.get("messages", []): message_ids.append(message.get("id"))
    saved = 0
    for message_id in {value for value in message_ids if value}:
        message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        thread_id = message.get("threadId", "")
        campaign_id = find_campaign_by_thread(thread_id)
        if not campaign_id: continue
        headers = {item["name"].lower(): _decode_header(item.get("value", "")) for item in message.get("payload", {}).get("headers", [])}
        saved += int(save_incoming_message({"campaign_id": campaign_id, "message_id": message_id, "thread_id": thread_id, "sender": headers.get("from", ""), "recipient": headers.get("to", ""), "subject": headers.get("subject", ""), "body": _message_body(message.get("payload", {})), "message_at": headers.get("date", ""), "headers": headers}))
    update_gmail_sync(response.get("historyId", start_history_id))
    return saved


def sync_mailbox() -> dict[str, Any]:
    account = get_gmail_account()
    if not account: return {"connected": False, "saved_replies": 0}
    return {"connected": True, "saved_replies": _sync_one_account()}


def start_watch() -> dict[str, Any]:
    topic = _setting("GMAIL_PUBSUB_TOPIC")
    if not topic: raise RuntimeError("GMAIL_PUBSUB_TOPIC is not configured.")
    credentials, account = _credentials()
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    response = service.users().watch(userId="me", body={"topicName": topic, "labelIds": ["INBOX"], "labelFilterBehavior": "INCLUDE"}).execute()
    save_gmail_account(account["email"], account["encrypted_credentials"], response.get("historyId"), response.get("expiration"))
    return response


def process_pubsub(payload: dict[str, Any]) -> dict[str, Any]:
    message = payload.get("message", {})
    encoded = message.get("data")
    if encoded:
        decoded = base64.urlsafe_b64decode(encoded + "===")
        notification = json.loads(decoded.decode())
        if notification.get("emailAddress") and get_gmail_account() and notification["emailAddress"] != get_gmail_account()["email"]:
            return {"ignored": True}
    return sync_mailbox()
