from fastapi import FastAPI
from app.auth import router as auth_router

app = FastAPI(title="Verdict API")

app.include_router(auth_router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Verdict"}