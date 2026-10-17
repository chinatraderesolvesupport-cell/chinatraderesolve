"""Opt-in human-operated sourcing pilot; no simulated search or payment success."""
from __future__ import annotations
import os
import secrets
from urllib.parse import urlsplit
from datetime import date, datetime, timezone
from fastapi.routing import APIRoute
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, Response, JSONResponse
from pydantic import TypeAdapter, EmailStr, ValidationError
from starlette.datastructures import UploadFile
from starlette.concurrency import run_in_threadpool
from .documents import prepare_upload, DocumentValidationError, unique_display_filename
from .security import SlidingWindowRateLimiter, client_key
from . import sourcing_store as store
from . import sourcing_mail, admin_deletion, sourcing_research
from . import sourcing_stats
from .sourcing_i18n import LANGUAGES, COPY, language, translator, localize_error

SERVICES={'search':'Найти поставщика','check':'Проверить поставщика','prepare':'Подготовить сделку'}
STATUSES={'received':'Заявка получена','reviewing':'Оценка задачи','in_progress':'В работе',
          'completed':'Отчёт готов','declined':'Задача не принята'}
MAX_PHOTOS=5
MAX_PHOTO_BYTES=8*1024*1024
MAX_TOTAL_BYTES=25*1024*1024
limiter=SlidingWindowRateLimiter(limit=6,window_seconds=600)
feedback_limiter=SlidingWindowRateLimiter(limit=5,window_seconds=600)
access_limiter=SlidingWindowRateLimiter(limit=8,window_seconds=900)


def enabled():
    return os.getenv('ENABLE_SOURCING_PILOT','').lower() in {'1','true','yes'}


def live():
    return enabled() and os.getenv('ENABLE_SOURCING_LIVE','').lower() in {'1','true','yes'}


def require_enabled():
    if not enabled():
        raise HTTPException(404)


def text(form, name, max_length=1000, required=False):
    raw=form.get(name,'')
    if not isinstance(raw,str):
        raise ValueError('Некорректное текстовое поле.')
    value=raw.strip()
    if len(value)>max_length or (required and not value):
        label={'product':'Товар','quantity':'Количество','destination':'Страна доставки','goal':'Задача','supplier':'Поставщик','email':'Email','summary':'Вывод','findings':'Что установлено','risks':'Риски','next_steps':'Следующие шаги','sources':'Источники'}.get(name,name)
        raise ValueError('Проверьте поле «'+label+'»: оно пустое или слишком длинное.')
    return value


def valid_sources(raw):
    urls=[u.strip() for u in raw.splitlines() if u.strip()]
    if not 1<=len(urls)<=30:
        raise ValueError('Добавьте от 1 до 30 ссылок на источники, по одной на строку.')
    for url in urls:
        parsed=urlsplit(url)
        if parsed.scheme not in {'https','http'} or not parsed.hostname or parsed.username or parsed.password or len(url)>2000:
            raise ValueError('Источники должны быть обычными HTTP(S)-ссылками без паролей.')
    return urls


