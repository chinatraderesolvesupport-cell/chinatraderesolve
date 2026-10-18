"""Isolated HTTP workflow and access boundaries; no production data or outbound services."""
from dataclasses import replace
from io import BytesIO
import re
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from app import main, db, sourcing, sourcing_store as store

ADMIN='sourcing-test-admin-abcdefghijklmnopqrstuvwxyz-123456'
SECRET='sourcing-test-session-abcdefghijklmnopqrstuvwxyz-654321'


@pytest.fixture
def pilot(tmp_path,monkeypatch):
    local=replace(main.settings,database_url=None,database_path=tmp_path/'pilot.db',
                  admin_token=ADMIN,app_secret=SECRET,turnstile_site_key='',turnstile_secret_key='')
    monkeypatch.setattr(main,'settings',local)
    monkeypatch.setattr(db,'settings',local)
    monkeypatch.setattr(main,'admin_login_limiter',sourcing.SlidingWindowRateLimiter(limit=5,window_seconds=900))
    monkeypatch.setenv('ENABLE_SOURCING_PILOT','true')
    db.init_db();store.init_sourcing_db();sourcing.sourcing_stats.init_db()
    sourcing.sourcing_stats.limiter.events.clear()
    sourcing.limiter.events.clear();sourcing.access_limiter.events.clear();sourcing.feedback_limiter.events.clear()
    async def allow(*args):return True
    # install_sourcing captured the original function; its settings are patched above.
    with TestClient(main.app,base_url='https://testserver') as client:
        yield client


def fields(client):
    page=client.get('/sourcing');assert page.status_code==200
    return {k:re.search(r'name="'+k+r'" value="([^"]+)"',page.text).group(1)
            for k in ('csrf_token','submission')}


def payload(client,**updates):
    data={**fields(client),'service':'search','product':'Smart key','quantity':'100 or 1000',
          'destination':'Serbia','email':'buyer@example.com','requirements':'Требуется ключ с экраном и подтверждённая совместимость с автомобилем.',
          'match':'exact','consent':'yes'}
    data.update(updates);return data


def image_bytes():
    out=BytesIO();Image.new('RGB',(16,16),'blue').save(out,format='JPEG');return out.getvalue()


def create(client,**updates):
    response=client.post('/sourcing/requests',data=payload(client,**updates),follow_redirects=False)
    assert response.status_code==303,response.text
    return response.headers['location'].split('/')[-1]


def admin(client):
    response=client.post('/admin/login',data={'token':ADMIN},follow_redirects=False)
    assert response.status_code==303


def admin_fields(client,rid):
    page=client.get('/admin/sourcing/'+rid);assert page.status_code==200
    return {k:re.search(r'name="'+k+r'" value="([^"]+)"',page.text).group(1)
            for k in ('csrf_token','version')}


def move(client,rid,status):
    f=admin_fields(client,rid)
    return client.post('/admin/sourcing/'+rid+'/status',data={**f,'status':status},follow_redirects=False)


def test_real_flow_photo_draft_report_recovery_delete(pilot):
    client=pilot
    data=payload(client,product='',requirements='',unknown='yes',alternatives='yes',goal='Удобный доступ к машине')
    response=client.post('/sourcing/requests',data=data,
        files=[('photos',('key.jpg',image_bytes(),'image/jpeg'))],follow_redirects=False)
    assert response.status_code==303,response.text
    rid=response.headers['location'].split('/')[-1]
    page=client.get(response.headers['location']);assert 'Определить по фотографии' in page.text
    code=re.search(r'<code class="access-code">([^<]+)</code>',page.text).group(1)
    item=store.get_request(rid);pid=item['photos'][0]['id']
    url='/sourcing/requests/'+rid+'/photos/'+pid
    assert client.get(url).headers['content-type'].startswith('image/jpeg')
    assert client.get(url).headers['cache-control']=='no-store'
    with TestClient(main.app,base_url='https://testserver') as stranger:
        assert stranger.get('/sourcing/requests/'+rid).status_code==404
        assert stranger.get(url).status_code==404
        assert stranger.get('/admin/sourcing').status_code==401
        stranger.get('/sourcing')
        csrf=fields(stranger)['csrf_token']
        assert stranger.post('/sourcing/access',data={'csrf_token':csrf,'request_id':rid,'access_code':'wrong'}).status_code==404
        assert stranger.post('/sourcing/access',data={'csrf_token':csrf,'request_id':rid,'access_code':code},follow_redirects=False).status_code==303
        assert stranger.get(url).status_code==200
    admin(client)
    assert move(client,rid,'completed').status_code==409
    assert move(client,rid,'reviewing').status_code==303
    assert move(client,rid,'in_progress').status_code==303
    admin_page=client.get('/admin/sourcing/'+rid)
    assert '/admin/sourcing/'+rid+'/photos/'+pid in admin_page.text
    assert client.get('/admin/sourcing/'+rid+'/photos/'+pid).status_code==200
    draft={'summary':'Черновик не виден клиенту','findings':'Установлено','risks':'Не проверен завод','next_steps':'Запросить документы','sources':'https://example.com/source'}
    assert client.post('/admin/sourcing/'+rid+'/draft',data={**admin_fields(client,rid),**draft},follow_redirects=False).status_code==303
    assert store.get_request(rid)['draft']['summary']==draft['summary']
    assert store.get_request(rid)['report'] is None
    f=admin_fields(client,rid)
    assert client.post('/admin/sourcing/'+rid+'/report',data={**f,**draft}).status_code==400
    bad={**f,**draft,'sources':'javascript:alert(1)','reviewed':'yes'}
    assert client.post('/admin/sourcing/'+rid+'/report',data=bad).status_code==400
    good={**f,**draft,'summary':'<script>alert(1)</script>','reviewed':'yes'}
    assert client.post('/admin/sourcing/'+rid+'/report',data=good,follow_redirects=False).status_code==303
    assert client.post('/admin/sourcing/'+rid+'/report',data=good,follow_redirects=False).status_code==409
    assert store.get_request(rid)['status']=='completed'
    # Admin login clears the browser session; the saved code restores buyer access.
    csrf=fields(client)['csrf_token']
    client.post('/sourcing/access',data={'csrf_token':csrf,'request_id':rid,'access_code':code})
    page=client.get('/sourcing/requests/'+rid)
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in page.text
    assert '<script>alert(1)</script>' not in page.text
    assert 'Черновик не виден клиенту' not in page.text
    assert client.post('/sourcing/requests/'+rid+'/delete',data={'confirm':'delete'}).status_code==403
    assert client.post('/sourcing/requests/'+rid+'/delete',data={'csrf_token':csrf,'confirm':'delete'}).status_code==200
    assert store.get_request(rid) is None
    assert store.get_photo(rid,pid) is None
    with db.transaction() as conn:
        assert db.execute(conn,'SELECT COUNT(*) AS n FROM sourcing_reports').fetchone()['n']==0
        assert db.execute(conn,'SELECT COUNT(*) AS n FROM cases').fetchone()['n']==0


