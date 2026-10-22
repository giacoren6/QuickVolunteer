from flask import Blueprint, jsonify, session

from auth import login_required
from db import get_db_connection


notification_bp = Blueprint("notifications", __name__)


@notification_bp.route("/api/notifications", methods=["GET"])
@login_required
def list_notifications():
    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                notification_id,
                task_application_id,
                title,
                content,
                read_at,
                created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC, notification_id DESC
        """, (user_id,))

        notifications = cursor.fetchall()

        for notification in notifications:
            notification["created_at"] = (
                notification["created_at"].isoformat()
            )

            if notification["read_at"] is not None:
                notification["read_at"] = (
                    notification["read_at"].isoformat()
                )

        return jsonify({
            "notifications": notifications
        }), 200

    finally:
        cursor.close()
        connection.close()


@notification_bp.route(
    "/api/notifications/<int:notification_id>/read",
    methods=["PATCH"]
)
@login_required
def mark_notification_read(notification_id):
    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE notifications
            SET read_at = COALESCE(read_at, CURRENT_TIMESTAMP)
            WHERE notification_id = %s
              AND user_id = %s
        """, (notification_id, user_id))

        if cursor.rowcount == 0:
            connection.rollback()
            return jsonify({
                "error": "Notification not found"
            }), 404

        connection.commit()

        return jsonify({
            "message": "Notification marked as read",
            "notification_id": notification_id
        }), 200

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()
