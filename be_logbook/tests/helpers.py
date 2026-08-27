from __future__ import annotations

from rest_framework.test import APIClient


def jwt_login(client: APIClient, email: str, password: str):
    return client.post("/api/v1/auth/login/", {"email": email, "password": password})