def test_idempotent_retry_and_multiple_tabs(pilot):
    first=payload(pilot)
    second=payload(pilot,product='Second product')
    a=pilot.post('/sourcing/requests',data=first,follow_redirects=False)
    replay=pilot.post('/sourcing/requests',data=first,follow_redirects=False)
    b=pilot.post('/sourcing/requests',data=second,follow_redirects=False)
    assert a.status_code==replay.status_code==b.status_code==303
    assert a.headers['location']==replay.headers['location']
    assert a.headers['location']!=b.headers['location']
    assert len(store.list_requests())==2


@pytest.mark.parametrize('updates',[
    {'email':'not-mail'}, {'service':'invalid'}, {'quantity':''}, {'destination':''},
    {'requirements':' '*60}, {'product':'','unknown':'yes'}, {'consent':''},
    {'service':'check','supplier':''}, {'alternatives':'yes','goal':' '},
    {'product':'x'*201}, {'csrf_token':'bad'}, {'submission':'wrong'},
])
def test_invalid_brief_not_persisted(pilot,updates):
    response=pilot.post('/sourcing/requests',data=payload(pilot,**updates))
    assert response.status_code in {400,403}
    assert not store.list_requests()


def test_real_images_required_and_photo_limits(pilot):
    data=payload(pilot)
    assert pilot.post('/sourcing/requests',data=data,files={'photos':('bad.jpg',b'not image','image/jpeg')}).status_code==400
    assert pilot.post('/sourcing/requests',data=data,files={'photos':('large.jpg',b'x'*(8*1024*1024+1),'image/jpeg')}).status_code==400
    assert pilot.post('/sourcing/requests',data=data,files=[('photos',('a.jpg',image_bytes(),'image/jpeg'))]*6).status_code==400
    assert not store.list_requests()


def test_disabled_routes_do_not_access_storage(pilot,monkeypatch):
    monkeypatch.setenv('ENABLE_SOURCING_PILOT','false')
    def forbidden(*args):raise AssertionError('disabled pilot must not query DB')
    monkeypatch.setattr(store,'get_request',forbidden)
    for path in ['/sourcing','/sourcing/requests/SRC-test','/admin/sourcing','/sourcing/access','/admin/sourcing-statistics','/sourcing/help','/sourcing/help/supplier','/sourcing/preview','/sourcing/reviews','/sourcing/feedback']:
        assert pilot.get(path).status_code==404


def test_optimistic_lock_and_admin_csrf(pilot):
    rid=create(pilot);admin(pilot);f=admin_fields(pilot,rid)
    assert pilot.post('/admin/sourcing/'+rid+'/status',data={'status':'reviewing','version':1}).status_code==403
    assert move(pilot,rid,'reviewing').status_code==303
    assert pilot.post('/admin/sourcing/'+rid+'/status',data={**f,'status':'in_progress'}).status_code==409
    assert store.get_request(rid)['status']=='reviewing'


def test_metadata_removed_and_format_detected(pilot):
    out=BytesIO();exif=Image.Exif();exif[270]='PRIVATE_METADATA'
    Image.new('RGB',(10,10)).save(out,format='JPEG',exif=exif)
    response=pilot.post('/sourcing/requests',data=payload(pilot),
        files={'photos':('wrong.png',out.getvalue(),'image/png')},follow_redirects=False)
    assert response.status_code==303
    rid=response.headers['location'].split('/')[-1];item=store.get_request(rid)
    photo=store.get_photo(rid,item['photos'][0]['id'])
    assert photo['content_type']=='image/jpeg'
    assert b'PRIVATE_METADATA' not in photo['content']


def test_nonsearch_and_unselected_alternatives_discard_extra_fields(pilot):
    rid=create(pilot,service='prepare',supplier='Seller',goal='must not carry over',
               limitations='discard',documents='Invoice',language='English',alternatives='yes')
    brief=store.get_request(rid)['brief']
    assert not brief['alternatives_requested'] and not brief['goal'] and not brief['limitations']
    assert brief['documents']=='Invoice'
    rid=create(pilot,documents='not applicable',language='English',goal='not requested')
    brief=store.get_request(rid)['brief']
    assert not brief['documents'] and not brief['language'] and not brief['goal']


