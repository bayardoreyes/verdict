import enum
from sqlalchemy import Column, Integer, Numeric, Text, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import relationship
from app.database import Base


class DecisionVerdict(enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("expense_requests.id"), nullable=False, unique=True)
    policy_version_id = Column(Integer, ForeignKey("expense_policies.id"), nullable=False)
    cited_rule_id = Column(Integer, ForeignKey("policy_rules.id"), nullable=False)

    ai_verdict = Column(SqlEnum(DecisionVerdict), nullable=False)
    ai_confidence = Column(Numeric(3, 2), nullable=False)
    ai_reasoning = Column(Text, nullable=False)

    current_status = Column(SqlEnum(DecisionVerdict), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    request = relationship("ExpenseRequest")
    policy_version = relationship("ExpensePolicy")
    cited_rule = relationship("PolicyRule")
    reviewer = relationship("User")

    def __repr__(self):
        return f"<Decision id={self.id} verdict={self.ai_verdict} status={self.current_status}>"