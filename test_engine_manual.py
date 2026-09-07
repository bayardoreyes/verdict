from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.expense_policy import ExpensePolicy
from app.models.policy_rule import PolicyRule
from app.models.expense_request import ExpenseRequest
from app.services.rule_based_engine import RuleBasedDecisionEngine

db = SessionLocal()

# Seed minimal data
employee = User(email="test@antonios.com", password_hash="fake_hash", role=UserRole.EMPLOYEE)
policy = ExpensePolicy(version_number=1, is_active=True)
db.add_all([employee, policy])
db.commit()

rule = PolicyRule(policy_id=policy.id, rule_code="R-01", category="meals", max_amount=50.00)
db.add(rule)
db.commit()

request = ExpenseRequest(employee_id=employee.id, amount=35.00, category="meals", description="Team lunch")
db.add(request)
db.commit()

engine = RuleBasedDecisionEngine()
verdict, confidence, reasoning, cited_rule_id = engine.evaluate(request, policy, db)

print(f"Verdict: {verdict}")
print(f"Confidence: {confidence}")
print(f"Reasoning: {reasoning}")
print(f"Cited rule ID: {cited_rule_id}")

db.close()