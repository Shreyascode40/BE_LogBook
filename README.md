# BE Logbook

**B.E. Project Log Book Management System** for *Akhil Bharatiya Maratha Shikshan Parishad's Anantrao Pawar College of Engineering & Research*.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

---

## Project Overview

BE Logbook is a backend platform that digitizes and manages the entire lifecycle of
Bachelor of Engineering (B.E.) final-year project log books. It lets students record
project activity, faculty guides verify entries, reviewers assess work with rubrics,
and the department produce the **official 40-page Project Log Book PDF** — generated
by overlaying approved database data onto the college's immutable master template
(rather than creating a new design).

The system enforces an approval-gated workflow so that the final log book can only be
generated once every required stage, document, review, and final submission is
complete and verified.

---

## Tech Stack

| Layer        | Technology                                              |
| ------------ | ------------------------------------------------------- |
| Language     | Python 3.14                                             |
| Web Framework| Django 6.x + Django REST Framework                      |
| Auth         | dj-rest-auth + Simple JWT (email-based login)           |
| Task Queue   | Celery + Redis                                          |
| Documents    | Private media storage, PDF generation via `reportlab` + `pypdf` |
| DB           | PostgreSQL (SQLite fallback for tests)                 |
| Tooling      | uv (deps), ruff (lint), pytest + pytest-django, drf-spectacular (OpenAPI) |

---

## User Roles (RBAC)

| Role       | Capabilities                                                                 |
| ---------- | ---------------------------------------------------------------------------- |
| **Student**| Belongs to a project group, enters activities, uploads documents, generates/accesses **own** group's log book. |
| **Faculty**| Acts as guide / reviewer, verifies submissions, enters marks, accesses assigned groups. |
| **Reviewer**| Assigned per stage/group, conducts reviews and finalizes marks (assignment-based). |
| **HOD**     | Full departmental access — all groups, final approvals, log book oversight. |

Access is enforced everywhere via `can_access_group()` plus role checks; the generated
PDF download URL is behind authentication + ownership/assignment and is not publicly
guessable.

---

## Core Modules

- **Accounts & Users** — email login, roles, `StudentProfile` (roll no, department, photo, TE result, exam seat) and `FacultyProfile`.
- **Academics** — `Department`, `AcademicYear`, `Term`.
- **Groups** — `ProjectGroup` (group number, department, academic year), `GroupMembership`, `GuideAssignment`, `ReviewAssignment`.
- **Projects** — `Project` (title, area, guide), `ProjectSchedule`, `TopicFinalization`, `CompetitionDetail`, `PublicationDetail`, `TermRecord`, `FinalSubmissionInfo`.
- **Workflow** — `Stage` (ordered, required, guide/reviewer approval, marks required), `StageDependency`, `StageDeadline`, `Section`.
- **Submissions** — `Submission` + versioned `SubmissionVersion`, `Approval`, `ChangeRequest`, `FacultyRemark`, `StudentActivity`.
- **Reviews** — `Review`, `ReviewMark`, `ReviewMarkCorrection` against `Rubric` / `RubricCriterion`.
- **Documents** — typed `Document` storage (PHOTO, REPORT, SYNOPSIS, CERTIFICATE, SPONSORSHIP, …) with versions and checksums.
- **CO/PO Attainment** — computed outcomes attainment per group.
- **Notifications & Audit** — event notifications and an append-only audit trail.
- **Final Log Book PDF** — see below.

---

## Final Log Book PDF Generation

The generated PDF is **the same official 40-page template** with real, approved data
filled into the blanks. The original `Project Log book.pdf` is treated as an immutable
master and is **never modified**; data is overlaid on a transparent layer and merged.

### Architecture (services in `be_logbook/logbook/`)

| Service | Responsibility |
| ------- | -------------- |
| `LogBookValidationService` | Eligibility gate — refuses generation unless required stages are approved, documents exist, reviews are finalized, and final submission is complete. Returns a clear `missing_items` list. |
| `LogBookDataAssembler` | Single source of truth — gathers only real, stored values (no fabrication). |
| `TemplateMappingService` | Locates template text anchors (via `pypdf` text visitor) and computes exact `(page, x, y)` placement instructions. |
| `PDFRenderer` | Draws text/images on transparent A4 overlays and merges them onto the template with `pypdf`; auto-wraps/shrinks long text and inserts photos into placeholders. |
| `PDFValidationService` | Post-generation check: 40 pages, opens correctly, structure intact. |
| `LogBookPDFService` | Orchestrator: validate → load template (read-only) → assemble → map → render → validate → persist a **versioned** `GeneratedLogBook`. |

### API Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| `POST` | `/api/v1/projects/<id>/logbook/generate/` | Generate the final log book. Returns `{success, message, file_url, page_count}` or `422` with `{success:false, missing_items:[...]}`. |
| `GET`  | `/api/v1/projects/<id>/logbook/` | Retrieve the latest generated log book + version list. |
| `GET`  | `/api/v1/logbook/<pk>/download/` | Authenticated, non-guessable file download. |

