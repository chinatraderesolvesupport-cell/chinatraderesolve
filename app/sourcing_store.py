"""Additive storage for sourcing; never reads or writes dispute-case records."""
from __future__ import annotations
import hashlib
import json
import secrets
from datetime import datetime, timezone
from .db import execute, transaction, using_postgres, utcnow, _insert_notifications
from . import sourcing_mail


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
        execute(conn, '''CREATE TABLE IF NOT EXISTS sourcing_notifications (
            request_id TEXT NOT NULL REFERENCES sourcing_requests(id) ON DELETE CASCADE,
            notification_id BIGINT NOT NULL REFERENCES notification_outbox(id) ON DELETE CASCADE,
            event TEXT NOT NULL, PRIMARY KEY(request_id,notification_id))''')
        init_feedback_db(conn)
        from .sourcing_research import init_db
        init_db(conn)
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
            _queue_mail(conn,request_id,email,'received',brief.get('locale','ru'))
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
        research = execute(conn, 'SELECT state,error_code,evidence_json,updated_at,attempts FROM sourcing_research WHERE request_id=?', (request_id,)).fetchone()
        result['research'] = dict(research) if research else None
        if result['research']:
            result['research']['evidence'] = json.loads(result['research'].pop('evidence_json'))
        result['notifications'] = [dict(n) for n in execute(conn,
            '''SELECT n.event,o.status FROM sourcing_notifications n
               JOIN notification_outbox o ON o.id=n.notification_id
               WHERE n.request_id=? AND o.recipient=? ORDER BY o.id''',
            (request_id,result['email'])).fetchall()]
        result['events'] = [dict(e) for e in execute(conn,
            'SELECT actor,event,created_at FROM sourcing_events WHERE request_id=? ORDER BY created_at,id',
            (request_id,)).fetchall()]
        return result


def list_requests():
    with transaction() as conn:
        return [dict(r) for r in execute(conn,
            '''SELECT r.id,r.email,r.status,r.version,r.created_at,j.state AS research_state,
               CASE WHEN v.request_id IS NULL AND r.status NOT IN ('completed','declined') THEN 1 ELSE 0 END AS is_new
               FROM sourcing_requests r LEFT JOIN sourcing_research j ON j.request_id=r.id
               LEFT JOIN sourcing_admin_views v ON v.request_id=r.id
               ORDER BY is_new DESC,r.created_at DESC,r.id LIMIT 200''').fetchall()]


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
        job=execute(conn,'SELECT evidence_json FROM sourcing_research WHERE request_id=?',(request_id,)).fetchone()
        if job:
            stages=json.loads(job['evidence_json']).get('stages',[])
            payload={**payload,'research_coverage':[{'key':stage['key'],'status':stage['status'],'checked_at':stage.get('checked_at','')}
                for stage in stages if stage.get('key') in {'identity','forums','records'} and stage.get('status') in {'searched','limited','failed'}]}
        execute(conn,'INSERT INTO sourcing_reports VALUES (?,?,?,?)',
                (request_id,expected_version+1,json.dumps(payload,ensure_ascii=False),utcnow()))
        execute(conn,"UPDATE sourcing_research SET state='published',updated_at=? WHERE request_id=?",(utcnow(),request_id))
        _event(conn,request_id,'admin','report_published')
        recipient=execute(conn,'SELECT email,brief_json FROM sourcing_requests WHERE id=?',(request_id,)).fetchone()
        _queue_mail(conn,request_id,recipient['email'],'report',json.loads(recipient['brief_json']).get('locale','ru'))


def delete_request(request_id, expected_version=None):
    with transaction() as conn:
        if expected_version is not None:
            if not using_postgres():
                execute(conn,'BEGIN IMMEDIATE')
            row=execute(conn,'SELECT version FROM sourcing_requests WHERE id=?'+(' FOR UPDATE' if using_postgres() else ''),(request_id,)).fetchone()
            if not row:
                return False
            if str(row['version'])!=str(expected_version):
                raise Conflict('Заявка изменилась. Откройте её и подтвердите удаление заново.')
        execute(conn,'''DELETE FROM notification_outbox WHERE id IN
            (SELECT notification_id FROM sourcing_notifications WHERE request_id=?)''',(request_id,))
        execute(conn,'DELETE FROM sourcing_requests WHERE id=?',(request_id,))
        return True


