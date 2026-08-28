from __future__ import annotations

import io
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from be_logbook.documents.models import Document
from be_logbook.logbook.models import GeneratedLogBook
from be_logbook.logbook.renderer import (
    A4_HEIGHT,
    A4_WIDTH,
    PDFRenderer,
    PDFValidationService,
)
from be_logbook.logbook.services import LogBookPDFService
from be_logbook.logbook.template_mapping import TemplateMappingService
from be_logbook.logbook.validation import LogBookValidationService
from be_logbook.projects.models import FinalSubmissionInfo
from be_logbook.submissions.models import Submission, SubmissionVersion

EXPECTED_PAGES = 40

# Static invariants that must survive on EVERY page of the official template.
PAGE_INVARIANTS = [
    "Akhil Bharatiya Maratha Shikshan Parishad",
    "Project Diary",
    "Record No.: ACA/D/003B",
]


def _template_bytes():
    from django.conf import settings
    import os

    path = os.path.join(settings.BASE_DIR, "Project Log book.pdf")
    with open(path, "rb") as fh:
        return fh.read()


def _mark_eligible(env):
    group = env["group"]
    project = env["project"]
    guide = env["guide"]
    created = []
    for code, stage in env["stages"].items():
        if not stage.required:
            continue
        sub, _ = Submission.objects.get_or_create(
            group=group,
            stage=stage,
            section=env["sections"][code],
            project=project,
            defaults={"submitted_by": guide, "status": "APPROVED"},
        )
        sub.status = "APPROVED"
        sub.save()
        SubmissionVersion.objects.get_or_create(
            submission=sub,
            version_number=1,
            defaults={"status": "APPROVED", "submitted_by": guide},
        )
        created.append(sub)
    Document.objects.create(
        document_type="REPORT",
        group=group,
        project=project,
        uploaded_by=guide,
        file=SimpleUploadedFile("report.pdf", b"dummy"),
        status="ACTIVE",
    )
    fs, _ = FinalSubmissionInfo.objects.get_or_create(
        project=project,
        defaults={"submitted": True, "submitted_date": date.today()},
    )
    fs.submitted = True
    fs.save()
    return created


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_validate_reports_missing_items_for_incomplete_project(env):
    ok, missing = LogBookValidationService.validate(env["project"])
    assert ok is False
    assert len(missing) > 0
    assert any("Stage" in m for m in missing)


@pytest.mark.django_db
def test_generate_refuses_incomplete_project(env, auth):
    client = auth(env["hod"])
    resp = client.post(f"/api/v1/projects/{env['project'].id}/logbook/generate/")
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert "missing_items" in body


# --------------------------------------------------------------------------- #
# Full generation
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_full_generation_produces_40_page_filled_pdf(env):
    _mark_eligible(env)
    gen = LogBookPDFService.generate(env["project"], env["hod"])
    assert isinstance(gen, GeneratedLogBook)
    assert gen.status == "READY"
    assert gen.template_version
    assert gen.file

    pdf_bytes = gen.file.read()
    validation = PDFValidationService.validate(pdf_bytes)
    assert validation["valid"] is True
    assert validation["page_count"] == EXPECTED_PAGES

    # Dynamic data made it in.
    import pypdf

    full = "\n".join((p.extract_text() or "") for p in pypdf.PdfReader(gen.file).pages)
    assert "Test Project" in full
    assert "G1" in full


@pytest.mark.django_db
def test_api_generate_and_retrieve(env, auth):
    _mark_eligible(env)
    client = auth(env["guide"])
    resp = client.post(f"/api/v1/projects/{env['project'].id}/logbook/generate/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["page_count"] == EXPECTED_PAGES
    assert "file_url" in body

    get_resp = client.get(f"/api/v1/projects/{env['project'].id}/logbook/")
    assert get_resp.status_code == 200
    assert get_resp.json()["exists"] is True
    assert get_resp.json()["latest"]["version"] == body["version"]


@pytest.mark.django_db
def test_generation_is_versioned_and_template_not_overwritten(env):
    _mark_eligible(env)
    original = _template_bytes()
    LogBookPDFService.generate(env["project"], env["hod"])
    LogBookPDFService.generate(env["project"], env["hod"])
    assert GeneratedLogBook.objects.filter(project=env["project"]).count() == 2
    # Original template file is byte-identical (never modified).
    assert _template_bytes() == original


# --------------------------------------------------------------------------- #
# Visual regression: structure / layout preservation
# --------------------------------------------------------------------------- #
def test_regression_template_vs_generated_preserves_layout():
    template = _template_bytes()
    import pypdf

    tpl_reader = pypdf.PdfReader(io.BytesIO(template))
    assert len(tpl_reader.pages) == EXPECTED_PAGES

    from be_logbook.logbook.data_assembler import LogBookData, MemberData

    data = LogBookData(
        department_name="Computer",
        academic_year="2025-26",
        group_number="G07",
        project_title="Smart Attendance System",
        area="AI",
        guide_name="Prof. Guide",
        topic_1="Topic one description.",
        topic_1_approved=True,
        evaluator_1_name="Prof. Eval One",
        evaluator_2_name="Prof. Eval Two",
        members=[
            MemberData(
                name="Student A",
                roll_number="R1",
                email="a@x.com",
                contribution="Lead",
            )
        ],
    )
    mapping = TemplateMappingService(template)
    placements = mapping.build_placements(data)

    # Every placement must sit inside the page box (no overflow / misplacement).
    for pl in placements:
        assert 0 <= pl.x <= A4_WIDTH
        assert 0 <= pl.y <= A4_HEIGHT

    pdf = PDFRenderer().render(template, placements)
    gen_reader = pypdf.PdfReader(io.BytesIO(pdf))
    assert len(gen_reader.pages) == EXPECTED_PAGES

    for i in range(EXPECTED_PAGES):
        tpl_text = tpl_reader.pages[i].extract_text() or ""
        gen_text = gen_reader.pages[i].extract_text() or ""
        for invariant in PAGE_INVARIANTS:
            # Invariant headers/logos/tables must remain on every page.
            assert invariant in tpl_text, f"template missing {invariant} p{i + 1}"
            assert invariant in gen_text, f"generated lost {invariant} p{i + 1}"

    # Dynamic data present, static template had it blank before.
    full = "\n".join((p.extract_text() or "") for p in gen_reader.pages)
    assert "Smart Attendance System" in full
    assert "Student A" in full


def test_empty_data_rule_never_writes_none_tokens():
    template = _template_bytes()
    from be_logbook.logbook.data_assembler import LogBookData

    data = LogBookData()  # entirely empty
    mapping = TemplateMappingService(template)
    placements = mapping.build_placements(data)
    # No real values -> no text placements (blank preserved).
    text_placements = [p for p in placements if p.text]
    assert text_placements == []
    pdf = PDFRenderer().render(template, placements)
    assert PDFValidationService.validate(pdf)["page_count"] == EXPECTED_PAGES