def test_sourcing_mail_is_atomic_private_and_deduplicated(pilot, monkeypatch):
    from app import sourcing_mail
    monkeypatch.setattr(sourcing_mail, 'configured', lambda: True)
    monkeypatch.setattr(sourcing_mail, 'settings', replace(main.settings,
        public_base_url='https://pilot.example', admin_email='operator@example.com'))
    data=payload(pilot)
    response=pilot.post('/sourcing/requests',data=data,follow_redirects=False)
    rid=response.headers['location'].split('/')[-1]
    assert pilot.post('/sourcing/requests',data=data,follow_redirects=False).status_code==303
    rows=db.pending_notifications()
    assert len(rows)==2
    assert data['requirements'] not in rows[0]['body']
    assert '/sourcing/email-access?token=' in rows[0]['body']
    page=pilot.get(response.headers['location'])
    code=re.search(r'<code class="access-code">([^<]+)</code>',page.text).group(1)
    assert code not in rows[0]['body']
    assert 'ожидает отправки' in page.text and '<details open>' in page.text
    assert '<dt>Ограничения</dt>' not in page.text
    admin(pilot)
    move(pilot,rid,'reviewing');move(pilot,rid,'in_progress')
    report={'summary':'Готовый вывод','findings':'Установлено','risks':'Ограничения проверки',
            'next_steps':'Следующие действия','sources':'https://example.com','reviewed':'yes'}
    f=admin_fields(pilot,rid)
    assert pilot.post('/admin/sourcing/'+rid+'/report',data={**f,**report},follow_redirects=False).status_code==303
    assert pilot.post('/admin/sourcing/'+rid+'/report',data={**f,**report},follow_redirects=False).status_code==409
    assert len(db.pending_notifications())==3
    assert report['summary'] not in db.pending_notifications()[-1]['body']
    store.delete_request(rid)
    assert not db.pending_notifications()


def test_disabled_mail_explained_on_confirmation(pilot):
    rid=create(pilot)
    page=pilot.get('/sourcing/requests/'+rid)
    assert 'Письмо не отправляется' in page.text
    assert 'Что дальше?' in page.text
    assert not db.pending_notifications()


@pytest.mark.parametrize('lang',['ru','en','de','fr','es','sr'])
def test_complete_language_flow_free_feedback_and_assessment(pilot,lang):
    from app.sourcing_i18n import COPY
    c=pilot;copy=COPY[lang]
    page=c.get('/sourcing?lang='+lang)
    assert '<html lang="'+lang+'">' in page.text
    assert copy['free_short'] in page.text and copy['submit'] in page.text
    if lang!='ru':
        assert not re.search('[А-Яа-яЁё]',re.sub(r'<div class="languages".*?</div>','',page.text))
    rid=create(c,product='Test product',requirements='A product with compatibility requirements and documentation needs.')
    assert store.get_request(rid)['brief']['locale']==lang
    assert store.get_request(rid)['brief']['pricing_mode']=='launch_free'
    for path in ('/sourcing/access','/sourcing/requests/'+rid,'/sourcing/reviews','/sourcing/feedback?request_id='+rid):
        page=c.get(path)
        assert page.status_code==200 and copy['free_short'] in page.text
        if lang!='ru': assert not re.search('[А-Яа-яЁё]',re.sub(r'<div class="languages".*?</div>','',page.text))
    page=c.post('/sourcing/access',data={'csrf_token':'invalid','request_id':rid,'access_code':'bad'})
    assert page.status_code==403 and copy['error_expired'] in page.text
    admin(c)
    for path in ('/admin/sourcing','/admin/sourcing/feedback','/admin/sourcing/'+rid):
        page=c.get(path+'?lang='+lang)
        assert page.status_code==200 and copy['admin_workspace'] in page.text
        assert copy['free_short'] not in page.text
        if lang!='ru': assert not re.search('[А-Яа-яЁё]',page.text)
    move(c,rid,'reviewing');move(c,rid,'in_progress')
    page=c.get('/admin/sourcing/'+rid)
    assert copy['assessment_optional'] in page.text
    if lang!='ru': assert not re.search('[А-Яа-яЁё]',re.sub(r'<div class="languages".*?</div>','',page.text))


def feedback_fields(c,request_id=''):
    page=c.get('/sourcing/feedback'+('?request_id='+request_id if request_id else ''))
    assert page.status_code==200
    return {k:re.search(r'name="'+k+r'" value="([^"]*)"',page.text).group(1)
            for k in ('csrf_token','submission','request_id')}


def test_feedback_privacy_consent_moderation_and_replay(pilot):
    c=pilot;rid=create(c)
    data={**feedback_fields(c,rid),'kind':'review','rating':'1','message':'Неудобно найти кнопку, нужна доработка. <script>alert(1)</script>',
          'consent':'yes','publish_consent':'yes'}
    assert c.post('/sourcing/feedback',data=data).status_code==200
    assert c.post('/sourcing/feedback',data=data).status_code==200
    entries=store.list_feedback();assert len(entries)==1
    assert entries[0]['request_id']==rid
    assert not store.list_feedback(public=True)
    with TestClient(main.app,base_url='https://testserver') as stranger:
        assert stranger.get('/sourcing/feedback?request_id='+rid).status_code==404
        assert stranger.get('/admin/sourcing/feedback').status_code==401
        assert data['message'] not in stranger.get('/sourcing/reviews').text
    admin(c)
    page=c.get('/admin/sourcing/feedback');assert page.status_code==200
    assert '&lt;script&gt;' in page.text and '<script>alert(1)</script>' not in page.text
    csrf=re.search(r'name="csrf_token" value="([^"]+)"',page.text).group(1)
    entry=entries[0];path='/admin/sourcing/feedback/'+entry['id']
    assert c.post(path,data={'version':'1','status':'published'}).status_code==403
    assert c.post(path,data={'csrf_token':csrf,'version':'1','status':'published'},follow_redirects=False).status_code==303
    assert c.post(path,data={'csrf_token':csrf,'version':'1','status':'rejected'}).status_code==409
    public=c.get('/sourcing/reviews')
    assert '1 / 5' in public.text and '&lt;script&gt;' in public.text
    assert rid not in public.text and 'buyer@example.com' not in public.text
    store.delete_request(rid)
    assert not store.list_feedback(public=True)


