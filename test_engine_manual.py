from sqlalchemy import text
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.expense_policy import ExpensePolicy
from app.models.policy_rule import PolicyRule
from app.models.expense_request import ExpenseRequest
from app.services.rule_based_engine import RuleBasedDecisionEngine
from app.services.llm_engine import LLMDecisionEngine

db = SessionLocal()

# Reset all data before each run — makes this manual test script safely re-runnable
db.execute(text(
    "TRUNCATE audit_logs, decisions, expense_requests, policy_rules, expense_policies, users RESTART IDENTITY CASCADE"
))
db.commit()

employee = User(email="test2@antonios.com", password_hash="fake_hash", role=UserRole.EMPLOYEE)
policy = ExpensePolicy(version_number=2, is_active=False)
db.add_all([employee, policy])
db.commit()

rule = PolicyRule(policy_id=policy.id, rule_code="R-02", category="travel", max_amount=200.00)
db.add(rule)
db.commit()

request = ExpenseRequest(employee_id=employee.id, amount=150.00, category="travel", description="Client site visit, mileage and tolls")
db.add(request)
db.commit()

print("=== RuleBasedDecisionEngine ===")
rule_engine = RuleBasedDecisionEngine()
verdict, confidence, reasoning, cited_rule_id = rule_engine.evaluate(request, policy, db)
print(f"Verdict: {verdict}, Confidence: {confidence}, Cited rule: {cited_rule_id}")
print(f"Reasoning: {reasoning}")

print("\n=== LLMDecisionEngine ===")
llm_engine = LLMDecisionEngine()
verdict, confidence, reasoning, cited_rule_id = llm_engine.evaluate(request, policy, db)
print(f"Verdict: {verdict}, Confidence: {confidence}, Cited rule: {cited_rule_id}")
print(f"Reasoning: {reasoning}")

print("\n=== Password hashing test ===")
u = User(email="hashtest@antonios.com", password_hash="placeholder", role=UserRole.EMPLOYEE)
u.set_password("correcthorsebattery")
print(f"Hash: {u.password_hash[:20]}...")
print(f"Verify correct password: {u.verify_password('correcthorsebattery')}")
print(f"Verify wrong password: {u.verify_password('wrongpassword')}")

db.close()