import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

logger = logging.getLogger(__name__)


def send_notification(subject, message, recipients):
    recipients = [email for email in recipients if email]
    if not recipients:
        return False
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception:
        logger.exception('Email notification failed')
        return False
    return True


def send_registration_email(user):
    return send_notification(
        'Добро пожаловать в личный кабинет кондитерской фабрики',
        (
            f'Здравствуйте, {user.first_name or user.username}!\n\n'
            'Регистрация прошла успешно. Теперь вы можете оформлять заявки, '
            'загружать документы и отслеживать историю обращений в личном кабинете.'
        ),
        [user.email],
    )


def send_request_created_email(customer_request):
    message = (
        f'Заявка #{customer_request.pk} принята.\n'
        f'Тип: {customer_request.get_request_type_display()}\n'
        f'Статус: {customer_request.get_status_display()}\n\n'
        'Мы свяжемся с вами после обработки обращения.'
    )
    return send_notification(
        'Ваша заявка принята',
        message,
        [customer_request.email],
    )


def build_password_reset_message(request):
    login_url = request.build_absolute_uri(reverse('login'))
    return (
        'Восстановление пароля можно подключить через стандартные views Django.\n'
        f'Страница входа: {login_url}'
    )
