import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token(user: User) -> str:
    expiration_minutes = int(os.getenv("JWT_EXPIRATION_MINUTES"))
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes),
    }
    secret = os.getenv("JWT_SECRET_KEY")
    return jwt.encode(payload, secret, algorithm="HS256")


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()

    if user is None or not user.verify_password(credentials.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user)
    return LoginResponse(access_token=token)