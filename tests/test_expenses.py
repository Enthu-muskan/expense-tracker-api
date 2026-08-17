import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(testing=True)

    app.config["DATABASE"] = str(tmp_path / "test.db")

    # Recreate the database using the test database path.
    from app.models import init_db

    init_db(app)

    with app.test_client() as client:
        yield client


def sample_expense():
    return {
        "title": "Lunch",
        "amount": 250,
        "category": "Food",
        "date": "2026-08-15",
    }


def test_create_expense(client):
    response = client.post(
        "/expenses",
        json=sample_expense(),
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["title"] == "Lunch"
    assert data["amount"] == 250
    assert data["category"] == "Food"


def test_get_expenses(client):
    client.post("/expenses", json=sample_expense())

    response = client.get("/expenses")

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["title"] == "Lunch"


def test_get_single_expense(client):
    create_response = client.post(
        "/expenses",
        json=sample_expense(),
    )

    expense_id = create_response.get_json()["id"]

    response = client.get(f"/expenses/{expense_id}")

    assert response.status_code == 200
    assert response.get_json()["id"] == expense_id


def test_get_missing_expense(client):
    response = client.get("/expenses/999")

    assert response.status_code == 404


def test_update_expense(client):
    create_response = client.post(
        "/expenses",
        json=sample_expense(),
    )

    expense_id = create_response.get_json()["id"]

    updated = {
        "title": "Dinner",
        "amount": 500,
        "category": "Food",
        "date": "2026-08-16",
    }

    response = client.put(
        f"/expenses/{expense_id}",
        json=updated,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["title"] == "Dinner"
    assert data["amount"] == 500


def test_delete_expense(client):
    create_response = client.post(
        "/expenses",
        json=sample_expense(),
    )

    expense_id = create_response.get_json()["id"]

    response = client.delete(
        f"/expenses/{expense_id}"
    )

    assert response.status_code == 200

    get_response = client.get(
        f"/expenses/{expense_id}"
    )

    assert get_response.status_code == 404


def test_missing_required_field(client):
    invalid_data = {
        "title": "Lunch",
        "amount": 200,
        "category": "Food",
    }

    response = client.post(
        "/expenses",
        json=invalid_data,
    )

    assert response.status_code == 400


def test_negative_amount(client):
    invalid_data = {
        "title": "Lunch",
        "amount": -100,
        "category": "Food",
        "date": "2026-08-15",
    }

    response = client.post(
        "/expenses",
        json=invalid_data,
    )

    assert response.status_code == 400


def test_invalid_date(client):
    invalid_data = {
        "title": "Lunch",
        "amount": 100,
        "category": "Food",
        "date": "15-08-2026",
    }

    response = client.post(
        "/expenses",
        json=invalid_data,
    )

    assert response.status_code == 400