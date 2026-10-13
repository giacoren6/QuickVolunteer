
from flask import Blueprint, jsonify, session, request
from auth import roles_required, get_db
from datetime import datetime

task_bp = Blueprint("task_management", __name__)


# Help Seekers and Organisations only
@task_bp.route("/api/tasks/permissions", methods=["GET"])
@roles_required("help_seeker", "organisation")
def task_permissions():
    return jsonify({
        "message": "You have permission to create tasks",
        "user_id": session["user_id"]
    }), 200


# Volunteers only
@task_bp.route("/api/volunteer/permissions", methods=["GET"])
@roles_required("volunteer")
def volunteer_permissions():
    return jsonify({
        "message": "You have permission to apply for tasks",
        "user_id": session["user_id"]
    }), 200



from datetime import datetime
from flask import request

# ==========================================
# CREATE A NEW VOLUNTEERING TASK
# ==========================================

@task_bp.route("/api/tasks", methods=["POST"])
@roles_required("help_seeker", "organisation")
def create_task():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "JSON body required"
        }), 400

    # Required task information
    title = data.get("title")
    description = data.get("description")
    category_id = data.get("category_id")
    delivery_mode = data.get("delivery_mode")
    estimated_minutes = data.get("estimated_minutes")
    deadline_at = data.get("deadline_at")
    location_text = data.get("location_text")
    contact_method = data.get("contact_method", "in_app")

    # Validate text fields
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
            return jsonify({"error": "Location is required for in-person tasks"}), 400

    if type(estimated_minutes) is not int or not 15 <= estimated_minutes <= 60:
        return jsonify({
            "error": "Duration must be between 15 and 60 minutes"
        }), 400

    if type(category_id) is not int:
        return jsonify({"error": "Valid category ID required"}), 400

    if not isinstance(contact_method, str) or not contact_method.strip():
        return jsonify({"error": "Contact method is required"}), 400

    try:
        deadline = datetime.fromisoformat(deadline_at)
        if deadline.tzinfo is not None:
            raise ValueError("Use a local date and time without timezone")

        if deadline <= datetime.now():
            return jsonify({"error": "Deadline must be in the future"}), 400

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid deadline format"}), 400

    connection = get_db()

    try:
        category = connection.execute("""
            SELECT category_id
            FROM task_categories
            WHERE category_id = ?
        """, (category_id,)).fetchone()

        if category is None:
            return jsonify({"error": "Category not found"}), 400

        cursor = connection.execute("""
            INSERT INTO tasks (
                creator_id,
                category_id,
                title,
                description,
                location_text,
                delivery_mode,
                contact_method,
                estimated_minutes,
                deadline_at,
                volunteer_capacity,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            category_id,
            title.strip(),
            description.strip(),
            location_text.strip() if isinstance(location_text, str) else None,
            delivery_mode,
            contact_method.strip(),
            estimated_minutes,
            deadline.strftime("%Y-%m-%d %H:%M:%S"),
            1,
            "open"
        ))

        connection.commit()

        return jsonify({
            "message": "Task created successfully",
            "task_id": cursor.lastrowid
        }), 201

    finally:
        connection.close()



# ==========================================
# VOLUNTEER APPLICATIONS
# ==========================================

@task_bp.route("/api/tasks/<int:task_id>/apply", methods=["POST"])
@roles_required("volunteer")
def apply_for_task(task_id):

    volunteer_id = session["user_id"]
    connection = get_db()

    try:
        task = connection.execute("""
            SELECT task_id, creator_id, status,
                   deadline_at, volunteer_capacity
            FROM tasks
            WHERE task_id = ?
        """, (task_id,)).fetchone()

        if task is None:
            return jsonify({"error": "Task not found"}), 404

        if task["status"] != "open":
            return jsonify({"error": "Task is not open"}), 409

        if datetime.fromisoformat(task["deadline_at"]) <= datetime.now():
            return jsonify({"error": "Task deadline has passed"}), 409

        if task["creator_id"] == volunteer_id:
            return jsonify({"error": "Cannot apply for your own task"}), 403

        existing = connection.execute("""
            SELECT application_id
            FROM task_applications
            WHERE task_id = ? AND volunteer_id = ?
        """, (task_id, volunteer_id)).fetchone()

        if existing:
            return jsonify({"error": "Already applied for this task"}), 409

        accepted_count = connection.execute("""
            SELECT COUNT(*) AS total
            FROM task_applications
            WHERE task_id = ?
              AND status IN ('accepted', 'completed')
        """, (task_id,)).fetchone()["total"]

        if accepted_count >= task["volunteer_capacity"]:
            return jsonify({"error": "Task is full"}), 409

        cursor = connection.execute("""
            INSERT INTO task_applications (
                task_id, volunteer_id, status
            )
            VALUES (?, ?, 'pending')
        """, (task_id, volunteer_id))

        connection.commit()

        return jsonify({
            "message": "Application submitted successfully",
            "application_id": cursor.lastrowid,
            "task_id": task_id,
            "status": "pending"
        }), 201

    finally:
        connection.close()


    
# ==========================================
# ACCEPT OR REJECT APPLICATIONS
# ==========================================

@task_bp.route(
    "/api/applications/<int:application_id>/decision",
    methods=["PATCH"]
)
@roles_required("help_seeker", "organisation")
def decide_application(application_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    decision = data.get("decision")

    if decision not in ("accepted", "rejected"):
        return jsonify({
            "error": "Decision must be accepted or rejected"
        }), 400

    connection = get_db()

    try:
        connection.execute("BEGIN IMMEDIATE")

        application = connection.execute("""
            SELECT
                a.application_id,
                a.status AS application_status,
                a.task_id,
                t.creator_id,
                t.status AS task_status,
                t.volunteer_capacity
            FROM task_applications AS a
            JOIN tasks AS t ON a.task_id = t.task_id
            WHERE a.application_id = ?
        """, (application_id,)).fetchone()

        if application is None:
            return jsonify({"error": "Application not found"}), 404

        if application["creator_id"] != session["user_id"]:
            return jsonify({"error": "Permission denied"}), 403

        if application["application_status"] != "pending":
            return jsonify({
                "error": "Application has already been reviewed"
            }), 409

        if application["task_status"] not in ("open", "filled"):
            return jsonify({
                "error": "Task is no longer accepting decisions"
            }), 409

        if decision == "accepted":
            if application["task_status"] != "open":
                return jsonify({"error": "Task is already full"}), 409

            accepted_count = connection.execute("""
                SELECT COUNT(*) AS total
                FROM task_applications
                WHERE task_id = ?
                  AND status IN ('accepted', 'completed')
            """, (application["task_id"],)).fetchone()["total"]

            if accepted_count >= application["volunteer_capacity"]:
                return jsonify({"error": "Task is already full"}), 409

        connection.execute("""
            UPDATE task_applications
            SET status = ?,
                accepted_at = CASE
                    WHEN ? = 'accepted' THEN CURRENT_TIMESTAMP
                    ELSE NULL
                END
            WHERE application_id = ?
        """, (decision, decision, application_id))

        if decision == "accepted":
            accepted_count += 1

            if accepted_count >= application["volunteer_capacity"]:
                connection.execute("""
                    UPDATE tasks
                    SET status = 'filled'
                    WHERE task_id = ?
                """, (application["task_id"],))

        connection.commit()

        return jsonify({
            "message": "Application reviewed successfully",
            "application_id": application_id,
            "status": decision
        }), 200

    finally:
        connection.close()

    

# ==========================================
# COMPLETE A VOLUNTEERING TASK
# ==========================================

@task_bp.route("/api/tasks/<int:task_id>/complete", methods=["PATCH"])
@roles_required("help_seeker", "organisation")
def complete_task(task_id):

    connection = get_db()

    try:
        connection.execute("BEGIN IMMEDIATE")

        task = connection.execute("""
            SELECT task_id, creator_id, status
            FROM tasks
            WHERE task_id = ?
        """, (task_id,)).fetchone()

        if task is None:
            return jsonify({
                "error": "Task not found"
            }), 404

        # Only the task creator can confirm completion
        if task["creator_id"] != session["user_id"]:
            return jsonify({
                "error": "Permission denied"
            }), 403

        if task["status"] == "completed":
            return jsonify({
                "error": "Task already completed"
            }), 409

        if task["status"] != "filled":
            return jsonify({
                "error": "Task must be filled before completion"
            }), 409

        # Complete accepted volunteer applications
        connection.execute("""
            UPDATE task_applications
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
              AND status = 'accepted'
        """, (task_id,))

        # Complete the task itself
        connection.execute("""
            UPDATE tasks
            SET status = 'completed'
            WHERE task_id = ?
        """, (task_id,))

        connection.commit()

        return jsonify({
            "message": "Task completed successfully",
            "task_id": task_id,
            "status": "completed"
        }), 200

    finally:
        connection.close()
