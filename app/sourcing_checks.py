"""Private candidate matches. Never supplied to the research provider or public reports."""
import json
import re
import unicodedata
from urllib.parse import urlsplit
from .db import transaction, execute


def identity(value):
    value=unicodedata.normalize('NFKC',str(value or '')).casefold().strip()
    if re.match(r'https?://',value):
        try:
            host=urlsplit(value).hostname or ''
            if host in {'alibaba.com','www.alibaba.com','1688.com','www.1688.com'}:return ''
            return 'host:'+host.removeprefix('www.')
        except ValueError:return ''
    words=re.findall(r'[a-z0-9]+|[\u3400-\u9fff]+',value)
    words=[w for w in words if w not in {'co','company','ltd','limited','inc','corporation','llc'}]
    result=''.join(words)
    return result if len(result)>=8 else ''


def internal_matches(item):
    key=identity(item['brief'].get('supplier'))
    if not key:return []
    matches=[]
    with transaction() as conn:
        rows=execute(conn,"SELECT id,case_reference,supplier_name,status,created_at FROM cases WHERE deleted_at IS NULL AND supplier_name<>'' ORDER BY created_at DESC LIMIT 1000").fetchall()
        for row in rows:
            if identity(row['supplier_name'])==key:
                matches.append({'kind':'dispute','reference':row['case_reference'],'url':'/admin/case/'+str(row['id']),
                                'date':row['created_at'][:10]})
        rows=execute(conn,'SELECT id,brief_json,created_at FROM sourcing_requests WHERE id<>? ORDER BY created_at DESC LIMIT 1000',(item['id'],)).fetchall()
        for row in rows:
            if identity(json.loads(row['brief_json']).get('supplier'))==key:
                matches.append({'kind':'request','reference':row['id'],'url':'/admin/sourcing/'+row['id'],
                                'date':row['created_at'][:10]})
    return matches[:20]
