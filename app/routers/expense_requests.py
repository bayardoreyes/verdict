from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.expense_request import ExpenseRequest

router = APIRouter(prefix="/expense-requests", tags=["expense-requests"])


class ExpenseRequestCreate(BaseModel):
    category: str
    amount: Decimal = Field(gt=0)
    description: str | None = None


class ExpenseRequestResponse(BaseModel):
    id: int
    employee_id: int
    category: str
    amount: Decimal
    description: str | None

    class Config:
        from_attributes = True


@router.post("/", response_model=ExpenseRequestResponse)
def create_expense_request(
    data: ExpenseRequestCreate,
    current_user: User = Depends(require_role(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
):
    new_request = ExpenseRequest(
        employee_id=current_user.id,
        category=data.category,
        amount=data.amount,
        description=data.description,
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request