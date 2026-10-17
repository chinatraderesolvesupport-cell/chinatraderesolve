"""Minimal sourcing notifications, stored in the existing durable outbox."""
import os
from .config import settings
from .notifications import email_delivery_is_configured


def configured():
    return os.getenv('ENABLE_SOURCING_EMAIL', '').lower() in {'1', 'true', 'yes'} and email_delivery_is_configured()


def messages(request_id, email, event):
    if not configured():
        return []
    url = settings.public_base_url.rstrip('/') + '/sourcing/access'
    if event == 'received':
        subject = 'China Trade: заявка получена — ' + request_id
        body = ('Ваша заявка сохранена.\nНомер: ' + request_id +
                '\n\nСначала оператор оценит задачу. Исследование не запускается автоматически. '
                'Объём, стоимость и срок работы согласовываются до оплаты.\n'
                'Статус и результат доступны в кабинете: ' + url +
                '\nВведите номер заявки и сохранённый при отправке код доступа. '
                'Код не включается в письмо; храните его отдельно.\n'
                'Фотографии и содержание заявки в письмо не включены.\n')
    else:
        subject = 'China Trade: отчёт готов — ' + request_id
        body = ('По заявке ' + request_id + ' опубликован проверенный оператором отчёт.\n'
                'Откройте кабинет: ' + url +
                '\nВведите номер заявки и ваш сохранённый код доступа. '
                'Отчёт и фотографии доступны только в кабинете.\n')
    result = [{'recipient': email, 'subject': subject, 'body': body}]
    if event == 'received' and settings.admin_email:
        result.append({'recipient': settings.admin_email,
                       'subject': 'China Trade: новая заявка подбора — ' + request_id,
                       'body': 'Получена заявка ' + request_id + '.\nОткройте кабинет оператора: ' +
                               settings.public_base_url.rstrip('/') + '/admin/sourcing\n'})
    return result
