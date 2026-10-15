from task_routes import task_bp
import os
from auth import auth_bp
from flask import Flask, jsonify, render_template
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)

app.config.update(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False  # Local development only
)

if not app.config["SECRET_KEY"]:
    raise RuntimeError("Set FLASK_SECRET_KEY before starting Flask")

app.register_blueprint(auth_bp)
app.register_blueprint(task_bp)

DB_PATH = Path(
    os.environ.get(
        "QUICKVOLUNTEER_DB_PATH",
        str(BASE_DIR / "database" / "quickvolunteer.db")
    )
)

def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def fetch_open_tasks():
    connection = get_db_connection()

    try:
        rows = connection.execute("""
            SELECT
                t.task_id,
                t.title,
                t.description,
                t.delivery_mode,
                t.estimated_minutes,
                t.location_text,
                t.status,
                c.category_name
            FROM tasks AS t
            JOIN task_categories AS c
                ON t.category_id = c.category_id
            WHERE t.status = 'open'
            ORDER BY t.task_id
        """).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


@app.route("/")
def home():
    return "Welcome to QuickVolunteer!"


@app.route("/tasks")
def tasks_page():
    tasks = fetch_open_tasks()
    return render_template("tasks.html", tasks=tasks)


@app.route("/api/tasks")
def tasks_api():
    return jsonify(fetch_open_tasks())


if __name__ == "__main__":
    app.run(debug=True)
