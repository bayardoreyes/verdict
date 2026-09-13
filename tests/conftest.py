import pytest
from unittest.mock import patch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.expense_policy import ExpensePolicy
from app.models.policy_rule import PolicyRule


def pytest_configure(config):
    config.addinivalue_line("markers", "real_llm_engine: bypasses the LLM test double")


@pytest.fixture()
def engine():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def db_session(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def disable_real_llm_calls(request):
    if request.node.get_closest_marker("real_llm_engine"):
        yield
        return

    with patch(
        "app.services.llm_engine.LLMDecisionEngine.evaluate",
        side_effect=Exception("LLM disabled in tests"),
    ):
        yield


@pytest.fixture()
def active_policy(db_session):
    policy = ExpensePolicy(version_number=1, is_active=True)
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    rules = [
        ("R-01", "meals", 50.00),
        ("R-02", "travel", 200.00),
        ("R-03", "office_supplies", 100.00),
        ("R-04", "software", 500.00),
    ]
    for code, category, max_amount in rules:
        db_session.add(
            PolicyRule(policy_id=policy.id, rule_code=code, category=category, max_amount=max_amount)
        )
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture()
def employee_user(db_session):
    user = User(email="employee@test.com", password_hash="x", role=UserRole.EMPLOYEE)
    user.set_password("testpass123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def reviewer_user(db_session):
    user = User(email="reviewer@test.com", password_hash="x", role=UserRole.REVIEWER)
    user.set_password("testpass123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def login(client: TestClient, email: str, password: str) -> None:
    response = client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=False
    )
    assert response.status_code == 303, f"Login failed for {email}: {response.text}"