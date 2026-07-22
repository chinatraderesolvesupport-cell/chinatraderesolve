from __future__ import annotations

import json
import sqlite3
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Iterator

from .config import settings
from .documents import unique_display_filename

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # SQLite-only local/test mode
    psycopg = None
    dict_row = None


class DocumentAnalysisInProgressError(RuntimeError):
    """Raised when evidence is changed while an analysis snapshot is running."""


class DocumentLimitError(ValueError):
    """Raised when a document batch would exceed a case storage limit."""


class DailyAnalysisLimitError(RuntimeError):
    """Raised when the database-backed daily OpenAI budget is exhausted."""


def _lock_case(conn: Any, case_id: int) -> bool:
    """Serialise document mutations and analysis claims for one case."""
    if using_postgres():
        row = execute(
            conn,
            "SELECT id FROM cases WHERE id=? AND deleted_at IS NULL FOR UPDATE",
            (case_id,),
        ).fetchone()
    else:
        # SQLite's default transaction is deferred. Taking the write lock before the
        # read prevents two concurrent requests from both passing the same guard.
        execute(conn, "BEGIN IMMEDIATE")
        row = execute(
            conn,
            "SELECT id FROM cases WHERE id=? AND deleted_at IS NULL",
            (case_id,),
        ).fetchone()
    return bool(row)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def using_postgres() -> bool:
    return bool(settings.database_url)


def _normalise_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def connect() -> Any:
    if using_postgres():
        if psycopg is None:
            raise RuntimeError("DATABASE_URL is set but psycopg is not installed")
        return psycopg.connect(
            _normalise_database_url(settings.database_url or ""),
            row_factory=dict_row,
            connect_timeout=15,
        )

    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_path, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _sql(query: str) -> str:
    return query.replace("?", "%s") if using_postgres() else query


def execute(conn: Any, query: str, params: tuple[Any, ...] | list[Any] = ()) -> Any:
    return conn.execute(_sql(query), params)


@contextmanager
def transaction() -> Iterator[Any]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_notification_retry_columns(conn: Any) -> None:
    """Add bounded-retry and cross-process lease metadata without losing messages."""
    if using_postgres():
        rows = execute(
            conn,
            "SELECT column_name FROM information_schema.columns WHERE table_name='notification_outbox'",
        ).fetchall()
        columns = {str(row["column_name"]) for row in rows}
    else:
        rows = execute(conn, "PRAGMA table_info(notification_outbox)").fetchall()
        columns = {str(row["name"]) for row in rows}
    if "attempts" not in columns:
        execute(conn, "ALTER TABLE notification_outbox ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0")
    if "next_attempt_at" not in columns:
        execute(conn, "ALTER TABLE notification_outbox ADD COLUMN next_attempt_at TEXT")
    if "claim_token" not in columns:
        execute(conn, "ALTER TABLE notification_outbox ADD COLUMN claim_token TEXT NOT NULL DEFAULT ''")
    if "claimed_at" not in columns:
        execute(conn, "ALTER TABLE notification_outbox ADD COLUMN claimed_at TEXT")
    execute(
        conn,
        "CREATE INDEX IF NOT EXISTS idx_notification_outbox_due "
        "ON notification_outbox(status,next_attempt_at,claimed_at,id)",
    )




def _ensure_document_analysis_run_token(conn: Any) -> None:
    """Add a per-run claim token so late workers cannot overwrite newer analyses."""
    if using_postgres():
        rows = execute(
            conn,
            "SELECT column_name FROM information_schema.columns WHERE table_name='document_analyses'",
        ).fetchall()
        columns = {str(row["column_name"]) for row in rows}
    else:
        rows = execute(conn, "PRAGMA table_info(document_analyses)").fetchall()
        columns = {str(row["name"]) for row in rows}
    if "run_token" not in columns:
        execute(conn, "ALTER TABLE document_analyses ADD COLUMN run_token TEXT NOT NULL DEFAULT ''")


def _ensure_case_document_page_count(conn: Any) -> None:
    """Add PDF page metadata without racing an overlapping PostgreSQL deploy."""
    if using_postgres():
        execute(
            conn,
            "ALTER TABLE case_documents ADD COLUMN IF NOT EXISTS page_count INTEGER NOT NULL DEFAULT 0",
        )
        return
    rows = execute(conn, "PRAGMA table_info(case_documents)").fetchall()
    columns = {str(row["name"]) for row in rows}
    if "page_count" not in columns:
        execute(
            conn,
            "ALTER TABLE case_documents ADD COLUMN page_count INTEGER NOT NULL DEFAULT 0",
        )


