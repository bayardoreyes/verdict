import enum
from sqlalchemy import Column, Integer, String, Enum as SqlEnum
from app.database import Base


class UserRole(enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    REVIEWER = "REVIEWER"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SqlEnum(UserRole), nullable=False)

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"