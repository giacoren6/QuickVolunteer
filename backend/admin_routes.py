
import mysql.connector
from flask import Blueprint, jsonify, request, session

from auth import roles_required
from db import get_db_connection


admin_bp = Blueprint("administration", __name__)


# ==========================================
# SUBMIT A REPORT
# ==========================================

@admin_bp.route("/api/reports", methods=["POST"])
@roles_required("volunteer", "help_seeker", "both")
def submit_report():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    reported_user_id = data.get("reported_user_id")
    task_id = data.get("task_id")
    reason = data.get("reason")

    if (reported_user_id is None) == (task_id is None):
        return jsonify({
            "error": "Report exactly one user or one task"
        }), 400

    target_id = (
        reported_user_id
        if reported_user_id is not None
        else task_id
    )

    if type(target_id) is not int or target_id <= 0:
        return jsonify({"error": "Invalid target ID"}), 400

    if not isinstance(reason, str) or not reason.strip():
        return jsonify({"error": "Reason is required"}), 400

    if len(reason.strip()) > 5000:
        return jsonify({"error": "Reason is too long"}), 400

    if reported_user_id == session["user_id"]:
        return jsonify({
            "error": "You cannot report yourself"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO reports (
                reporter_id,
                reported_user_id,
                task_id,
                reason
            )
            VALUES (%s, %s, %s, %s)
        """, (
            session["user_id"],
            reported_user_id,
            task_id,
            reason.strip()
        ))

        report_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Report submitted successfully",
            "report_id": report_id
        }), 201

    except mysql.connector.IntegrityError:
        connection.rollback()
        return jsonify({
            "error": "Reported user or task does not exist"
        }), 404

    finally:
        cursor.close()
        connection.close()



# ==========================================
# ADMINISTRATOR - VIEW REPORTS
# ==========================================

@admin_bp.route("/api/admin/reports", methods=["GET"])
@roles_required("admin")
def admin_get_reports():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                report_id,
                reporter_id,
                reported_user_id,
                task_id,
                reviewed_by,
                reason,
                status,
                created_at,
                reviewed_at
            FROM reports
            ORDER BY created_at DESC, report_id DESC
        """)

        reports = cursor.fetchall()

        for report in reports:
            for field in ("created_at", "reviewed_at"):
                if report[field] is not None:
                    report[field] = report[field].isoformat()

        return jsonify({
            "reports": reports,
            "total": len(reports)
        }), 200

    finally:
        cursor.close()
        connection.close()



    
@admin_bp.route("/api/admin/reports/<int:report_id>/status", methods=["PATCH"])
@roles_required("admin")
def admin_update_report_status(report_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    status = data.get("status")

    if status not in ("open", "reviewing", "closed"):
        return jsonify({"error": "Invalid report status"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE reports
            SET status = %s,
                reviewed_by = %s,
                reviewed_at = CASE
                    WHEN %s = 'open' THEN NULL
                    ELSE NOW()
                END
            WHERE report_id = %s
        """, (status, session["user_id"], status, report_id))

        
    

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT report_id FROM reports WHERE report_id = %s",
                (report_id,)
            )

            if cursor.fetchone() is None:
                connection.rollback()
                return jsonify({"error": "Report not found"}), 404

        connection.commit()

        return jsonify({
            "message": "Report status updated successfully",
            "report_id": report_id,
            "status": status
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# ADMINISTRATOR - REVIEW MODERATION
# ==========================================


@admin_bp.route("/api/admin/reviews/<int:review_id>/moderation", methods=["PATCH"])
@roles_required("admin")
def admin_moderate_review(review_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    status = data.get("status")
    reason = data.get("reason")

    if status not in ("visible", "hidden"):
        return jsonify({"error": "Invalid moderation status"}), 400

    if not isinstance(reason, str) or not reason.strip():
        return jsonify({"error": "Moderation reason is required"}), 400

    reason = reason.strip()

    if len(reason) > 5000:
        return jsonify({"error": "Moderation reason is too long"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT review_id
            FROM reviews
            WHERE review_id = %s
        """, (review_id,))

        if cursor.fetchone() is None:
            return jsonify({"error": "Review not found"}), 404

        cursor.execute("""
            UPDATE reviews
            SET moderation_status = %s,
                moderated_by = %s,
                moderated_at = NOW(),
                moderation_reason = %s
            WHERE review_id = %s
        """, (
            status,
            session["user_id"],
            reason,
            review_id
        ))

        connection.commit()

        return jsonify({
            "message": "Review moderation updated successfully",
            "review_id": review_id,
            "moderation_status": status
        }), 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

