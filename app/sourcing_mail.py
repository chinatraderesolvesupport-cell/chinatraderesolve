"""Minimal sourcing notifications, stored in the existing durable outbox."""
import os
from .config import settings
from .notifications import email_delivery_is_configured


def configured():
    return os.getenv('ENABLE_SOURCING_EMAIL', '').lower() in {'1', 'true', 'yes'} and email_delivery_is_configured()


def messages(request_id, email, event, locale='ru'):
    if not configured():
        return []
    from .sourcing_i18n import COPY
    from .sourcing_research import configured as research_configured
    from .sourcing_links import issue
    copy=COPY.get(locale,COPY['ru'])
    label='mail_received' if event=='received' else 'mail_access' if event=='access_link' else 'mail_report'
    url=settings.public_base_url.rstrip('/')+'/sourcing/email-access?token='+issue(request_id)+'&lang='+ (locale if locale in COPY else 'ru')
    body=((copy['received'] if event=='received' else copy['mail_access'] if event=='access_link' else copy['completed'])+'\n'+copy['request_id']+': '+request_id+'\n\n'+copy['free']+'\n\n'+
          ((copy['research_client_wait'] if research_configured() else copy['next_received']+' '+copy['next_scope']) if event=='received' else copy['email_access_intro'] if event=='access_link' else copy['email_report_intro'])+
          '\n\n'+copy['access']+': '+url+'\n'+copy['email_link_note']+'\n')
    result=[{'recipient':email,'subject':'China Trade: '+copy[label]+' — '+request_id,'body':body}]
    if event=='received' and settings.admin_email:
        result.append({'recipient':settings.admin_email,'subject':'China Trade: '+COPY['ru']['new']+' — '+request_id,
                       'body':COPY['ru']['request_id']+': '+request_id+'\n'+settings.public_base_url.rstrip('/')+'/admin/sourcing/'+request_id+'\n'})
    return result
