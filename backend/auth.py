
from functools import wraps
import sqlite3
from pathlib import Path

from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint("auth", __name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "quickvolunteer.db"

ALLOWED_ROLES = {"volunteer", "help_seeker", "organisation"}


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401

        return function(*args, **kwargs)

    return wrapper


@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    first_name = str(data.get("first_name") or "").strip()
    last_name = str(data.get("last_name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")
    role = data.get("role")

    if not all([first_name, last_name, email, password, role]):
        return jsonify({"error": "All fields are required"}), 400

    if not isinstance(password, str) or len(password) < 12:
        return jsonify({"error": "Password must have at least 12 characters"}), 400

    if role not in ALLOWED_ROLES:
        return jsonify({"error": "Invalid registration role"}), 400

    if len(first_name) > 50 or len(last_name) > 50:
        return jsonify({"error": "Name is too long"}), 400

    if len(email) > 254 or "@" not in email:
        return jsonify({"error": "Invalid email address"}), 400

    password_hash = generate_password_hash(password)

    connection = get_db()

    try:
        with connection:
            role_row = connection.execute(
                "SELECT role_id FROM roles WHERE role_name = ?",
                (role,)
            ).fetchone()

            if role_row is None:
                return jsonify({"error": "Role not configured"}), 500

            cursor = connection.execute("""
                INSERT INTO users (
                    first_name,
                    last_name,
                    email,
                    password_hash,
                    account_status
                )
                VALUES (?, ?, ?, ?, 'active')
            """, (
                first_name,
                last_name,
                email,
                password_hash
            ))

            user_id = cursor.lastrowid

            connection.execute("""
                INSERT INTO user_roles (user_id, role_id)
                VALUES (?, ?)
            """, (user_id, role_row["role_id"]))

        return jsonify({
            "message": "Account created successfully",
            "user_id": user_id
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Invalid account details or email already registered"}), 409

    finally:
        connection.close()


@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not isinstance(password, str):
        return jsonify({"error": "Email and password required"}), 400

    connection = get_db()

    try:
        user = connection.execute("""
            SELECT user_id, first_name, email,
                   password_hash, account_status
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({"error": "Invalid credentials"}), 401

        if user["account_status"] != "active":
            return jsonify({"error": "Account is not active"}), 403

        session.clear()
        session["user_id"] = user["user_id"]

        return jsonify({
            "message": "Login successful",
            "user": {
                "user_id": user["user_id"],
                "first_name": user["first_name"],
                "email": user["email"]
            }
        }), 200

    finally:
        connection.close()


@auth_bp.route("/api/me", methods=["GET"])
@login_required
def current_user():
    connection = get_db()

    try:
        user = connection.execute("""
            SELECT user_id, first_name, last_name, email
            FROM users
            WHERE user_id = ?
              AND account_status = 'active'
        """, (session["user_id"],)).fetchone()

        if user is None:
            session.clear()
            return jsonify({"error": "Session no longer valid"}), 401

        return jsonify({"user": dict(user)}), 200

    finally:
        connection.close()


@auth_bp.route("/api/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200



# ==========================================
# ROLE-BASED AUTHORISATION
# ==========================================

def roles_required(*allowed_roles):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):

            user_id = session.get("user_id")

            if user_id is None:
                return jsonify({
                    "error": "Login required"
                }), 401

            connection = get_db()

            try:
                rows = connection.execute("""
                    SELECT r.role_name
                    FROM user_roles AS ur
                    JOIN roles AS r
                        ON ur.role_id = r.role_id
                    JOIN users AS u
                        ON ur.user_id = u.user_id
                    WHERE u.user_id = ?
                      AND u.account_status = 'active'
                """, (user_id,)).fetchall()

                user_roles = {
                    row["role_name"] for row in rows
                }

                if not user_roles:
                    return jsonify({
                        "error": "Account inactive or no roles assigned"
                    }), 403

                if not user_roles.intersection(allowed_roles):
                    return jsonify({
                        "error": "Permission denied"
                    }), 403

                return function(*args, **kwargs)

            finally:
                connection.close()

        return wrapper

    return decorator
