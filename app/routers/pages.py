from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import get_db
from app.models.user import User, UserRole
from app.models.expense_request import ExpenseRequest
from app.auth import create_access_token, get_current_user_from_cookie, require_role_cookie
from app.services.decision_orchestrator import evaluate_expense_request

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
def dashboard(request: Request, user: User = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse(request, "dashboard.html", {"user": user})


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