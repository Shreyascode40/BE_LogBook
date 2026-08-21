from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from be_logbook.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from be_logbook.users.models import User


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:
    return UserFactory.create()
