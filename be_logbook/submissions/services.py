from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from be_logbook.submissions.models import SubmissionVersion
from be_logbook.utils.access import is_faculty
from be_logbook.utils.access import is_hod
from be_logbook.utils.access import is_student
from be_logbook.utils.exceptions import BusinessRuleViolation

if TYPE_CHECKING:
    from be_logbook.groups.models import ProjectGroup
    from be_logbook.users.models import User
    from be_logbook.workflow.models import Stage

ALLOWED_EDIT_STATES = {"DRAFT", "CHANGES_REQUIRED", "RESUBMITTED"}


class SubmissionService:
    """State machine for submissions. All transitions are server-enforced."""

    @classmethod
    def _assert_can_edit(cls, submission, user):
        if not is_student(user):
            msg = "Only students in the group may edit this submission."
            raise BusinessRuleViolation({"permission": [msg]})
        from be_logbook.utils.access import is_group_member

        if not is_group_member(user, submission.group):
            msg = "You are not a member of this group."
            raise BusinessRuleViolation({"permission": [msg]})
        if submission.status not in ALLOWED_EDIT_STATES:
            msg = "This submission can no longer be edited."
            raise BusinessRuleViolation({"status": [msg]})
        # Stage must be unlocked.
        from be_logbook.workflow.services import WorkflowService

        if not WorkflowService.is_stage_unlocked(submission.group, submission.stage):
            msg = "The stage for this submission is locked."
            raise BusinessRuleViolation({"stage": [msg]})

    @classmethod
    def _snapshot(cls, submission, user, status, remarks=""):
        submission.version_number += 1
        submission.save(update_fields=["version_number", "updated_at"])
        version = SubmissionVersion.objects.create(
            submission=submission,
            version_number=submission.version_number,
            data=submission.data,
            status=status,
            submitted_by=user,
            remarks=remarks,
        )
        return version

    @classmethod
    def save_draft(cls, submission, user, data, request=None):
        with transaction.atomic():
            cls._assert_can_edit(submission, user)
            submission.data = data
            submission.save(update_fields=["data", "updated_at"])
            cls._audit(submission, user, "SUBMISSION_DRAFT_SAVED", request=request)
        return submission

    @classmethod
    def submit(cls, submission, user, request=None):
        with transaction.atomic():
            cls._assert_can_edit(submission, user)
            previous = submission.status
            new_status = "SUBMITTED" if previous == "DRAFT" else "RESUBMITTED"
            submission.status = new_status
            submission.submitted_at = timezone.now()
            submission.save(
                update_fields=[
                    "data",
                    "status",
                    "version_number",
                    "submitted_at",
                    "updated_at",
                ]
            )
            version = cls._snapshot(submission, user, new_status)
            cls._audit(
                submission,
                user,
                "SUBMISSION_SUBMITTED",
                previous_state=previous,
                new_state=new_status,
                request=request,
            )
            cls._notify_group_guide(
                submission,
                "Submission submitted",
                f"A submission for {submission.stage.name} was submitted.",
            )
            cls._recompute(submission.group)
            return submission, version

    @classmethod
    def begin_review(cls, submission, user, request=None):
        with transaction.atomic():
            cls._assert_guide_or_hod(submission, user)
            if submission.status not in ("SUBMITTED", "RESUBMITTED"):
                msg = "Submission is not awaiting review."
                raise BusinessRuleViolation({"status": [msg]})
            submission.status = "UNDER_REVIEW"
            submission.reviewed_at = timezone.now()
            submission.save(update_fields=["status", "reviewed_at", "updated_at"])
            cls._audit(submission, user, "SUBMISSION_REVIEW_STARTED", request=request)
            cls._recompute(submission.group)
        return submission

    @classmethod
    def request_changes(cls, submission, user, text, request=None):
        with transaction.atomic():
            cls._assert_guide_or_hod(submission, user)
            if submission.status != "UNDER_REVIEW":
                msg = "Submission is not under review."
                raise BusinessRuleViolation({"status": [msg]})
            submission.status = "CHANGES_REQUIRED"
            submission.save(update_fields=["status", "updated_at"])
            from be_logbook.submissions.models import ChangeRequest

            ChangeRequest.objects.create(
                submission=submission, requested_by=user, text=text
            )
            cls._approval(submission, user, "CHANGES_REQUIRED", text)
            cls._snapshot(submission, user, "CHANGES_REQUIRED", text)
            cls._audit(
                submission,
                user,
                "CHANGES_REQUESTED",
                new_state="CHANGES_REQUIRED",
                request=request,
            )
            cls._notify_group_students(
                submission,
                "Changes requested",
                f"Changes were requested on {submission.stage.name}: {text}",
            )
            cls._recompute(submission.group)
        return submission

    @classmethod
    def approve(cls, submission, user, remarks="", request=None):
        with transaction.atomic():
            cls._assert_guide_or_hod(submission, user)
            if submission.status != "UNDER_REVIEW":
                msg = "Submission is not under review."
                raise BusinessRuleViolation({"status": [msg]})
            submission.status = "APPROVED"
            submission.approved_at = timezone.now()
            submission.current_approved_version = submission.version_number
            submission.save(
                update_fields=[
                    "status",
                    "approved_at",
                    "current_approved_version",
                    "updated_at",
                ]
            )
            cls._approval(submission, user, "APPROVED", remarks)
            cls._snapshot(submission, user, "APPROVED", remarks)
            cls._audit(
                submission,
                user,
                "SUBMISSION_APPROVED",
                new_state="APPROVED",
                request=request,
            )
            cls._notify_group_students(
                submission,
                "Submission approved",
                f"Your submission for {submission.stage.name} was approved.",
            )
            cls._recompute(submission.group)
        return submission

    @classmethod
    def lock(cls, submission, user, request=None):
        with transaction.atomic():
            cls._assert_guide_or_hod(submission, user)
            if submission.status != "APPROVED":
                msg = "Only approved submissions can be locked."
                raise BusinessRuleViolation({"status": [msg]})
            submission.status = "LOCKED"
            submission.locked_at = timezone.now()
            submission.save(update_fields=["status", "locked_at", "updated_at"])
            cls._audit(
                submission,
                user,
                "SUBMISSION_LOCKED",
                new_state="LOCKED",
                request=request,
            )
            cls._recompute(submission.group)
        return submission

    # ----- helpers -----
    @classmethod
    def _assert_guide_or_hod(cls, submission, user):
        if is_hod(user):
            return
        if not is_faculty(user):
            msg = "Only the assigned guide or HOD may review this submission."
            raise BusinessRuleViolation({"permission": [msg]})
        from be_logbook.utils.access import is_guide_for

        if not is_guide_for(user, submission.group):
            msg = "You are not the assigned guide for this group."
            raise BusinessRuleViolation({"permission": [msg]})

    @classmethod
    def _approval(cls, submission, user, decision, remarks):
        from be_logbook.submissions.models import Approval
        from be_logbook.submissions.models import SubmissionVersion

        version = (
            SubmissionVersion.objects.filter(submission=submission)
            .order_by("-version_number")
            .first()
        )
        Approval.objects.create(
            submission=submission,
            approver=user,
            role=getattr(user, "role", ""),
            decision=decision,
            remarks=remarks,
            version=version,
        )

    @classmethod
    def _recompute(cls, group):
        from be_logbook.workflow.services import WorkflowService

        WorkflowService.recompute_group_status(group)

    @classmethod
    def _audit(
        cls, submission, user, action, previous_state=None, new_state=None, request=None
    ):
        from be_logbook.audit.services import AuditService

        AuditService.record(
            actor=user,
            action=action,
            entity="Submission",
            object_id=submission.id,
            previous_state=previous_state,
            new_state=new_state,
            request=request,
        )

    @classmethod
    def _notify_group_students(cls, submission, title, message):
        from be_logbook.notifications.services import NotificationService

        for m in submission.group.memberships.filter(status="ACTIVE"):
            NotificationService.create(
                recipient=m.student,
                notification_type="SUBMISSION",
                title=title,
                message=message,
                related_object=submission,
            )

    @classmethod
    def _notify_group_guide(cls, submission, title, message):
        from be_logbook.notifications.services import NotificationService

        guide = submission.group.active_guide
        if guide:
            NotificationService.create(
                recipient=guide,
                notification_type="SUBMISSION",
                title=title,
                message=message,
                related_object=submission,
            )
