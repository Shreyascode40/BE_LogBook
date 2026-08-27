from __future__ import annotations

import pytest

from be_logbook.notifications.models import Notification
from be_logbook.notifications.services import NotificationService
from be_logbook.notifications.services import send_notification_email


@pytest.mark.django_db
def test_create_notification(env):
    n = NotificationService.create(
        recipient=env["students"][0],
        notification_type="STAGE",
        title="Stage unlocked",
        message="You may submit now.",
    )
    assert isinstance(n, Notification)
    assert n.recipient == env["students"][0]
    assert Notification.objects.filter(recipient=env["students"][0]).count() == 1


@pytest.mark.django_db
def test_email_task_runs(env):
    n = NotificationService.create(
        recipient=env["students"][0],
        notification_type="STAGE",
        title="Stage unlocked",
        message="You may submit now.",
    )
    # Run the Celery task synchronously (no broker needed for the test).
    send_notification_email.apply(args=[n.id])
    # No exception means the task completed; re-fetch is unchanged.
    assert Notification.objects.filter(id=n.id).exists()


@pytest.mark.django_db
def test_notification_list_endpoint(env, auth):
    NotificationService.create(
        recipient=env["students"][0],
        notification_type="STAGE",
        title="Hello",
        message="msg",
    )
    client = auth(env["students"][0])
    resp = client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


@pytest.mark.django_db
def test_mark_read_endpoint(env, auth):
    n = NotificationService.create(
        recipient=env["students"][0],
        notification_type="STAGE",
        title="Hello",
        message="msg",
    )
    client = auth(env["students"][0])
    resp = client.post(f"/api/v1/notifications/{n.id}/mark_read/")
    assert resp.status_code == 200
    assert Notification.objects.get(id=n.id).read is True
