from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import math


db = SQLAlchemy()


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    expense_date = db.Column(
        db.Date,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).date()
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "amount": round(self.amount, 2),
            "category": self.category,
            "description": self.description,
            "expense_date": self.expense_date.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///expenses.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.get("/")
    def health_check():
        return jsonify({
            "message": "expense tracker api",
            "status": "ok"
        })

    @app.post("/expenses")
    def create_expense():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "request body must be a JSON object"
            }), 400

        errors = validate_expense(data, required=True)

        if errors:
            return jsonify({"errors": errors}), 400

        expense_date = parse_date(data.get("expense_date"))

        if data.get("expense_date") and expense_date is None:
            return jsonify({
                "errors": {
                    "expense_date": "must use YYYY-MM-DD format"
                }
            }), 400

        expense = Expense(
            title=data["title"].strip(),
            amount=data["amount"],
            category=data["category"].strip(),
            description=data.get("description", "").strip(),
            expense_date=expense_date or datetime.now(
                timezone.utc
            ).date(),
        )

        db.session.add(expense)
        db.session.commit()

        return jsonify(expense.to_dict()), 201

    @app.get("/expenses")
    def list_expenses():
        query = Expense.query

        # Existing category filter
        category = request.args.get("category")

        if category:
            query = query.filter(
                db.func.lower(Expense.category)
                == category.strip().lower()
            )

        # Existing amount filters
        min_amount = request.args.get("min_amount", type=float)
        max_amount = request.args.get("max_amount", type=float)

        if min_amount is not None:
            query = query.filter(
                Expense.amount >= min_amount
            )

        if max_amount is not None:
            query = query.filter(
                Expense.amount <= max_amount
            )

        # ---------------------------------------------------------
        # DATE FILTERING
        # ---------------------------------------------------------

        start_date_value = request.args.get("start_date")
        end_date_value = request.args.get("end_date")

        start_date = None
        end_date = None

        if start_date_value is not None:
            start_date = parse_date(start_date_value)

            if start_date is None:
                return jsonify({
                    "error": "start_date must use YYYY-MM-DD format"
                }), 400

            query = query.filter(
                Expense.expense_date >= start_date
            )

        if end_date_value is not None:
            end_date = parse_date(end_date_value)

            if end_date is None:
                return jsonify({
                    "error": "end_date must use YYYY-MM-DD format"
                }), 400

            query = query.filter(
                Expense.expense_date <= end_date
            )

        # start_date cannot be after end_date
        if (
            start_date is not None
            and end_date is not None
            and start_date > end_date
        ):
            return jsonify({
                "error": "start_date cannot be later than end_date"
            }), 400

        # ---------------------------------------------------------
        # ORDERING
        # ---------------------------------------------------------

        query = query.order_by(
            Expense.expense_date.desc(),
            Expense.id.desc()
        )

        # ---------------------------------------------------------
        # PAGINATION
        # ---------------------------------------------------------

        page_value = request.args.get("page")
        per_page_value = request.args.get("per_page")

        # Pagination is requested if either parameter is present.
        pagination_requested = (
            page_value is not None
            or per_page_value is not None
        )

        if pagination_requested:

            # Default values
            if page_value is None:
                page = 1
            else:
                try:
                    page = int(page_value)
                except (TypeError, ValueError):
                    return jsonify({
                        "error": "page must be a positive integer"
                    }), 400

            if per_page_value is None:
                per_page = 10
            else:
                try:
                    per_page = int(per_page_value)
                except (TypeError, ValueError):
                    return jsonify({
                        "error": "per_page must be a positive integer"
                    }), 400

            # Positive integer validation
            if page <= 0:
                return jsonify({
                    "error": "page must be a positive integer"
                }), 400

            if per_page <= 0:
                return jsonify({
                    "error": "per_page must be a positive integer"
                }), 400

            # Get total AFTER applying all filters
            total = query.count()

            # Calculate total pages
            pages = math.ceil(total / per_page)

            # Calculate offset
            offset = (page - 1) * per_page

            # Apply pagination AFTER filtering
            expenses = query.offset(offset).limit(per_page).all()

            return jsonify({
                "expenses": [
                    expense.to_dict()
                    for expense in expenses
                ],
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": pages
            })

        # ---------------------------------------------------------
        # ORIGINAL / NON-PAGINATED RESPONSE
        # ---------------------------------------------------------

        expenses = query.all()

        return jsonify([
            expense.to_dict()
            for expense in expenses
        ])

    @app.get("/expenses/<int:expense_id>")
    def get_expense(expense_id):
        expense = db.session.get(Expense, expense_id)

        if expense is None:
            return jsonify({
                "error": "expense not found"
            }), 404

        return jsonify(expense.to_dict())

    @app.put("/expenses/<int:expense_id>")
    def update_expense(expense_id):
        expense = db.session.get(Expense, expense_id)

        if expense is None:
            return jsonify({
                "error": "expense not found"
            }), 404

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "request body must be a JSON object"
            }), 400

        errors = validate_expense(data, required=False)

        if errors:
            return jsonify({"errors": errors}), 400

        if "title" in data:
            expense.title = data["title"].strip()

        if "amount" in data:
            expense.amount = data["amount"]

        if "category" in data:
            expense.category = data["category"].strip()

        if "description" in data:
            expense.description = data["description"].strip()

        if "expense_date" in data:
            parsed_date = parse_date(data["expense_date"])

            if parsed_date is None:
                return jsonify({
                    "errors": {
                        "expense_date":
                            "must use YYYY-MM-DD format"
                    }
                }), 400

            expense.expense_date = parsed_date

        db.session.commit()

        return jsonify(expense.to_dict())

    @app.delete("/expenses/<int:expense_id>")
    def delete_expense(expense_id):
        expense = db.session.get(Expense, expense_id)

        if expense is None:
            return jsonify({
                "error": "expense not found"
            }), 404

        db.session.delete(expense)
        db.session.commit()

        return jsonify({
            "message": "expense deleted"
        })

    @app.get("/expenses/summary")
    def expense_summary():
        expenses = Expense.query.all()

        total = sum(
            expense.amount
            for expense in expenses
        )

        by_category = {}

        for expense in expenses:
            by_category[expense.category] = (
                by_category.get(expense.category, 0)
                + expense.amount
            )

        return jsonify({
            "total_expenses": round(total, 2),
            "expense_count": len(expenses),
            "by_category": {
                category: round(amount, 2)
                for category, amount
                in sorted(by_category.items())
            }
        })

    return app


def parse_date(value):
    if value is None or value == "":
        return None

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d"
        ).date()
    except (TypeError, ValueError):
        return None


def validate_expense(data, required=True):
    errors = {}

    if required:
        for field in ["title", "amount", "category"]:
            if field not in data:
                errors[field] = "field is required"

    if "title" in data:
        if (
            not isinstance(data["title"], str)
            or not data["title"].strip()
        ):
            errors["title"] = "must be a non-empty string"

    if "category" in data:
        if (
            not isinstance(data["category"], str)
            or not data["category"].strip()
        ):
            errors["category"] = "must be a non-empty string"

    if "description" in data:
        if not isinstance(data["description"], str):
            errors["description"] = "must be a string"

    if "amount" in data:
        amount = data["amount"]

        if isinstance(amount, bool):
            errors["amount"] = "must be a number"

        elif not isinstance(amount, (int, float)):
            errors["amount"] = "must be a number"

        elif amount <= 0:
            errors["amount"] = "must be greater than zero"

    if "expense_date" in data:
        if (
            not isinstance(data["expense_date"], str)
            or parse_date(data["expense_date"]) is None
        ):
            errors["expense_date"] = (
                "must use YYYY-MM-DD format"
            )

    return errors


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )