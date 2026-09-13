from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=True)
    policy_rule_id = Column(Integer, ForeignKey("policy_rules.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(50), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    raw_llm_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    decision = relationship("Decision")
    policy_rule = relationship("PolicyRule")
    actor = relationship("User")

    def __repr__(self):
        return f"<AuditLog id={self.id} event={self.event_type} decision={self.decision_id}>"