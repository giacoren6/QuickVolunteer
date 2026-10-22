import mysql.connector
from flask import Blueprint, jsonify, request, session

from auth import roles_required
from db import get_db_connection


verification_bp = Blueprint("verification", __name__)


# ==========================================
# USER VERIFICATION REQUESTS
# ==========================================

# Users can request account or DBS verification.
# Only administrators can approve or reject requests.


@verification_bp.route("/api/verifications", methods=["POST"])
@roles_required("volunteer", "help_seeker", "both")
def request_verification():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    verification_type = data.get("verification_type")

    if verification_type not in ("account", "dbs"):
        return jsonify({
            "error": "Verification type must be account or dbs"
        }), 400

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute("""
            SELECT user_id
            FROM users
            WHERE user_id = %s
            FOR UPDATE
        """, (user_id,))
        cursor.fetchone()

        cursor.execute("""
            SELECT verification_id, status
            FROM user_verifications
            WHERE user_id = %s
              AND verification_type = %s
              AND status IN ('pending', 'approved')
            ORDER BY verification_id DESC
            LIMIT 1
        """, (user_id, verification_type))

        existing = cursor.fetchone()

        if existing:
            connection.rollback()
            return jsonify({
                "error": "Verification already pending or approved",
                "status": existing["status"]
            }), 409

        cursor.execute("""
            INSERT INTO user_verifications (
                user_id,
                verification_type,
                status
            )
            VALUES (%s, %s, 'pending')
        """, (user_id, verification_type))

        verification_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Verification request submitted",
            "verification_id": verification_id,
            "status": "pending"
        }), 201

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


@verification_bp.route("/api/verifications/me", methods=["GET"])
@roles_required("volunteer", "help_seeker", "both")
def my_verifications():
    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                verification_id,
                verification_type,
                status,
                requested_at,
                reviewed_at
            FROM user_verifications
            WHERE user_id = %s
            ORDER BY requested_at DESC, verification_id DESC
        """, (user_id,))

        verifications = cursor.fetchall()

        for verification in verifications:
            for field in ("requested_at", "reviewed_at"):
                if verification[field] is not None:
                    verification[field] = (
                        verification[field].isoformat()
                    )

        return jsonify({
            "verifications": verifications,
            "total": len(verifications)
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# ADMINISTRATOR - VERIFICATION DECISIONS
# ==========================================

@verification_bp.route(
    "/api/admin/verifications/<int:verification_id>/decision",
    methods=["PATCH"]
)
@roles_required("admin")
def admin_decide_verification(verification_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    status = data.get("status")

    if status not in ("approved", "rejected"):
        return jsonify({
            "error": "Status must be approved or rejected"
        }), 400

    admin_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute("""
            SELECT verification_id, status
            FROM user_verifications
            WHERE verification_id = %s
            FOR UPDATE
        """, (verification_id,))

        verification = cursor.fetchone()

        if verification is None:
            connection.rollback()
            return jsonify({
                "error": "Verification request not found"
            }), 404

        if verification["status"] != "pending":
            connection.rollback()
            return jsonify({
                "error": "Only pending requests can be reviewed"
            }), 409

        cursor.execute("""
            UPDATE user_verifications
            SET status = %s,
                reviewed_by = %s,
                reviewed_at = NOW()
            WHERE verification_id = %s
        """, (status, admin_id, verification_id))

        connection.commit()

        return jsonify({
            "message": "Verification decision saved",
            "verification_id": verification_id,
            "status": status
        }), 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ==========================================
# ADMINISTRATOR - LIST VERIFICATIONS
# ==========================================

@verification_bp.route("/api/admin/verifications", methods=["GET"])
@roles_required("admin")
def admin_list_verifications():
    status = request.args.get("status")

    if status is not None and status not in (
        "pending", "approved", "rejected"
    ):
        return jsonify({"error": "Invalid verification status"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                v.verification_id,
                v.user_id,
                v.verification_type,
                v.status,
                v.requested_at,
                v.reviewed_by,
                v.reviewed_at
            FROM user_verifications AS v
        """

        params = ()

        if status is not None:
            query += " WHERE v.status = %s"
            params = (status,)

        query += " ORDER BY v.requested_at DESC, v.verification_id DESC"

        cursor.execute(query, params)
        verifications = cursor.fetchall()

        for verification in verifications:
            for field in ("requested_at", "reviewed_at"):
                if verification[field] is not None:
                    verification[field] = (
                        verification[field].isoformat()
                    )

        return jsonify({
            "verifications": verifications,
            "total": len(verifications)
        }), 200

    finally:
        cursor.close()
        connection.close()
