from __future__ import annotations

import pytest

from be_logbook.logbook.services import LogBookGenerationService


@pytest.mark.django_db
def test_validate_fails_when_incomplete(env, auth):
    ok, missing = LogBookGenerationService.validate(env["project"])
    assert ok is False
    assert len(missing) > 0
    assert any("Stage" in m for m in missing)


@pytest.mark.django_db
def test_generate_endpoint_refuses_incomplete(env, auth):
    hod = auth(env["hod"])
    resp = hod.post(f"/api/v1/logbook/generate/{env['project'].id}/")
    assert resp.status_code == 422
    assert resp.json()["success"] is False