@pytest.mark.parametrize('kind,consent',[('bug','yes'),('suggestion','yes'),('review','')])
def test_feedback_without_publication_permission_cannot_be_published(pilot,kind,consent):
    data={**feedback_fields(pilot),'kind':kind,'rating':'5','message':'A private note to the team only.',
          'consent':'yes','publish_consent':consent}
    assert pilot.post('/sourcing/feedback',data=data).status_code==200
    entry=store.list_feedback()[0]
    assert not entry['publish_consent']
    with pytest.raises(ValueError):store.moderate_feedback(entry['id'],1,'published')
    assert not store.list_feedback(public=True)


def test_feedback_invalid_and_forged_request_are_not_stored(pilot):
    base={**feedback_fields(pilot),'kind':'review','message':'A valid message to the team.','consent':'yes'}
    for changes in ({'rating':'9'},{'consent':''},{'message':'short'},{'csrf_token':'bad'},
                    {'submission':'fake'},{'request_id':'SRC-NOT-OWNED'},{'kind':'other'}):
        sourcing.feedback_limiter.events.clear()
        r=pilot.post('/sourcing/feedback',data={**base,**changes})
        assert r.status_code in {400,403,404}
    assert not store.list_feedback()


def test_supplier_evidence_and_archived_review_are_validated(pilot):
    rid=create(pilot);admin(pilot)
    move(pilot,rid,'reviewing');move(pilot,rid,'in_progress')
    draft={'summary':'Supplier assessment','findings':'Documents checked','risks':'Delivery remains uncertain',
           'next_steps':'Request a sample','sources':'https://example.com/company','reviewed':'yes',
           'supplier_1_name':'Example supplier','supplier_1_role':'reseller','supplier_1_outcome':'concerns',
           'supplier_1_checked_on':'2026-01-01','supplier_1_notes':'Public history needs further clarification.',
           'supplier_1_sources':'https://example.com/company','supplier_1_archive':'found',
           'supplier_1_archive_date':'2025-12-01','supplier_1_archive_url':'https://web.archive.org/web/20251201/https://example.com/company'}
    path='/admin/sourcing/'+rid
    for bad in ({'supplier_1_archive_url':''},{'supplier_1_sources':'javascript:alert(1)'},
                {'supplier_1_checked_on':'2999-01-01'},{'supplier_1_archive_date':'2026-02-01'},
                {'supplier_1_role':'trusted'},{'supplier_1_name':''}):
        assert pilot.post(path+'/report',data={**draft,**bad,**admin_fields(pilot,rid)}).status_code==400
    assert pilot.post(path+'/draft',data={**draft,**admin_fields(pilot,rid)},follow_redirects=False).status_code==303
    assert store.get_request(rid)['draft']['suppliers'][0]['role']=='reseller'
    assert pilot.post(path+'/report',data={**draft,**admin_fields(pilot,rid)},follow_redirects=False).status_code==303
    report=store.get_request(rid)['report'];assert len(report['suppliers'])==1
    page=pilot.get(path+'?lang=en')
    assert 'Public snapshot found' in page.text and 'Example supplier' in page.text
    assert 'proves neither removal' in page.text


@pytest.mark.parametrize('lang',['ru','en','de','fr','es','sr'])
def test_unified_preview_languages_routes_and_honest_examples(pilot,lang):
    from app.sourcing_i18n import COPY
    copy=COPY[lang]
    for path in ('/sourcing/preview','/sourcing/preview/dispute','/sourcing/preview/account'):
        page=pilot.get(path+'?lang='+lang)
        assert page.status_code==200
        assert '<html lang="'+lang+'">' in page.text
        assert 'noindex' in page.headers['x-robots-tag']
        assert copy['u_preview'] in page.text
        if lang!='ru':
            assert not re.search('[А-Яа-яЁё]',re.sub(r'<div class="wrap languages".*?</div>','',page.text))
    page=pilot.get('/sourcing/preview?lang='+lang)
    assert '/sourcing?lang='+lang+'&amp;service=search' in page.text
    assert '/sourcing/preview/dispute?lang='+lang in page.text
    assert copy['u_samples_note'] in page.text
    assert page.text.count('class="example"')==3
    assert copy['u_step1'] in page.text and copy['u_step3_text'] in page.text
    assert not store.list_requests()


@pytest.mark.parametrize('service',['search','check','prepare','invalid'])
def test_unified_preview_passes_service_choice(pilot,service):
    page=pilot.get('/sourcing?service='+service)
    selected=service if service!='invalid' else 'search'
    assert re.search(r'<option value="'+selected+r'" selected>',page.text)


