from app.database import SessionLocal
from app.models.user import User, UserRole

db = SessionLocal()

test_users = [
    ("reviewer@antonios.com", "testpass123", UserRole.REVIEWER),
    ("employee@antonios.com", "testpass123", UserRole.EMPLOYEE),
]

for email, password, role in test_users:
    existing = db.query(User).filter(User.email == email).first()
    if existing is None:
        user = User(email=email, password_hash="placeholder", role=role)
        user.set_password(password)
        db.add(user)
        db.commit()
        print(f"Created: {email} ({role.value})")
    else:
        print(f"Already exists: {email} ({role.value})")

db.close()