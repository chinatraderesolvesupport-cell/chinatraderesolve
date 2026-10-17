"""Exercise the intended client → actual provider adapter → private draft → approval flow."""
import asyncio
from dataclasses import replace
import json
import re
import time

import httpx
import pytest
from app import db, sourcing_research as research, sourcing_store as store, sourcing_mail
from test_sourcing import pilot, create, admin, admin_fields, payload, image_bytes


def enable(monkeypatch):
    monkeypatch.setenv('ENABLE_SOURCING_RESEARCH','true')
    monkeypatch.setattr(research,'settings',replace(db.settings,openai_api_key='isolated-test-key',
        openai_billing_ready=True,openai_model='gpt-4.1-mini',openai_document_model='gpt-4.1-mini'))


def search_response():
    return {'id':'resp_test','status':'completed','usage':{'total_tokens':50},'output':[
        {'type':'web_search_call','status':'completed','action':{'type':'search','sources':[{'url':'https://example.com/company'}]}},
        {'type':'message','content':[{'type':'output_text','text':'The seller claims to operate a factory. citation',
            'annotations':[{'type':'url_citation','url':'https://example.com/company','start_index':39,'end_index':47}]}]}]}


def draft_response():
    return {'status':'completed','usage':{'total_tokens':20},'output_text':json.dumps({
        'summary':'PRIVATE AI DRAFT — identity not independently verified',
        'findings':'Factory status is a seller claim [1].',
        'risks':'No independent factory evidence.',
        'next_steps':'Request the Chinese legal name, business licence and a sample agreement.'})}


def provider(monkeypatch, responses):
    calls=[]
    real_client=httpx.AsyncClient
    def respond(request):
        calls.append(json.loads(request.content))
        item=responses[min(len(calls)-1,len(responses)-1)]
        if isinstance(item,Exception): raise item
        return httpx.Response(item[0],json=item[1])
    monkeypatch.setattr(research.httpx,'AsyncClient',lambda **kwargs:real_client(**kwargs,transport=httpx.MockTransport(respond)))
    return calls


def wait_for(rid,states={'ready','failed','stale'}):
    for _ in range(150):
        item=store.get_request(rid)
        if item['research'] and item['research']['state'] in states:return item
        time.sleep(.02)
    pytest.fail('Research did not reach terminal state')


def test_submission_ai_draft_is_visible_in_main_inbox_until_approved(pilot,monkeypatch):
    enable(monkeypatch)
    calls=provider(monkeypatch,[(200,search_response()),(200,draft_response())])
    monkeypatch.setattr(sourcing_mail,'messages',lambda rid,email,event,locale:[
        {'recipient':email,'subject':event,'body':'isolated notification'}])
    rid=create(pilot,service='check',supplier='Example Company',email='private-buyer@example.com')
    item=wait_for(rid)
    assert item['research']['state']=='ready'
    assert item['status']=='in_progress' and item['draft']['findings'].endswith('[1].')
    assert item['report'] is None
    assert [n['event'] for n in item['notifications']]==['received']
    assert len(calls)==2 and calls[0]['store'] is False and calls[0]['tools']==[{'type':'web_search'}]
    assert calls[0]['max_tool_calls']==8
    assert 'private-buyer@example.com' not in json.dumps(calls)
    assert item['access_hash'] not in json.dumps(calls)
    public=pilot.get('/sourcing/requests/'+rid)
    assert 'PRIVATE AI DRAFT' not in public.text and 'research_client_review' not in public.text
    assert 'ожидает проверки' in public.text
    access_code=re.search(r'<code class="access-code">([^<]+)</code>',public.text).group(1)
    admin(pilot)
    dashboard=pilot.get('/admin').text
    assert rid in dashboard and 'НОВАЯ ЗАЯВКА' in dashboard
    assert 'Черновики на проверку: 1' in dashboard
    f=admin_fields(pilot,rid)
    assert not research.inbox()[0]['is_new']
    assert rid in pilot.get('/admin').text  # remains prominent as an unpublished draft
    page=pilot.get('/admin/sourcing/'+rid).text
    assert 'PRIVATE AI DRAFT' in page and 'https://example.com/company' in page
    assert pilot.post('/admin/sourcing/'+rid+'/report',data={**f,**item['draft']}).status_code==400
    response=pilot.post('/admin/sourcing/'+rid+'/report',data={**f,**item['draft'],'reviewed':'yes'},follow_redirects=False)
    assert response.status_code==303,response.text
    from test_sourcing import fields
    pilot.post('/sourcing/access',data={'csrf_token':fields(pilot)['csrf_token'],'request_id':rid,'access_code':access_code})
    assert 'PRIVATE AI DRAFT' in pilot.get('/sourcing/requests/'+rid).text
    completed=store.get_request(rid)
    assert completed['report']['reviewed_by_human'] and completed['draft']=={}
    assert [n['event'] for n in completed['notifications']]==['received','report']
    assert research.inbox()==[]
    assert pilot.post('/admin/sourcing/'+rid+'/report',data={**f,**item['draft'],'reviewed':'yes'}).status_code==409
    assert len(store.get_request(rid)['notifications'])==2