@pytest.mark.parametrize('lang',['ru','en','de','fr','es','sr'])
def test_buyer_guides_and_optional_context(pilot,lang):
    hub=pilot.get('/sourcing/help?lang='+lang)
    assert hub.status_code==200
    assert 'noindex' in hub.headers['x-robots-tag']
    for topic in ('supplier','spec','cost','photo'):
        page=pilot.get('/sourcing/help/'+topic+'?lang='+lang)
        assert page.status_code==200
        assert f'<html lang="{lang}">' in page.text
        assert sourcing.COPY[lang]['g_'+topic+'_title'] in page.text
    assert pilot.get('/sourcing/help/not-a-topic').status_code==404
    rid=create(pilot,platform='1688',purchase_purpose='resale')
    item=store.get_request(rid)
    assert item['brief']['platform']=='1688'
    assert item['brief']['purchase_purpose']=='resale'
    page=pilot.get('/sourcing/requests/'+rid+'?lang='+lang)
    assert sourcing.COPY[lang]['purpose_resale'] in page.text
    assert pilot.post('/sourcing/requests',data=payload(pilot,platform='arbitrary')).status_code==400


def test_visit_aggregates_privacy_and_actual_use(pilot):
    from app import sourcing_stats as stats
    from datetime import datetime,timedelta,timezone
    chrome={'user-agent':'Mozilla/5.0 Chrome/130 Safari/537.36'}
    assert pilot.get('/admin/sourcing-statistics').status_code==401
    pilot.get('/sourcing/preview',headers=chrome)
    pilot.get('/sourcing/help/supplier?lang=en&access_code=must-not-store',headers=chrome)
    pilot.get('/sourcing/help/not-found',headers=chrome)
    pilot.get('/sourcing/access',headers=chrome)
    pilot.get('/health',headers=chrome)
    pilot.get('/sourcing',headers={**chrome,'dnt':'1'})
    pilot.get('/sourcing',headers={**chrome,'sec-gpc':'1'})
    pilot.get('/sourcing',headers={'user-agent':'Googlebot'})
    row=stats.summary()['periods'][0]
    assert (row['views'],row['sessions'])==(2,1)
    rid=create(pilot)
    pilot.get('/sourcing/requests/'+rid,headers=chrome)
    assert stats.summary()['periods'][0]['requests']==1
    now=db.utcnow()
    with db.transaction() as conn:
        for revision in (2,3):
            db.execute(conn,'INSERT INTO sourcing_reports VALUES (?,?,?,?)',(rid,revision,'{}',now))
        old=(datetime.now(timezone.utc).date()-timedelta(days=10)).isoformat()
        db.execute(conn,'INSERT INTO sourcing_daily_stats VALUES (?,?,?)',(old,10,5))
        rows=[dict(r) for r in db.execute(conn,'SELECT * FROM sourcing_daily_stats').fetchall()]
        assert all(set(r)=={'day','pageviews','sessions'} for r in rows)
        assert 'must-not-store' not in str(rows)
    result=stats.summary()
    assert result['periods'][0]['reports']==1
    assert result['periods'][1]['views']==2
    assert result['periods'][2]['views']==12
    admin(pilot)
    pilot.get('/sourcing/preview',headers=chrome)
    assert stats.summary()['periods'][0]['views']==2
    page=pilot.get('/admin/sourcing-statistics')
    assert page.status_code==200 and 'no-store' in page.headers['cache-control']
    assert '/admin/sourcing-statistics' in pilot.get('/admin').text
    with db.transaction() as conn:
        db.execute(conn,'DELETE FROM sourcing_requests WHERE id=?',(rid,))
    assert stats.summary()['periods'][0]['requests']==0
    assert stats.summary()['periods'][0]['reports']==0


def test_statistics_failure_does_not_block_public_page(pilot,monkeypatch):
    from app import sourcing_stats as stats
    def broken():raise RuntimeError('database offline')
    monkeypatch.setattr(stats,'transaction',broken)
    response=pilot.get('/sourcing/preview',headers={'user-agent':'Mozilla/5.0 Chrome/130'})
    assert response.status_code==200


def test_admin_navigation_and_disabled_pilot_boundary(pilot,monkeypatch):
    rid=create(pilot)
    admin(pilot)
    home=pilot.get('/admin')
    assert 'href="/admin/sourcing"' in home.text
    assert 'href="/admin/sourcing-statistics"' in home.text
    assert '/admin/sourcing/'+rid in pilot.get('/admin/sourcing').text
    assert pilot.get('/admin/sourcing/'+rid).status_code==200
    monkeypatch.setenv('ENABLE_SOURCING_PILOT','false')
    home=pilot.get('/admin')
    assert home.status_code==200
    assert 'href="/admin/sourcing"' not in home.text
    assert 'href="/admin/sourcing-statistics"' not in home.text
    assert pilot.get('/admin/sourcing').status_code==404
    # Turning the pilot off does not discard its data or alter dispute records.
    assert store.get_request(rid)['id']==rid
    with db.transaction() as conn:
        assert db.execute(conn,'SELECT COUNT(*) AS n FROM cases').fetchone()['n']==0


