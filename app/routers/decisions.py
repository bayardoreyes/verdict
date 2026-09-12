from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.decision import Decision, DecisionVerdict
from app.models.expense_request import ExpenseRequest
from app.services.review_service import apply_human_review

router = APIRouter(prefix="/decisions", tags=["decisions"])


class DecisionListItem(BaseModel):
    id: int
    request_id: int
    category: str
    amount: Decimal
    ai_verdict: str
    ai_confidence: float
    current_status: str
    reviewer_id: int | None

    class Config:
        from_attributes = True


class ReviewRequest(BaseModel):
    new_status: DecisionVerdict


@router.get("/", response_model=list[DecisionListItem])
def search_decisions(
    status: Optional[DecisionVerdict] = Query(None, description="Filter by current_status"),
    category: Optional[str] = Query(None, description="Filter by expense category"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Decision).join(ExpenseRequest)

    if current_user.role == UserRole.EMPLOYEE:
        query = query.filter(ExpenseRequest.employee_id == current_user.id)

    if status is not None:
        query = query.filter(Decision.current_status == status)

    if category is not None:
        query = query.filter(ExpenseRequest.category == category)

    results = query.all()

    return [
        DecisionListItem(
            id=d.id,
            request_id=d.request_id,
            category=d.request.category,
            amount=d.request.amount,
            ai_verdict=d.ai_verdict.value,
            ai_confidence=float(d.ai_confidence),
            current_status=d.current_status.value,
            reviewer_id=d.reviewer_id,
        )
        for d in results
    ]


@router.patch("/{decision_id}/review", response_model=DecisionListItem)
def review_decision(
    decision_id: int,
    review: ReviewRequest,
    current_user: User = Depends(require_role(UserRole.REVIEWER)),
    db: Session = Depends(get_db),
):
    decision = db.query(Decision).filter(Decision.id == decision_id).first()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    apply_human_review(decision, review.new_status, current_user, db)

    return DecisionListItem(
        id=decision.id,
        request_id=decision.request_id,
        category=decision.request.category,
        amount=decision.request.amount,
        ai_verdict=decision.ai_verdict.value,
        ai_confidence=float(decision.ai_confidence),
        current_status=decision.current_status.value,
        reviewer_id=decision.reviewer_id,
    )