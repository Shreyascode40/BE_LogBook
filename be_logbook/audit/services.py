from __future__ import annotations

from typing import TYPE_CHECKING, Any

from be_logbook.audit.models import AuditLog


class AuditService:
    """Records append-only audit entries for critical academic actions."""

    @staticmethod
    def record(
        *,
        actor=None,
        action: str,
        entity: str,
        object_id: int | None = None,
        previous_state: Any = None,
        new_state: Any = None,
        request=None,
        meta: dict | None = None,
    ) -> AuditLog:
        ip = None
        ua = ""
        if request is not None:
            ip = AuditService._get_client_ip(request)
            ua = request.META.get("HTTP_USER_AGENT", "")[:500]
        return AuditLog.objects.create(
            actor=actor,
            actor_role=getattr(actor, "role", "") if actor else "",
            action=action,
            entity=entity,
            object_id=object_id,
            previous_state=str(previous_state) if previous_state is not None else None,
            new_state=str(new_state) if new_state is not None else None,
            ip_address=ip,
            user_agent=ua,
            meta=meta or {},
        )

    @staticmethod
    def _get_client_ip(request) -> str | None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
