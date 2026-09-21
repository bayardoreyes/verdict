"""
Idempotent database initialization script for deployment.
Creates all tables (if they don't exist), then seeds the active
policy and test users by reusing the existing seed scripts' logic.
Safe to run on every container start.
"""
from app.database import Base, engine, SessionLocal
from app.models.expense_policy import ExpensePolicy
from app.models.policy_rule import PolicyRule
from app.models.user import User, UserRole

print("Creating tables (if they don't already exist)...")
Base.metadata.create_all(bind=engine)
print("Tables ready.")

db = SessionLocal()

existing_active = db.query(ExpensePolicy).filter(ExpensePolicy.is_active == True).first()

if existing_active is None:
    policy = ExpensePolicy(version_number=1, is_active=True)
    db.add(policy)
    db.commit()
    db.refresh(policy)

    rules = [
        PolicyRule(policy_id=policy.id, rule_code="R-01", category="meals", max_amount=50.00),
        PolicyRule(policy_id=policy.id, rule_code="R-02", category="travel", max_amount=200.00),
        PolicyRule(policy_id=policy.id, rule_code="R-03", category="office_supplies", max_amount=100.00),
        PolicyRule(policy_id=policy.id, rule_code="R-04", category="software", max_amount=500.00),
        PolicyRule(policy_id=policy.id, rule_code="R-05", category="lodging", max_amount=250.00),
        PolicyRule(policy_id=policy.id, rule_code="R-06", category="mileage", max_amount=100.00),
        PolicyRule(policy_id=policy.id, rule_code="R-07", category="client_entertainment", max_amount=150.00),
        PolicyRule(policy_id=policy.id, rule_code="R-08", category="conference_registration", max_amount=800.00),
    ]
    db.add_all(rules)
    db.commit()
    print(f"Created active policy v{policy.version_number} with {len(rules)} rules")
else:
    print(f"Active policy already exists: v{existing_active.version_number}")

test_users = [
    ("reviewer@antonios.com", "testpass123", UserRole.REVIEWER),
    ("employee@antonios.com", "testpass123", UserRole.EMPLOYEE),
]

for email, password, role in test_users:
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user is None:
        user = User(email=email, password_hash="placeholder", role=role)
        user.set_password(password)
        db.add(user)
        db.commit()
        print(f"Created test user: {email} ({role.value})")
    else:
        print(f"Test user already exists: {email} ({role.value})")

db.close()
print("Database initialization complete.")