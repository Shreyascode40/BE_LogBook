from __future__ import annotations

import decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from be_logbook.reviews.models import ReviewMark
from be_logbook.utils.access import is_faculty
from be_logbook.utils.access import is_hod
from be_logbook.utils.exceptions import BusinessRuleViolation

if TYPE_CHECKING:
    from be_logbook.reviews.models import Review
    from be_logbook.users.models import User


class ReviewService:
    """Handles review marks, finalization and audited corrections."""

    @classmethod
    def _assert_reviewer(cls, review: "Review", user: "User"):
        if is_hod(user):
            return
        if not is_faculty(user):
            msg = "Only an assigned reviewer or HOD may act on this review."
            raise BusinessRuleViolation({"permission": [msg]})
        from be_logbook.utils.access import is_reviewer_for

        if not is_reviewer_for(user, review.group, review.stage):
            msg = "You are not the assigned reviewer for this group/stage."
            raise BusinessRuleViolation({"permission": [msg]})

    @classmethod
    def enter_mark(cls, review, criterion, obtained, remarks, user, request=None):
        with transaction.atomic():
            cls._assert_reviewer(review, user)
            if review.status in ("FINALIZED", "CORRECTION_REQUESTED"):
                # Allow entry only in DRAFT/SUBMITTED/CORRECTED states.
                if review.status == "FINALIZED":
                    msg = "Review is finalized; request a correction first."
                    raise BusinessRuleViolation({"status": [msg]})
            if obtained < 0:
                msg = "Marks cannot be negative."
                raise BusinessRuleViolation({"obtained_marks": [msg]})
            if obtained > criterion.max_marks:
                msg = "Obtained marks exceed the maximum."
                raise BusinessRuleViolation({"obtained_marks": [msg]})
            mark, _ = ReviewMark.objects.update_or_create(
                review=review,
                criterion=criterion,
                defaults={
                    "max_marks": criterion.max_marks,
                    "obtained_marks": obtained,
                    "remarks": remarks or "",
                },
            )
            cls._recompute(review)
            cls._audit(
                review,
                user,
                "MARK_ENTERED",
                request=request,
                new_state=f"{criterion.code}={obtained}",
            )
        return mark

    @classmethod
    def submit(cls, review, user, request=None):
        with transaction.atomic():
            cls._assert_reviewer(review, user)
            cls._check_required(review)
            review.status = "SUBMITTED"
            review.save(update_fields=["status", "updated_at"])
            cls._audit(review, user, "REVIEW_SUBMITTED", request=request)
        return review

    @classmethod
    def finalize(cls, review, user, request=None):
        with transaction.atomic():
            cls._assert_reviewer(review, user)
            cls._check_required(review)
            review.status = "FINALIZED"
            review.finalized_at = timezone.now()
            review.finalized_by = user
            review.save(
                update_fields=["status", "finalized_at", "finalized_by", "updated_at"]
            )
            cls._audit(
                review, user, "REVIEW_FINALIZED", request=request, new_state="FINALIZED"
            )
            # Notify HOD / guide.
            from be_logbook.notifications.services import NotificationService

            NotificationService.create(
                recipient=review.reviewer,
                notification_type="REVIEW",
                title="Review finalized",
                message=f"Review for {review.group} / {review.stage} finalized.",
                related_object=review,
            )
        return review

    @classmethod
    def request_correction(cls, review, user, reason, request=None):
        with transaction.atomic():
            if not is_hod(user):
                msg = "Only HOD may request a mark correction."
                raise BusinessRuleViolation({"permission": [msg]})
            if review.status != "FINALIZED":
                msg = "Only a finalized review can be corrected."
                raise BusinessRuleViolation({"status": [msg]})
            review.status = "CORRECTION_REQUESTED"
            review.save(update_fields=["status", "updated_at"])
            cls._audit(
                review,
                user,
                "REVIEW_CORRECTION_REQUESTED",
                new_state="CORRECTION_REQUESTED",
                request=request,
            )
        return review

    @classmethod
    def correct_mark(
        cls, review, criterion, new_obtained, user, reason, approval=None, request=None
    ):
        with transaction.atomic():
            if not is_hod(user):
                msg = "Only HOD may correct marks."
                raise BusinessRuleViolation({"permission": [msg]})
            if review.status not in ("CORRECTION_REQUESTED", "CORRECTED"):
                msg = "Review must be in a correction state."
                raise BusinessRuleViolation({"status": [msg]})
            if new_obtained < 0 or new_obtained > criterion.max_marks:
                msg = "Corrected marks are out of range."
                raise BusinessRuleViolation({"obtained_marks": [msg]})
            mark = ReviewMark.objects.get(review=review, criterion=criterion)
            from be_logbook.reviews.models import ReviewMarkCorrection

            ReviewMarkCorrection.objects.create(
                review_mark=mark,
                review=review,
                corrected_by=user,
                old_obtained=mark.obtained_marks,
                new_obtained=new_obtained,
                reason=reason,
                approval=approval,
            )
            mark.obtained_marks = new_obtained
            mark.save(update_fields=["obtained_marks", "updated_at"])
            review.status = "CORRECTED"
            review.save(update_fields=["status", "updated_at"])
            cls._recompute(review)
            cls._audit(
                review,
                user,
                "MARK_CORRECTED",
                previous_state=str(mark.obtained_marks),
                new_state=f"{criterion.code}={new_obtained}",
                request=request,
            )
        return mark

    # ----- helpers -----
    @classmethod
    def _check_required(cls, review):
        missing = (
            review.rubric.criteria.filter(is_required=True)
            .exclude(id__in=review.marks.values_list("criterion_id", flat=True))
            .exists()
        )
        if missing:
            msg = "All required criteria must have marks before finalizing."
            raise BusinessRuleViolation({"marks": [msg]})

    @classmethod
    def _recompute(cls, review):
        total_max = decimal.Decimal(0)
        total_obtained = decimal.Decimal(0)
        for mark in review.marks.all():
            total_max += mark.max_marks
            total_obtained += mark.obtained_marks
        review.total_max = total_max
        review.total_obtained = total_obtained
        review.save(update_fields=["total_max", "total_obtained", "updated_at"])

    @classmethod
    def _audit(
        cls, review, user, action, previous_state=None, new_state=None, request=None
    ):
        from be_logbook.audit.services import AuditService

        AuditService.record(
            actor=user,
            action=action,
            entity="Review",
            object_id=review.id,
            previous_state=previous_state,
            new_state=new_state,
            request=request,
        )
