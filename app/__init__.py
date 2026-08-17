from flask import Flask

from .models import init_db
from .routes import expense_bp


def create_app(testing=False):
    app = Flask(__name__)

    app.config["TESTING"] = testing
    app.config["DATABASE"] = "expenses.db"

    init_db(app)
    app.register_blueprint(expense_bp)

    return app