def test_sourcing_lifecycle_preserves_existing_dispute(pilot):
    """Both directions share an isolated database; never use a real customer case."""
    dispute=db.create_case(
        {'full_name':'Synthetic audit buyer','email':'audit@example.com',
         'main_problem':'Goods not received','description':'Synthetic non-delivery case used only in isolated tests.',
         'ai_consent':True,'sharing_authority':True,'free_access_terms':True,'no_guarantee':True},
        {'decision':'needs_information','priority':50,'risk_level':'medium','source':'rules','public_message':'Synthetic audit'},
        'CTR-TEST-COEXIST','synthetic-private-token')
    rid=create(pilot)
    admin(pilot)
    assert pilot.get('/admin/case/'+str(dispute['id'])).status_code==200
    # Opening an existing case may record an admin view; snapshot after that.
    before=db.get_case(dispute['id'])
    assert move(pilot,rid,'reviewing').status_code==303
    assert move(pilot,rid,'in_progress').status_code==303
    report={'summary':'Synthetic result','findings':'Documented','risks':'Not verified',
            'next_steps':'Ask supplier','sources':'https://example.com/evidence','reviewed':'yes'}
    assert pilot.post('/admin/sourcing/'+rid+'/report',data={**admin_fields(pilot,rid),**report},follow_redirects=False).status_code==303
    assert db.get_case(dispute['id'])==before
    store.delete_request(rid)
    assert db.get_case(dispute['id'])==before
    assert db.get_case_by_public('CTR-TEST-COEXIST','synthetic-private-token')==before
    assert pilot.get('/case/CTR-TEST-COEXIST/synthetic-private-token').status_code==200


@pytest.mark.parametrize('lang',['ru','en','de','fr','es','sr'])
def test_combined_home_free_and_privacy(pilot,monkeypatch,lang):
    monkeypatch.setenv('ENABLE_SOURCING_LIVE','true')
    page=pilot.get('/?lang='+lang)
    assert page.status_code==200
    assert 'id="homeBuy"' in page.text and 'id="homeDispute"' in page.text
    assert 'id="homeChooseHelp" href="#directions"' in page.text
    assert sourcing.COPY[lang]['u_headline'] in page.text
    assert 'id="caseForm"' in page.text
    assert sourcing.COPY[lang]['free_short'] in page.text
    assert sourcing.COPY[lang]['sourcing_privacy'] in pilot.get('/privacy?lang='+lang).text
    assert sourcing.COPY[lang]['live_operator'] in pilot.get('/sourcing?lang='+lang).text


@pytest.mark.parametrize('path',['/','/buying','/disputes'])
def test_combined_home_counter_does_not_wake_database(pilot,monkeypatch,path):
    from app import sourcing_stats as stats
    monkeypatch.setenv('ENABLE_SOURCING_LIVE','true')
    stats._pending.clear()
    original=stats.transaction
    def forbidden():raise AssertionError('homepage must not wake database')
    monkeypatch.setattr(stats,'transaction',forbidden)
    response=pilot.get(path,headers={'user-agent':'Mozilla/5.0 Chrome/130'})
    assert response.status_code==200
    assert sum(v[0] for v in stats._pending.values())==1
    monkeypatch.setattr(stats,'transaction',original)
    assert stats.summary()['periods'][0]['views']==1
    assert not stats._pending


def test_only_public_buyer_guides_enter_live_search_index(pilot,monkeypatch):
    monkeypatch.setenv('ENABLE_SOURCING_LIVE','true')
    monkeypatch.setattr(main,'search_indexing_checks',lambda:{'ready':True})
    page=pilot.get('/sourcing/help/supplier?lang=de&utm_source=test')
    assert page.headers['x-robots-tag']=='index, follow'
    assert '/sourcing/help/supplier?lang=de"' in page.text
    assert 'rel="alternate" hreflang="sr"' in page.text
    assert 'utm_source=test' not in page.text
    sitemap=pilot.get('/sitemap.xml').text
    assert '/sourcing/help/supplier?lang=de' in sitemap
    assert '/sourcing/requests/' not in sitemap
    rid=create(pilot)
    assert 'noindex' in pilot.get('/sourcing/requests/'+rid).headers['x-robots-tag']
    assert 'noindex' in pilot.get('/sourcing').headers['x-robots-tag']
    monkeypatch.setattr(main,'search_indexing_checks',lambda:{'ready':False})
    assert 'noindex' in pilot.get('/sourcing/help').headers['x-robots-tag']
    assert '/sourcing/help/supplier' not in pilot.get('/sitemap.xml').text


def test_private_integration_archive_is_complete_and_read_only(pilot,tmp_path):
    import gzip,json,stat
    from scripts.backup_for_integration import backup
    rid=create(pilot)
    original=store.get_request(rid)
    path=tmp_path/'private-backup.jsonl.gz'
    result=backup(path)
    assert result['verified_complete'] and result['counts']['sourcing_requests']==1
    assert stat.S_IMODE(path.stat().st_mode)==0o600
    with gzip.open(path,'rt',encoding='utf-8') as stream:rows=[json.loads(line) for line in stream]
    assert rows[-1]['complete'] is True
    assert any(r.get('table')=='sourcing_requests' and r['row']['id']==rid for r in rows)
    assert store.get_request(rid)==original
    with pytest.raises(FileExistsError):backup(path)


def test_internal_checks_do_not_count_as_customer_requests(pilot,monkeypatch):
    from app import sourcing_stats as stats
    rid=create(pilot,system_test='true')
    brief=store.get_request(rid)['brief']
    assert 'system_test' not in brief  # Public submissions cannot opt out of metrics.
    internal,access=store.create_request({**brief,'system_test':True},'operator@example.com',[],'internal-system-check')
    with db.transaction() as conn:
        db.execute(conn,'INSERT INTO sourcing_reports VALUES (?,?,?,?)',(internal,2,'{}',db.utcnow()))
    assert stats.summary()['periods'][0]['requests']==1
    assert stats.summary()['periods'][0]['reports']==0
    assert store.get_request(internal)['brief']['system_test'] is True
    monkeypatch.setenv('SOURCING_SYSTEM_TEST_REQUEST_ID',rid)
    assert stats.summary()['periods'][0]['requests']==0
    assert store.get_request(rid) is not None


