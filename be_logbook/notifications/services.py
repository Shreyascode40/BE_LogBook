from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.utils import timezone

from be_logbook.notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Creates in-app notifications and optionally queues email delivery."""

    @staticmethod
    def create(
        *,
        recipient,
        notification_type: str,
        title: str,
        message: str,
        related_object: Any = None,
        send_email: bool = False,
    ) -> Notification:
        ct = None
        obj_id = None
        if related_object is not None:
            ct = ContentType.objects.get_for_model(related_object.__class__)
            obj_id = related_object.pk
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            content_type=ct,
            object_id=obj_id,
        )
        if send_email and recipient.email:
            send_notification_email.delay(notification.id)
        return notification


@shared_task
def send_notification_email(notification_id: int) -> None:
    try:
        notification = Notification.objects.select_related("recipient").get(
            id=notification_id
        )
    except Notification.DoesNotExist:
        logger.warning("Notification %s not found for email", notification_id)
        return
    try:
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=None,
            recipient_list=[notification.recipient.email],
            fail_silently=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send notification email %s", notification_id)
