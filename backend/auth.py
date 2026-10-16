
from functools import wraps

import mysql.connector
from flask import Blueprint, jsonify, request, session
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from db import get_db_connection


auth_bp = Blueprint("auth", __name__)

# Public registration roles only.
# Admin accounts must be created internally.
ALLOWED_ACCOUNT_TYPES = {
    "volunteer",
    "help_seeker",
    "both"
}


# ==========================================
# LOGIN REQUIRED
# ==========================================

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")

        if user_id is None:
            return jsonify({
                "error": "Login required"
            }), 401

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT user_id, account_status
                FROM users
                WHERE user_id = %s
            """, (user_id,))

            user = cursor.fetchone()

            if user is None or user["account_status"] != "active":
                session.clear()
                return jsonify({
                    "error": "Session is no longer valid"
                }), 401

        finally:
            cursor.close()
            connection.close()

        return function(*args, **kwargs)

    return wrapper


# ==========================================
# REGISTER
# ==========================================

@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "JSON body required"
        }), 400

    first_name = str(data.get("first_name") or "").strip()
    last_name = str(data.get("last_name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")

    # Accept the new field, with temporary compatibility
    # for clients still sending "role".
    account_type = data.get("account_type", data.get("role"))

    if not all([
        first_name,
        last_name,
        email,
        password,
        account_type
    ]):
        return jsonify({
            "error": "All fields are required"
        }), 400

    if not isinstance(password, str) or len(password) < 12:
        return jsonify({
            "error": "Password must have at least 12 characters"
        }), 400

    if account_type not in ALLOWED_ACCOUNT_TYPES:
        return jsonify({
            "error": "Invalid registration account type"
        }), 400

    if len(first_name) > 50 or len(last_name) > 50:
        return jsonify({
            "error": "Name is too long"
        }), 400

    if len(email) > 254 or "@" not in email:
        return jsonify({
            "error": "Invalid email address"
        }), 400

    password_hash = generate_password_hash(password)

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (
                first_name,
                last_name,
                email,
                password_hash,
                account_type,
                account_status
            )
            VALUES (%s, %s, %s, %s, %s, 'active')
        """, (
            first_name,
            last_name,
            email,
            password_hash,
            account_type
        ))

        user_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Account created successfully",
            "user_id": user_id,
            "account_type": account_type
        }), 201

    except mysql.connector.IntegrityError:
        connection.rollback()
        return jsonify({
            "error": "Invalid account details or email already registered"
        }), 409

    finally:
        cursor.close()
        connection.close()


# ==========================================
# LOGIN
# ==========================================

@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "JSON body required"
        }), 400

    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not isinstance(password, str):
        return jsonify({
            "error": "Email and password required"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                user_id,
                first_name,
                email,
                password_hash,
                account_type,
                account_status
            FROM users
            WHERE email = %s
        """, (email,))

        user = cursor.fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({
                "error": "Invalid credentials"
            }), 401

        if user["account_status"] != "active":
            return jsonify({
                "error": "Account is not active"
            }), 403

        session.clear()
        session["user_id"] = user["user_id"]

        return jsonify({
            "message": "Login successful",
            "user": {
                "user_id": user["user_id"],
                "first_name": user["first_name"],
                "email": user["email"],
                "account_type": user["account_type"]
            }
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# CURRENT USER
# ==========================================

@auth_bp.route("/api/me", methods=["GET"])
@login_required
def current_user():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                user_id,
                first_name,
                last_name,
                email,
                account_type
            FROM users
            WHERE user_id = %s
              AND account_status = 'active'
        """, (session["user_id"],))

        user = cursor.fetchone()

        if user is None:
            session.clear()
            return jsonify({
                "error": "Session no longer valid"
            }), 401

        return jsonify({
            "user": user
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# LOGOUT
# ==========================================

@auth_bp.route("/api/logout", methods=["POST"])
@login_required
def logout():
    session.clear()

    return jsonify({
        "message": "Logged out successfully"
    }), 200


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

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            try:
                cursor.execute("""
                    SELECT account_type, account_status
                    FROM users
                    WHERE user_id = %s
                """, (user_id,))

                user = cursor.fetchone()

                if user is None or user["account_status"] != "active":
                    session.clear()
                    return jsonify({
                        "error": "Session is no longer valid"
                    }), 401

                account_type = user["account_type"]

                # A "both" user has volunteer and
                # help-seeker permissions.
                user_roles = {account_type}

                if account_type == "both":
                    user_roles = {
                        "volunteer",
                        "help_seeker",
                        "both"
                    }

                if not user_roles.intersection(allowed_roles):
                    return jsonify({
                        "error": "Permission denied"
                    }), 403

            finally:
                cursor.close()
                connection.close()

            return function(*args, **kwargs)

        return wrapper

    return decorator
