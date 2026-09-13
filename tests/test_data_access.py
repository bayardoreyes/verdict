import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app.models.user import User, UserRole
from app.models.expense_request import ExpenseRequest
from app.models.decision import Decision, DecisionVerdict
from app.models.policy_rule import PolicyRule
from app.models.audit_log import AuditLog


def _make_expense(db_session, employee, category="meals", amount=30):
    expense = ExpenseRequest(
        employee_id=employee.id, category=category, amount=Decimal(str(amount)), description="test"
    )
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)
    return expense


def _make_decision(db_session, expense, active_policy, cited_rule_id=None):
    decision = Decision(
        request_id=expense.id,
        policy_version_id=active_policy.id,
        cited_rule_id=cited_rule_id,
        ai_verdict=DecisionVerdict.APPROVE,
        ai_confidence=Decimal("1.00"),
        ai_reasoning="test reasoning",
        current_status=DecisionVerdict.APPROVE,
    )
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    return decision


def test_policy_rule_code_must_be_unique_within_a_policy(db_session, active_policy):
    duplicate = PolicyRule(policy_id=active_policy.id, rule_code="R-01", category="travel", max_amount=999)
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_decision_request_id_must_be_unique(db_session, active_policy, employee_user):
    expense = _make_expense(db_session, employee_user)
    _make_decision(db_session, expense, active_policy)

    second_decision = Decision(
        request_id=expense.id,
        policy_version_id=active_policy.id,
        ai_verdict=DecisionVerdict.REJECT,
        ai_confidence=Decimal("1.00"),
        ai_reasoning="duplicate attempt",
        current_status=DecisionVerdict.REJECT,
    )
    db_session.add(second_decision)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_decision_cannot_cite_a_nonexistent_rule(db_session, active_policy, employee_user):
    expense = _make_expense(db_session, employee_user)
    bad_decision = Decision(
        request_id=expense.id,
        policy_version_id=active_policy.id,
        cited_rule_id=999999,
        ai_verdict=DecisionVerdict.APPROVE,
        ai_confidence=Decimal("1.00"),
        ai_reasoning="cites a rule that does not exist",
        current_status=DecisionVerdict.APPROVE,
    )
    db_session.add(bad_decision)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_email_must_be_unique(db_session, employee_user):
    duplicate = User(email=employee_user.email, password_hash="x", role=UserRole.REVIEWER)
    duplicate.set_password("anotherpass")
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_cannot_delete_a_policy_rule_already_cited_by_a_decision(db_session, active_policy, employee_user):
    rule = db_session.query(PolicyRule).filter_by(policy_id=active_policy.id, rule_code="R-01").first()
    expense = _make_expense(db_session, employee_user)
    _make_decision(db_session, expense, active_policy, cited_rule_id=rule.id)

    db_session.delete(rule)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_deleting_an_uncited_policy_rule_nullifies_its_audit_entries(db_session, active_policy, reviewer_user):
    rule = PolicyRule(policy_id=active_policy.id, rule_code="R-99", category="meals", max_amount=999)
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    audit_entry = AuditLog(
        policy_rule_id=rule.id,
        event_type="policy_rule_created",
        actor_id=reviewer_user.id,
        new_value=f"rule_code={rule.rule_code}, category=meals, max_amount=999",
    )
    db_session.add(audit_entry)
    db_session.commit()
    db_session.refresh(audit_entry)

    db_session.delete(rule)
    db_session.commit()

    db_session.refresh(audit_entry)
    assert audit_entry.policy_rule_id is None
    assert "rule_code=R-99" in audit_entry.new_value