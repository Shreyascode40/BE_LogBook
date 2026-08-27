from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from be_logbook.documents.models import Document
from be_logbook.groups.models import GroupMembership
from be_logbook.groups.models import ProjectGroup
from be_logbook.users.models import StudentProfile
from be_logbook.users.models import User


def _upload(client, group, dtype="REPORT", ext="pdf", content=b"%PDF-1.4 fake"):
    f = SimpleUploadedFile(f"report.{ext}", content, content_type="application/pdf")
    return client.post(
        "/api/v1/documents/",
        {"file": f, "document_type": dtype, "group_id": group.id},
        format="multipart",
    )


@pytest.mark.django_db
def test_valid_upload(env, auth):
    student = auth(env["students"][0])
    resp = _upload(student, env["group"])
    assert resp.status_code == 201
    assert Document.objects.count() == 1


@pytest.mark.django_db
def test_invalid_extension_rejected(env, auth):
    student = auth(env["students"][0])
    resp = _upload(student, env["group"], ext="exe", content=b"MZ")
    assert resp.status_code == 422
    assert Document.objects.count() == 0


@pytest.mark.django_db
def test_unauthorized_download_forbidden(env, auth):
    student = auth(env["students"][0])
    _upload(student, env["group"])
    doc = Document.objects.first()

    # Build an outsider student in another group
    other = ProjectGroup.objects.create(
        group_number="G9", academic_year=env["ay"], department=env["dept"]
    )
    u2 = User.objects.create_user(
        email="out2@be.edu",
        name="O2",
        role="STUDENT",
        is_active=True,
        password="o12345",
    )
    StudentProfile.objects.create(
        user=u2, roll_number="O2", department=env["dept"], academic_year=env["ay"]
    )
    GroupService_add = other
    from be_logbook.groups.services import GroupService

    GroupService.add_member(group=other, student=u2, created_by=env["hod"])
    outsider = auth(u2)
    resp = outsider.get(f"/api/v1/documents/{doc.id}/download/")
    assert resp.status_code in (403, 404)


@pytest.mark.django_db
def test_document_versioning(env, auth):
    student = auth(env["students"][0])
    _upload(student, env["group"], content=b"v1")
    _upload(student, env["group"], content=b"v2")
    doc = Document.objects.get()
    assert doc.version == 2
    assert Document.objects.count() == 1  # same logical doc, versioned
    # versions endpoint accessible to group member
    resp = student.get(f"/api/v1/documents/{doc.id}/versions/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