def init_db() -> None:
    if using_postgres():
        statements = [
            """
            CREATE TABLE IF NOT EXISTS cases (
                id BIGSERIAL PRIMARY KEY,
                case_reference TEXT NOT NULL UNIQUE,
                public_token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                risk_level TEXT NOT NULL DEFAULT 'medium',
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                country TEXT NOT NULL DEFAULT '',
                preferred_language TEXT NOT NULL DEFAULT 'English',
                purchasing_channel TEXT NOT NULL DEFAULT '',
                amount_in_dispute TEXT NOT NULL DEFAULT '',
                main_problem TEXT NOT NULL,
                supplier_name TEXT NOT NULL DEFAULT '',
                order_number TEXT NOT NULL DEFAULT '',
                order_value TEXT NOT NULL DEFAULT '',
                requested_result TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL,
                ai_consent INTEGER NOT NULL,
                sharing_authority INTEGER NOT NULL,
                pilot_terms INTEGER NOT NULL,
                no_guarantee INTEGER NOT NULL,
                triage_json TEXT NOT NULL,
                triage_source TEXT NOT NULL,
                public_message TEXT NOT NULL,
                admin_note TEXT NOT NULL DEFAULT '',
                deleted_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id BIGSERIAL PRIMARY KEY,
                case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details_json TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS notification_outbox (
                id BIGSERIAL PRIMARY KEY,
                created_at TEXT NOT NULL,
                case_id BIGINT REFERENCES cases(id) ON DELETE SET NULL,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT NOT NULL DEFAULT '',
                sent_at TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT,
                claim_token TEXT NOT NULL DEFAULT '',
                claimed_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id BIGSERIAL PRIMARY KEY,
                case_id BIGINT NOT NULL UNIQUE REFERENCES cases(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                feedback_text TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                testimonial_consent INTEGER NOT NULL DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS case_documents (
                id BIGSERIAL PRIMARY KEY,
                case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                original_name TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes BIGINT NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 0,
                sha256 TEXT NOT NULL,
                content_blob BYTEA NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS document_analyses (
                case_id BIGINT PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                result_json TEXT NOT NULL DEFAULT '{}',
                error TEXT NOT NULL DEFAULT '',
                run_token TEXT NOT NULL DEFAULT ''
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS usage_counters (
                counter_key TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_cases_status_priority ON cases(status, priority DESC, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_cases_email ON cases(email)",
            "CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_log(case_id, created_at DESC)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_case_documents_hash ON case_documents(case_id, sha256)",
            "CREATE INDEX IF NOT EXISTS idx_case_documents_case ON case_documents(case_id, created_at)",
        ]
        with transaction() as conn:
            for statement in statements:
                execute(conn, statement)
            _ensure_notification_retry_columns(conn)
            _ensure_document_analysis_run_token(conn)
            _ensure_case_document_page_count(conn)
        return

    with transaction() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_reference TEXT NOT NULL UNIQUE,
                public_token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                risk_level TEXT NOT NULL DEFAULT 'medium',
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                country TEXT NOT NULL DEFAULT '',
                preferred_language TEXT NOT NULL DEFAULT 'English',
                purchasing_channel TEXT NOT NULL DEFAULT '',
                amount_in_dispute TEXT NOT NULL DEFAULT '',
                main_problem TEXT NOT NULL,
                supplier_name TEXT NOT NULL DEFAULT '',
                order_number TEXT NOT NULL DEFAULT '',
                order_value TEXT NOT NULL DEFAULT '',
                requested_result TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL,
                ai_consent INTEGER NOT NULL,
                sharing_authority INTEGER NOT NULL,
                pilot_terms INTEGER NOT NULL,
                no_guarantee INTEGER NOT NULL,
                triage_json TEXT NOT NULL,
                triage_source TEXT NOT NULL,
                public_message TEXT NOT NULL,
                admin_note TEXT NOT NULL DEFAULT '',
                deleted_at TEXT
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details_json TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notification_outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                case_id INTEGER,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT NOT NULL DEFAULT '',
                sent_at TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT,
                claim_token TEXT NOT NULL DEFAULT '',
                claimed_at TEXT,
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                feedback_text TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                testimonial_consent INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS case_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                original_name TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 0,
                sha256 TEXT NOT NULL,
                content_blob BLOB NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS document_analyses (
                case_id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                result_json TEXT NOT NULL DEFAULT '{}',
                error TEXT NOT NULL DEFAULT '',
                run_token TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS usage_counters (
                counter_key TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_cases_status_priority ON cases(status, priority DESC, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_cases_email ON cases(email);
            CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_log(case_id, created_at DESC);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_case_documents_hash ON case_documents(case_id, sha256);
            CREATE INDEX IF NOT EXISTS idx_case_documents_case ON case_documents(case_id, created_at);
            """
        )
        _ensure_notification_retry_columns(conn)
        _ensure_document_analysis_run_token(conn)
        _ensure_case_document_page_count(conn)


def add_audit(conn: Any, case_id: int, actor: str, event_type: str, details: dict[str, Any]) -> None:
    execute(
        conn,
        "INSERT INTO audit_log(case_id,created_at,actor,event_type,details_json) VALUES (?,?,?,?,?)",
        (case_id, utcnow(), actor, event_type, json.dumps(details, ensure_ascii=False)),
    )


def record_audit(case_id: int, actor: str, event_type: str, details: dict[str, Any]) -> None:
    """Append a safe audit event outside an existing transaction."""
    with transaction() as conn:
        add_audit(conn, case_id, actor, event_type, details)


def grant_ai_consent(case_id: int, actor: str = "client") -> bool:
    """Persist explicit AI consent granted from the private case page."""
    with transaction() as conn:
        row = execute(conn, "SELECT ai_consent FROM cases WHERE id=? AND deleted_at IS NULL", (case_id,)).fetchone()
        if not row:
            raise KeyError("Case not found")
        already_granted = bool(row["ai_consent"])
        if not already_granted:
            execute(conn, "UPDATE cases SET ai_consent=1,updated_at=? WHERE id=?", (utcnow(), case_id))
            add_audit(conn, case_id, actor, "ai_consent_granted", {"scope": "document_analysis"})
        return not already_granted


