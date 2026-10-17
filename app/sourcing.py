"""Opt-in human-operated sourcing pilot; no simulated search or payment success."""
from __future__ import annotations
import os
import secrets
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, Response
from pydantic import TypeAdapter, EmailStr, ValidationError
from starlette.datastructures import UploadFile
from starlette.concurrency import run_in_threadpool
from .documents import prepare_upload, DocumentValidationError, unique_display_filename
from .security import SlidingWindowRateLimiter, client_key
from . import sourcing_store as store
from . import sourcing_mail

SERVICES={'search':'Найти поставщика','check':'Проверить поставщика','prepare':'Подготовить сделку'}
STATUSES={'received':'Заявка получена','reviewing':'Оценка задачи','in_progress':'В работе',
          'completed':'Отчёт готов','declined':'Задача не принята'}
MAX_PHOTOS=5
MAX_PHOTO_BYTES=8*1024*1024
MAX_TOTAL_BYTES=25*1024*1024
limiter=SlidingWindowRateLimiter(limit=6,window_seconds=600)
access_limiter=SlidingWindowRateLimiter(limit=8,window_seconds=900)


def enabled():
    return os.getenv('ENABLE_SOURCING_PILOT','').lower() in {'1','true','yes'}


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
                     verify_turnstile, turnstile_site_key, schedule_delivery=None):
    if enabled():
        store.init_sourcing_db()
    router=APIRouter(dependencies=[Depends(require_enabled)])

    def render(request,name,context=None,status=200):
        context={**(context or {}),'services':SERVICES,'statuses':STATUSES,'sourcing_email_enabled':sourcing_mail.configured()}
        return templates.TemplateResponse(request=request,name='sourcing/'+name,context=context,
            status_code=status,headers={'Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow, noarchive'})

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

    @router.get('/sourcing')
    def home(request:Request):
        submission=secrets.token_urlsafe(32)
        pending=list(request.session.get('sourcing_submissions',[]))
        request.session['sourcing_submissions']=(pending+[submission])[-6:]
        return render(request,'form.html',{'csrf_token':csrf(request),
            'submission':submission,'turnstile_site_key':turnstile_site_key})

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
            brief.update(service=service,schema_version=1)
            if not brief['quantity'] or not brief['destination']:
                raise ValueError('Укажите количество и страну доставки.')
            if service!='search' and not brief['supplier']:
                raise ValueError('Для этой услуги укажите поставщика или ссылку.')
            uploads=[v for v in form.getlist('photos') if isinstance(v,UploadFile) and v.filename]
            if uploads and service!='search':
                raise ValueError('Фото товара прикладываются к услуге подбора.')
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

    @router.get('/admin/sourcing/{request_id}')
    def admin_detail(request:Request,request_id:str):
        item=authorize(request,request_id,True)
        return render(request,'detail.html',{'item':item,'admin':True,
            'csrf_token':admin_csrf_token(request),'transitions':store.TRANSITIONS[item['status']]})

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
        async with request.form(max_files=0,max_fields=12) as form:
            require_admin_csrf(request,str(form.get('csrf_token') or ''))
            try:
                payload={k:text(form,k,30000,True) for k in ('summary','findings','risks','next_steps')}
                payload['sources']=valid_sources(text(form,'sources',30000,True))
                if form.get('reviewed')!='yes':
                    raise ValueError('Подтвердите проверку отчёта человеком.')
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
        async with request.form(max_files=0,max_fields=12) as form:
            require_admin_csrf(request,str(form.get('csrf_token') or ''))
            try:
                payload={k:text(form,k,30000) for k in ('summary','findings','risks','next_steps','sources')}
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
