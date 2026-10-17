"""Short-lived, target-bound confirmations for administrator deletion forms."""
import secrets
import time
from fastapi import HTTPException


def begin(request, target, version):
    now=time.time()
    intents={key:value for key,value in request.session.get('admin_delete_intents',{}).items()
             if value.get('expires',0)>now}
    while len(intents)>=4:
        intents.pop(next(iter(intents)))
    nonce=secrets.token_urlsafe(24)
    intents[nonce]={'target':target,'version':str(version),'expires':now+600}
    request.session['admin_delete_intents']=intents
    return nonce


def validate(request, target, nonce, confirmed):
    if confirmed!='delete':
        raise HTTPException(400,'Подтвердите безвозвратное удаление.')
    value=request.session.get('admin_delete_intents',{}).get(nonce,{})
    if value.get('target')!=target or value.get('expires',0)<=time.time():
        raise HTTPException(409,'Подтверждение устарело. Откройте заявку и повторите удаление.')
    return value['version']


def finish(request, nonce):
    intents=dict(request.session.get('admin_delete_intents',{}));intents.pop(nonce,None)
    request.session['admin_delete_intents']=intents