def install_sourcing(app, templates, require_admin, admin_csrf_token, require_admin_csrf,
                     verify_turnstile, turnstile_site_key, schedule_delivery=None, indexing_ready=None):
    if enabled():
        store.init_sourcing_db()
        sourcing_stats.init_db()
    class LocalizedRoute(APIRoute):
        def get_route_handler(self):
            handler=super().get_route_handler()
            async def localized(request):
                language(request)
                try:
                    return await handler(request)
                except HTTPException as exc:
                    if not enabled(): raise
                    return render(request,'error.html',{'message':str(exc.detail)},exc.status_code)
            return localized
    router=APIRouter(dependencies=[Depends(require_enabled)],route_class=LocalizedRoute)

    def render(request,name,context=None,status=200):
        lang=language(request);base_t=translator(lang)
        ai_ready=sourcing_research.configured()
        def t(key):
            if key=='pilot' and (live() or ai_ready):
                key='live_ai' if ai_ready else 'live_operator'
            elif ai_ready and key in {'u_honest_text','g_photo_3'}:
                key += '_ai'
            return base_t(key)
        if status==200:
            sourcing_stats.record_view(request,buffered=request.url.path=='/buying')
        context={**(context or {}),'services':{key:t(key) for key in SERVICES},
            'statuses':{key:t(key) for key in STATUSES},'sourcing_email_enabled':sourcing_mail.configured(),
            't':t,'sourcing_ux':COPY[lang],'lang':lang,'languages':LANGUAGES,'sourcing_live':live(),
            'js_copy':{key:value for key,value in COPY[lang].items() if key.startswith('js_') or key in {'optional','optional_name','optional_photo','min50','photo_alt'}},
            'is_error':status>=400,'sourcing_statistics_enabled':enabled()}
        context['research_configured']=sourcing_research.configured()
        if request.url.path.startswith('/admin/') and request.session.get('admin'):
            context.setdefault('csrf_token',admin_csrf_token(request))
        if 'message_key' in context: context['message']=t(context.pop('message_key'))
        elif 'message' in context: context['message']=localize_error(context['message'],lang)
        public_info=status==200 and name in {'help.html','buying.html'} and live() and indexing_ready and indexing_ready()
        context['public_info']=bool(public_info)
        if public_info:
            base=sourcing_mail.settings.public_base_url.rstrip('/')
            context['canonical_url']=base+request.url.path+'?lang='+lang
            context['help_alternates']=[{'lang':code,'url':base+request.url.path+'?lang='+code} for code in LANGUAGES]
        return templates.TemplateResponse(request=request,name='sourcing/'+name,context=context,
            status_code=status,headers={'Cache-Control':'no-store',
                'X-Robots-Tag':'index, follow' if public_info else 'noindex, nofollow, noarchive'})

    def csrf(request):
        token=request.session.get('sourcing_csrf')
        if not token:
            token=secrets.token_urlsafe(32)
            request.session['sourcing_csrf']=token
        return token

    def validate_csrf(request, form):
        if not secrets.compare_digest(str(request.session.get('sourcing_csrf') or ''),str(form.get('csrf_token') or '')) or not request.session.get('sourcing_csrf'):
            raise HTTPException(403,'Форма устарела. Обновите страницу.')

    def authorize(request,request_id,admin=False):
        if admin:
            require_admin(request)
        item=store.get_request(request_id)
        access=request.session.get('sourcing_access',{}).get(request_id,'')
        if not item or (not admin and not secrets.compare_digest(store.digest(access),item['access_hash'])):
            raise HTTPException(404,'Заявка не найдена или нет доступа.')
        return item

    def remember(request,request_id,access):
        accesses=dict(request.session.get('sourcing_access',{}))
        # Bound signed cookie size. Old requests remain recoverable with their code.
        accesses.pop(request_id,None)
        accesses[request_id]=access
        while len(accesses)>8:
            accesses.pop(next(iter(accesses)))
        request.session['sourcing_access']=accesses

    @router.get('/buying')
    def buying(request:Request):
        return render(request,'buying.html')

    @router.get('/sourcing')
    def home(request:Request):
        submission=secrets.token_urlsafe(32)
        pending=list(request.session.get('sourcing_submissions',[]))
        request.session['sourcing_submissions']=(pending+[submission])[-6:]
        return render(request,'form.html',{'csrf_token':csrf(request),
            'submission':submission,'turnstile_site_key':turnstile_site_key,
            'selected_service':request.query_params.get('service') if request.query_params.get('service') in SERVICES else 'search'})

    @router.get('/admin/sourcing-statistics')
    def statistics(request:Request):
        require_admin(request)
        period=request.query_params.get('days','7')
        days=int(period) if period in {'1','7','30'} else 7
        statistics=sourcing_stats.summary()
        selected=next(row for row in statistics['periods'] if row['days']==days)
        return render(request,'statistics.html',{'statistics':statistics,'selected':selected})

    @router.get('/sourcing/help')
    def help_hub(request:Request):
        return render(request,'help.html',{'topics':['supplier','spec','cost','photo']})

    @router.get('/sourcing/help/{topic}')
    def help_topic(request:Request,topic:str):
        if topic not in {'supplier','spec','cost','photo'}:
            raise HTTPException(404)
        return render(request,'help.html',{'topic':topic,'topics':['supplier','spec','cost','photo']})

    @router.get('/sourcing/preview')
    def unified_preview(request:Request):
        return render(request,'unified.html',{'preview_view':'home'})

    @router.get('/sourcing/preview/dispute')
    def unified_dispute(request:Request):
        return render(request,'unified.html',{'preview_view':'dispute'})

    @router.get('/sourcing/preview/account')
    def unified_account(request:Request):
        return render(request,'unified.html',{'preview_view':'account'})

    @router.post('/sourcing/requests')
    async def submit(request:Request, background_tasks:BackgroundTasks):
        if not limiter.allow(client_key(request)):
            raise HTTPException(429,'Слишком много заявок. Повторите позже.')
        form=await request.form(max_files=5,max_fields=30)
        try:
            validate_csrf(request,form)
            submission=text(form,'submission',100,True)
            pending=request.session.get('sourcing_submissions',[])
            if not any(secrets.compare_digest(submission,s) for s in pending):
                raise HTTPException(403,'Форма устарела. Откройте новую заявку.')
            service=text(form,'service',20,True)
            if service not in SERVICES:
                raise ValueError('Выберите услугу.')
            if text(form,'website',200):
                raise ValueError('Не удалось принять заявку.')
            if form.get('consent')!='yes':
                raise ValueError('Подтвердите согласие на обработку заявки.')
            try:
                email=str(TypeAdapter(EmailStr).validate_python(text(form,'email',254,True)))
            except ValidationError as exc:
                raise ValueError('Укажите корректный email.') from exc
            brief={k:text(form,k,n) for k,n in {'product':200,'quantity':100,'destination':100,
                'budget':100,'deadline':100,'supplier':1000,'requirements':10000,
                'documents':5000,'language':100}.items()}
            for key,allowed in {'platform':{'','alibaba','aliexpress','1688','made_in_china','direct','other','unsure'},
                                'purchase_purpose':{'','personal','business','resale','unsure'}}.items():
                brief[key]=text(form,key,30)
                if brief[key] not in allowed:
                    raise ValueError('Проверьте выбранный вариант.')
            brief.update(service=service,schema_version=4,locale=language(request),pricing_mode='launch_free',ai_processing_consent=True)
            if not brief['quantity'] or not brief['destination']:
                raise ValueError('Укажите количество и страну доставки.')
            if service!='search' and not brief['supplier']:
                raise ValueError('Для этой услуги укажите поставщика или ссылку.')
            uploads=[v for v in form.getlist('photos') if isinstance(v,UploadFile) and v.filename]
            if sum(u.size or 0 for u in uploads)>MAX_TOTAL_BYTES:
                raise ValueError('Общий размер фотографий — до 25 МБ.')
            photos=[];used=set();total=0
            for upload in uploads:
                document=await prepare_upload(upload)
                if document.content_type not in {'image/jpeg','image/png','image/webp'}:
                    raise ValueError('Прикрепляйте только JPG, PNG или WebP, до 8 МБ каждый.')
                total+=document.size_bytes
                if total>MAX_TOTAL_BYTES:
                    raise ValueError('Общий размер обработанных фотографий — до 25 МБ.')
                from dataclasses import replace
                photos.append(replace(document,original_name=unique_display_filename(document.original_name,used)))
            unknown=service=='search' and bool(photos) and form.get('unknown')=='yes'
            if not brief['product'] and not unknown:
                raise ValueError('Укажите товар или приложите фото и отметьте, что название неизвестно.')
            if not photos and len(brief['requirements'])<50:
                raise ValueError('Без фотографии опишите товар минимум в 50 символах.')
            brief['unknown_product']=unknown
            brief['match']=text(form,'match',20) if service=='search' else ''
            if service=='search' and brief['match'] not in {'exact','similar','help'}:
                raise ValueError('Выберите точность совпадения.')
            brief['alternatives_requested']=service=='search' and form.get('alternatives')=='yes'
            brief['goal']=text(form,'goal',5000,brief['alternatives_requested']) if brief['alternatives_requested'] else ''
            brief['limitations']=text(form,'limitations',5000) if brief['alternatives_requested'] else ''
            if service!='prepare':
                brief['documents']='';brief['language']=''
            if not await verify_turnstile(str(form.get('cf-turnstile-response') or ''),request):
                raise ValueError('Пройдите проверку защиты от роботов.')
            request_id,access=await run_in_threadpool(store.create_request,brief,email,photos,submission)
            remember(request,request_id,access)
            if sourcing_research.configured():
                try:
                    await run_in_threadpool(sourcing_research.enqueue,request_id)
                except store.Conflict:
                    pass  # Idempotent replay may refer to an already processed request.
                background_tasks.add_task(sourcing_research.schedule)
            if schedule_delivery and sourcing_mail.configured():
                background_tasks.add_task(schedule_delivery)
            return RedirectResponse('/sourcing/requests/'+request_id,status_code=303,background=background_tasks)
        except DocumentValidationError:
            return render(request,'error.html',{'message':'Не удалось обработать фото. Нужен исправный JPG, PNG или WebP, не больше 8 МБ.'},400)
        except ValueError as exc:
            return render(request,'error.html',{'message':str(exc)},400)
        finally:
            await form.close()

    @router.get('/sourcing/access')
    def access_page(request:Request):
        return render(request,'access.html',{'csrf_token':csrf(request)})

    @router.post('/sourcing/access')
    async def access(request:Request):
        if not access_limiter.allow(client_key(request)):
            raise HTTPException(429,'Повторите позже.')
        async with request.form(max_files=0,max_fields=4) as form:
            validate_csrf(request,form)
            request_id=str(form.get('request_id') or '')[:100]
            code=str(form.get('access_code') or '')[:100]
            item=await run_in_threadpool(store.get_request,request_id)
            if not item or not secrets.compare_digest(store.digest(code),item['access_hash']):
                return render(request,'error.html',{'message':'Номер или код доступа неверен.'},404)
            remember(request,request_id,code)
            return RedirectResponse('/sourcing/requests/'+request_id,303)

    @router.get('/sourcing/requests/{request_id}')
    def detail(request:Request,request_id:str):
        item=authorize(request,request_id)
        return render(request,'detail.html',{'item':item,'access_code':request.session['sourcing_access'][request_id],'csrf_token':csrf(request)})

    @router.get('/sourcing/requests/{request_id}/progress')
    def progress(request:Request,request_id:str):
        item=authorize(request,request_id)
        t=translator(language(request))
        return JSONResponse({'mail':[{'label':t('mail_received') if mail['event']=='received' else t('mail_report'),
            'text':t('mail_sent') if mail['status']=='sent' else t('mail_failed') if mail['status']=='failed' else t('mail_pending'),
            'pending':mail['status'] not in {'sent','failed'}} for mail in item['notifications']]},
            headers={'Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow, noarchive'})

    @router.get('/sourcing/requests/{request_id}/photos/{photo_id}')
    def photo(request:Request,request_id:str,photo_id:str):
        authorize(request,request_id)
        return photo_response(request_id,photo_id)

    def photo_response(request_id,photo_id):
        p=store.get_photo(request_id,photo_id)
        if not p:raise HTTPException(404)
        return Response(bytes(p['content']),media_type=p['content_type'],headers={
            'Cache-Control':'no-store','X-Robots-Tag':'noindex, noarchive','Content-Disposition':'inline'})

    @router.get('/admin/sourcing')
    def queue(request:Request):
        require_admin(request)
        return render(request,'queue.html',{'items':store.list_requests()})

    @router.get('/sourcing/reviews')
    def reviews(request:Request):
        return render(request,'reviews.html',{'reviews':store.list_feedback(public=True)})

    @router.get('/sourcing/feedback')
    def feedback_page(request:Request):
        request_id=str(request.query_params.get('request_id') or '')[:100]
        if request_id: authorize(request,request_id)
        submission=secrets.token_urlsafe(32)
        request.session['sourcing_feedback_submissions']=(list(request.session.get('sourcing_feedback_submissions',[]))+[submission])[-6:]
        return render(request,'feedback.html',{'csrf_token':csrf(request),'submission':submission,
            'request_id':request_id,'turnstile_site_key':turnstile_site_key})

    @router.post('/sourcing/feedback')
    async def feedback_submit(request:Request):
        if not feedback_limiter.allow(client_key(request)): raise HTTPException(429,'Слишком много попыток. Повторите позже.')
        async with request.form(max_files=0,max_fields=15) as form:
            validate_csrf(request,form)
            try:
                submission=text(form,'submission',100,True)
                if not any(secrets.compare_digest(submission,value) for value in request.session.get('sourcing_feedback_submissions',[])):
                    raise HTTPException(403,'Форма устарела. Откройте её заново.')
                if text(form,'website',200) or form.get('consent')!='yes': raise ValueError('Подтвердите согласие.')
                kind=text(form,'kind',20,True)
                if kind not in {'review','bug','suggestion'}: raise ValueError('Выберите тип сообщения.')
                message=text(form,'message',3000,True)
                if len(message)<10: raise ValueError('Сообщение: не менее 10 символов.')
                raw_rating=text(form,'rating',1)
                rating=int(raw_rating) if raw_rating else None
                if rating is not None and rating not in range(1,6): raise ValueError('Оценка — от 1 до 5.')
                if kind!='review': rating=None
                request_id=text(form,'request_id',100)
                if request_id: authorize(request,request_id)
                if not await verify_turnstile(str(form.get('cf-turnstile-response') or ''),request): raise ValueError('Пройдите проверку защиты от роботов.')
                await run_in_threadpool(store.create_feedback,submission,request_id,kind,rating,message,
                    language(request),form.get('publish_consent')=='yes')
            except ValueError as exc:
                return render(request,'error.html',{'message':str(exc)},400)
        return render(request,'error.html',{'message_key':'feedback_saved'})

    @router.get('/admin/sourcing/feedback')
    def moderation(request:Request):
        require_admin(request)
        return render(request,'moderation.html',{'entries':store.list_feedback(),'csrf_token':admin_csrf_token(request)})

    @router.post('/admin/sourcing/feedback/{feedback_id}')
    async def moderate(request:Request,feedback_id:str):
        require_admin(request)
        async with request.form(max_files=0,max_fields=4) as form:
            require_admin_csrf(request,str(form.get('csrf_token') or ''))
            try:
                await run_in_threadpool(store.moderate_feedback,feedback_id,int(form.get('version') or 0),str(form.get('status') or ''))
            except (ValueError,store.Conflict) as exc:
                return render(request,'error.html',{'message':str(exc)},409)
        return RedirectResponse('/admin/sourcing/feedback',303)

    @router.get('/admin/sourcing/{request_id}')
    def admin_detail(request:Request,request_id:str):
        require_admin(request)
        sourcing_research.recover_stale(request_id)
        item=authorize(request,request_id,True)
        sourcing_research.mark_viewed(request_id)
        return render(request,'detail.html',{'item':item,'admin':True,
            'csrf_token':admin_csrf_token(request),'transitions':store.TRANSITIONS[item['status']]})

    @router.post('/admin/sourcing/{request_id}/research')
    async def start_research(request:Request,request_id:str,background_tasks:BackgroundTasks):
        require_admin(request)
        async with request.form(max_files=0,max_fields=3) as form:
            require_admin_csrf(request,str(form.get('csrf_token') or ''))
            if not sourcing_research.configured():
                return render(request,'error.html',{'message_key':'research_disabled'},503)
            try:
                await run_in_threadpool(sourcing_research.enqueue,request_id,int(form.get('version') or 0),True)
            except (ValueError,store.Conflict) as exc:
                return render(request,'error.html',{'message':str(exc)},409)
        background_tasks.add_task(sourcing_research.schedule)
        return RedirectResponse('/admin/sourcing/'+request_id,303,background=background_tasks)

    @router.get('/admin/sourcing/{request_id}/research-progress')
    def research_progress(request:Request,request_id:str):
        item=authorize(request,request_id,True)
        state=item['research']['state'] if item['research'] else ''
        t=translator(language(request))
        return JSONResponse({'state':state,'label':t('research_'+state) if state else '',
            'refresh':t('refresh_status')},headers={'Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow, noarchive'})

    @router.get('/admin/sourcing/{request_id}/delete')
    def confirm_admin_delete(request:Request,request_id:str):
        item=authorize(request,request_id,True)
        nonce=admin_deletion.begin(request,'sourcing:'+request_id,item['version'])
        return render(request,'delete.html',{'delete_nonce':nonce,'target_label':request_id,
            'target_description':item['email'],'cancel_url':'/admin/sourcing/'+request_id})

    @router.post('/admin/sourcing/{request_id}/delete')
    async def admin_delete(request:Request,request_id:str):
        require_admin(request)
        async with request.form(max_files=0,max_fields=4) as form:
            require_admin_csrf(request,str(form.get('csrf_token') or ''))
            nonce=str(form.get('delete_nonce') or '')
            version=admin_deletion.validate(request,'sourcing:'+request_id,nonce,form.get('confirm'))
            try:
                deleted=await run_in_threadpool(store.delete_request,request_id,version)
            except store.Conflict as exc:
                return render(request,'error.html',{'message':str(exc)},409)
            if not deleted:
                raise HTTPException(404,'Заявка не найдена.')
        admin_deletion.finish(request,nonce)
        accesses=dict(request.session.get('sourcing_access',{}));accesses.pop(request_id,None)
        request.session['sourcing_access']=accesses
        return RedirectResponse('/admin/sourcing?deleted=1',303)

    @router.get('/admin/sourcing/{request_id}/photos/{photo_id}')
    def admin_photo(request:Request,request_id:str,photo_id:str):
        authorize(request,request_id,True)
        return photo_response(request_id,photo_id)

    @router.post('/admin/sourcing/{request_id}/status')
    async def status(request:Request,request_id:str):
        require_admin(request)
        async with request.form(max_files=0,max_fields=5) as form:
            require_admin_csrf(request,str(form.get('csrf_token') or ''))
            try:await run_in_threadpool(store.change_status,request_id,int(form.get('version') or 0),str(form.get('status') or ''))
            except (ValueError,store.Conflict) as exc:
                return render(request,'error.html',{'message':str(exc)},409)
        return RedirectResponse('/admin/sourcing/'+request_id,303)

    @router.post('/admin/sourcing/{request_id}/report')
    async def report(request:Request,request_id:str,background_tasks:BackgroundTasks):
        require_admin(request)
        async with request.form(max_files=0,max_fields=50) as form:
            require_admin_csrf(request,str(form.get('csrf_token') or ''))
            try:
                payload={k:text(form,k,30000,True) for k in ('summary','findings','risks','next_steps')}
                payload['sources']=valid_sources(text(form,'sources',30000,True))
                if form.get('reviewed')!='yes':
                    raise ValueError('Подтвердите проверку отчёта человеком.')
                payload['suppliers']=supplier_assessments(form,publish=True)
                payload['reviewed_by_human']=True
                await run_in_threadpool(store.publish_report,request_id,int(form.get('version') or 0),payload)
                if schedule_delivery and sourcing_mail.configured():
                    background_tasks.add_task(schedule_delivery)
            except store.Conflict as exc:
                return render(request,'error.html',{'message':str(exc)},409)
            except ValueError as exc:
                return render(request,'error.html',{'message':str(exc)},400)
        return RedirectResponse('/admin/sourcing/'+request_id,303,background=background_tasks)

    @router.post('/admin/sourcing/{request_id}/draft')
    async def draft(request:Request,request_id:str):
        require_admin(request)
        async with request.form(max_files=0,max_fields=50) as form:
            require_admin_csrf(request,str(form.get('csrf_token') or ''))
            try:
                payload={k:text(form,k,30000) for k in ('summary','findings','risks','next_steps','sources')}
                payload['suppliers']=supplier_assessments(form,publish=False)
                await run_in_threadpool(store.save_draft,request_id,int(form.get('version') or 0),payload)
            except ValueError as exc:
                return render(request,'error.html',{'message':str(exc)},409)
        return RedirectResponse('/admin/sourcing/'+request_id,303)

    @router.post('/sourcing/requests/{request_id}/delete')
    async def delete_request(request:Request,request_id:str):
        authorize(request,request_id)
        async with request.form(max_files=0,max_fields=3) as form:
            validate_csrf(request,form)
            if form.get('confirm')!='delete':
                raise HTTPException(400,'Подтвердите удаление.')
            await run_in_threadpool(store.delete_request,request_id)
        accesses=dict(request.session.get('sourcing_access',{}));accesses.pop(request_id,None)
        request.session['sourcing_access']=accesses
        return render(request,'error.html',{'message':'Заявка и фотографии удалены.'},200)

    app.include_router(router)


