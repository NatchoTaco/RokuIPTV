from sqlalchemy.orm import Session

from streamforge_api.models import AuditEvent


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        event_type: str,
        *,
        actor_user_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self.db.add(
            AuditEvent(
                actor_user_id=actor_user_id,
                event_type=event_type,
                ip_address=ip_address,
                user_agent=user_agent,
                details_json=details or {},
            )
        )
