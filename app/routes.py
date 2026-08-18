from flask import Blueprint, jsonify, request
from datetime import datetime
from math import ceil

from .models import (
    get_all_expenses,
    get_expense,
    create_expense,
    update_expense,
    delete_expense,
)


expense_bp = Blueprint("expenses", __name__)


def parse_date(value):
    """Parse a date in YYYY-MM-DD format."""
    if value is None:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@expense_bp.route("/expenses", methods=["POST"])
def add_expense():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "Request body must be valid JSON."
        }), 400

    error = validate_expense(data)

    if error:
        return jsonify({"error": error}), 400

    expense_id = create_expense(
        data["title"].strip(),
        float(data["amount"]),
        data["category"].strip(),
        data["date"],
    )

    # create_expense() returns the ID, so fetch the complete
    # expense before returning the response.
    return jsonify(get_expense(expense_id)), 201


@expense_bp.route("/expenses", methods=["GET"])
def list_expenses():
    # ---------------------------------------------------------
    # Check whether pagination was requested
    # ---------------------------------------------------------
    page_value = request.args.get("page")
    per_page_value = request.args.get("per_page")

    pagination_requested = (
        page_value is not None
        or per_page_value is not None
    )

    # Defaults when pagination is requested
    page = 1
    per_page = 10

    # ---------------------------------------------------------
    # Validate page
    # ---------------------------------------------------------
    if page_value is not None:
        try:
            page = int(page_value)
        except (TypeError, ValueError):
            return jsonify({
                "error": "page must be a positive integer."
            }), 400

        if page <= 0:
            return jsonify({
                "error": "page must be a positive integer."
            }), 400

    # ---------------------------------------------------------
    # Validate per_page
    # ---------------------------------------------------------
    if per_page_value is not None:
        try:
            per_page = int(per_page_value)
        except (TypeError, ValueError):
            return jsonify({
                "error": "per_page must be a positive integer."
            }), 400

        if per_page <= 0:
            return jsonify({
                "error": "per_page must be a positive integer."
            }), 400

    # ---------------------------------------------------------
    # Validate start_date
    # ---------------------------------------------------------
    start_date_value = request.args.get("start_date")
    start_date = None

    if start_date_value is not None:
        start_date = parse_date(start_date_value)

        if start_date is None:
            return jsonify({
                "error": "start_date must use YYYY-MM-DD format."
            }), 400

    # ---------------------------------------------------------
    # Validate end_date
    # ---------------------------------------------------------
    end_date_value = request.args.get("end_date")
    end_date = None

    if end_date_value is not None:
        end_date = parse_date(end_date_value)

        if end_date is None:
            return jsonify({
                "error": "end_date must use YYYY-MM-DD format."
            }), 400

    # ---------------------------------------------------------
    # Validate date range
    # ---------------------------------------------------------
    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        return jsonify({
            "error": "start_date must be on or before end_date."
        }), 400

    # ---------------------------------------------------------
    # Get all existing expenses
    # ---------------------------------------------------------
    expenses = get_all_expenses()

    # ---------------------------------------------------------
    # Apply date filtering BEFORE pagination
    # ---------------------------------------------------------
    filtered_expenses = []

    for expense in expenses:
        expense_date = parse_date(expense.get("date"))

        if expense_date is None:
            continue

        # Inclusive start boundary
        if (
            start_date is not None
            and expense_date < start_date
        ):
            continue

        # Inclusive end boundary
        if (
            end_date is not None
            and expense_date > end_date
        ):
            continue

        filtered_expenses.append(expense)

    # ---------------------------------------------------------
    # No pagination:
    # preserve existing list response
    # ---------------------------------------------------------
    if not pagination_requested:
        return jsonify(filtered_expenses), 200

    # ---------------------------------------------------------
    # Pagination AFTER date filtering
    # ---------------------------------------------------------
    total = len(filtered_expenses)

    if total == 0:
        pages = 0
    else:
        pages = ceil(total / per_page)

    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    page_expenses = filtered_expenses[
        start_index:end_index
    ]

    return jsonify({
        "expenses": page_expenses,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
    }), 200


@expense_bp.route("/expenses/<int:expense_id>", methods=["GET"])
def fetch_expense(expense_id):
    expense = get_expense(expense_id)

    if expense is None:
        return jsonify({
            "error": "Expense not found."
        }), 404

    return jsonify(expense), 200


@expense_bp.route("/expenses/<int:expense_id>", methods=["PUT"])
def edit_expense(expense_id):
    if get_expense(expense_id) is None:
        return jsonify({
            "error": "Expense not found."
        }), 404

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "Request body must be valid JSON."
        }), 400

    error = validate_expense(data)

    if error:
        return jsonify({
            "error": error
        }), 400

    update_expense(
        expense_id,
        data["title"].strip(),
        float(data["amount"]),
        data["category"].strip(),
        data["date"],
    )

    return jsonify(get_expense(expense_id)), 200


@expense_bp.route("/expenses/<int:expense_id>", methods=["DELETE"])
def remove_expense(expense_id):
    if get_expense(expense_id) is None:
        return jsonify({
            "error": "Expense not found."
        }), 404

    delete_expense(expense_id)

    return jsonify({
        "message": "Expense deleted."
    }), 200


def validate_expense(data):
    required_fields = [
        "title",
        "amount",
        "category",
        "date",
    ]

    for field in required_fields:
        if field not in data:
            return f"{field} is required."

    if (
        not isinstance(data["title"], str)
        or not data["title"].strip()
    ):
        return "title must be a non-empty string."

    if (
        not isinstance(data["category"], str)
        or not data["category"].strip()
    ):
        return "category must be a non-empty string."

    try:
        amount = float(data["amount"])
    except (TypeError, ValueError):
        return "amount must be a number."

    if amount <= 0:
        return "amount must be greater than zero."

    if parse_date(data["date"]) is None:
        return "date must use YYYY-MM-DD format."

    return None