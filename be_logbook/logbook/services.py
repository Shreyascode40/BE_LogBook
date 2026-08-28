from __future__ import annotations

import io
import os
import uuid
from datetime import datetime

from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.utils import timezone

from be_logbook.utils.exceptions import BusinessRuleViolation

from .data_assembler import LogBookDataAssembler
from .models import GeneratedLogBook
from .renderer import PDFRenderer, PDFValidationService
from .template_mapping import TemplateMappingService
from .validation import LogBookValidationService

TEMPLATE_FILENAME = "Project Log book.pdf"
TEMPLATE_VERSION = "ACA/D/003B-rev00"


class LogBookPDFService:
    """Orchestrates final log book generation.

    Flow: validate eligibility -> load official template -> assemble approved
    data -> map to placements -> render overlay -> validate PDF -> persist a
    new versioned record. The original template file is never modified.
    """

    @classmethod
    def validate(cls, project) -> tuple[bool, list[str]]:
        return LogBookValidationService.validate(project)

    # ------------------------------------------------------------------ #
    @classmethod
    @transaction.atomic
    def generate(cls, project, user, request=None) -> GeneratedLogBook:
        ok, missing = cls.validate(project)
        if not ok:
            raise BusinessRuleViolation(
                {
                    "logbook": [
                        "Final log book cannot be generated.",
                        *missing,
                    ]
                }
            )

        template_bytes = cls._load_template()
        data = LogBookDataAssembler(project).assemble()
        mapping = TemplateMappingService(template_bytes)
        placements = mapping.build_placements(data)
        pdf_bytes = PDFRenderer().render(template_bytes, placements)

        validation = PDFValidationService.validate(pdf_bytes)
        if not validation["valid"]:
            raise BusinessRuleViolation(
                {
                    "logbook": [
                        "Generated PDF failed structural validation.",
                        *validation["errors"],
                    ]
                }
            )

        version = GeneratedLogBook.objects.filter(project=project).count() + 1
        group_number = project.group.group_number or "group"
        safe_group = "".join(c for c in str(group_number) if c.isalnum() or c in "-_")
        gen = GeneratedLogBook.objects.create(
            project=project,
            generated_by=user,
            version=version,
            template_version=TEMPLATE_VERSION,
            status="READY",
            metadata={
                "generated_at": timezone.now().isoformat(),
                "page_count": validation["page_count"],
                "template": TEMPLATE_FILENAME,
            },
        )
        filename = f"Project_Log_Book_{safe_group}.pdf"
        gen.file.save(filename, File(io.BytesIO(pdf_bytes)), save=True)

        from be_logbook.audit.services import AuditService

        AuditService.record(
            actor=user,
            action="LOGBOOK_GENERATED",
            entity="GeneratedLogBook",
            object_id=gen.id,
            new_state=f"v{version}",
            request=request,
        )
        return gen

    @classmethod
    def latest(cls, project) -> GeneratedLogBook | None:
        return (
            GeneratedLogBook.objects.filter(project=project)
            .order_by("-version")
            .first()
        )

    # ------------------------------------------------------------------ #
    @classmethod
    def _load_template(cls) -> bytes:
        path = getattr(settings, "LOGBOOK_TEMPLATE_PATH", None)
        if not path:
            path = os.path.join(settings.BASE_DIR, TEMPLATE_FILENAME)
        with open(path, "rb") as fh:
            return fh.read()
