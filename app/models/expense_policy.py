from sqlalchemy import Column, Integer, Boolean
from app.database import Base


class ExpensePolicy(Base):
    __tablename__ = "expense_policies"

    id = Column(Integer, primary_key=True)
    version_number = Column(Integer, nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<ExpensePolicy v{self.version_number} active={self.is_active}>"