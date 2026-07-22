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
            """
            CREATE TABLE IF NOT EXISTS case_documents (
                id BIGSERIAL PRIMARY KEY,
                case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                original_name TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes BIGINT NOT NULL,
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
                error TEXT NOT NULL DEFAULT ''
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

            CREATE TABLE IF NOT EXISTS case_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                original_name TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
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
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_cases_status_priority ON cases(status, priority DESC, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_cases_email ON cases(email);
            CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_log(case_id, created_at DESC);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_case_documents_hash ON case_documents(case_id, sha256);
            CREATE INDEX IF NOT EXISTS idx_case_documents_case ON case_documents(case_id, created_at);
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
    deleted_at = utcnow()
    with transaction() as conn:
        rows = execute(
            conn,
            "SELECT id FROM cases WHERE deleted_at IS NULL AND created_at<? AND status='closed'",
            (cutoff,),
        ).fetchall()
        case_ids = [int(row["id"]) for row in rows]
        for case_id in case_ids:
            # Remove free-text and contact data from every related table, not only the main case row.
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
        return len(case_ids)



def list_case_documents(case_id: int, include_content: bool = False) -> list[dict[str, Any]]:
    columns = "*" if include_content else "id,case_id,created_at,original_name,content_type,size_bytes,sha256"
    with transaction() as conn:
        rows = execute(
            conn,
            f"SELECT {columns} FROM case_documents WHERE case_id=? ORDER BY id",
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


def add_case_document(case_id: int, document: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    now = utcnow()
    with transaction() as conn:
        case = execute(conn, "SELECT id FROM cases WHERE id=? AND deleted_at IS NULL", (case_id,)).fetchone()
        if not case:
            raise KeyError("Case not found")
        existing = execute(
            conn,
            "SELECT * FROM case_documents WHERE case_id=? AND sha256=?",
            (case_id, document["sha256"]),
        ).fetchone()
        if existing:
            return dict(existing), False
        values = (
            case_id, now, document["original_name"], document["content_type"],
            document["size_bytes"], document["sha256"], document["content"],
        )
        sql = """
            INSERT INTO case_documents(case_id,created_at,original_name,content_type,size_bytes,sha256,content_blob)
            VALUES (?,?,?,?,?,?,?)
        """
        if using_postgres():
            row = execute(conn, sql + " RETURNING id", values).fetchone()
            document_id = int(row["id"])
        else:
            cursor = execute(conn, sql, values)
            document_id = int(cursor.lastrowid)
        execute(conn, "DELETE FROM document_analyses WHERE case_id=?", (case_id,))
        add_audit(conn, case_id, "client", "document_uploaded", {
            "document_id": document_id,
            "filename": document["original_name"],
            "content_type": document["content_type"],
            "size_bytes": document["size_bytes"],
        })
        row = execute(conn, "SELECT * FROM case_documents WHERE id=?", (document_id,)).fetchone()
        return dict(row), True


def delete_case_document(case_id: int, document_id: int, actor: str = "client") -> bool:
    with transaction() as conn:
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


def set_document_analysis_status(case_id: int, status: str, model: str = "", error: str = "") -> None:
    if status not in {"pending", "running", "completed", "failed"}:
        raise ValueError("Invalid document-analysis status")
    now = utcnow()
    with transaction() as conn:
        existing = execute(conn, "SELECT case_id,created_at FROM document_analyses WHERE case_id=?", (case_id,)).fetchone()
        if existing:
            execute(
                conn,
                "UPDATE document_analyses SET updated_at=?,status=?,model=?,error=? WHERE case_id=?",
                (now, status, model, error[:1000], case_id),
            )
        else:
            execute(
                conn,
                "INSERT INTO document_analyses(case_id,created_at,updated_at,status,model,result_json,error) VALUES (?,?,?,?,?,'{}',?)",
                (case_id, now, now, status, model, error[:1000]),
            )


def save_document_analysis(case_id: int, result: dict[str, Any], model: str) -> dict[str, Any]:
    now = utcnow()
    result_json = json.dumps(result, ensure_ascii=False)
    with transaction() as conn:
        existing = execute(conn, "SELECT case_id FROM document_analyses WHERE case_id=?", (case_id,)).fetchone()
        if existing:
            execute(
                conn,
                "UPDATE document_analyses SET updated_at=?,status='completed',model=?,result_json=?,error='' WHERE case_id=?",
                (now, model, result_json, case_id),
            )
        else:
            execute(
                conn,
                "INSERT INTO document_analyses(case_id,created_at,updated_at,status,model,result_json,error) VALUES (?,?,?,'completed',?,?,'')",
                (case_id, now, now, model, result_json),
            )
        add_audit(conn, case_id, "triage", "documents_analysed", {
            "document_count": len(list_case_documents_for_connection(conn, case_id)),
            "readiness_score": result.get("readiness_score"),
            "model": model,
        })
        row = execute(conn, "SELECT * FROM document_analyses WHERE case_id=?", (case_id,)).fetchone()
        return dict(row)


def list_case_documents_for_connection(conn: Any, case_id: int) -> list[dict[str, Any]]:
    return [dict(row) for row in execute(
        conn,
        "SELECT id,case_id,created_at,original_name,content_type,size_bytes,sha256 FROM case_documents WHERE case_id=? ORDER BY id",
        (case_id,),
    ).fetchall()]


def get_document_analysis(case_id: int) -> dict[str, Any] | None:
    with transaction() as conn:
        row = execute(conn, "SELECT * FROM document_analyses WHERE case_id=?", (case_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
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