@pytest.mark.parametrize('lang',['ru','en','de','fr','es','sr'])
def test_independent_public_directions_keep_private_forms_and_old_links(pilot,monkeypatch,lang):
    monkeypatch.setenv('ENABLE_SOURCING_LIVE','true')
    monkeypatch.setattr(main,'search_indexing_checks',lambda:{'ready':True})
    home=pilot.get('/?lang='+lang)
    assert 'combined-number' not in home.text.split('<main',1)[1].split('</main>',1)[0]
    assert 'href="/buying?lang='+lang+'"' in home.text
    assert 'href="/disputes?lang='+lang+'"' in home.text
    assert 'id="legacyDispute"' in home.text and 'id="caseForm"' in home.text
    buying=pilot.get('/buying?lang='+lang)
    assert buying.status_code==200 and 'index, follow'==buying.headers['x-robots-tag']
    assert sourcing.COPY[lang]['u_buy_risk'] in buying.text
    assert '/disputes?lang='+lang in buying.text
    dispute=pilot.get('/disputes?lang='+lang)
    assert dispute.status_code==200 and 'id="disputeApply"' in dispute.text
    assert 'id="legacyDispute"' not in dispute.text
    assert 'id="caseForm"' in dispute.text and '/buying?lang='+lang in dispute.text
    assert 'noindex' in pilot.get('/sourcing?lang='+lang).headers['x-robots-tag']
    sitemap=pilot.get('/sitemap.xml').text
    assert '/buying?lang='+lang in sitemap and '/disputes?lang='+lang in sitemap


def test_admin_statistics_disputes_periods_and_workspace_navigation(pilot):
    from app import sourcing_stats as stats
    from datetime import datetime,timedelta,timezone
    payload={'full_name':'Isolated buyer','email':'buyer@example.com','main_problem':'Goods not received',
             'description':'Synthetic isolated case','ai_consent':True,'sharing_authority':True,
             'free_access_terms':True,'no_guarantee':True}
    triage={'decision':'closed','priority':50,'risk_level':'medium','source':'rules','public_message':'Test'}
    cases=[db.create_case(payload,triage,'CTR-STATS-'+str(i),'private-'+str(i)) for i in range(3)]
    with db.transaction() as conn:
        old=(datetime.now(timezone.utc)-timedelta(days=10)).isoformat()
        db.execute(conn,'UPDATE cases SET created_at=? WHERE id=?',(old,cases[1]['id']))
        db.execute(conn,'UPDATE cases SET deleted_at=? WHERE id=?',(db.utcnow(),cases[2]['id']))
    assert [row['disputes'] for row in stats.summary()['periods']]==[1,1,2]
    rid=create(pilot)
    admin(pilot)
    for path in ['/admin','/admin/feedback','/admin/case/'+str(cases[0]['id']),
                 '/admin/sourcing','/admin/sourcing/'+rid,'/admin/sourcing/feedback',
                 '/admin/sourcing-statistics?days=30']:
        page=pilot.get(path)
        assert page.status_code==200
        assert 'aria-label="Кабинет администратора"' in page.text
        assert 'Рабочий кабинет</a>' in page.text and '>Обновить</a>' in page.text
        assert 'action="/admin/logout"' in page.text
        assert '/static/admin-workspace.css' in page.text
        assert 'site-brand' not in page.text
    page=pilot.get('/admin/sourcing-statistics?days=30')
    assert 'days=30" aria-current="page"' in page.text
    assert 'Как считаем показатели' in page.text
    assert 'Подбор и проверку выполняет оператор' not in page.text
    assert 'days=7" aria-current="page"' in pilot.get('/admin/sourcing-statistics?days=bad').text
    assert 'admin-toolbar' not in pilot.get('/sourcing').text
    assert 'admin-toolbar' not in pilot.get('/sourcing/requests/'+rid).text


def deletion_form(client,path):
    page=client.get(path)
    assert page.status_code==200,page.text
    return {key:re.search(r'name="'+key+r'" value="([^"]+)"',page.text).group(1)
            for key in ('csrf_token','delete_nonce')}


def deletion_case(reference):
    return db.create_case(
        {'full_name':'Isolated buyer','email':'buyer@example.com','main_problem':'Goods not received',
         'description':'Isolated deletion test','ai_consent':True,'sharing_authority':True,
         'free_access_terms':True,'no_guarantee':True},
        {'decision':'closed','priority':1,'risk_level':'low','source':'rules','public_message':'Test'},
        reference,'private-test-'+reference)


