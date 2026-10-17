#!/usr/bin/env python3
"""Consistent private data archive before an additive release; no secrets in output.

Run with the existing service environment. This is a logical data archive, not a
pg_dump substitute: retain the application source/schema and provider recovery as
well. No restore or delete operation is performed by this script.
"""
import argparse
import base64
from datetime import date,datetime,timezone
from decimal import Decimal
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import db


def encode(value):
    if isinstance(value,(bytes,bytearray,memoryview)):
        return {'$bytes':base64.b64encode(bytes(value)).decode('ascii')}
    if isinstance(value,(datetime,date,Decimal,UUID)):
        return {'$type':type(value).__name__,'value':str(value)}
    raise TypeError(type(value).__name__)


def serialized(value):
    return json.dumps(value,default=encode,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def fingerprint(reference):
    with db.transaction() as conn:
        row=db.execute(conn,'SELECT * FROM cases WHERE case_reference=?',(reference,)).fetchone()
        if row is None:raise RuntimeError('Required existing case was not found')
        return hashlib.sha256(serialized(dict(row)).encode()).hexdigest()


def backup(path,require_reference=None):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    counts={}
    # Refuse overwrite; backup bytes contain private customer records.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,'wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb') as compressed,db.transaction() as conn:
            if db.using_postgres():
                db.execute(conn,'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                tables=[row['table_name'] for row in db.execute(conn,"SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name").fetchall()]
            else:
                db.execute(conn,'BEGIN')
                tables=[row['name'] for row in db.execute(conn,"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]
            def write(item):compressed.write((serialized(item)+'\n').encode())
            write({'format':'ctr-logical-data-v1','created_at':datetime.now(timezone.utc).isoformat(),
                   'backend':'postgresql' if db.using_postgres() else 'sqlite','tables':tables})
            if require_reference:
                row=db.execute(conn,'SELECT * FROM cases WHERE case_reference=?',(require_reference,)).fetchone()
                if row is None:raise RuntimeError('Required existing case was not found')
                write({'required_case_sha256':hashlib.sha256(serialized(dict(row)).encode()).hexdigest()})
            for table in tables:
                # Identifiers are introspected and quoted, never interpolated unquoted.
                quoted='"'+table.replace('"','""')+'"'
                cursor=db.execute(conn,'SELECT * FROM '+quoted)
                count=0
                while rows:=cursor.fetchmany(100):
                    for row in rows:
                        write({'table':table,'row':dict(row)});count+=1
                counts[table]=count
            write({'complete':True,'counts':counts})
    except Exception:
        path.unlink(missing_ok=True)
        raise
    hasher=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):hasher.update(chunk)
    digest=hasher.hexdigest()
    # Verify gzip framing and terminal completeness without printing record data.
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        last=None
        for line in stream:last=json.loads(line)
    if not last or last.get('complete') is not True:raise RuntimeError('Incomplete archive')
    return {'path':str(path),'sha256':digest,'counts':counts,'verified_complete':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--require-reference')
    parser.add_argument('--fingerprint-reference')
    args=parser.parse_args()
    if args.fingerprint_reference:
        print(serialized({'case_sha256':fingerprint(args.fingerprint_reference)}))
    elif args.output:
        print(serialized(backup(args.output,args.require_reference)))
    else:parser.error('--output or --fingerprint-reference is required')
