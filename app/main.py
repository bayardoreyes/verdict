from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.auth import router as auth_router
from app.routers.expense_requests import router as expense_requests_router
from app.routers.decisions import router as decisions_router
from app.routers.pages import router as pages_router

app = FastAPI(title="Verdict API")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_router)
app.include_router(expense_requests_router)
app.include_router(decisions_router)
app.include_router(pages_router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Verdict"}