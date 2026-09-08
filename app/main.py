from fastapi import FastAPI
from app.auth import router as auth_router
from app.routers.expense_requests import router as expense_requests_router

app = FastAPI(title="Verdict API")

app.include_router(auth_router)
app.include_router(expense_requests_router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Verdict"}