def supplier_assessments(form,publish=False):
    result=[]
    today=datetime.now(timezone.utc).date()
    for i in range(1,4):
        def field(name,length=1000): return text(form,'supplier_'+str(i)+'_'+name,length)
        name=field('name',200)
        if not name:
            # A blank slot is ignored only if its substantive fields are blank.
            if any(field(key,10000) for key in ('notes','sources','checked_on','archive_url','archive_date')):
                raise ValueError('Укажите название компании в карточке поставщика.')
            continue
        role=field('role') or 'unknown_role';outcome=field('outcome') or 'insufficient';archive=field('archive') or 'not_checked'
        if role not in {'unknown_role','manufacturer','reseller'} or outcome not in {'insufficient','concerns','documented'} or archive not in {'not_checked','not_found','found'}:
            raise ValueError('Проверьте поля оценки поставщика.')
        checked=field('checked_on');notes=field('notes',5000);sources=field('sources',10000)
        archive_url=field('archive_url',2000);archive_date=field('archive_date')
        for value in (checked,archive_date):
            if value:
                try: parsed_date=date.fromisoformat(value)
                except ValueError: raise ValueError('Укажите корректную дату.') from None
                if parsed_date>today: raise ValueError('Дата проверки не может быть в будущем.')
        urls=valid_sources(sources) if sources else []
        if archive_url:
            archive_urls=valid_sources(archive_url)
            if len(archive_urls)!=1: raise ValueError('Укажите одну ссылку на архивную копию.')
            archive_url=archive_urls[0]
        if archive!='found' and (archive_url or archive_date): raise ValueError('Архивная ссылка относится к статусу найденной копии.')
        if archive_date and checked and archive_date>checked: raise ValueError('Архивная копия не может быть позднее даты проверки.')
        if publish and (not checked or not notes or not urls or (archive=='found' and (not archive_url or not archive_date))):
            raise ValueError('Для оценки нужны дата, пояснение и источники; для найденного архива — ссылка и дата копии.')
        result.append(dict(name=name,role=role,outcome=outcome,checked_on=checked,notes=notes,sources=urls,
            archive=archive,archive_url=archive_url,archive_date=archive_date))
    return result
