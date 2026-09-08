from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.expense_request import ExpenseRequest
from app.services.decision_orchestrator import evaluate_expense_request

router = APIRouter(prefix="/expense-requests", tags=["expense-requests"])


class ExpenseRequestCreate(BaseModel):
    category: str
    amount: Decimal = Field(gt=0)
    description: str | None = None


class DecisionSummary(BaseModel):
    id: int
    ai_verdict: str
    ai_confidence: float
    ai_reasoning: str

    class Config:
        from_attributes = True


class ExpenseRequestResponse(BaseModel):
    id: int
    employee_id: int
    category: str
    amount: Decimal
    description: str | None
    decision: DecisionSummary

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

    try:
        decision = evaluate_expense_request(new_request, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ExpenseRequestResponse(
        id=new_request.id,
        employee_id=new_request.employee_id,
        category=new_request.category,
        amount=new_request.amount,
        description=new_request.description,
        decision=DecisionSummary(
            id=decision.id,
            ai_verdict=decision.ai_verdict.value,
            ai_confidence=float(decision.ai_confidence),
            ai_reasoning=decision.ai_reasoning,
        ),
    )