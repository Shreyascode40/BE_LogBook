from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from be_logbook.tests.helpers import jwt_login


@pytest.mark.django_db
def test_login_success(env):
    client = APIClient()
    resp = jwt_login(client, "hod@be.edu", "hod12345")
    assert resp.status_code == 200
    assert "access" in resp.json()["user"] or "access" in resp.json()


@pytest.mark.django_db
def test_login_invalid_password(env):
    client = APIClient()
    resp = client.post(
        "/api/v1/auth/login/", {"email": "hod@be.edu", "password": "wrong"}
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_inactive_user_cannot_login(env):
    from be_logbook.users.models import User

    u = User.objects.create_user(
        email="inactive@be.edu",
        name="X",
        role="STUDENT",
        is_active=False,
        password="x12345",
    )
    client = APIClient()
    resp = client.post(
        "/api/v1/auth/login/", {"email": "inactive@be.edu", "password": "x12345"}
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_me_endpoint_returns_role(env, auth):
    client = auth(env["hod"])
    resp = client.get("/api/v1/auth/me/")
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "HOD"