def _insert_notifications(
    conn: Any,
    case_id: int | None,
    notifications: list[dict[str, str]] | None,
) -> None:
    """Insert outbox messages in the caller's transaction."""
    for notification in notifications or []:
        execute(
            conn,
            "INSERT INTO notification_outbox(created_at,case_id,recipient,subject,body) VALUES (?,?,?,?,?)",
            (
                utcnow(),
                case_id,
                str(notification["recipient"]),
                str(notification["subject"]),
                str(notification["body"]),
            ),
        )


def create_case(
    payload: dict[str, Any],
    triage: dict[str, Any],
    reference: str,
    public_token: str,
    *,
    notifications: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    now = utcnow()
    status = triage["decision"]
    values = (
        reference, public_token, now, now, status, triage["priority"], triage["risk_level"],
        payload["full_name"], payload["email"], payload.get("country", ""), payload.get("preferred_language", "English"),
        payload.get("purchasing_channel", ""), payload.get("amount_in_dispute", ""), payload["main_problem"],
        payload.get("supplier_name", ""), payload.get("order_number", ""), payload.get("order_value", ""),
        payload.get("requested_result", ""), payload["description"], int(payload["ai_consent"]),
        int(payload["sharing_authority"]), int(payload["free_access_terms"]), int(payload["no_guarantee"]),
        json.dumps(triage, ensure_ascii=False), triage["source"], triage["public_message"],
    )
    insert_sql = """
        INSERT INTO cases(
            case_reference,public_token,created_at,updated_at,status,priority,risk_level,
            full_name,email,country,preferred_language,purchasing_channel,amount_in_dispute,
            main_problem,supplier_name,order_number,order_value,requested_result,description,
            ai_consent,sharing_authority,pilot_terms,no_guarantee,triage_json,triage_source,public_message
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    with transaction() as conn:
        if using_postgres():
            row = execute(conn, insert_sql + " RETURNING id", values).fetchone()
            case_id = int(row["id"])
        else:
            cur = execute(conn, insert_sql, values)
            case_id = int(cur.lastrowid)
        add_audit(conn, case_id, "system", "application_created", {"status": status})
        add_audit(conn, case_id, "triage", "triage_completed", triage)
        _insert_notifications(conn, case_id, notifications)
        row = execute(conn, "SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        return dict(row)


def get_case_by_public(reference: str, token: str) -> dict[str, Any] | None:
    with transaction() as conn:
        row = execute(
            conn,
            "SELECT * FROM cases WHERE case_reference=? AND public_token=? AND deleted_at IS NULL",
            (reference, token),
        ).fetchone()
        return dict(row) if row else None


def get_case(case_id: int) -> dict[str, Any] | None:
    with transaction() as conn:
        row = execute(conn, "SELECT * FROM cases WHERE id=? AND deleted_at IS NULL", (case_id,)).fetchone()
        return dict(row) if row else None


def list_cases(status: str | None = None, risk: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM cases WHERE deleted_at IS NULL"
    args: list[Any] = []
    if status:
        query += " AND status=?"
        args.append(status)
    if risk:
        query += " AND risk_level=?"
        args.append(risk)
    query += " ORDER BY CASE risk_level WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC, priority DESC, created_at DESC"
    with transaction() as conn:
        return [dict(r) for r in execute(conn, query, args).fetchall()]


def get_audit(case_id: int) -> list[dict[str, Any]]:
    with transaction() as conn:
        return [dict(r) for r in execute(conn, "SELECT * FROM audit_log WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall()]


ALLOWED_TRANSITIONS = {
    "submitted": {"needs_information", "pilot_candidate", "human_review", "declined"},
    "needs_information": {"pilot_candidate", "human_review", "declined", "closed"},
    "pilot_candidate": {"accepted", "human_review", "declined", "closed"},
    "human_review": {"needs_information", "pilot_candidate", "accepted", "declined", "closed"},
    "accepted": {"needs_information", "closed"},
    "declined": {"closed"},
    "closed": set(),
}


def update_status(
    case_id: int,
    status: str,
    note: str,
    actor: str = "admin",
    *,
    close_notifications: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    with transaction() as conn:
        if not _lock_case(conn, case_id):
            raise KeyError("Case not found")
        row = execute(conn, "SELECT * FROM cases WHERE id=? AND deleted_at IS NULL", (case_id,)).fetchone()
        if not row:
            raise KeyError("Case not found")
        current = row["status"]
        if status != current and status not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(f"Transition {current} -> {status} is not allowed")
        execute(
            conn,
            "UPDATE cases SET status=?,admin_note=?,updated_at=? WHERE id=?",
            (status, note[:1000], utcnow(), case_id),
        )
        add_audit(conn, case_id, actor, "status_updated", {"from": current, "to": status, "note": note[:1000]})
        if current != "closed" and status == "closed":
            _insert_notifications(conn, case_id, close_notifications)
        updated = execute(conn, "SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        return dict(updated)


def replace_triage(case_id: int, triage: dict[str, Any], actor: str = "admin") -> dict[str, Any]:
    with transaction() as conn:
        row = execute(conn, "SELECT * FROM cases WHERE id=? AND deleted_at IS NULL", (case_id,)).fetchone()
        if not row:
            raise KeyError("Case not found")
        next_status = row["status"] if row["status"] in {"accepted", "closed"} else triage["decision"]
        execute(
            conn,
            "UPDATE cases SET status=?,priority=?,risk_level=?,triage_json=?,triage_source=?,public_message=?,updated_at=? WHERE id=?",
            (next_status, triage["priority"], triage["risk_level"], json.dumps(triage, ensure_ascii=False), triage["source"], triage["public_message"], utcnow(), case_id),
        )
        add_audit(conn, case_id, actor, "triage_recomputed", triage)
        updated = execute(conn, "SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        return dict(updated)


def queue_notification(case_id: int | None, recipient: str, subject: str, body: str) -> None:
    with transaction() as conn:
        _insert_notifications(
            conn,
            case_id,
            [{"recipient": recipient, "subject": subject, "body": body}],
        )


def pending_notifications(limit: int = 100) -> list[dict[str, Any]]:
    """Return due, unclaimed messages for diagnostics and tests."""
    now = utcnow()
    with transaction() as conn:
        return [dict(r) for r in execute(
            conn,
            """
            SELECT * FROM notification_outbox
            WHERE status='pending' AND (next_attempt_at IS NULL OR next_attempt_at<=?)
            ORDER BY id LIMIT ?
            """,
            (now, max(1, min(int(limit), 500))),
        ).fetchall()]


def claim_pending_notifications(
    limit: int = 100,
    *,
    lease_seconds: int = 300,
) -> list[dict[str, Any]]:
    """Atomically lease due outbox rows to one process.

    Render can briefly run the old and new service instances at the same time
    during a zero-downtime deploy.  A database-backed lease prevents both
    processes from sending the same pending email concurrently.  An abandoned
    lease is recovered after ``lease_seconds``.
    """
    limit = max(1, min(int(limit), 500))
    lease_seconds = max(60, min(int(lease_seconds), 3600))
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat(timespec="seconds")
    stale_before = (now_dt - timedelta(seconds=lease_seconds)).isoformat(timespec="seconds")
    claim_token = secrets.token_urlsafe(24)

    with transaction() as conn:
        if not using_postgres():
            # SQLite begins transactions lazily; take the write lock before
            # selecting rows so two local workers cannot claim the same row.
            execute(conn, "BEGIN IMMEDIATE")

        execute(
            conn,
            """
            UPDATE notification_outbox
            SET status='pending',claim_token='',claimed_at=NULL
            WHERE status='sending' AND (claimed_at IS NULL OR claimed_at<=?)
            """,
            (stale_before,),
        )

        if using_postgres():
            rows = execute(
                conn,
                """
                SELECT id FROM notification_outbox
                WHERE status='pending' AND (next_attempt_at IS NULL OR next_attempt_at<=?)
                ORDER BY id LIMIT ? FOR UPDATE SKIP LOCKED
                """,
                (now, limit),
            ).fetchall()
        else:
            rows = execute(
                conn,
                """
                SELECT id FROM notification_outbox
                WHERE status='pending' AND (next_attempt_at IS NULL OR next_attempt_at<=?)
                ORDER BY id LIMIT ?
                """,
                (now, limit),
            ).fetchall()
        ids = [int(row["id"]) for row in rows]
        if not ids:
            return []

        claimed_ids: list[int] = []
        for notification_id in ids:
            cursor = execute(
                conn,
                """
                UPDATE notification_outbox
                SET status='sending',claim_token=?,claimed_at=?
                WHERE id=? AND status='pending'
                  AND (next_attempt_at IS NULL OR next_attempt_at<=?)
                """,
                (claim_token, now, notification_id, now),
            )
            if int(cursor.rowcount or 0) == 1:
                claimed_ids.append(notification_id)

        claimed: list[dict[str, Any]] = []
        for notification_id in claimed_ids:
            row = execute(
                conn,
                "SELECT * FROM notification_outbox WHERE id=? AND claim_token=?",
                (notification_id, claim_token),
            ).fetchone()
            if row:
                claimed.append(dict(row))
        return claimed


def mark_notification(
    notification_id: int,
    status: str,
    error: str = "",
    *,
    retry_delay_seconds: int = 0,
    expected_claim_token: str | None = None,
) -> bool:
    if status not in {"pending", "sent", "failed"}:
        raise ValueError("Invalid notification status")
    now = datetime.now(timezone.utc)
    next_attempt_at = None
    if status == "pending" and retry_delay_seconds > 0:
        next_attempt_at = (now + timedelta(seconds=retry_delay_seconds)).isoformat(timespec="seconds")
    with transaction() as conn:
        params: tuple[Any, ...] = (
            status,
            error[:500],
            now.isoformat(timespec="seconds") if status == "sent" else None,
            next_attempt_at,
            notification_id,
        )
        if expected_claim_token:
            cursor = execute(
                conn,
                """
                UPDATE notification_outbox
                SET status=?,error=?,sent_at=?,attempts=attempts+1,next_attempt_at=?,
                    claim_token='',claimed_at=NULL
                WHERE id=? AND status='sending' AND claim_token=?
                """,
                (*params, expected_claim_token),
            )
        else:
            cursor = execute(
                conn,
                """
                UPDATE notification_outbox
                SET status=?,error=?,sent_at=?,attempts=attempts+1,next_attempt_at=?,
                    claim_token='',claimed_at=NULL
                WHERE id=?
                """,
                params,
            )
        return int(cursor.rowcount or 0) == 1



def dashboard_counts() -> dict[str, int]:
    with transaction() as conn:
        rows = execute(conn, "SELECT status,COUNT(*) AS n FROM cases WHERE deleted_at IS NULL GROUP BY status").fetchall()
        counts = {r["status"]: r["n"] for r in rows}
        counts["total"] = sum(counts.values())
        counts["exceptions"] = sum(counts.get(k, 0) for k in ("human_review", "needs_information"))
        feedback_row = execute(conn, "SELECT COUNT(*) AS n FROM feedback").fetchone()
        counts["feedback"] = int(feedback_row["n"]) if feedback_row else 0
        return counts


def _anonymize_case_for_connection(conn: Any, case_id: int, deleted_at: str) -> None:
    """Remove related personal content and leave only a non-identifying tombstone."""
    execute(conn, "DELETE FROM feedback WHERE case_id=?", (case_id,))
    execute(conn, "DELETE FROM notification_outbox WHERE case_id=?", (case_id,))
    execute(conn, "DELETE FROM case_documents WHERE case_id=?", (case_id,))
    execute(conn, "DELETE FROM document_analyses WHERE case_id=?", (case_id,))
    execute(conn, "DELETE FROM audit_log WHERE case_id=?", (case_id,))
    execute(
        conn,
        """
        UPDATE cases SET
            deleted_at=?, updated_at=?, full_name='DELETED', email='deleted@example.invalid',
            country='', purchasing_channel='', amount_in_dispute='', supplier_name='',
            order_number='', order_value='', requested_result='', description='DELETED',
            ai_consent=0, sharing_authority=0, pilot_terms=0, no_guarantee=0,
            triage_json='{"deleted":true}', triage_source='deleted',
            public_message='DELETED', admin_note=''
        WHERE id=?
        """,
        (deleted_at, deleted_at, case_id),
    )


def soft_delete_expired(days: int, inactive_days: int | None = None) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    inactive_cutoff = (
        datetime.now(timezone.utc) - timedelta(days=inactive_days)
    ).isoformat(timespec="seconds") if inactive_days else None
    deleted_at = utcnow()
    with transaction() as conn:
        if inactive_cutoff:
            rows = execute(
                conn,
                "SELECT id FROM cases WHERE deleted_at IS NULL AND "
                "((status='closed' AND updated_at<?) OR updated_at<?)",
                (cutoff, inactive_cutoff),
            ).fetchall()
        else:
            rows = execute(
                conn,
                "SELECT id FROM cases WHERE deleted_at IS NULL AND updated_at<? AND status='closed'",
                (cutoff,),
            ).fetchall()
        case_ids = [int(row["id"]) for row in rows]
        for case_id in case_ids:
            _anonymize_case_for_connection(conn, case_id, deleted_at)
        return len(case_ids)


def delete_case_now(case_id: int) -> bool:
    """Immediately anonymise a case after an authenticated private-link request."""
    deleted_at = utcnow()
    with transaction() as conn:
        row = execute(
            conn, "SELECT id FROM cases WHERE id=? AND deleted_at IS NULL", (case_id,)
        ).fetchone()
        if not row:
            return False
        _anonymize_case_for_connection(conn, case_id, deleted_at)
        return True


def revoke_ai_consent(case_id: int, actor: str = "client") -> bool:
    """Withdraw consent for future AI work and remove any stored AI report."""
    with transaction() as conn:
        if not _lock_case(conn, case_id):
            raise KeyError("Case not found")
        analysis = execute(
            conn, "SELECT status FROM document_analyses WHERE case_id=?", (case_id,)
        ).fetchone()
        if analysis and analysis["status"] == "running":
            raise DocumentAnalysisInProgressError(
                "AI consent cannot be changed while analysis is running"
            )
        row = execute(conn, "SELECT ai_consent FROM cases WHERE id=?", (case_id,)).fetchone()
        if not row or not bool(row["ai_consent"]):
            return False
        execute(conn, "UPDATE cases SET ai_consent=0,updated_at=? WHERE id=?", (utcnow(), case_id))
        execute(conn, "DELETE FROM document_analyses WHERE case_id=?", (case_id,))
        add_audit(conn, case_id, actor, "ai_consent_revoked", {"scope": "future_ai_processing"})
        return True



def list_case_documents(case_id: int, include_content: bool = False) -> list[dict[str, Any]]:
    with transaction() as conn:
        if include_content:
            rows = execute(
                conn,
                "SELECT * FROM case_documents WHERE case_id=? ORDER BY id",
                (case_id,),
            ).fetchall()
        else:
            rows = execute(
                conn,
                """
                SELECT id,case_id,created_at,original_name,content_type,size_bytes,page_count,sha256
                FROM case_documents WHERE case_id=? ORDER BY id
                """,
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]


def get_case_document(document_id: int, case_id: int | None = None) -> dict[str, Any] | None:
    query = "SELECT * FROM case_documents WHERE id=?"
    args: list[Any] = [document_id]
    if case_id is not None:
        query += " AND case_id=?"
        args.append(case_id)
    with transaction() as conn:
        row = execute(conn, query, args).fetchone()
        return dict(row) if row else None


def add_case_documents(
    case_id: int,
    documents: list[dict[str, Any]],
    *,
    max_documents: int,
    max_total_bytes: int,
    max_total_pdf_pages: int = 200,
    actor: str = "client",
) -> tuple[list[dict[str, Any]], int]:
    """Atomically add a prepared batch and invalidate an older report.

    The case-row lock makes count/size checks authoritative even when two browser
    uploads arrive together. Evidence cannot change while an analysis is running,
    so a completed report always describes the same document snapshot.
    """
    if not documents:
        return [], 0
    now = utcnow()
    with transaction() as conn:
        if not _lock_case(conn, case_id):
            raise KeyError("Case not found")
        analysis = execute(
            conn, "SELECT status FROM document_analyses WHERE case_id=?", (case_id,)
        ).fetchone()
        if analysis and analysis["status"] == "running":
            raise DocumentAnalysisInProgressError(
                "Documents cannot be changed while analysis is running"
            )

        existing = [dict(row) for row in execute(
            conn,
            "SELECT id,original_name,size_bytes,page_count,sha256 FROM case_documents WHERE case_id=? ORDER BY id",
            (case_id,),
        ).fetchall()]
        existing_hashes = {str(item["sha256"]) for item in existing}
        used_names = {str(item["original_name"]).casefold() for item in existing}
        batch_hashes: set[str] = set()
        accepted: list[dict[str, Any]] = []
        for raw_document in documents:
            document = dict(raw_document)
            digest = str(document["sha256"])
            if digest in existing_hashes or digest in batch_hashes:
                continue
            batch_hashes.add(digest)
            document["original_name"] = unique_display_filename(
                str(document["original_name"]), used_names
            )
            accepted.append(document)

        if len(existing) + len(accepted) > max_documents:
            raise DocumentLimitError(
                f"A case can contain no more than {max_documents} documents"
            )
        existing_total = sum(int(item["size_bytes"]) for item in existing)
        new_total = sum(int(item["size_bytes"]) for item in accepted)
        if existing_total + new_total > max_total_bytes:
            raise DocumentLimitError(
                "The total document size for one case cannot exceed 45 MB"
            )
        existing_pages = sum(int(item.get("page_count") or 0) for item in existing)
        new_pages = sum(int(item.get("page_count") or 0) for item in accepted)
        if existing_pages + new_pages > max_total_pdf_pages:
            raise DocumentLimitError(
                f"The PDFs in one case can contain no more than {max_total_pdf_pages} pages in total"
            )

        added: list[dict[str, Any]] = []
        for document in accepted:
            values = (
                case_id, now, document["original_name"], document["content_type"],
                document["size_bytes"], int(document.get("page_count") or 0),
                document["sha256"], document["content"],
            )
            sql = """
                INSERT INTO case_documents(case_id,created_at,original_name,content_type,size_bytes,page_count,sha256,content_blob)
                VALUES (?,?,?,?,?,?,?,?)
            """
            if using_postgres():
                row = execute(conn, sql + " RETURNING id", values).fetchone()
                document_id = int(row["id"])
            else:
                cursor = execute(conn, sql, values)
                document_id = int(cursor.lastrowid)
            add_audit(conn, case_id, actor, "document_uploaded", {
                "document_id": document_id,
                "filename": document["original_name"],
                "content_type": document["content_type"],
                "size_bytes": document["size_bytes"],
            })
            row = execute(
                conn,
                "SELECT id,case_id,created_at,original_name,content_type,size_bytes,page_count,sha256 FROM case_documents WHERE id=?",
                (document_id,),
            ).fetchone()
            added.append(dict(row))

        if added:
            execute(conn, "DELETE FROM document_analyses WHERE case_id=?", (case_id,))
        return added, len(documents) - len(accepted)


def add_case_document(case_id: int, document: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Backward-compatible one-document helper used by tests and scripts."""
    added, _ = add_case_documents(
        case_id, [document], max_documents=20, max_total_bytes=45 * 1024 * 1024,
        max_total_pdf_pages=200,
    )
    if added:
        return added[0], True
    with transaction() as conn:
        existing = execute(
            conn,
            "SELECT * FROM case_documents WHERE case_id=? AND sha256=?",
            (case_id, document["sha256"]),
        ).fetchone()
        if not existing:
            raise RuntimeError("Duplicate document could not be resolved")
        return dict(existing), False


def delete_case_document(case_id: int, document_id: int, actor: str = "client") -> bool:
    with transaction() as conn:
        if not _lock_case(conn, case_id):
            return False
        analysis = execute(
            conn, "SELECT status FROM document_analyses WHERE case_id=?", (case_id,)
        ).fetchone()
        if analysis and analysis["status"] == "running":
            raise DocumentAnalysisInProgressError(
                "Documents cannot be changed while analysis is running"
            )
        row = execute(
            conn,
            "SELECT original_name FROM case_documents WHERE id=? AND case_id=?",
            (document_id, case_id),
        ).fetchone()
        if not row:
            return False
        execute(conn, "DELETE FROM case_documents WHERE id=? AND case_id=?", (document_id, case_id))
        execute(conn, "DELETE FROM document_analyses WHERE case_id=?", (case_id,))
        add_audit(conn, case_id, actor, "document_deleted", {
            "document_id": document_id,
            "filename": row["original_name"],
        })
        return True


def claim_document_analysis(
    case_id: int,
    model: str,
    *,
    actor: str,
    document_count: int,
    allow_completed: bool = False,
    max_daily_analyses: int | None = None,
) -> str | None:
    """Atomically claim the single analysis slot and return its unique run token."""
    now = utcnow()
    run_token = secrets.token_urlsafe(24)
    with transaction() as conn:
        if not _lock_case(conn, case_id):
            raise KeyError("Case not found")
        actual_count_row = execute(
            conn, "SELECT COUNT(*) AS count FROM case_documents WHERE case_id=?", (case_id,)
        ).fetchone()
        actual_document_count = int(actual_count_row["count"] if actual_count_row else 0)
        if actual_document_count == 0:
            return None
        current = execute(
            conn, "SELECT status,created_at FROM document_analyses WHERE case_id=?", (case_id,)
        ).fetchone()
        if current and current["status"] == "running":
            return None
        if current and current["status"] == "completed" and not allow_completed:
            return None
        if max_daily_analyses:
            counter_key = f"document_analysis:{datetime.now(timezone.utc).date().isoformat()}"
            counter = execute(
                conn,
                """
                INSERT INTO usage_counters(counter_key,count) VALUES (?,1)
                ON CONFLICT(counter_key) DO UPDATE SET count=usage_counters.count+1
                WHERE usage_counters.count<?
                RETURNING count
                """,
                (counter_key, int(max_daily_analyses)),
            ).fetchone()
            if not counter:
                raise DailyAnalysisLimitError("The daily document-analysis budget has been reached")
        if current:
            execute(
                conn,
                "UPDATE document_analyses SET updated_at=?,status='running',model=?,result_json='{}',error='',run_token=? WHERE case_id=?",
                (now, model, run_token, case_id),
            )
        else:
            execute(
                conn,
                "INSERT INTO document_analyses(case_id,created_at,updated_at,status,model,result_json,error,run_token) VALUES (?,?,?,'running',?,'{}','',?)",
                (case_id, now, now, model, run_token),
            )
        add_audit(conn, case_id, actor, "document_analysis_started", {
            "status": "running", "model": model, "document_count": actual_document_count,
        })
        return run_token


def get_daily_analysis_usage() -> int:
    counter_key = f"document_analysis:{datetime.now(timezone.utc).date().isoformat()}"
    with transaction() as conn:
        row = execute(
            conn, "SELECT count FROM usage_counters WHERE counter_key=?", (counter_key,)
        ).fetchone()
        return int(row["count"]) if row else 0

def _analysis_is_stale(updated_at: str, stale_seconds: int) -> bool:
    if stale_seconds <= 0:
        return True
    try:
        value = datetime.fromisoformat(str(updated_at or ""))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return True
    return datetime.now(timezone.utc) - value > timedelta(seconds=stale_seconds)


def fail_stale_document_analysis(case_id: int, stale_seconds: int) -> bool:
    """Fail one abandoned run only if it is still running and still stale."""
    now = utcnow()
    message = "Document analysis did not finish before the worker stopped or timed out"
    with transaction() as conn:
        row = execute(
            conn, "SELECT status,updated_at,model FROM document_analyses WHERE case_id=?", (case_id,)
        ).fetchone()
        if not row or row["status"] != "running" or not _analysis_is_stale(row["updated_at"], stale_seconds):
            return False
        cursor = execute(
            conn,
            "UPDATE document_analyses SET updated_at=?,status='failed',error=?,run_token='' "
            "WHERE case_id=? AND status='running' AND updated_at=?",
            (now, message, case_id, row["updated_at"]),
        )
        if int(cursor.rowcount or 0) != 1:
            return False
        add_audit(conn, case_id, "document_ai", "document_analysis_failed", {
            "status": "failed", "model": row["model"], "error": message,
        })
        return True


def fail_running_document_analyses_on_startup(stale_seconds: int = 0) -> int:
    """Recover abandoned jobs without invalidating fresh work on an overlapping deploy."""
    with transaction() as conn:
        rows = execute(
            conn, "SELECT case_id,status,updated_at,model FROM document_analyses WHERE status='running'"
        ).fetchall()
    recovered = 0
    for row in rows:
        if _analysis_is_stale(row["updated_at"], stale_seconds) and fail_stale_document_analysis(
            int(row["case_id"]), stale_seconds
        ):
            recovered += 1
    return recovered

def set_document_analysis_status(
    case_id: int,
    status: str,
    model: str = "",
    error: str = "",
    actor: str = "document_ai",
    document_count: int | None = None,
    *,
    expected_run_token: str | None = None,
) -> bool:
    """Set analysis state; workers may update only the run they originally claimed."""
    if status not in {"pending", "running", "completed", "failed"}:
        raise ValueError("Invalid document-analysis status")
    now = utcnow()
    safe_error = error[:1000]
    with transaction() as conn:
        if not _lock_case(conn, case_id):
            raise KeyError("Case not found")
        existing = execute(
            conn, "SELECT case_id,created_at,status,run_token FROM document_analyses WHERE case_id=?", (case_id,)
        ).fetchone()
        if expected_run_token:
            if (
                not existing
                or existing["status"] != "running"
                or not secrets.compare_digest(str(existing["run_token"] or ""), expected_run_token)
            ):
                return False
        next_run_token = str(existing["run_token"] or "") if existing else ""
        if status == "running" and not next_run_token:
            next_run_token = secrets.token_urlsafe(24)
        elif status != "running":
            # Empty means that no worker currently owns this analysis row.
            next_run_token = ""  # nosec B105
        if existing:
            execute(
                conn,
                "UPDATE document_analyses SET updated_at=?,status=?,model=?,error=?,run_token=? WHERE case_id=?",
                (now, status, model, safe_error, next_run_token, case_id),
            )
        else:
            execute(
                conn,
                "INSERT INTO document_analyses(case_id,created_at,updated_at,status,model,result_json,error,run_token) VALUES (?,?,?,?,?,'{}',?,?)",
                (case_id, now, now, status, model, safe_error, next_run_token),
            )
        details: dict[str, Any] = {"status": status, "model": model}
        if document_count is not None:
            details["document_count"] = int(document_count)
        if safe_error:
            details["error"] = safe_error
        if status == "running":
            add_audit(conn, case_id, actor, "document_analysis_started", details)
        elif status == "failed":
            add_audit(conn, case_id, actor, "document_analysis_failed", details)
        return True

def save_document_analysis(
    case_id: int,
    result: dict[str, Any],
    model: str,
    expected_run_token: str,
) -> dict[str, Any] | None:
    """Persist a result only for the exact analysis run that still owns the claim."""
    now = utcnow()
    result_json = json.dumps(result, ensure_ascii=False)
    with transaction() as conn:
        if not _lock_case(conn, case_id):
            return None
        existing = execute(
            conn, "SELECT case_id,status,run_token FROM document_analyses WHERE case_id=?", (case_id,)
        ).fetchone()
        if (
            not existing
            or existing["status"] != "running"
            or not secrets.compare_digest(str(existing["run_token"] or ""), expected_run_token)
        ):
            return None
        execute(
            conn,
            "UPDATE document_analyses SET updated_at=?,status='completed',model=?,result_json=?,error='',run_token='' WHERE case_id=?",
            (now, model, result_json, case_id),
        )
        usage = result.get("provider_usage") if isinstance(result.get("provider_usage"), dict) else {}
        add_audit(conn, case_id, "document_ai", "documents_analysed", {
            "document_count": len(list_case_documents_for_connection(conn, case_id)),
            "readiness_score": result.get("readiness_score"),
            "model": model,
            "input_tokens": int(usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        })
        row = execute(conn, "SELECT * FROM document_analyses WHERE case_id=?", (case_id,)).fetchone()
        saved = dict(row)
        saved.pop("run_token", None)
        return saved

def list_case_documents_for_connection(conn: Any, case_id: int) -> list[dict[str, Any]]:
    return [dict(row) for row in execute(
        conn,
        "SELECT id,case_id,created_at,original_name,content_type,size_bytes,page_count,sha256 FROM case_documents WHERE case_id=? ORDER BY id",
        (case_id,),
    ).fetchall()]


def get_document_analysis(case_id: int) -> dict[str, Any] | None:
    with transaction() as conn:
        row = execute(conn, "SELECT * FROM document_analyses WHERE case_id=?", (case_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result.pop("run_token", None)
        try:
            result["result"] = json.loads(result.get("result_json") or "{}")
        except json.JSONDecodeError:
            result["result"] = {}
        return result

def save_feedback(case_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    now = utcnow()
    with transaction() as conn:
        case = execute(conn, "SELECT id FROM cases WHERE id=? AND deleted_at IS NULL", (case_id,)).fetchone()
        if not case:
            raise KeyError("Case not found")
        execute(
            conn,
            """
            INSERT INTO feedback(case_id,created_at,updated_at,rating,feedback_text,display_name,testimonial_consent)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(case_id) DO UPDATE SET
                updated_at=excluded.updated_at,
                rating=excluded.rating,
                feedback_text=excluded.feedback_text,
                display_name=excluded.display_name,
                testimonial_consent=excluded.testimonial_consent
            """,
            (
                case_id, now, now, int(payload["rating"]), payload["feedback_text"],
                payload.get("display_name", ""), int(bool(payload.get("testimonial_consent"))),
            ),
        )
        add_audit(conn, case_id, "client", "feedback_submitted", {
            "rating": int(payload["rating"]),
            "testimonial_consent": bool(payload.get("testimonial_consent")),
        })
        row = execute(conn, "SELECT * FROM feedback WHERE case_id=?", (case_id,)).fetchone()
        return dict(row)


def get_feedback(case_id: int) -> dict[str, Any] | None:
    with transaction() as conn:
        row = execute(conn, "SELECT * FROM feedback WHERE case_id=?", (case_id,)).fetchone()
        return dict(row) if row else None
