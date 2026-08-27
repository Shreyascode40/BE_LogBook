from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Q

from be_logbook.utils.exceptions import BusinessRuleViolation

if TYPE_CHECKING:
    from be_logbook.groups.models import ProjectGroup
    from be_logbook.workflow.models import Stage


class WorkflowService:
    """Central state machine for stage unlocking and group progress.

    The backend is the source of truth: a stage unlocks only when all of its
    configured prerequisites are satisfied (i.e. have an approved submission).
    """

    APPROVED_STATES = ("APPROVED", "LOCKED")

    @classmethod
    def is_stage_satisfied(cls, group, stage) -> bool:
        from be_logbook.submissions.models import Submission

        return Submission.objects.filter(
            group=group,
            stage=stage,
            status__in=cls.APPROVED_STATES,
        ).exists()

    @classmethod
    def are_prerequisites_satisfied(cls, group, stage) -> bool:
        prereqs = stage.dependencies.values_list("depends_on_id", flat=True)
        if not prereqs:
            return True
        from be_logbook.workflow.models import Stage as StageModel

        for prereq in StageModel.objects.filter(id__in=prereqs):
            if not cls.is_stage_satisfied(group, prereq):
                return False
        return True

    @classmethod
    def is_stage_unlocked(cls, group, stage) -> bool:
        if not stage.is_active:
            return False
        return cls.are_prerequisites_satisfied(group, stage)

    @classmethod
    def get_current_stage(cls, group):
        if group.current_stage_id:
            return group.current_stage
        return cls.compute_current_stage(group)

    @classmethod
    def compute_current_stage(cls, group):
        from be_logbook.workflow.models import Stage

        for stage in Stage.objects.filter(is_active=True, required=True).order_by(
            "display_order"
        ):
            if not cls.is_stage_satisfied(group, stage):
                return stage
        return None

    @classmethod
    @transaction.atomic
    def recompute_group_status(cls, group) -> None:
        from be_logbook.submissions.models import Submission
        from be_logbook.workflow.models import Stage

        current = None
        any_submitted = Submission.objects.filter(group=group).exists()
        for stage in Stage.objects.filter(is_active=True).order_by("display_order"):
            if cls.is_stage_satisfied(group, stage):
                continue
            current = stage
            break

        group.current_stage = current
        if group.status == "CANCELLED":
            pass
        elif current is None:
            group.status = "COMPLETED" if any_submitted else "NOT_STARTED"
        elif any_submitted:
            # Refine based on the latest submission state of the current stage.
            latest = (
                Submission.objects.filter(group=group, stage=current)
                .order_by("-version_number")
                .first()
            )
            if latest:
                group.status = latest.status
            else:
                group.status = "IN_PROGRESS"
        else:
            group.status = "NOT_STARTED"
        group.save(update_fields=["current_stage", "status", "updated_at"])

    @classmethod
    def stage_states(cls, group):
        """Return ordered states of all active stages for a group."""
        from be_logbook.workflow.models import Stage

        out = []
        for stage in Stage.objects.filter(is_active=True).order_by("display_order"):
            unlocked = cls.is_stage_unlocked(group, stage)
            satisfied = cls.is_stage_satisfied(group, stage)
            out.append(
                {
                    "stage_id": stage.id,
                    "code": stage.code,
                    "name": stage.name,
                    "unlocked": unlocked,
                    "satisfied": satisfied,
                    "is_current": group.current_stage_id == stage.id,
                }
            )
        return out
