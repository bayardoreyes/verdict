from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class PolicyRule(Base):
    __tablename__ = "policy_rules"
    __table_args__ = (
        UniqueConstraint("policy_id", "rule_code", name="uq_policy_rule_code"),
    )

    id = Column(Integer, primary_key=True)
    policy_id = Column(Integer, ForeignKey("expense_policies.id"), nullable=False)
    rule_code = Column(String(20), nullable=False)
    category = Column(String(100), nullable=False)
    max_amount = Column(Numeric(10, 2), nullable=False)

    policy = relationship("ExpensePolicy")

    def __repr__(self):
        return f"<PolicyRule {self.rule_code} category={self.category} max={self.max_amount}>"