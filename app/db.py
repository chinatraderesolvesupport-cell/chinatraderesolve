from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Iterator

from .config import settings

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # SQLite-only local/test mode
    psycopg = None
    dict_row = None


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
                sent_at TEXT
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
            "CREATE INDEX IF NOT EXISTS idx_cases_status_priority ON cases(status, priority DESC, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_cases_email ON cases(email)",
            "CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_log(case_id, created_at DESC)",
        ]
        with transaction() as conn:
            for statement in statements:
                execute(conn, statement)
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

            CREATE INDEX IF NOT EXISTS idx_cases_status_priority ON cases(status, priority DESC, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_cases_email ON cases(email);
            CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_log(case_id, created_at DESC);
            """
        )


def add_audit(conn: Any, case_id: int, actor: str, event_type: str, details: dict[str, Any]) -> None:
    execute(
        conn,
        "INSERT INTO audit_log(case_id,created_at,actor,event_type,details_json) VALUES (?,?,?,?,?)",
        (case_id, utcnow(), actor, event_type, json.dumps(details, ensure_ascii=False)),
    )


def create_case(payload: dict[str, Any], triage: dict[str, Any], reference: str, public_token: str) -> dict[str, Any]:
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


def update_status(case_id: int, status: str, note: str, actor: str = "admin") -> dict[str, Any]:
    with transaction() as conn:
        row = execute(conn, "SELECT * FROM cases WHERE id=? AND deleted_at IS NULL", (case_id,)).fetchone()
        if not row:
            raise KeyError("Case not found")
        current = row["status"]
        if status != current and status not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(f"Transition {current} -> {status} is not allowed")
        execute(
            conn,
            "UPDATE cases SET status=?,admin_note=?,updated_at=? WHERE id=?",
            (status, note, utcnow(), case_id),
        )
        add_audit(conn, case_id, actor, "status_updated", {"from": current, "to": status, "note": note})
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
        execute(
            conn,
            "INSERT INTO notification_outbox(created_at,case_id,recipient,subject,body) VALUES (?,?,?,?,?)",
            (utcnow(), case_id, recipient, subject, body),
        )


def pending_notifications() -> list[dict[str, Any]]:
    with transaction() as conn:
        return [dict(r) for r in execute(conn, "SELECT * FROM notification_outbox WHERE status='pending' ORDER BY id").fetchall()]


def mark_notification(notification_id: int, status: str, error: str = "") -> None:
    with transaction() as conn:
        execute(
            conn,
            "UPDATE notification_outbox SET status=?,error=?,sent_at=? WHERE id=?",
            (status, error, utcnow() if status == "sent" else None, notification_id),
        )


def dashboard_counts() -> dict[str, int]:
    with transaction() as conn:
        rows = execute(conn, "SELECT status,COUNT(*) AS n FROM cases WHERE deleted_at IS NULL GROUP BY status").fetchall()
        counts = {r["status"]: r["n"] for r in rows}
        counts["total"] = sum(counts.values())
        counts["exceptions"] = sum(counts.get(k, 0) for k in ("human_review", "needs_information"))
        feedback_row = execute(conn, "SELECT COUNT(*) AS n FROM feedback").fetchone()
        counts["feedback"] = int(feedback_row["n"]) if feedback_row else 0
        return counts


def soft_delete_expired(days: int) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    with transaction() as conn:
        cur = execute(
            conn,
            "UPDATE cases SET deleted_at=?,full_name='DELETED',email='deleted@example.invalid',description='DELETED',admin_note='' WHERE deleted_at IS NULL AND created_at<? AND status='closed'",
            (utcnow(), cutoff),
        )
        return int(cur.rowcount)


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
