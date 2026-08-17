import sqlite3
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(exception=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        db = get_db()

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                date TEXT NOT NULL
            )
            """
        )

        db.commit()

    app.teardown_appcontext(close_db)


def create_expense(title, amount, category, date):
    db = get_db()

    cursor = db.execute(
        """
        INSERT INTO expenses (title, amount, category, date)
        VALUES (?, ?, ?, ?)
        """,
        (title, amount, category, date),
    )

    db.commit()

    return cursor.lastrowid


def get_all_expenses():
    db = get_db()

    rows = db.execute(
        """
        SELECT id, title, amount, category, date
        FROM expenses
        ORDER BY id
        """
    ).fetchall()

    return [dict(row) for row in rows]


def get_expense(expense_id):
    db = get_db()

    row = db.execute(
        """
        SELECT id, title, amount, category, date
        FROM expenses
        WHERE id = ?
        """,
        (expense_id,),
    ).fetchone()

    return dict(row) if row else None


def update_expense(expense_id, title, amount, category, date):
    db = get_db()

    cursor = db.execute(
        """
        UPDATE expenses
        SET title = ?, amount = ?, category = ?, date = ?
        WHERE id = ?
        """,
        (title, amount, category, date, expense_id),
    )

    db.commit()

    return cursor.rowcount


def delete_expense(expense_id):
    db = get_db()

    cursor = db.execute(
        """
        DELETE FROM expenses
        WHERE id = ?
        """,
        (expense_id,),
    )

    db.commit()

    return cursor.rowcount