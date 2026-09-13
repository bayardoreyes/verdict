from decimal import Decimal
from app.models.expense_request import ExpenseRequest
from app.models.decision import DecisionVerdict
from app.services.rule_based_engine import RuleBasedDecisionEngine


def _make_expense(db_session, employee, category, amount, description="test"):
    expense = ExpenseRequest(
        employee_id=employee.id,
        category=category,
        amount=Decimal(str(amount)),
        description=description,
    )
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)
    return expense


def test_approve_when_amount_is_below_limit(db_session, active_policy, employee_user):
    expense = _make_expense(db_session, employee_user, "meals", 30)
    engine = RuleBasedDecisionEngine()

    verdict, confidence, reasoning, cited_rule_id = engine.evaluate(expense, active_policy, db_session)

    assert verdict == DecisionVerdict.APPROVE
    assert confidence == 1.0
    assert "within" in reasoning
    assert cited_rule_id is not None


def test_approve_at_exact_limit_boundary(db_session, active_policy, employee_user):
    expense = _make_expense(db_session, employee_user, "meals", 50)
    engine = RuleBasedDecisionEngine()

    verdict, *_ = engine.evaluate(expense, active_policy, db_session)

    assert verdict == DecisionVerdict.APPROVE


def test_escalate_when_amount_exceeds_limit(db_session, active_policy, employee_user):
    expense = _make_expense(db_session, employee_user, "meals", 50.01)
    engine = RuleBasedDecisionEngine()

    verdict, confidence, reasoning, cited_rule_id = engine.evaluate(expense, active_policy, db_session)

    assert verdict == DecisionVerdict.ESCALATE
    assert confidence == 0.5
    assert "exceeds" in reasoning
    assert cited_rule_id is not None


def test_reject_when_category_has_no_rule(db_session, active_policy, employee_user):
    expense = _make_expense(db_session, employee_user, "unknown_category", 10)
    engine = RuleBasedDecisionEngine()

    verdict, confidence, reasoning, cited_rule_id = engine.evaluate(expense, active_policy, db_session)

    assert verdict == DecisionVerdict.REJECT
    assert confidence == 1.0
    assert "not covered by any rule" in reasoning
    assert cited_rule_id is None


def test_reject_applies_regardless_of_amount_size(db_session, active_policy, employee_user):
    expense = _make_expense(db_session, employee_user, "unknown_category", 999999)
    engine = RuleBasedDecisionEngine()

    verdict, *_ = engine.evaluate(expense, active_policy, db_session)

    assert verdict == DecisionVerdict.REJECT