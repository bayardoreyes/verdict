from app.database import SessionLocal
from app.models.user import User, UserRole

db = SessionLocal()

existing = db.query(User).filter(User.email == "reviewer@antonios.com").first()
if existing is None:
    user = User(email="reviewer@antonios.com", password_hash="placeholder", role=UserRole.REVIEWER)
    user.set_password("testpass123")
    db.add(user)
    db.commit()
    print("User created")
else:
    print("User already exists")

db.close()