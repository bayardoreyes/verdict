from tests.conftest import login


def test_negative_amount_is_rejected(client, active_policy, employee_user):
    login(client, "employee@test.com", "testpass123")

    response = client.post(
        "/expense-requests/new",
        data={"category": "meals", "amount": "-500", "description": "malicious attempt"},
    )

    assert response.status_code == 422


def test_zero_amount_is_rejected(client, active_policy, employee_user):
    login(client, "employee@test.com", "testpass123")

    response = client.post(
        "/expense-requests/new",
        data={"category": "meals", "amount": "0", "description": "zero amount"},
    )

    assert response.status_code == 422


def test_valid_amount_is_accepted_end_to_end(client, active_policy, employee_user):
    login(client, "employee@test.com", "testpass123")

    response = client.post(
        "/expense-requests/new",
        data={"category": "meals", "amount": "30", "description": "team lunch"},
    )

    assert response.status_code == 200
    assert "APPROVE" in response.text


def test_negative_policy_rule_max_amount_is_rejected(client, active_policy, reviewer_user):
    login(client, "reviewer@test.com", "testpass123")

    response = client.post(
        "/policy-rules",
        data={"rule_code": "R-99", "category": "meals", "max_amount": "-10"},
    )

    assert response.status_code == 422


def test_zero_policy_rule_max_amount_is_rejected(client, active_policy, reviewer_user):
    login(client, "reviewer@test.com", "testpass123")

    response = client.post(
        "/policy-rules",
        data={"rule_code": "R-99", "category": "meals", "max_amount": "0"},
    )

    assert response.status_code == 422


def test_employee_cannot_access_policy_rules(client, active_policy, employee_user):
    login(client, "employee@test.com", "testpass123")

    response = client.get("/policy-rules")

    assert response.status_code == 403


def test_reviewer_cannot_submit_expense(client, active_policy, reviewer_user):
    login(client, "reviewer@test.com", "testpass123")

    response = client.get("/expense-requests/new")

    assert response.status_code == 403


def test_unauthenticated_request_is_rejected(client):
    response = client.get("/dashboard")

    assert response.status_code == 401