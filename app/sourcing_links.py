"""Purpose-bound email links grant viewing only, never administration or deletion."""
import time
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from .config import settings

MAX_AGE=7*24*60*60


def signer():
    return URLSafeTimedSerializer(settings.app_secret,salt='sourcing-read-only-v1')


def issue(request_id):
    return signer().dumps({'request_id':request_id,'scope':'view'})


def verify(token):
    try:
        value,created=signer().loads(token,max_age=MAX_AGE,return_timestamp=True)
        if value.get('scope')!='view' or not isinstance(value.get('request_id'),str):return None
        return {'request_id':value['request_id'],'expires_at':int(created.timestamp())+MAX_AGE}
    except (BadSignature,SignatureExpired,TypeError,ValueError,AttributeError):
        return None


def remember(request,grant):
    grants=dict(request.session.get('sourcing_read_only',{}))
    grants.pop(grant['request_id'],None)
    grants[grant['request_id']]=grant['expires_at']
    while len(grants)>8:grants.pop(next(iter(grants)))
    request.session['sourcing_read_only']=grants


def allowed(request,request_id):
    expiry=request.session.get('sourcing_read_only',{}).get(request_id,0)
    return isinstance(expiry,(int,float)) and 0<time.time()<=expiry
