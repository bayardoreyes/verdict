from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models.user import User, UserRole
from app.models.expense_request import ExpenseRequest
from app.models.decision import Decision, DecisionVerdict
from app.models.audit_log import AuditLog
from app.models.expense_policy import ExpensePolicy
from app.models.policy_rule import PolicyRule
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


def _get_own_expense_or_403(request_id: int, user: User, db: Session) -> ExpenseRequest:
    expense = db.query(ExpenseRequest).filter(ExpenseRequest.id == request_id).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense request not found")
    if expense.employee_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this expense")
    return expense


def _get_editable_decision_or_403(request_id: int, db: Session) -> Decision | None:
    decision = db.query(Decision).filter(Decision.request_id == request_id).first()
    if decision is not None and decision.reviewer_id is not None:
        raise HTTPException(
            status_code=403,
            detail="Cannot modify an expense that has already been reviewed by a human",
        )
    return decision


@router.get("/expense-requests/{request_id}/edit")
def edit_expense_page(
    request_id: int,
    request: Request,
    user: User = Depends(require_role_cookie(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
):
    expense = _get_own_expense_or_403(request_id, user, db)
    decision = _get_editable_decision_or_403(request_id, db)

    return templates.TemplateResponse(
        request, "edit_expense.html", {"expense": expense, "decision": decision, "error": None}
    )


@router.post("/expense-requests/{request_id}/edit")
def edit_expense_submit(
    request_id: int,
    request: Request,
    category: str = Form(...),
    amount: Decimal = Form(...),
    description: str = Form(""),
    user: User = Depends(require_role_cookie(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
):
    expense = _get_own_expense_or_403(request_id, user, db)
    decision = _get_editable_decision_or_403(request_id, db)

    expense.category = category
    expense.amount = amount
    expense.description = description or None
    db.commit()

    if decision is not None:
        db.query(AuditLog).filter(AuditLog.decision_id == decision.id).delete()
        db.delete(decision)
        db.commit()

    new_decision = evaluate_expense_request(expense, db)

    return templates.TemplateResponse(
        request, "expense_result.html", {"expense": expense, "decision": new_decision}
    )


@router.post("/expense-requests/{request_id}/delete")
def delete_expense_request(
    request_id: int,
    user: User = Depends(require_role_cookie(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
):
    expense = _get_own_expense_or_403(request_id, user, db)
    decision = _get_editable_decision_or_403(request_id, db)

    if decision is not None:
        db.query(AuditLog).filter(AuditLog.decision_id == decision.id).delete()
        db.delete(decision)

    db.delete(expense)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)


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
        {"decision": decision, "audit_entries": audit_entries, "user": user},
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

    firm_decisions = [d for d in decisions if d.ai_verdict != DecisionVerdict.ESCALATE]
    agreed_firm = [d for d in firm_decisions if d.current_status == d.ai_verdict]
    agreement_rate = (
        round(len(agreed_firm) / len(firm_decisions) * 100, 1) if firm_decisions else None
    )

    escalated = [d for d in decisions if d.ai_verdict == DecisionVerdict.ESCALATE]
    escalated_pending = [d for d in escalated if d.current_status == DecisionVerdict.ESCALATE]
    escalated_approved = [d for d in escalated if d.current_status == DecisionVerdict.APPROVE]
    escalated_rejected = [d for d in escalated if d.current_status == DecisionVerdict.REJECT]

    return templates.TemplateResponse(
        request,
        "report_decisions.html",
        {
            "decisions": decisions,
            "generated_at": datetime.now(),
            "firm_count": len(firm_decisions),
            "agreed_count": len(agreed_firm),
            "agreement_rate": agreement_rate,
            "escalated_count": len(escalated),
            "escalated_pending_count": len(escalated_pending),
            "escalated_approved_count": len(escalated_approved),
            "escalated_rejected_count": len(escalated_rejected),
        },
    )


@router.get("/search")
def search_decisions_page(
    request: Request,
    category: str = "",
    status: str = "",
    min_amount: str = "",
    max_amount: str = "",
    date_from: str = "",
    date_to: str = "",
    user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    searched = bool(request.query_params)

    query = db.query(Decision).join(ExpenseRequest)

    if user.role == UserRole.EMPLOYEE:
        query = query.filter(ExpenseRequest.employee_id == user.id)

    if category:
        query = query.filter(ExpenseRequest.category == category)

    if status:
        query = query.filter(Decision.current_status == DecisionVerdict[status])

    if min_amount:
        try:
            query = query.filter(ExpenseRequest.amount >= Decimal(min_amount))
        except InvalidOperation:
            pass

    if max_amount:
        try:
            query = query.filter(ExpenseRequest.amount <= Decimal(max_amount))
        except InvalidOperation:
            pass

    if date_from or date_to:
        query = query.join(AuditLog, AuditLog.decision_id == Decision.id).filter(
            AuditLog.event_type == "decision_generated_by_llm"
        )
        if date_from:
            query = query.filter(AuditLog.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.filter(
                AuditLog.created_at < datetime.fromisoformat(date_to) + timedelta(days=1)
            )

    decisions = query.order_by(Decision.id.desc()).all() if searched else []

    return templates.TemplateResponse(
        request,
        "search_decisions.html",
        {
            "decisions": decisions,
            "searched": searched,
            "category": category,
            "status": status,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


def _get_active_policy_or_404(db: Session) -> ExpensePolicy:
    policy = db.query(ExpensePolicy).filter(ExpensePolicy.is_active == True).first()
    if policy is None:
        raise HTTPException(status_code=404, detail="No active policy configured")
    return policy


@router.get("/policy-rules")
def policy_rules_page(
    request: Request,
    error: str | None = None,
    user: User = Depends(require_role_cookie(UserRole.REVIEWER)),
    db: Session = Depends(get_db),
):
    policy = _get_active_policy_or_404(db)
    rules = (
        db.query(PolicyRule)
        .filter(PolicyRule.policy_id == policy.id)
        .order_by(PolicyRule.rule_code)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "policy_rules.html",
        {"policy": policy, "rules": rules, "error": error},
    )


@router.post("/policy-rules")
def create_policy_rule(
    rule_code: str = Form(...),
    category: str = Form(...),
    max_amount: Decimal = Form(...),
    user: User = Depends(require_role_cookie(UserRole.REVIEWER)),
    db: Session = Depends(get_db),
):
    policy = _get_active_policy_or_404(db)
    new_rule = PolicyRule(
        policy_id=policy.id, rule_code=rule_code, category=category, max_amount=max_amount
    )
    db.add(new_rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            url="/policy-rules?error=A rule with that code already exists for this policy",
            status_code=303,
        )
    return RedirectResponse(url="/policy-rules", status_code=303)


@router.post("/policy-rules/{rule_id}/edit")
def edit_policy_rule(
    rule_id: int,
    category: str = Form(...),
    max_amount: Decimal = Form(...),
    user: User = Depends(require_role_cookie(UserRole.REVIEWER)),
    db: Session = Depends(get_db),
):
    rule = db.query(PolicyRule).filter(PolicyRule.id == rule_id).first()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.category = category
    rule.max_amount = max_amount
    db.commit()
    return RedirectResponse(url="/policy-rules", status_code=303)


@router.post("/policy-rules/{rule_id}/delete")
def delete_policy_rule(
    rule_id: int,
    user: User = Depends(require_role_cookie(UserRole.REVIEWER)),
    db: Session = Depends(get_db),
):
    rule = db.query(PolicyRule).filter(PolicyRule.id == rule_id).first()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            url="/policy-rules?error=Cannot delete a rule already cited by past decisions",
            status_code=303,
        )
    return RedirectResponse(url="/policy-rules", status_code=303)