from app.database import SessionLocal
from app.models.expense_policy import ExpensePolicy
from app.models.policy_rule import PolicyRule

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

db.close()