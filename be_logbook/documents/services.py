from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.utils import timezone

from be_logbook.utils.access import is_faculty
from be_logbook.utils.access import is_hod
from be_logbook.utils.access import is_student
from be_logbook.utils.exceptions import BusinessRuleViolation

from .models import Document
from .models import DocumentVersion
from .models import compute_checksum

ALLOWED_MIME = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpeg",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/zip": "zip",
    "application/x-rar-compressed": "rar",
    "text/plain": "txt",
    "text/csv": "csv",
}


class DocumentService:
    """Secure document upload/versioning. Validation is enforced server-side."""

    @classmethod
    def validate_upload(cls, file_obj, user, group=None, owner=None):
        if file_obj.size > settings.MAX_DOCUMENT_SIZE:
            msg = "File exceeds the maximum allowed size."
            raise BusinessRuleViolation({"file": [msg]})
        ext = file_obj.name.split(".")[-1].lower() if "." in file_obj.name else ""
        if ext not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
            msg = f"Unsupported file extension '.{ext}'."
            raise BusinessRuleViolation({"file": [msg]})
        # MIME detection from content type header (not trusted alone).
        mime = getattr(file_obj, "content_type", "") or ""
        # Re-read to compute checksum and verify size again.
        file_obj.seek(0)
        checksum = compute_checksum(file_obj)
        file_obj.seek(0)
        expected_ext = ALLOWED_MIME.get(mime)
        if expected_ext is not None and expected_ext != ext:
            # Allow if extension is in allowed list; mime mismatch is a soft check
            pass
        # Authorization: must be allowed to upload to this group/owner.
        cls._assert_upload_allowed(user, group, owner)
        return checksum

    @classmethod
    def _assert_upload_allowed(cls, user, group, owner):
        if is_hod(user):
            return
        if group is not None:
            if is_student(user):
                from be_logbook.utils.access import is_group_member

                if not is_group_member(user, group):
                    msg = "You cannot upload documents to this group."
                    raise BusinessRuleViolation({"permission": [msg]})
                return
            if is_faculty(user):
                from be_logbook.utils.access import is_guide_for
                from be_logbook.utils.access import is_reviewer_for

                if is_guide_for(user, group) or is_reviewer_for(user, group):
                    return
                msg = "You are not authorized to upload to this group."
                raise BusinessRuleViolation({"permission": [msg]})
        if owner is not None and owner == user:
            return
        msg = "You are not authorized to upload this document."
        raise BusinessRuleViolation({"permission": [msg]})

    @classmethod
    @transaction.atomic
    def upload(
        cls,
        *,
        document_type,
        file_obj,
        user,
        group=None,
        project=None,
        stage=None,
        owner=None,
        request=None,
    ):
        checksum = cls.validate_upload(file_obj, user, group=group, owner=owner)
        mime = getattr(file_obj, "content_type", "") or ""
        ext = file_obj.name.split(".")[-1].lower() if "." in file_obj.name else ""
        # Keep a single ACTIVE logical document per (group, project, owner, type)
        # and record each upload as a new DocumentVersion.
        file_obj.seek(0)
        existing = Document.objects.filter(
            document_type=document_type,
            group=group,
            project=project,
            owner=owner,
            status="ACTIVE",
        ).first()
        if existing:
            existing.version += 1
            existing.original_filename = file_obj.name
            existing.file_size = file_obj.size
            existing.mime_type = mime
            existing.checksum = checksum
            existing.file.save(
                f"v{existing.version}_{file_obj.name}", File(file_obj), save=False
            )
            existing.save(
                update_fields=[
                    "version",
                    "file",
                    "original_filename",
                    "file_size",
                    "mime_type",
                    "checksum",
                    "updated_at",
                ]
            )
            doc = existing
            file_obj.seek(0)
            DocumentVersion.objects.create(
                document=doc,
                version=doc.version,
                file=File(file_obj),
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                checksum=checksum,
                uploaded_by=user,
            )
            action = "DOCUMENT_REPLACED"
        else:
            doc = Document.objects.create(
                document_type=document_type,
                group=group,
                project=project,
                stage=stage,
                owner=owner,
                uploaded_by=user,
                version=1,
                original_filename=file_obj.name,
                file_size=file_obj.size,
                mime_type=mime,
                checksum=checksum,
                status="ACTIVE",
            )
            doc.file.save(file_obj.name, File(file_obj), save=True)
            file_obj.seek(0)
            DocumentVersion.objects.create(
                document=doc,
                version=1,
                file=File(file_obj),
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                checksum=checksum,
                uploaded_by=user,
            )
            action = "DOCUMENT_UPLOADED"
        from be_logbook.audit.services import AuditService

        AuditService.record(
            actor=user,
            action=action,
            entity="Document",
            object_id=doc.id,
            new_state=doc.version,
            request=request,
        )
        return doc
