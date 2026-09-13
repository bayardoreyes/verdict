import json
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from app.models.expense_request import ExpenseRequest
from app.models.decision import DecisionVerdict
from app.services.llm_engine import LLMDecisionEngine

pytestmark = pytest.mark.real_llm_engine


def _make_expense(db_session, employee, category="meals", amount=30):
    expense = ExpenseRequest(
        employee_id=employee.id, category=category, amount=Decimal(str(amount)), description="test"
    )
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)
    return expense


def _fake_openrouter_response(payload_dict):
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload_dict)}}]
    }
    return fake_response


@patch("app.services.llm_engine.requests.post")
def test_llm_approve_response_is_parsed_correctly(mock_post, db_session, active_policy, employee_user):
    mock_post.return_value = _fake_openrouter_response(
        {"verdict": "APPROVE", "confidence": 0.95, "reasoning": "Within limit.", "cited_rule_code": "R-01"}
    )
    expense = _make_expense(db_session, employee_user, "meals", 30)
    engine = LLMDecisionEngine()

    verdict, confidence, reasoning, cited_rule_id = engine.evaluate(expense, active_policy, db_session)

    assert verdict == DecisionVerdict.APPROVE
    assert confidence == 0.95
    assert reasoning == "Within limit."
    assert cited_rule_id is not None
    mock_post.assert_called_once()


@patch("app.services.llm_engine.requests.post")
def test_llm_escalates_when_cited_rule_does_not_exist(mock_post, db_session, active_policy, employee_user):
    mock_post.return_value = _fake_openrouter_response(
        {"verdict": "APPROVE", "confidence": 0.9, "reasoning": "Looks fine.", "cited_rule_code": "R-99-FAKE"}
    )
    expense = _make_expense(db_session, employee_user)
    engine = LLMDecisionEngine()

    verdict, confidence, reasoning, cited_rule_id = engine.evaluate(expense, active_policy, db_session)

    assert verdict == DecisionVerdict.ESCALATE
    assert cited_rule_id is None
    assert "does not exist" in reasoning


@patch("app.services.llm_engine.requests.post")
def test_llm_escalates_on_unrecognized_verdict_text(mock_post, db_session, active_policy, employee_user):
    mock_post.return_value = _fake_openrouter_response(
        {"verdict": "MAYBE", "confidence": 0.5, "reasoning": "Not sure.", "cited_rule_code": None}
    )
    expense = _make_expense(db_session, employee_user)
    engine = LLMDecisionEngine()

    verdict, confidence, reasoning, cited_rule_id = engine.evaluate(expense, active_policy, db_session)

    assert verdict == DecisionVerdict.ESCALATE
    assert "unrecognized verdict" in reasoning


@patch("app.services.llm_engine.requests.post")
def test_llm_raises_on_malformed_json_triggering_orchestrator_fallback(
    mock_post, db_session, active_policy, employee_user
):
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {"choices": [{"message": {"content": "not valid json"}}]}
    mock_post.return_value = fake_response

    expense = _make_expense(db_session, employee_user)
    engine = LLMDecisionEngine()

    with pytest.raises(json.JSONDecodeError):
        engine.evaluate(expense, active_policy, db_session)