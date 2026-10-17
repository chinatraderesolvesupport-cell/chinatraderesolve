"""Additive storage for sourcing; never reads or writes dispute-case records."""
from __future__ import annotations
import hashlib
import json
import secrets
from datetime import datetime, timezone
from .db import execute, transaction, using_postgres, utcnow


class Conflict(ValueError):
    pass


def init_sourcing_db():
    binary = 'BYTEA' if using_postgres() else 'BLOB'
    with transaction() as conn:
        execute(conn, '''CREATE TABLE IF NOT EXISTS sourcing_requests (
            id TEXT PRIMARY KEY, access_hash TEXT NOT NULL,
            submission_hash TEXT NOT NULL UNIQUE, email TEXT NOT NULL,
            brief_json TEXT NOT NULL, status TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1, draft_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)''')
        execute(conn, f'''CREATE TABLE IF NOT EXISTS sourcing_photos (
            id TEXT PRIMARY KEY, request_id TEXT NOT NULL REFERENCES sourcing_requests(id) ON DELETE CASCADE,
            filename TEXT NOT NULL, content_type TEXT NOT NULL, content {binary} NOT NULL)''')
        execute(conn, '''CREATE TABLE IF NOT EXISTS sourcing_reports (
            request_id TEXT NOT NULL REFERENCES sourcing_requests(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(request_id, revision))''')
        execute(conn, '''CREATE TABLE IF NOT EXISTS sourcing_events (
            id TEXT PRIMARY KEY, request_id TEXT NOT NULL REFERENCES sourcing_requests(id) ON DELETE CASCADE,
            actor TEXT NOT NULL, event TEXT NOT NULL, created_at TEXT NOT NULL)''')
        execute(conn, 'CREATE INDEX IF NOT EXISTS sourcing_photos_request ON sourcing_photos(request_id)')


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _event(conn, request_id, actor, event):
    execute(conn, 'INSERT INTO sourcing_events VALUES (?,?,?,?,?)',
            (secrets.token_urlsafe(18), request_id, actor, event, datetime.now(timezone.utc).isoformat()))


def create_request(brief, email, photos, submission_secret):
    """Deterministic access credential makes replay return the same private request."""
    submission_hash = digest(submission_secret)
    access = hashlib.sha256(('sourcing-access:' + submission_secret).encode()).hexdigest()
    request_id = 'SRC-' + submission_hash[:20].upper()
    now = utcnow()
    with transaction() as conn:
        # ON CONFLICT prevents duplicate submissions across workers.
        row = execute(conn, '''INSERT INTO sourcing_requests
            (id,access_hash,submission_hash,email,brief_json,status,version,created_at,updated_at)
            VALUES (?,?,?,?,?,'received',1,?,?) ON CONFLICT(submission_hash) DO NOTHING RETURNING id''',
            (request_id,digest(access),submission_hash,email,json.dumps(brief,ensure_ascii=False),now,now)).fetchone()
        if row:
            for photo in photos:
                execute(conn, 'INSERT INTO sourcing_photos VALUES (?,?,?,?,?)',
                        (secrets.token_urlsafe(18),request_id,photo.original_name,photo.content_type,photo.content))
            _event(conn,request_id,'client','created')
    return request_id, access


def get_request(request_id):
    with transaction() as conn:
        row = execute(conn,'SELECT * FROM sourcing_requests WHERE id=?',(request_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result['brief'] = json.loads(result.pop('brief_json'))
        result['draft'] = json.loads(result.pop('draft_json'))
        result['photos'] = [dict(p) for p in execute(conn,
            'SELECT id,filename,content_type FROM sourcing_photos WHERE request_id=?',(request_id,)).fetchall()]
        report = execute(conn,'SELECT * FROM sourcing_reports WHERE request_id=? ORDER BY revision DESC LIMIT 1',
                         (request_id,)).fetchone()
        result['report'] = json.loads(report['payload_json']) if report else None
        result['report_revision'] = report['revision'] if report else None
        result['events'] = [dict(e) for e in execute(conn,
            'SELECT actor,event,created_at FROM sourcing_events WHERE request_id=? ORDER BY created_at,id',
            (request_id,)).fetchall()]
        return result


def list_requests():
    with transaction() as conn:
        return [dict(r) for r in execute(conn,
            'SELECT id,email,status,version,created_at FROM sourcing_requests ORDER BY created_at DESC,id LIMIT 200').fetchall()]


def get_photo(request_id, photo_id):
    with transaction() as conn:
        row=execute(conn,'SELECT * FROM sourcing_photos WHERE request_id=? AND id=?',(request_id,photo_id)).fetchone()
        return dict(row) if row else None


TRANSITIONS = {
    'received': {'reviewing','declined'},
    'reviewing': {'in_progress','declined'},
    'in_progress': {'reviewing','declined'},
    'completed': {'reviewing'}, 'declined': set(),
}


def change_status(request_id, expected_version, status):
    with transaction() as conn:
        row=execute(conn,'SELECT status FROM sourcing_requests WHERE id=?',(request_id,)).fetchone()
        if not row or status not in TRANSITIONS.get(row['status'],set()):
            raise Conflict('Недопустимый переход статуса.')
        updated=execute(conn,'''UPDATE sourcing_requests SET status=?,version=version+1,updated_at=?
            WHERE id=? AND version=?''',(status,utcnow(),request_id,expected_version))
        if updated.rowcount!=1:
            raise Conflict('Заявка уже изменена. Обновите страницу.')
        _event(conn,request_id,'admin','status:'+status)


def publish_report(request_id, expected_version, payload):
    with transaction() as conn:
        updated=execute(conn,'''UPDATE sourcing_requests SET status='completed',draft_json='{}',version=version+1,updated_at=?
            WHERE id=? AND version=? AND status='in_progress' ''',
            (utcnow(),request_id,expected_version))
        if updated.rowcount!=1:
            raise Conflict('Сначала начните работу или обновите изменённую заявку.')
        execute(conn,'INSERT INTO sourcing_reports VALUES (?,?,?,?)',
                (request_id,expected_version+1,json.dumps(payload,ensure_ascii=False),utcnow()))
        _event(conn,request_id,'admin','report_published')


def delete_request(request_id):
    with transaction() as conn:
        execute(conn,'DELETE FROM sourcing_requests WHERE id=?',(request_id,))


def save_draft(request_id, expected_version, payload):
    with transaction() as conn:
        result=execute(conn,"""UPDATE sourcing_requests SET draft_json=?,version=version+1,updated_at=?
            WHERE id=? AND version=? AND status='in_progress' """,
            (json.dumps(payload,ensure_ascii=False),utcnow(),request_id,expected_version))
        if result.rowcount!=1:
            raise Conflict('Черновик не сохранён: заявка изменилась или работа ещё не начата.')
        _event(conn,request_id,'admin','draft_saved')