Output filename: `Project_Log_Book_<group_number>.pdf`.

### Field Coverage (pages filled from DB)

- **Page 1** — Department, A.Y., Group No., Project Title, Area, Project Guide.
- **Pages 3–4** — Member name, TE result, roll no, mobile, exam seat, email, contribution, and photo (into the "Affix your photo here" placeholder).
- **Page 5** — Undertaking: department, batch years, academic year, project title, student names.
- **Page 6** — Schedule table dates (from `StageDeadline`).
- **Pages 7–8** — Topic finalization text, "Approved (Yes/No)", reviewer & coordinator names. Topic 2 only filled when Topic 1 is rejected (template rule).
- **Pages 25 / 34** — Evaluation committee names.
- **Pages 27 / 35** — External examiner feedback project title.
- **Pages 28 / 39** — Competition & Publication tables (name, date, college, type, award / title, conference, ISSN, volume, page).
- **Pages 37 / 38** — Sponsored-project company (only when a SPONSORSHIP document exists).

Pages that are intentionally **preserved unchanged** (static official content): rules,
activity-chart planned text, RTM, cost-estimation, review cover pages, and submission
checklists. Blank fields stay blank — the system never writes `None` / `N/A`.

### Tests

`be_logbook/tests/test_logbook.py` includes a **visual regression test** asserting the
generated PDF keeps exactly 40 pages, every page preserves static invariants (institution
name, "Project Diary", record number), dynamic data is present, all placements stay
within page bounds, the original template file is never mutated, and the empty-data
rule is honored.

---

## Getting Started

### Prerequisites
- Python 3.14, `uv`, PostgreSQL (optional for local dev; tests fall back to SQLite).

### Setup

```bash
uv sync                      # install dependencies
cp .envs/.local/.django .envs/.local/.postgres   # configure env (see .envs/.local/)
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

### Running tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check be_logbook
uv run mypy be_logbook
```

### Celery (optional)

```bash
uv run celery -A config.celery_app worker -l info
```

---

## ✅ Work Done (Checklist)

- [x] Cookiecutter-Django backend scaffold (settings, apps, API schema).
- [x] Authentication & RBAC (HOD / Faculty / Student / Reviewer) with JWT.
- [x] Groups, memberships, guide & reviewer assignments.
- [x] Workflow engine: ordered stages, dependencies, deadlines, sections.
- [x] Submissions with versions, approvals, change requests, faculty remarks.
- [x] Student activities logged against stages.
- [x] Reviews with rubrics, criteria, marks, and mark-correction audit.
- [x] Document management (typed, versioned, checksummed) including PHOTO & SPONSORSHIP.
- [x] CO/PO attainment computation.
- [x] Notifications and audit logging.
- [x] **Final Log Book PDF generation** built as a template-overlay engine (not a new design).
- [x] Eligibility validation that refuses generation with a `missing_items` report.
- [x] `LogBookPDFService` + `LogBookDataAssembler` + `TemplateMappingService` + `PDFRenderer` + `PDFValidationService` + `LogBookValidationService`.
- [x] API endpoints `POST/GET …/logbook/` and `…/logbook/generate/` + authenticated download.
- [x] Versioned `GeneratedLogBook` records (template version, generator, status, file).
- [x] `StudentProfile` extended with `photo`, `te_result`, `exam_seat_number`.
- [x] Visual regression test (40-page preservation, layout invariants, empty-data rule).
- [x] Activity-chart planned text, RTM, cost, and checklist pages preserved verbatim.

## 🚧 Remaining Work (Checklist)

- [ ] **Activity-chart dynamic data** — populate Date / Completion status / student & guide signatures per month from `StudentActivity` (currently preserved as static template text to avoid misalignment).
- [ ] **RTM & Cost-Estimation pages** — add data models/sources so these pages can be filled (currently left blank per the empty-data rule).
- [ ] **Review detail pages** — the template's Term-I/II review pages are title-only; wire detailed review/marks forms if the official forms are added to the template.
- [ ] **Final Evaluation marks table** — populate the official final-evaluation marks table from finalized `ReviewMark` values once the table layout is present in the template.
- [ ] **Digital signatures** — implement the authorized signature/upload flow for guide, reviewer, coordinator, HOD, and external examiner (currently kept blank by design).
- [ ] **Photo ingestion UI** — admin/student form to upload `StudentProfile.photo` (field exists; upload UI not yet built).
- [ ] **Frontend / web client** — this repo is an API backend; a UI consuming the DRF/OpenAPI schema is not included.
- [ ] **Sponsored-project detail fields** — add model fields (e.g., sponsored company, meeting summaries) beyond the SPONSORSHIP document flag.
- [ ] **CI/CD** — wire the test + ruff + mypy suite into a pipeline and add PDF regression to it.
- [ ] **Production hardening** — Sentry DSN, secret management, and object storage for generated log books.

---

## Deployment

See the [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html)
for full deployment guidance (Docker, gunicorn, static files, env config).
