import pytest

from app import create_app
from app.models import init_db


@pytest.fixture
def client(tmp_path):
    app = create_app(testing=True)
    app.config["DATABASE"] = str(tmp_path / "test.db")
    init_db(app)

    with app.test_client() as client:
        yield client


def create_expense(client, title, amount, category, date):
    response = client.post(
        "/expenses",
        json={
            "title": title,
            "amount": amount,
            "category": category,
            "date": date,
        },
    )
    assert response.status_code == 201
    return response.get_json()


def test_pagination_returns_metadata_and_requested_page(client):
    for index in range(1, 6):
        create_expense(
            client,
            f"Expense {index}",
            index * 100,
            "Food",
            f"2026-08-{index:02d}",
        )

    response = client.get("/expenses?page=2&per_page=2")

    assert response.status_code == 200
    data = response.get_json()
    assert data["page"] == 2
    assert data["per_page"] == 2
    assert data["total"] == 5
    assert data["pages"] == 3
    assert len(data["expenses"]) == 2
    assert data["expenses"][0]["title"] == "Expense 3"
    assert data["expenses"][1]["title"] == "Expense 4"


def test_only_page_uses_default_per_page(client):
    for index in range(1, 4):
        create_expense(
            client,
            f"Expense {index}",
            index * 100,
            "Food",
            "2026-08-15",
        )

    response = client.get("/expenses?page=1")

    assert response.status_code == 200
    data = response.get_json()
    assert data["page"] == 1
    assert data["per_page"] == 10
    assert data["total"] == 3
    assert data["pages"] == 1
    assert len(data["expenses"]) == 3


def test_only_per_page_uses_default_page(client):
    for index in range(1, 4):
        create_expense(
            client,
            f"Expense {index}",
            index * 100,
            "Food",
            "2026-08-15",
        )

    response = client.get("/expenses?per_page=2")

    assert response.status_code == 200
    data = response.get_json()
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert data["total"] == 3
    assert data["pages"] == 2
    assert len(data["expenses"]) == 2


def test_no_pagination_parameters_preserve_list_response(client):
    create_expense(client, "Lunch", 200, "Food", "2026-08-15")

    response = client.get("/expenses")

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "Lunch"


def test_date_range_filter_is_inclusive(client):
    create_expense(client, "Before", 100, "Food", "2026-08-10")
    create_expense(client, "Start", 200, "Food", "2026-08-15")
    create_expense(client, "Middle", 300, "Travel", "2026-08-17")
    create_expense(client, "End", 400, "Food", "2026-08-20")
    create_expense(client, "After", 500, "Food", "2026-08-25")

    response = client.get(
        "/expenses?start_date=2026-08-15&end_date=2026-08-20"
    )

    assert response.status_code == 200
    data = response.get_json()
    assert [expense["title"] for expense in data] == [
        "Start",
        "Middle",
        "End",
    ]


def test_start_date_filter(client):
    create_expense(client, "Old", 100, "Food", "2026-08-10")
    create_expense(client, "New", 200, "Food", "2026-08-20")

    response = client.get("/expenses?start_date=2026-08-15")

    assert response.status_code == 200
    data = response.get_json()
    assert [expense["title"] for expense in data] == ["New"]


def test_end_date_filter(client):
    create_expense(client, "Old", 100, "Food", "2026-08-10")
    create_expense(client, "New", 200, "Food", "2026-08-20")

    response = client.get("/expenses?end_date=2026-08-15")

    assert response.status_code == 200
    data = response.get_json()
    assert [expense["title"] for expense in data] == ["Old"]


def test_invalid_page_returns_400(client):
    response = client.get("/expenses?page=0&per_page=2")
    assert response.status_code == 400


def test_invalid_per_page_returns_400(client):
    response = client.get("/expenses?page=1&per_page=0")
    assert response.status_code == 400


def test_non_integer_page_returns_400(client):
    response = client.get("/expenses?page=abc&per_page=2")
    assert response.status_code == 400


def test_non_integer_per_page_returns_400(client):
    response = client.get("/expenses?page=1&per_page=abc")
    assert response.status_code == 400


def test_invalid_date_returns_400(client):
    response = client.get("/expenses?start_date=15-08-2026")
    assert response.status_code == 400


def test_invalid_date_range_returns_400(client):
    response = client.get(
        "/expenses?start_date=2026-08-20&end_date=2026-08-10"
    )
    assert response.status_code == 400


def test_pagination_and_date_filter_work_together(client):
    dates = [
        "2026-08-10",
        "2026-08-15",
        "2026-08-16",
        "2026-08-17",
        "2026-08-20",
        "2026-08-25",
    ]

    for index, date in enumerate(dates, start=1):
        create_expense(
            client,
            f"Expense {index}",
            index * 100,
            "Food",
            date,
        )

    response = client.get(
        "/expenses?start_date=2026-08-15&end_date=2026-08-20"
        "&page=2&per_page=2"
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 4
    assert data["pages"] == 2
    assert data["page"] == 2
    assert data["per_page"] == 2
    assert len(data["expenses"]) == 2
    assert data["expenses"][0]["title"] == "Expense 4"
    assert data["expenses"][1]["title"] == "Expense 5"