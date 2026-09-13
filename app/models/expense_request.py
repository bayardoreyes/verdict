from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class ExpenseRequest(Base):
    __tablename__ = "expense_requests"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    employee = relationship("User")

    def __repr__(self):
        return f"<ExpenseRequest id={self.id} amount={self.amount} category={self.category}>"