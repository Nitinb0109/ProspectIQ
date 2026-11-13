"""SQLite persistence for campaigns, Gmail accounts, and conversations."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATABASE_PATH = DATA_DIR / "prospectiq.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def init_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_name TEXT NOT NULL,
                company TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                review_score INTEGER,
                review_approved INTEGER NOT NULL DEFAULT 0,
                approval_status TEXT NOT NULL DEFAULT 'pending',
                email_subject TEXT NOT NULL DEFAULT '',
                payload TEXT NOT NULL
            )
            """
        )
        columns = _columns(connection, "campaigns")
        additions = {
            "designation": "TEXT NOT NULL DEFAULT ''",
            "prospect_email": "TEXT NOT NULL DEFAULT ''",
            "sender_company": "TEXT NOT NULL DEFAULT ''",
            "product_or_service": "TEXT NOT NULL DEFAULT ''",
            "value_proposition": "TEXT NOT NULL DEFAULT ''",
            "final_subject": "TEXT NOT NULL DEFAULT ''",
            "final_body": "TEXT NOT NULL DEFAULT ''",
            "approval_timestamp": "TEXT",
            "gmail_message_id": "TEXT",
            "gmail_thread_id": "TEXT",
            "sending_status": "TEXT NOT NULL DEFAULT 'not_sent'",
            "sent_at": "TEXT",
            "reply_status": "TEXT NOT NULL DEFAULT 'not_replied'",
            "last_updated": "TEXT",
            "idempotency_key": "TEXT",
        }
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE campaigns ADD COLUMN {name} {definition}")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_campaigns_idempotency_key ON campaigns(idempotency_key) WHERE idempotency_key IS NOT NULL")

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS gmail_accounts (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                email TEXT NOT NULL,
                encrypted_credentials TEXT NOT NULL,
                history_id TEXT,
                watch_expiration TEXT,
                connected_at TEXT NOT NULL,
                last_sync_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS email_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                gmail_message_id TEXT NOT NULL UNIQUE,
                gmail_thread_id TEXT NOT NULL,
                direction TEXT NOT NULL CHECK (direction IN ('outgoing', 'incoming')),
                sender TEXT NOT NULL DEFAULT '',
                recipient TEXT NOT NULL DEFAULT '',
                subject TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                message_at TEXT,
                raw_headers TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                return_to TEXT NOT NULL DEFAULT '',
                code_verifier TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        oauth_columns = _columns(connection, "oauth_states")
        if "return_to" not in oauth_columns:
            connection.execute("ALTER TABLE oauth_states ADD COLUMN return_to TEXT NOT NULL DEFAULT ''")
        if "code_verifier" not in oauth_columns:
            connection.execute("ALTER TABLE oauth_states ADD COLUMN code_verifier TEXT NOT NULL DEFAULT ''")


def create_campaign(payload: dict[str, Any], request_data: dict[str, Any]) -> int:
    research = payload.get("research", {})
    prospect = research.get("prospect", {})
    email = payload.get("email", {})
    review = payload.get("review", {})
    generated_at = now_iso()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO campaigns (
                prospect_name, designation, company, prospect_email,
                sender_company, product_or_service, value_proposition,
                generated_at, review_score, review_approved, email_subject,
                final_subject, final_body, payload, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prospect.get("name", request_data.get("prospect_name", "Unknown prospect")),
                request_data.get("designation", prospect.get("role", "")),
                prospect.get("company", request_data.get("company", "Unknown company")),
                request_data.get("prospect_email", ""),
                request_data.get("sender_company", ""),
                request_data.get("product_or_service", ""),
                request_data.get("value_proposition", ""),
                generated_at,
                review.get("quality_score"),
                int(bool(review.get("approved"))),
                email.get("subject", ""),
                email.get("subject", ""),
                email.get("email_body", ""),
                json.dumps(payload, ensure_ascii=False),
                generated_at,
            ),
        )
        return int(cursor.lastrowid)


def _campaign_summary(row: sqlite3.Row) -> dict[str, Any]:
    payload = json.loads(row["payload"])
    status = row["sending_status"]
    if row["reply_status"] == "replied":
        status = "replied"
    elif status == "not_sent":
        if row["approval_status"] == "approved":
            status = "approved"
        else:
            status = "awaiting_approval" if row["review_approved"] else "ai_review_failed"
    return {
        "id": row["id"],
        "prospect_name": row["prospect_name"],
        "designation": row["designation"],
        "company": row["company"],
        "prospect_email": row["prospect_email"],
        "generated_at": row["generated_at"],
        "sent_at": row["sent_at"],
        "review_score": row["review_score"],
        "review_approved": bool(row["review_approved"]),
        "approval_status": row["approval_status"],
        "sending_status": row["sending_status"],
        "reply_status": row["reply_status"],
        "status": status,
        "email_subject": row["email_subject"],
        "source_count": len(payload.get("research", {}).get("sources", [])),
    }


