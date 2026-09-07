import os
import json
import requests
from app.services.decision_engine import DecisionEngine
from app.models.decision import DecisionVerdict
from app.models.policy_rule import PolicyRule

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMDecisionEngine(DecisionEngine):
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL")

    def evaluate(self, expense_request, active_policy, db_session):
        rules = (
            db_session.query(PolicyRule)
            .filter(PolicyRule.policy_id == active_policy.id)
            .all()
        )

        rules_context = "\n".join(
            f"- {r.rule_code}: category='{r.category}', max_amount={r.max_amount}"
            for r in rules
        )

        prompt = f"""You are an expense approval assistant. Given the active policy rules below,
evaluate this expense request and respond with ONLY a JSON object, no other text.

Active policy rules:
{rules_context}

Expense request:
- category: {expense_request.category}
- amount: {expense_request.amount}
- description: {expense_request.description}

Respond with exactly this JSON shape:
{{"verdict": "APPROVE" | "REJECT" | "ESCALATE", "confidence": 0.0-1.0, "reasoning": "short explanation", "cited_rule_code": "the rule code you used, or null"}}
"""

        response = requests.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        response.raise_for_status()
        raw_content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(raw_content)

        cited_rule = None
        if parsed.get("cited_rule_code"):
            cited_rule = next(
                (r for r in rules if r.rule_code == parsed["cited_rule_code"]), None
            )

        if parsed.get("cited_rule_code") and cited_rule is None:
            return (
                DecisionVerdict.ESCALATE,
                0.3,
                f"AI cited rule '{parsed['cited_rule_code']}' which does not exist in the active policy. Escalated for human review.",
                None,
            )

        verdict_text = parsed.get("verdict", "").strip().upper()
        try:
            verdict = DecisionVerdict[verdict_text]
        except KeyError:
            return (
                DecisionVerdict.ESCALATE,
                0.2,
                f"AI returned an unrecognized verdict format: '{parsed.get('verdict')}'. Escalated for human review.",
                None,
            )

        return (
            verdict,
            float(parsed["confidence"]),
            parsed["reasoning"],
            cited_rule.id if cited_rule else None,
        )