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
    db.init_db();store.init_sourcing_db()
    sourcing.limiter.events.clear();sourcing.access_limiter.events.clear()
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
    for path in ['/sourcing','/sourcing/requests/SRC-test','/admin/sourcing','/sourcing/access']:
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