def list_campaigns(search: str = "", status: str = "all") -> list[dict[str, Any]]:
    query = "SELECT * FROM campaigns"
    clauses: list[str] = []
    parameters: list[str] = []
    if search.strip():
        clauses.append("(prospect_name LIKE ? OR company LIKE ? OR prospect_email LIKE ?)")
        term = f"%{search.strip()}%"
        parameters.extend([term, term, term])
    valid_statuses = {"sent", "failed", "replied", "awaiting_approval", "ai_review_failed", "approved"}
    if status in valid_statuses:
        if status == "replied": clauses.append("reply_status = 'replied'")
        elif status == "sent": clauses.append("sending_status = 'sent' AND reply_status != 'replied'")
        elif status == "failed": clauses.append("sending_status = 'failed'")
        elif status == "approved": clauses.append("approval_status = 'approved'")
        elif status == "awaiting_approval": clauses.append("sending_status = 'not_sent' AND review_approved = 1")
        elif status == "ai_review_failed": clauses.append("sending_status = 'not_sent' AND review_approved = 0")
    if clauses: query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY generated_at DESC"
    with _connect() as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [_campaign_summary(row) for row in rows]


def get_campaign(campaign_id: int) -> Optional[dict[str, Any]]:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if row is None: return None
    campaign = json.loads(row["payload"])
    campaign.update({"id": row["id"], "history_id": row["id"], "generated_at": row["generated_at"], "approval_status": row["approval_status"], "prospect_email": row["prospect_email"], "designation": row["designation"], "sender_company": row["sender_company"], "sending_status": row["sending_status"], "sent_at": row["sent_at"], "reply_status": row["reply_status"], "gmail_message_id": row["gmail_message_id"], "gmail_thread_id": row["gmail_thread_id"]})
    return campaign


def get_campaign_row(campaign_id: int) -> Optional[sqlite3.Row]:
    with _connect() as connection:
        return connection.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()


def set_approval(campaign_id: int, approved: bool) -> bool:
    with _connect() as connection:
        cursor = connection.execute("UPDATE campaigns SET approval_status = ?, approval_timestamp = ?, last_updated = ? WHERE id = ?", ("approved" if approved else "pending", now_iso() if approved else None, now_iso(), campaign_id))
        return cursor.rowcount > 0


def claim_send(campaign_id: int, idempotency_key: str, subject: str, body: str) -> Optional[dict[str, Any]]:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if row is None: return None
        if row["sending_status"] == "sent": return {"already_sent": True, "message_id": row["gmail_message_id"], "thread_id": row["gmail_thread_id"]}
        if row["sending_status"] == "sending": return {"in_progress": True}
        cursor = connection.execute("UPDATE campaigns SET idempotency_key = ?, final_subject = ?, final_body = ?, sending_status = 'sending', last_updated = ? WHERE id = ? AND sending_status != 'sent' AND sending_status != 'sending'", (idempotency_key, subject, body, now_iso(), campaign_id))
        if cursor.rowcount == 0: return {"in_progress": True}
        return {"already_sent": False}


def complete_send(campaign_id: int, message_id: str, thread_id: str) -> None:
    timestamp = now_iso()
    with _connect() as connection:
        connection.execute("UPDATE campaigns SET sending_status = 'sent', sent_at = ?, gmail_message_id = ?, gmail_thread_id = ?, last_updated = ? WHERE id = ?", (timestamp, message_id, thread_id, timestamp, campaign_id))


def fail_send(campaign_id: int) -> None:
    with _connect() as connection:
        connection.execute("UPDATE campaigns SET sending_status = 'failed', last_updated = ? WHERE id = ?", (now_iso(), campaign_id))


def delete_campaign(campaign_id: int) -> bool:
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
        return cursor.rowcount > 0


def save_outgoing_message(campaign_id: int, message_id: str, thread_id: str, sender: str, recipient: str, subject: str, body: str) -> None:
    with _connect() as connection:
        connection.execute("INSERT OR IGNORE INTO email_messages (campaign_id, gmail_message_id, gmail_thread_id, direction, sender, recipient, subject, body, message_at, created_at) VALUES (?, ?, ?, 'outgoing', ?, ?, ?, ?, ?, ?)", (campaign_id, message_id, thread_id, sender, recipient, subject, body, now_iso(), now_iso()))


