"""Pilot-only daily aggregates: no IP, URL, referrer or browser ID stored.

Session-day counts are estimates, not unique people. Only successfully rendered
public pilot pages are counted. Existing signed-session flags deduplicate visits;
DNT/GPC and administrators are excluded. Production routes never call this module.
"""
import logging
from datetime import datetime, timedelta, timezone
from .db import execute, transaction
from .security import SlidingWindowRateLimiter, client_key

log=logging.getLogger(__name__)
limiter=SlidingWindowRateLimiter(limit=120,window_seconds=60)
PUBLIC={'/sourcing','/sourcing/preview','/sourcing/preview/dispute','/sourcing/preview/account',
        '/sourcing/reviews','/sourcing/help'}


def init_db():
    with transaction() as conn:
        execute(conn,'''CREATE TABLE IF NOT EXISTS sourcing_daily_stats (
            day TEXT PRIMARY KEY, pageviews INTEGER NOT NULL DEFAULT 0,
            sessions INTEGER NOT NULL DEFAULT 0)''')


def record_view(request):
    path=request.url.path
    if path not in PUBLIC and not path.startswith('/sourcing/help/'):
        return
    if request.session.get('admin') or request.headers.get('dnt')=='1' or request.headers.get('sec-gpc')=='1':
        return
    agent=request.headers.get('user-agent','').lower()
    if not agent or any(word in agent for word in ('bot','spider','crawler','headless','curl','wget','python','httpx','testclient')):
        return
    if not limiter.allow(client_key(request)):
        return
    day=datetime.now(timezone.utc).date().isoformat()
    first=request.session.get('sourcing_stats_day')!=day
    try:
        with transaction() as conn:
            execute(conn,'''INSERT INTO sourcing_daily_stats(day,pageviews,sessions) VALUES (?,1,?)
                ON CONFLICT(day) DO UPDATE SET pageviews=sourcing_daily_stats.pageviews+1,
                sessions=sourcing_daily_stats.sessions+?''',(day,int(first),int(first)))
        request.session['sourcing_stats_day']=day
    except Exception:
        # Metrics must never prevent a customer opening the form.
        log.warning('Pilot visit aggregate could not be saved',exc_info=False)


def summary():
    today=datetime.now(timezone.utc).date()
    result=[]
    with transaction() as conn:
        for days in (1,7,30):
            start=(today-timedelta(days=days-1)).isoformat()
            end=(today+timedelta(days=1)).isoformat()
            row=execute(conn,'''SELECT COALESCE(SUM(pageviews),0) AS views,
                COALESCE(SUM(sessions),0) AS sessions FROM sourcing_daily_stats WHERE day>=? AND day<?''',(start,end)).fetchone()
            requests=execute(conn,'SELECT COUNT(*) AS n FROM sourcing_requests WHERE created_at>=? AND created_at<?',(start,end)).fetchone()['n']
            reports=execute(conn,'''SELECT COUNT(DISTINCT request_id) AS n FROM sourcing_reports
                WHERE created_at>=? AND created_at<?''',(start,end)).fetchone()['n']
            result.append(dict(days=days,start=start,views=row['views'],sessions=row['sessions'],requests=requests,reports=reports))
        first=execute(conn,'SELECT MIN(day) AS day FROM sourcing_daily_stats').fetchone()['day']
    return dict(periods=result,first=first,today=today.isoformat())
