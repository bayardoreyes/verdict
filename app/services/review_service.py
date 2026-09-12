from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.models.decision import Decision, DecisionVerdict
from app.models.user import User


def apply_human_review(
    decision: Decision,
    new_status: DecisionVerdict,
    reviewer: User,
    db: Session,
) -> Decision:
    """
    Applies a human reviewer's verdict to an existing Decision and records the
    change in the audit trail. Shared by the JSON API (PATCH) and the
    server-rendered GUI (POST) so both entry points behave identically.
    The status change and the audit entry are committed together.
    """
    previous_status = decision.current_status.value

    decision.current_status = new_status
    decision.reviewer_id = reviewer.id

    audit_entry = AuditLog(
        decision_id=decision.id,
        event_type="human_review",
        actor_id=reviewer.id,
        previous_value=previous_status,
        new_value=new_status.value,
    )
    db.add(audit_entry)

    db.commit()
    db.refresh(decision)
    return decision