def save_incoming_message(message: dict[str, Any]) -> bool:
    with _connect() as connection:
        try:
            connection.execute("INSERT INTO email_messages (campaign_id, gmail_message_id, gmail_thread_id, direction, sender, recipient, subject, body, message_at, raw_headers, created_at) VALUES (?, ?, ?, 'incoming', ?, ?, ?, ?, ?, ?, ?)", (message.get("campaign_id"), message["message_id"], message["thread_id"], message.get("sender", ""), message.get("recipient", ""), message.get("subject", ""), message.get("body", ""), message.get("message_at"), json.dumps(message.get("headers", {})), now_iso()))
        except sqlite3.IntegrityError:
            return False
        if message.get("campaign_id"):
            connection.execute("UPDATE campaigns SET reply_status = 'replied', last_updated = ? WHERE id = ?", (now_iso(), message["campaign_id"]))
        return True


def find_campaign_by_thread(thread_id: str) -> Optional[int]:
    with _connect() as connection:
        row = connection.execute("SELECT id FROM campaigns WHERE gmail_thread_id = ?", (thread_id,)).fetchone()
    return int(row["id"]) if row else None


def list_inbox() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute("SELECT c.id, c.prospect_name, c.company, c.prospect_email, c.email_subject, c.reply_status, MAX(m.message_at) AS last_message_at, (SELECT body FROM email_messages x WHERE x.campaign_id = c.id ORDER BY x.message_at DESC LIMIT 1) AS last_preview FROM campaigns c JOIN email_messages m ON m.campaign_id = c.id WHERE c.reply_status = 'replied' GROUP BY c.id ORDER BY last_message_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_conversation(campaign_id: int) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM email_messages WHERE campaign_id = ? ORDER BY message_at ASC, id ASC", (campaign_id,)).fetchall()
    return [dict(row) for row in rows]


def save_oauth_state(state: str, return_to: str = "", code_verifier: str = "") -> None:
    with _connect() as connection:
        connection.execute("DELETE FROM oauth_states WHERE created_at < ?", (datetime.fromtimestamp(datetime.now().timestamp() - 600, timezone.utc).isoformat(),))
        connection.execute("INSERT INTO oauth_states (state, return_to, code_verifier, created_at) VALUES (?, ?, ?, ?)", (state, return_to, code_verifier, now_iso()))


def consume_oauth_state(state: str) -> Optional[dict[str, Optional[str]]]:
    with _connect() as connection:
        row = connection.execute("SELECT state, return_to, code_verifier FROM oauth_states WHERE state = ?", (state,)).fetchone()
        if not row: return None
        connection.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        return {"return_to": row["return_to"] or None, "code_verifier": row["code_verifier"] or None}


def get_oauth_return_to(state: str) -> Optional[str]:
    with _connect() as connection:
        row = connection.execute("SELECT return_to FROM oauth_states WHERE state = ?", (state,)).fetchone()
    return row["return_to"] if row and row["return_to"] else None


def save_gmail_account(email: str, encrypted_credentials: str, history_id: str | None, expiration: str | None = None) -> None:
    with _connect() as connection:
        connection.execute("INSERT INTO gmail_accounts (id, email, encrypted_credentials, history_id, watch_expiration, connected_at, last_sync_at) VALUES (1, ?, ?, ?, ?, ?, NULL) ON CONFLICT(id) DO UPDATE SET email=excluded.email, encrypted_credentials=excluded.encrypted_credentials, history_id=excluded.history_id, watch_expiration=excluded.watch_expiration, connected_at=excluded.connected_at", (email, encrypted_credentials, history_id, expiration, now_iso()))


def get_gmail_account() -> Optional[dict[str, Any]]:
    with _connect() as connection:
        row = connection.execute("SELECT * FROM gmail_accounts WHERE id = 1").fetchone()
    return dict(row) if row else None


def update_gmail_sync(history_id: str | None) -> None:
    with _connect() as connection:
        connection.execute("UPDATE gmail_accounts SET history_id = ?, last_sync_at = ? WHERE id = 1", (history_id, now_iso()))


def delete_gmail_account() -> None:
    with _connect() as connection:
        connection.execute("DELETE FROM gmail_accounts WHERE id = 1")


init_db()
