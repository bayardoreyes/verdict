from sqlalchemy.orm import Session
from app.models.expense_policy import ExpensePolicy
from app.models.decision import Decision
from app.models.audit_log import AuditLog
from app.services.rule_based_engine import RuleBasedDecisionEngine
from app.services.llm_engine import LLMDecisionEngine


def evaluate_expense_request(expense_request, db_session: Session) -> Decision:
    active_policy = (
        db_session.query(ExpensePolicy)
        .filter(ExpensePolicy.is_active == True)
        .first()
    )
    if active_policy is None:
        raise ValueError("No active expense policy is configured.")

    llm_engine = LLMDecisionEngine()
    used_fallback = False

    try:
        verdict, confidence, reasoning, cited_rule_id = llm_engine.evaluate(
            expense_request, active_policy, db_session
        )
        raw_payload = getattr(llm_engine, "last_raw_response", None)
    except Exception as exc:
        used_fallback = True
        raw_payload = None
        rule_engine = RuleBasedDecisionEngine()
        verdict, confidence, reasoning, cited_rule_id = rule_engine.evaluate(
            expense_request, active_policy, db_session
        )
        reasoning = f"[Fallback to rule engine — LLM error: {exc}] {reasoning}"

    decision = Decision(
        request_id=expense_request.id,
        policy_version_id=active_policy.id,
        cited_rule_id=cited_rule_id,
        ai_verdict=verdict,
        ai_confidence=confidence,
        ai_reasoning=reasoning,
        current_status=verdict,
        reviewer_id=None,
    )
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)

    audit_entry = AuditLog(
        decision_id=decision.id,
        event_type="decision_fallback_to_rules" if used_fallback else "decision_generated_by_llm",
        actor_id=None,
        new_value=verdict.value,
        raw_llm_payload=raw_payload,
    )
    db_session.add(audit_entry)
    db_session.commit()

    return decision