"""Email → fresh browser → approved report; email tokens never grant deletion."""
from dataclasses import replace
import re
import time
from urllib.parse import urlsplit,parse_qs

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
import pytest
from app import main,db,sourcing_mail,sourcing_links as links,sourcing_store as store
from test_sourcing import pilot,create,admin,admin_fields,move,fields


def enable_mail(monkeypatch):
    monkeypatch.setattr(sourcing_mail,'configured',lambda:True)
    monkeypatch.setattr(sourcing_mail,'settings',replace(db.settings,public_base_url='https://testserver',admin_email='operator@example.com'))
    monkeypatch.setattr(links,'settings',db.settings)


def published(client,rid):
    admin(client);move(client,rid,'reviewing');move(client,rid,'in_progress')
    data={'summary':'Reviewed supplier result','findings':'Evidence [1]','risks':'Check identity',
          'next_steps':'Ask for documents','sources':'https://example.com/evidence','reviewed':'yes'}
    response=client.post('/admin/sourcing/'+rid+'/report',data={**admin_fields(client,rid),**data},follow_redirects=False)
    assert response.status_code==303,response.text


def test_ready_email_opens_approved_report_in_a_fresh_browser_without_admin_password(pilot,monkeypatch):
    enable_mail(monkeypatch)
    rid=create(pilot);published(pilot,rid)
    row=[row for row in db.pending_notifications() if 'Готовность отчёта' in row['subject']][0]
    assert row['body'].startswith('Отчёт готов')
    url=re.search(r'https://testserver/sourcing/email-access\?[^\s]+',row['body']).group(0)
    token=parse_qs(urlsplit(url).query)['token'][0]
    assert links.verify(token)['request_id']==rid
    with TestClient(main.app,base_url='https://testserver') as buyer:
        response=buyer.get(url,follow_redirects=False)
        assert response.status_code==303 and response.headers['location']=='/sourcing/requests/'+rid
        assert 'token=' not in response.headers['location']
        assert response.headers['referrer-policy']=='no-referrer'
        page=buyer.get(response.headers['location'])
        assert page.status_code==200 and 'Reviewed supplier result' in page.text
        assert '<code class="access-code">' not in page.text
        assert rid+'/delete' not in page.text
        assert token not in page.text
        assert buyer.get('/admin/sourcing/'+rid).status_code==401
        csrf=fields(buyer)['csrf_token']
        assert buyer.post('/sourcing/requests/'+rid+'/delete',data={'csrf_token':csrf,'confirm':'delete'}).status_code==404
        assert store.get_request(rid) is not None


def test_view_link_hides_draft_and_survives_publication_without_granting_delete(pilot):
    rid=create(pilot)
    token=links.issue(rid)
    admin(pilot);move(pilot,rid,'reviewing');move(pilot,rid,'in_progress')
    store.save_draft(rid,store.get_request(rid)['version'],{'summary':'TOP SECRET INTERNAL DRAFT'})
    with TestClient(main.app,base_url='https://testserver') as buyer:
        assert buyer.get('/sourcing/email-access',params={'token':token}).status_code==200
        assert 'TOP SECRET INTERNAL DRAFT' not in buyer.get('/sourcing/requests/'+rid).text
        assert buyer.get('/sourcing/requests/'+rid+'/progress').status_code==200
        assert buyer.get('/sourcing/feedback',params={'request_id':rid}).status_code==200


def test_expired_tampered_wrong_scope_and_deleted_links_are_recoverable(pilot,monkeypatch):
    rid=create(pilot)
    with monkeypatch.context() as patch:
        patch.setattr(TimestampSigner,'get_timestamp',lambda self:int(time.time())-links.MAX_AGE-10)
        expired=links.issue(rid)
    for token in [expired,links.issue(rid)+'x',links.signer().dumps({'request_id':rid,'scope':'admin'})]:
        assert links.verify(token) is None
        response=pilot.get('/sourcing/email-access',params={'token':token})
        assert response.status_code==400 and 'action="/sourcing/access/email"' in response.text
        assert 'Новая заявка' not in response.text
    token=links.issue(rid);store.delete_request(rid)
    assert pilot.get('/sourcing/email-access',params={'token':token}).status_code==400


def test_recovery_uses_stored_recipient_is_limited_and_does_not_disclose_existence(pilot,monkeypatch):
    enable_mail(monkeypatch)
    rid=create(pilot,email='owner@example.com')
    csrf=fields(pilot)['csrf_token']
    assert pilot.post('/sourcing/access/email',data={'request_id':rid}).status_code==403
    for _ in range(5):
        response=pilot.post('/sourcing/access/email',data={'csrf_token':csrf,'request_id':rid})
        assert response.status_code==200
    with db.transaction() as conn:
        rows=db.execute(conn,"SELECT o.recipient,o.body FROM sourcing_notifications n JOIN notification_outbox o ON o.id=n.notification_id WHERE n.event='access_link'").fetchall()
    assert len(rows)==3 and all(row['recipient']=='owner@example.com' for row in rows)
    assert all('/sourcing/email-access?token=' in row['body'] for row in rows)
    missing=pilot.post('/sourcing/access/email',data={'csrf_token':csrf,'request_id':'SRC-'+'F'*20})
    assert missing.status_code==200
    assert 'Если номер верен' in missing.text and 'Если номер верен' in response.text


def test_wrong_autofilled_account_stays_on_access_form_instead_of_starting_new_request(pilot):
    csrf=fields(pilot)['csrf_token']
    response=pilot.post('/sourcing/access',data={'csrf_token':csrf,'request_id':'МОЙ КАБИНЕТ','access_code':'administrator-password'})
    assert response.status_code==404 and 'action="/sourcing/access/email"' in response.text
    assert 'Пароль администратора не подходит' in response.text
    assert 'Новая заявка' not in response.text


def test_prefilled_reference_and_all_six_languages(pilot):
    rid=create(pilot)
    # A separate browser has no original access credential.
    with TestClient(main.app,base_url='https://testserver') as buyer:
        from app.sourcing_i18n import COPY
        for language in COPY:
            response=buyer.get('/sourcing/access',params={'request_id':rid,'lang':language})
            assert response.status_code==200 and 'value="'+rid+'"' in response.text
            assert COPY[language]['email_send_link'] in response.text
        assert buyer.get('/sourcing/requests/'+rid).status_code==404
        assert 'action="/sourcing/access/email"' in buyer.get('/sourcing/requests/'+rid).text
