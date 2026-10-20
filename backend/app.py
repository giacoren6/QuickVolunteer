
import os
from pathlib import Path

from flask import Flask, jsonify, render_template
from flask_wtf.csrf import CSRFProtect, generate_csrf

from db import get_db_connection
from auth import auth_bp
from task_routes import task_bp
from admin_routes import admin_bp


# ==========================================
# FLASK APPLICATION CONFIGURATION
# ==========================================

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
    raise RuntimeError(
        "Set FLASK_SECRET_KEY before starting Flask"
    )


# ==========================================
# REGISTER BLUEPRINTS AND CSRF PROTECTION
# ==========================================

app.register_blueprint(auth_bp)
app.register_blueprint(task_bp)
app.register_blueprint(admin_bp)

csrf = CSRFProtect(app)


# ==========================================
# MYSQL TASK QUERY
# ==========================================

def fetch_open_tasks():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
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
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():
    return "Welcome to QuickVolunteer!"


# ==========================================
# TASKS PAGE
# ==========================================

@app.route("/tasks")
def tasks_page():
    tasks = fetch_open_tasks()
    return render_template("tasks.html", tasks=tasks)


# ==========================================
# REST API - GET TASKS
# ==========================================

@app.route("/api/tasks", methods=["GET"])
def tasks_api():
    return jsonify(fetch_open_tasks())



# ==========================================
# REST API - GET TASK CATEGORIES
# ==========================================

@app.route("/api/categories", methods=["GET"])
def categories_api():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                category_id,
                category_name
            FROM task_categories
            ORDER BY category_name
        """)

        categories = cursor.fetchall()
        return jsonify(categories), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# CSRF TOKEN ENDPOINT
# ==========================================

@app.route("/api/csrf-token", methods=["GET"])
def csrf_token():
    return jsonify({
        "csrf_token": generate_csrf()
    })


# ==========================================
# RUN FLASK
# ==========================================

if __name__ == "__main__":
    app.run(debug=False)
