from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import get_db
from app.models.user import User, UserRole
from app.models.expense_request import ExpenseRequest
from app.models.decision import Decision, DecisionVerdict
from app.models.audit_log import AuditLog
from app.auth import create_access_token, get_current_user_from_cookie, require_role_cookie
from app.services.decision_orchestrator import evaluate_expense_request
from app.services.review_service import apply_human_review

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.verify_password(password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid email or password"},
            status_code=401,
        )

    token = create_access_token(user)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.get("/dashboard")
def dashboard(
    request: Request,
    user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    review_queue = []
    if user.role == UserRole.REVIEWER:
        review_queue = (
            db.query(Decision)
            .join(ExpenseRequest)
            .filter(Decision.current_status == DecisionVerdict.ESCALATE)
            .order_by(Decision.id.desc())
            .all()
        )

    return templates.TemplateResponse(
        request, "dashboard.html", {"user": user, "review_queue": review_queue}
    )


@router.get("/expense-requests/new")
def new_expense_page(
    request: Request, user: User = Depends(require_role_cookie(UserRole.EMPLOYEE))
):
    return templates.TemplateResponse(request, "new_expense.html", {"error": None})


@router.post("/expense-requests/new")
def new_expense_submit(
    request: Request,
    category: str = Form(...),
    amount: Decimal = Form(...),
    description: str = Form(""),
    user: User = Depends(require_role_cookie(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
):
    new_request = ExpenseRequest(
        employee_id=user.id,
        category=category,
        amount=amount,
        description=description or None,
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    decision = evaluate_expense_request(new_request, db)

    return templates.TemplateResponse(
        request, "expense_result.html", {"expense": new_request, "decision": decision}
    )


@router.post("/decisions/{decision_id}/review")
def review_decision_form(
    decision_id: int,
    new_status: DecisionVerdict = Form(...),
    user: User = Depends(require_role_cookie(UserRole.REVIEWER)),
    db: Session = Depends(get_db),
):
    decision = db.query(Decision).filter(Decision.id == decision_id).first()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    apply_human_review(decision, new_status, user, db)
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/decisions/{decision_id}")
def decision_detail_page(
    decision_id: int,
    request: Request,
    user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    decision = db.query(Decision).filter(Decision.id == decision_id).first()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    if user.role == UserRole.EMPLOYEE and decision.request.employee_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this decision")

    audit_entries = (
        db.query(AuditLog)
        .filter(AuditLog.decision_id == decision.id)
        .order_by(AuditLog.created_at)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "decision_detail.html",
        {"decision": decision, "audit_entries": audit_entries},
    )


@router.get("/reports/decisions")
def decisions_report_page(
    request: Request,
    user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    query = db.query(Decision).join(ExpenseRequest)

    if user.role == UserRole.EMPLOYEE:
        query = query.filter(ExpenseRequest.employee_id == user.id)

    decisions = query.order_by(Decision.id.desc()).all()

    return templates.TemplateResponse(
        request,
        "report_decisions.html",
        {"decisions": decisions, "generated_at": datetime.now()},
    )