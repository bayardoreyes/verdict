from app.services.decision_engine import DecisionEngine
from app.models.decision import DecisionVerdict
from app.models.policy_rule import PolicyRule

class RuleBasedDecisionEngine(DecisionEngine):
    def evaluate(self, expense_request, active_policy, db_session):
        rule = (
            db_session.query(PolicyRule)
            .filter(
                PolicyRule.policy_id == active_policy.id,
                PolicyRule.category == expense_request.category,
            )
            .first()
        )

        if rule is None:
            return (
                DecisionVerdict.REJECT,
                1.0,
                f"Category '{expense_request.category}' is not covered by any rule in the active policy.",
                None,
            )

        if expense_request.amount <= rule.max_amount:
            return (
                DecisionVerdict.APPROVE,
                1.0,
                f"Amount {expense_request.amount} is within the {rule.max_amount} limit for rule {rule.rule_code}.",
                rule.id,
            )

        return (
            DecisionVerdict.ESCALATE,
            0.5,
            f"Amount {expense_request.amount} exceeds the {rule.max_amount} limit for rule {rule.rule_code}; needs human review.",
            rule.id,
        )