def save_draft(request_id, expected_version, payload):
    with transaction() as conn:
        result=execute(conn,"""UPDATE sourcing_requests SET draft_json=?,version=version+1,updated_at=?
            WHERE id=? AND version=? AND status='in_progress' """,
            (json.dumps(payload,ensure_ascii=False),utcnow(),request_id,expected_version))
        if result.rowcount!=1:
            raise Conflict('Черновик не сохранён: заявка изменилась или работа ещё не начата.')
        _event(conn,request_id,'admin','draft_saved')


def _queue_mail(conn, request_id, email, event, locale='ru'):
    ids = _insert_notifications(conn, None, sourcing_mail.messages(request_id, email, event, locale))
    for notification_id in ids:
        execute(conn, 'INSERT INTO sourcing_notifications VALUES (?,?,?)',
                (request_id, notification_id, event))


def recover_email_access(request_id):
    """The destination is always the stored owner email; at most three requests/day."""
    if not sourcing_mail.configured():return False
    with transaction() as conn:
        if not using_postgres():execute(conn,'BEGIN IMMEDIATE')
        row=execute(conn,'SELECT email,brief_json FROM sourcing_requests WHERE id=?'+(' FOR UPDATE' if using_postgres() else ''),(request_id,)).fetchone()
        if not row:return False
        count=execute(conn,"""SELECT COUNT(*) AS n FROM sourcing_notifications n
            JOIN notification_outbox o ON o.id=n.notification_id
            WHERE n.request_id=? AND n.event='access_link' AND o.created_at>=?""",
            (request_id,utcnow()[:10])).fetchone()['n']
        if count>=3:return False
        _queue_mail(conn,request_id,row['email'],'access_link',json.loads(row['brief_json']).get('locale','ru'))
        return True


def init_feedback_db(conn):
    execute(conn, '''CREATE TABLE IF NOT EXISTS sourcing_feedback (
        id TEXT PRIMARY KEY, submission_hash TEXT NOT NULL UNIQUE,
        request_id TEXT REFERENCES sourcing_requests(id) ON DELETE CASCADE,
        kind TEXT NOT NULL, rating INTEGER, message TEXT NOT NULL,
        locale TEXT NOT NULL, publish_consent INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending', version INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL)''')


def create_feedback(submission, request_id, kind, rating, message, locale, publish_consent):
    hashed=digest(submission)
    with transaction() as conn:
        execute(conn, '''INSERT INTO sourcing_feedback
            (id,submission_hash,request_id,kind,rating,message,locale,publish_consent,created_at)
            VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(submission_hash) DO NOTHING''',
            ('FB-'+hashed[:20].upper(),hashed,request_id or None,kind,rating,message,locale,
             int(publish_consent and kind=='review'),utcnow()))


def list_feedback(public=False):
    with transaction() as conn:
        where="WHERE kind='review' AND publish_consent=1 AND status='published'" if public else ''
        columns='created_at,locale,message,rating,request_id' if public else '*'
        return [dict(row) for row in execute(conn,
            'SELECT '+columns+' FROM sourcing_feedback '+where+' ORDER BY created_at DESC,id DESC LIMIT 200').fetchall()]


def moderate_feedback(feedback_id, version, status):
    if status not in {'pending','published','rejected'}: raise ValueError('Некорректный статус.')
    with transaction() as conn:
        row=execute(conn,'SELECT kind,publish_consent FROM sourcing_feedback WHERE id=?',(feedback_id,)).fetchone()
        if not row or (status=='published' and (row['kind']!='review' or not row['publish_consent'])):
            raise ValueError('Публикация этого сообщения не разрешена.')
        changed=execute(conn,'''UPDATE sourcing_feedback SET status=?,version=version+1
            WHERE id=? AND version=?''',(status,feedback_id,version))
        if changed.rowcount!=1: raise Conflict('Сообщение изменилось. Обновите страницу.')


def request_counts():
    with transaction() as conn:
        rows=execute(conn,'SELECT status,COUNT(*) AS n FROM sourcing_requests GROUP BY status').fetchall()
    counts={row['status']:int(row['n']) for row in rows}
    counts['total']=sum(counts.values())
    counts['active']=sum(counts.get(status,0) for status in ('received','reviewing','in_progress'))
    return counts
