from sqlalchemy.orm import Session
from app.models.expense_policy import ExpensePolicy
from app.models.decision import Decision
from app.models.audit_log import AuditLog
from app.services.rule_based_engine import RuleBasedDecisionEngine
from app.services.llm_engine import LLMDecisionEngine


def _get_active_policy(db_session: Session) -> ExpensePolicy:
    active_policy = (
        db_session.query(ExpensePolicy)
        .filter(ExpensePolicy.is_active == True)
        .first()
    )
    if active_policy is None:
        raise ValueError("No active expense policy is configured.")
    return active_policy


def _run_engines(expense_request, active_policy, db_session: Session):
    """
    Runs the LLM engine, falling back to the rule-based engine on any failure.
    Returns (verdict, confidence, reasoning, cited_rule_id, raw_payload, used_fallback).
    Pure evaluation logic — never touches the database itself.
    """
    llm_engine = LLMDecisionEngine()

    try:
        verdict, confidence, reasoning, cited_rule_id = llm_engine.evaluate(
            expense_request, active_policy, db_session
        )
        raw_payload = getattr(llm_engine, "last_raw_response", None)
        return verdict, confidence, reasoning, cited_rule_id, raw_payload, False
    except Exception as exc:
        rule_engine = RuleBasedDecisionEngine()
        verdict, confidence, reasoning, cited_rule_id = rule_engine.evaluate(
            expense_request, active_policy, db_session
        )
        reasoning = f"[Fallback to rule engine — LLM error: {exc}] {reasoning}"
        return verdict, confidence, reasoning, cited_rule_id, None, True


def evaluate_expense_request(expense_request, db_session: Session) -> Decision:
    """
    Used when a NEW expense request is submitted. Creates a fresh Decision row
    and its first audit log entry.
    """
    active_policy = _get_active_policy(db_session)
    verdict, confidence, reasoning, cited_rule_id, raw_payload, used_fallback = _run_engines(
        expense_request, active_policy, db_session
    )

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


def re_evaluate_expense_request(expense_request, decision: Decision, editor_id: int, db_session: Session) -> Decision:
    """
    Used when an employee edits an expense request that has not yet been
    reviewed by a human. Updates the SAME Decision row in place (never
    deletes it) and APPENDS new audit log entries — the original creation
    entry is preserved untouched, keeping the audit log fully append-only.
    """
    active_policy = _get_active_policy(db_session)

    previous_verdict = decision.ai_verdict.value
    edit_audit_entry = AuditLog(
        decision_id=decision.id,
        event_type="expense_edited_by_employee",
        actor_id=editor_id,
        previous_value=f"category={expense_request.category}, amount={expense_request.amount}",
        new_value=None,
    )
    db_session.add(edit_audit_entry)
    db_session.commit()

    verdict, confidence, reasoning, cited_rule_id, raw_payload, used_fallback = _run_engines(
        expense_request, active_policy, db_session
    )

    decision.ai_verdict = verdict
    decision.ai_confidence = confidence
    decision.ai_reasoning = reasoning
    decision.cited_rule_id = cited_rule_id
    decision.current_status = verdict
    db_session.commit()
    db_session.refresh(decision)

    regenerated_audit_entry = AuditLog(
        decision_id=decision.id,
        event_type="decision_regenerated_after_edit_fallback"
        if used_fallback
        else "decision_regenerated_after_edit",
        actor_id=None,
        previous_value=previous_verdict,
        new_value=verdict.value,
        raw_llm_payload=raw_payload,
    )
    db_session.add(regenerated_audit_entry)
    db_session.commit()

    return decision