@pytest.mark.parametrize('responses,code',[
    ([(429,{'error':{'message':'private provider text'}})],'provider_429'),
    ([(200,{'status':'incomplete'})],'incomplete'),
    ([(200,{'status':'completed','output':[]})],'no_search'),
    ([(200,{'status':'completed','output':[{'type':'web_search_call','status':'completed'}]})],'no_sources'),
    ([(200,search_response()),(200,{'status':'completed','output_text':json.dumps({'summary':'S','findings':'Fake [999]','risks':'R','next_steps':'N'})})],'invalid_citations'),
])
def test_failures_never_publish_or_fake_a_success(pilot,monkeypatch,responses,code):
    enable(monkeypatch);calls=provider(monkeypatch,responses)
    rid=create(pilot)
    item=wait_for(rid)
    assert item['research']['state']=='failed' and item['research']['error_code']==code
    assert item['report'] is None and item['draft']=={} and item['status']=='received'
    assert len(calls)<=2
    assert 'private provider text' not in pilot.get('/sourcing/requests/'+rid).text
    admin(pilot)
    page=pilot.get('/admin/sourcing/'+rid).text
    assert code in page and '/research' in page
    assert rid in pilot.get('/admin').text


def test_draft_and_status_edits_cannot_be_overwritten_by_late_research(pilot):
    rid=create(pilot)
    research.enqueue(rid)
    job=research.claim()
    store.change_status(rid,1,'reviewing')
    store.change_status(rid,2,'in_progress')
    store.save_draft(rid,3,{'summary':'Human work'})
    assert research.finish(job,{'summary':'Late AI work'},{'sources':[]}) is False
    item=store.get_request(rid)
    assert item['draft']['summary']=='Human work' and item['research']['state']=='stale'
    with pytest.raises(store.Conflict):research.enqueue(rid,retry=True)


def test_deleting_a_running_request_cannot_resurrect_it(pilot):
    rid=create(pilot);research.enqueue(rid);job=research.claim()
    store.delete_request(rid)
    assert not research.finish(job,{'summary':'Late'},{'sources':[]})
    assert store.get_request(rid) is None
    with db.transaction() as conn:
        assert db.execute(conn,'SELECT COUNT(*) AS n FROM sourcing_research').fetchone()['n']==0


def test_daily_cap_counts_retries_and_queue_claims_are_exclusive(pilot,monkeypatch):
    monkeypatch.setenv('SOURCING_RESEARCH_DAILY_LIMIT','1')
    rid=create(pilot);research.enqueue(rid)
    job=research.claim();assert job and research.claim() is None
    assert research.finish(job,error='timeout') is False
    assert research.enqueue(rid,retry=True)
    assert research.claim()=={'limited':True}
    assert store.get_request(rid)['research']['error_code']=='daily_limit'


def test_recovery_and_authorization(pilot,monkeypatch):
    rid=create(pilot)
    assert pilot.post('/admin/sourcing/'+rid+'/research',data={}).status_code==401
    admin(pilot);f=admin_fields(pilot,rid)
    assert pilot.post('/admin/sourcing/'+rid+'/research',data={'version':1}).status_code==403
    assert pilot.post('/admin/sourcing/'+rid+'/research',data=f).status_code==503
    research.enqueue(rid);job=research.claim()
    with db.transaction() as conn:
        db.execute(conn,"UPDATE sourcing_research SET updated_at='2000-01-01T00:00:00+00:00' WHERE request_id=?",(rid,))
    pilot.get('/admin/sourcing/'+rid)
    assert store.get_request(rid)['research']['error_code']=='interrupted'
    assert not research.finish(job,{'summary':'late'},{'sources':[]})


