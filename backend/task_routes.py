
from datetime import datetime

import mysql.connector
from flask import Blueprint, jsonify, request, session

from auth import roles_required
from db import get_db_connection


task_bp = Blueprint("task_management", __name__)


# ==========================================
# PERMISSIONS
# ==========================================

@task_bp.route("/api/tasks/permissions", methods=["GET"])
@roles_required("help_seeker")
def task_permissions():
    return jsonify({
        "message": "You have permission to create tasks",
        "user_id": session["user_id"]
    }), 200


@task_bp.route("/api/volunteer/permissions", methods=["GET"])
@roles_required("volunteer")
def volunteer_permissions():
    return jsonify({
        "message": "You have permission to apply for tasks",
        "user_id": session["user_id"]
    }), 200


# ==========================================
# CREATE A TASK
# ==========================================

@task_bp.route("/api/tasks", methods=["POST"])
@roles_required("help_seeker")
def create_task():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    title = data.get("title")
    description = data.get("description")
    category_id = data.get("category_id")
    delivery_mode = data.get("delivery_mode")
    estimated_minutes = data.get("estimated_minutes")
    deadline_at = data.get("deadline_at")
    location_text = data.get("location_text")

    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "Title is required"}), 400

    if len(title.strip()) > 160:
        return jsonify({"error": "Title is too long"}), 400

    if not isinstance(description, str) or not description.strip():
        return jsonify({"error": "Description is required"}), 400

    if delivery_mode not in ("remote", "in_person"):
        return jsonify({"error": "Invalid delivery mode"}), 400

    if delivery_mode == "in_person":
        if not isinstance(location_text, str) or not location_text.strip():
            return jsonify({
                "error": "Location is required for in-person tasks"
            }), 400

    if isinstance(location_text, str) and len(location_text.strip()) > 160:
        return jsonify({"error": "Location is too long"}), 400

    if type(estimated_minutes) is not int or not 15 <= estimated_minutes <= 60:
        return jsonify({
            "error": "Duration must be between 15 and 60 minutes"
        }), 400

    if type(category_id) is not int or category_id <= 0:
        return jsonify({"error": "Valid category ID required"}), 400

    deadline = None

    if deadline_at is not None:
        try:
            deadline = datetime.fromisoformat(deadline_at)

            if deadline.tzinfo is not None:
                raise ValueError("Timezone not supported")

            if deadline <= datetime.now():
                return jsonify({
                    "error": "Deadline must be in the future"
                }), 400

        except (ValueError, TypeError):
            return jsonify({"error": "Invalid deadline format"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT category_id
            FROM task_categories
            WHERE category_id = %s
        """, (category_id,))

        if cursor.fetchone() is None:
            return jsonify({"error": "Category not found"}), 400

        cursor.execute("""
            INSERT INTO tasks (
                creator_id,
                category_id,
                title,
                description,
                location_text,
                delivery_mode,
                estimated_minutes,
                deadline_at,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'open')
        """, (
            session["user_id"],
            category_id,
            title.strip(),
            description.strip(),
            location_text.strip() if isinstance(location_text, str) else None,
            delivery_mode,
            estimated_minutes,
            deadline,
        ))

        task_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Task created successfully",
            "task_id": task_id
        }), 201

    except mysql.connector.Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ==========================================
# APPLY FOR A TASK
# ==========================================

@task_bp.route("/api/tasks/<int:task_id>/apply", methods=["POST"])
@roles_required("volunteer")
def apply_for_task(task_id):
    volunteer_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute("""
            SELECT task_id, creator_id, status, deadline_at
            FROM tasks
            WHERE task_id = %s
            FOR UPDATE
        """, (task_id,))

        task = cursor.fetchone()

        if task is None:
            return jsonify({"error": "Task not found"}), 404

        if task["status"] != "open":
            return jsonify({"error": "Task is not open"}), 409

        if task["deadline_at"] is not None:
            if task["deadline_at"] <= datetime.now():
                return jsonify({"error": "Task deadline has passed"}), 409

        if task["creator_id"] == volunteer_id:
            return jsonify({
                "error": "Cannot apply for your own task"
            }), 403

        cursor.execute("""
            SELECT application_id
            FROM task_applications
            WHERE task_id = %s AND volunteer_id = %s
        """, (task_id, volunteer_id))

        if cursor.fetchone() is not None:
            return jsonify({
                "error": "Already applied for this task"
            }), 409

        cursor.execute("""
            INSERT INTO task_applications (
                task_id, volunteer_id, status
            )
            VALUES (%s, %s, 'pending')
        """, (task_id, volunteer_id))

        application_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Application submitted successfully",
            "application_id": application_id,
            "task_id": task_id,
            "status": "pending"
        }), 201

    except mysql.connector.IntegrityError:
        connection.rollback()
        return jsonify({
            "error": "Already applied or invalid application"
        }), 409

    except mysql.connector.Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ==========================================
# ACCEPT OR REJECT AN APPLICATION
# ==========================================

@task_bp.route(
    "/api/applications/<int:application_id>/decision",
    methods=["PATCH"]
)
@roles_required("help_seeker")
def decide_application(application_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    decision = data.get("decision")

    if decision not in ("accepted", "rejected"):
        return jsonify({
            "error": "Decision must be accepted or rejected"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        # Find the parent task first, then lock it.
        cursor.execute("""
            SELECT task_id
            FROM task_applications
            WHERE application_id = %s
        """, (application_id,))

        application_ref = cursor.fetchone()

        if application_ref is None:
            return jsonify({"error": "Application not found"}), 404

        task_id = application_ref["task_id"]

        cursor.execute("""
            SELECT task_id, creator_id, status
            FROM tasks
            WHERE task_id = %s
            FOR UPDATE
        """, (task_id,))

        task = cursor.fetchone()

        if task is None:
            return jsonify({"error": "Task not found"}), 404

        if task["creator_id"] != session["user_id"]:
            return jsonify({"error": "Permission denied"}), 403

        cursor.execute("""
            SELECT application_id, status
            FROM task_applications
            WHERE application_id = %s AND task_id = %s
            FOR UPDATE
        """, (application_id, task_id))

        application = cursor.fetchone()

        if application is None:
            return jsonify({"error": "Application not found"}), 404

        if application["status"] != "pending":
            return jsonify({
                "error": "Application has already been reviewed"
            }), 409

        if decision == "accepted" and task["status"] != "open":
            return jsonify({
                "error": "Task is no longer open"
            }), 409

        if decision == "rejected" and task["status"] not in ("open", "filled"):
            return jsonify({
                "error": "Task is no longer accepting decisions"
            }), 409

        if decision == "accepted":
            cursor.execute("""
                UPDATE task_applications
                SET status = 'accepted',
                    accepted_at = CURRENT_TIMESTAMP
                WHERE application_id = %s
            """, (application_id,))

            # One accepted volunteer per task in V1.
            cursor.execute("""
                UPDATE tasks
                SET status = 'filled'
                WHERE task_id = %s
            """, (task_id,))

            # Reject remaining pending applications.
            cursor.execute("""
                UPDATE task_applications
                SET status = 'rejected'
                WHERE task_id = %s
                  AND application_id <> %s
                  AND status = 'pending'
            """, (task_id, application_id))

        else:
            cursor.execute("""
                UPDATE task_applications
                SET status = 'rejected'
                WHERE application_id = %s
            """, (application_id,))

        connection.commit()

        return jsonify({
            "message": "Application reviewed successfully",
            "application_id": application_id,
            "status": decision
        }), 200

    except mysql.connector.Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ==========================================
# DUAL TASK COMPLETION
# ==========================================

@task_bp.route("/api/tasks/<int:task_id>/complete", methods=["PATCH"])
@roles_required("help_seeker", "volunteer")
def complete_task(task_id):
    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute("""
            SELECT task_id, creator_id, status
            FROM tasks
            WHERE task_id = %s
            FOR UPDATE
        """, (task_id,))

        task = cursor.fetchone()

        if task is None:
            return jsonify({"error": "Task not found"}), 404

        if task["status"] == "completed":
            return jsonify({
                "error": "Task already completed"
            }), 409

        if task["status"] != "filled":
            return jsonify({
                "error": "Task must be filled before completion"
            }), 409

        cursor.execute("""
            SELECT application_id, volunteer_id,
                   volunteer_completed_at,
                   help_seeker_completed_at
            FROM task_applications
            WHERE task_id = %s
              AND status = 'accepted'
            FOR UPDATE
        """, (task_id,))

        application = cursor.fetchone()

        if application is None:
            return jsonify({
                "error": "No accepted volunteer found"
            }), 409

        if user_id == task["creator_id"]:
            field = "help_seeker_completed_at"
        elif user_id == application["volunteer_id"]:
            field = "volunteer_completed_at"
        else:
            return jsonify({"error": "Permission denied"}), 403

        if application[field] is not None:
            return jsonify({
                "error": "You already confirmed completion"
            }), 409

        # The column name comes from a fixed internal choice,
        # never directly from user input.
        cursor.execute(f"""
            UPDATE task_applications
            SET {field} = CURRENT_TIMESTAMP
            WHERE application_id = %s
        """, (application["application_id"],))

        cursor.execute("""
            SELECT volunteer_completed_at,
                   help_seeker_completed_at
            FROM task_applications
            WHERE application_id = %s
        """, (application["application_id"],))

        confirmations = cursor.fetchone()

        both_confirmed = (
            confirmations["volunteer_completed_at"] is not None
            and confirmations["help_seeker_completed_at"] is not None
        )

        if both_confirmed:
            cursor.execute("""
                UPDATE task_applications
                SET status = 'completed'
                WHERE application_id = %s
            """, (application["application_id"],))

            cursor.execute("""
                UPDATE tasks
                SET status = 'completed'
                WHERE task_id = %s
            """, (task_id,))

        connection.commit()

        return jsonify({
            "message": (
                "Task completed successfully"
                if both_confirmed
                else "Completion confirmed; waiting for the other person"
            ),
            "task_id": task_id,
            "status": "completed" if both_confirmed else "filled",
            "volunteer_confirmed": (
                confirmations["volunteer_completed_at"] is not None
            ),
            "help_seeker_confirmed": (
                confirmations["help_seeker_completed_at"] is not None
            )
        }), 200

    except mysql.connector.Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()