@pytest.mark.parametrize('kind',['case','sourcing'])
def test_admin_single_deletion_confirmation_isolation_and_cascades(pilot,kind):
    case=deletion_case('CTR-DELETE');other_case=deletion_case('CTR-KEEP')
    rid=create(pilot);other_rid=create(pilot)
    with db.transaction() as conn:
        db.execute(conn,'INSERT INTO case_documents(case_id,created_at,original_name,content_type,size_bytes,page_count,sha256,content_blob) VALUES (?,?,?,?,?,?,?,?)',
                   (case['id'],db.utcnow(),'proof.txt','text/plain',4,1,'test',b'test'))
        db.execute(conn,'INSERT INTO sourcing_photos VALUES (?,?,?,?,?)',('photo',rid,'key.jpg','image/jpeg',image_bytes()))
        db.execute(conn,'INSERT INTO sourcing_reports VALUES (?,?,?,?)',(rid,1,'{}',db.utcnow()))
    # Populate every personal-content relation so cascade assertions are meaningful.
    db.save_feedback(case['id'],{'rating':3,'feedback_text':'Synthetic feedback','display_name':'Test','testimonial_consent':False})
    db.queue_notification(case['id'],'buyer@example.com','Synthetic subject','Synthetic body')
    store.create_feedback('isolated-feedback',rid,'review',3,'Synthetic sourcing feedback','ru',True)
    with db.transaction() as conn:
        db.execute(conn,"INSERT INTO case_messages(case_id,created_at,author,body) VALUES (?,?,'client','Synthetic message')",(case['id'],db.utcnow()))
        db.execute(conn,"INSERT INTO document_analyses(case_id,created_at,updated_at,status) VALUES (?,?,?,'completed')",(case['id'],db.utcnow(),db.utcnow()))
        notification_id=db._insert_notifications(conn,None,[{'recipient':'buyer@example.com','subject':'Test','body':'Synthetic sourcing notification'}])[0]
        db.execute(conn,'INSERT INTO sourcing_notifications VALUES (?,?,?)',(rid,notification_id,'received'))
    path='/admin/case/'+str(case['id'])+'/delete' if kind=='case' else '/admin/sourcing/'+rid+'/delete'
    other_path='/admin/case/'+str(other_case['id'])+'/delete' if kind=='case' else '/admin/sourcing/'+other_rid+'/delete'
    assert pilot.get(path).status_code==401
    assert pilot.post(path,data={'confirm':'delete'}).status_code==401
    admin(pilot)
    data=deletion_form(pilot,path)
    assert db.get_case(case['id']) and store.get_request(rid)
    assert pilot.post(path,data={**data,'csrf_token':'invalid','confirm':'delete'}).status_code==403
    assert pilot.post(path,data=data).status_code==400
    assert pilot.post(other_path,data={**data,'confirm':'delete'}).status_code==409
    with db.transaction() as conn:
        if kind=='case':db.execute(conn,'UPDATE cases SET updated_at=? WHERE id=?',('changed',case['id']))
        else:db.execute(conn,'UPDATE sourcing_requests SET version=version+1 WHERE id=?',(rid,))
    assert pilot.post(path,data={**data,'confirm':'delete'}).status_code==409
    data=deletion_form(pilot,path)
    response=pilot.post(path,data={**data,'confirm':'delete'},follow_redirects=False)
    assert response.status_code==303,response.text
    assert 'deleted=1' in response.headers['location']
    if kind=='case':assert 'view=closed' in response.headers['location']
    assert pilot.post(path,data={**data,'confirm':'delete'}).status_code==409
    assert pilot.get('/admin').status_code==200
    assert db.get_case(other_case['id']) and store.get_request(other_rid)
    with db.transaction() as conn:
        if kind=='case':
            assert not db.get_case(case['id'])
            assert db.execute(conn,'SELECT COUNT(*) AS n FROM cases WHERE id=?',(case['id'],)).fetchone()['n']==0
            for table in ('case_documents','case_messages','document_analyses','audit_log','feedback','notification_outbox'):
                assert db.execute(conn,'SELECT COUNT(*) AS n FROM '+table+' WHERE case_id=?',(case['id'],)).fetchone()['n']==0
            assert store.get_request(rid)
        else:
            assert store.get_request(rid) is None
            for table in ('sourcing_photos','sourcing_reports','sourcing_events','sourcing_feedback','sourcing_notifications'):
                assert db.execute(conn,'SELECT COUNT(*) AS n FROM '+table+' WHERE request_id=?',(rid,)).fetchone()['n']==0
            assert db.get_case(case['id'])
    if kind=='case':assert pilot.get('/case/CTR-DELETE/private-test-CTR-DELETE').status_code==404
    else:assert pilot.get('/sourcing/requests/'+rid).status_code==404


def test_admin_dispute_deletion_waits_for_running_analysis(pilot):
    case=deletion_case('CTR-RUNNING');admin(pilot)
    with db.transaction() as conn:
        db.execute(conn,"INSERT INTO document_analyses(case_id,created_at,updated_at,status,model,result_json,error,run_token) VALUES (?,?,?,'running','','{}','','active')",(case['id'],db.utcnow(),db.utcnow()))
    path='/admin/case/'+str(case['id'])+'/delete'
    data=deletion_form(pilot,path)
    assert pilot.post(path,data={**data,'confirm':'delete'}).status_code==409
    assert db.get_case(case['id']) is not None


def test_admin_delete_intents_expire_and_keep_multiple_tabs(monkeypatch):
    from app import admin_deletion
    from types import SimpleNamespace
    request=SimpleNamespace(session={})
    now=admin_deletion.time.time()
    first=admin_deletion.begin(request,'case:1','v1')
    second=admin_deletion.begin(request,'sourcing:2','v2')
    assert admin_deletion.validate(request,'case:1',first,'delete')=='v1'
    admin_deletion.finish(request,first)
    assert admin_deletion.validate(request,'sourcing:2',second,'delete')=='v2'
    monkeypatch.setattr(admin_deletion.time,'time',lambda:now+601)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:admin_deletion.validate(request,'sourcing:2',second,'delete')
    assert error.value.status_code==409


def test_main_workspace_shows_both_request_directions(pilot):
    deletion_case('CTR-DIRECTION');create(pilot);admin(pilot)
    page=pilot.get('/admin')
    assert 'Споры с поставщиками' in page.text and 'Подбор поставщиков' in page.text
    assert 'Активных: 0 · Всего: 1' in page.text
    assert 'В работе: 1 · Всего: 1' in page.text