@pytest.mark.parametrize('service',['search','check','prepare'])
def test_photos_are_available_and_saved_for_every_service(pilot,service):
    form=payload(pilot,service=service,supplier='Example supplier',requirements='Photo reference')
    response=pilot.post('/sourcing/requests',data=form,files={'photos':('sofa.jpg',image_bytes(),'image/jpeg')},follow_redirects=False)
    assert response.status_code==303,response.text
    item=store.get_request(response.headers['location'].split('/')[-1]);assert len(item['photos'])==1
    assert item['brief']['ai_processing_consent'] is True
    page=pilot.get(response.headers['location']).text
    assert 'Прикреплено фотографий: 1' in page


def test_mail_progress_is_private_and_contains_no_draft_or_access_code(pilot):
    rid=create(pilot)
    response=pilot.get('/sourcing/requests/'+rid+'/progress')
    assert response.status_code==200 and set(response.json())=={'mail'}
    assert response.headers['cache-control']=='no-store'
    from fastapi.testclient import TestClient
    from app import main
    with TestClient(main.app,base_url='https://testserver') as stranger:
        assert stranger.get('/sourcing/requests/'+rid+'/progress').status_code==404


def test_public_brief_strips_email_and_url_tokens():
    brief=research._public_brief({'email':'private@example.com','supplier':'https://example.com/item?secret=token#private',
                                 'requirements':'Contact private@example.com','access_code':'secret'})
    assert 'private@example.com' not in json.dumps(brief) and 'secret' not in json.dumps(brief)


def test_new_jobs_wake_a_busy_worker_without_losing_submissions(pilot,monkeypatch):
    enable(monkeypatch)
    started=[]
    async def delayed(item):
        started.append(item['id'])
        await asyncio.sleep(.08)
        return {'summary':'Draft','findings':'Evidence [1]','risks':'Unknown','next_steps':'Ask',
                'sources':'https://example.com','suppliers':[]},{'sources':['https://example.com'],'text':'Evidence [1]'}
    monkeypatch.setattr(research,'research',delayed)
    first=create(pilot);second=create(pilot)
    assert wait_for(first)['research']['state']=='ready'
    assert wait_for(second)['research']['state']=='ready'
    assert started==[first,second]
    # The idle event-driven worker must not hold a database polling loop.
    monkeypatch.setattr(research,'claim',lambda:pytest.fail('idle worker queried database'))
    time.sleep(.05)



def test_admin_retry_is_explicit_and_submission_replay_does_not_bill_twice(pilot,monkeypatch):
    enable(monkeypatch)
    calls=provider(monkeypatch,[(503,{}),(200,search_response()),(200,draft_response())])
    data=payload(pilot)
    result=pilot.post('/sourcing/requests',data=data,follow_redirects=False)
    rid=result.headers['location'].split('/')[-1]
    assert wait_for(rid)['research']['error_code']=='provider_503'
    replay=pilot.post('/sourcing/requests',data=data,follow_redirects=False)
    assert replay.status_code==303 and len(calls)==1
    admin(pilot)
    response=pilot.post('/admin/sourcing/'+rid+'/research',data=admin_fields(pilot,rid),follow_redirects=False)
    assert response.status_code==303,response.text
    assert wait_for(rid)['research']['state']=='ready' and len(calls)==3
    assert store.get_request(rid)['research']['attempts']==2


def test_startup_recovers_a_queued_consented_request(pilot,monkeypatch):
    rid=create(pilot)
    enable(monkeypatch)
    calls=provider(monkeypatch,[(200,search_response()),(200,draft_response())])
    pilot.portal.call(research.startup)
    assert wait_for(rid)['research']['state']=='ready' and len(calls)==2


def test_reference_photo_is_sent_only_with_ai_processing_consent(pilot):
    data=payload(pilot,requirements='Photo')
    response=pilot.post('/sourcing/requests',data=data,files={'photos':('item.jpg',image_bytes(),'image/jpeg')},follow_redirects=False)
    item=store.get_request(response.headers['location'].split('/')[-1])
    images=research._image_inputs(item)
    assert len(images)==1 and images[0]['image_url'].startswith('data:image/jpeg;base64,')
    item['brief'].pop('ai_processing_consent')
    assert research._image_inputs(item)==[]


def test_ai_pages_render_in_all_six_languages(pilot,monkeypatch):
    rid=create(pilot);enable(monkeypatch);admin(pilot)
    from app.sourcing_i18n import COPY
    for lang in ('ru','en','de','fr','es','sr'):
        page=pilot.get('/admin/sourcing/'+rid+'?lang='+lang)
        assert page.status_code==200 and COPY[lang]['research_heading'] in page.text
        page=pilot.get('/buying?lang='+lang)
        assert page.status_code==200 and COPY[lang]['live_ai'] in page.text
