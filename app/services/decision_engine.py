from abc import ABC, abstractmethod
from app.models.decision import DecisionVerdict


class DecisionEngine(ABC):
    @abstractmethod
    def evaluate(self, expense_request, active_policy, db_session):
        """
        Evaluates an expense request against the active policy.
        Must return a tuple: (verdict: DecisionVerdict, confidence: float,
        reasoning: str, cited_rule_id: int | None)
        """
        raise NotImplementedError