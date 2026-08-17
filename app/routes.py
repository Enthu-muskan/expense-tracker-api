from datetime import datetime

from flask import Blueprint, jsonify, request

from .models import (
    create_expense,
    delete_expense,
    get_all_expenses,
    get_expense,
    update_expense,
)


expense_bp = Blueprint("expenses", __name__)


def validate_expense(data):
    required_fields = ["title", "amount", "category", "date"]

    for field in required_fields:
        if field not in data:
            return f"Missing required field: {field}"

    if not isinstance(data["title"], str) or not data["title"].strip():
        return "Title must be a non-empty string."

    try:
        amount = float(data["amount"])
    except (TypeError, ValueError):
        return "Amount must be a number."

    if amount <= 0:
        return "Amount must be greater than zero."

    if not isinstance(data["category"], str) or not data["category"].strip():
        return "Category must be a non-empty string."

    try:
        datetime.strptime(data["date"], "%Y-%m-%d")
    except (TypeError, ValueError):
        return "Date must use YYYY-MM-DD format."

    return None


@expense_bp.route("/expenses", methods=["POST"])
def add_expense():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    error = validate_expense(data)

    if error:
        return jsonify({"error": error}), 400

    expense_id = create_expense(
        data["title"].strip(),
        float(data["amount"]),
        data["category"].strip(),
        data["date"],
    )

    expense = get_expense(expense_id)

    return jsonify(expense), 201


@expense_bp.route("/expenses", methods=["GET"])
def list_expenses():
    return jsonify(get_all_expenses()), 200


@expense_bp.route("/expenses/<int:expense_id>", methods=["GET"])
def fetch_expense(expense_id):
    expense = get_expense(expense_id)

    if expense is None:
        return jsonify({"error": "Expense not found."}), 404

    return jsonify(expense), 200


@expense_bp.route("/expenses/<int:expense_id>", methods=["PUT"])
def edit_expense(expense_id):
    if get_expense(expense_id) is None:
        return jsonify({"error": "Expense not found."}), 404

    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    error = validate_expense(data)

    if error:
        return jsonify({"error": error}), 400

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
        return jsonify({"error": "Expense not found."}), 404

    delete_expense(expense_id)

    return jsonify({"message": "Expense deleted successfully."}), 200