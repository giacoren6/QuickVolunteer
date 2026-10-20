import mysql.connector
from flask import Blueprint, jsonify, request, session

from auth import login_required
from db import get_db_connection


skills_bp = Blueprint("skills", __name__)


# ==========================================
# GET ALL AVAILABLE SKILLS
# ==========================================

@skills_bp.route("/api/skills", methods=["GET"])
def get_skills():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT skill_id, skill_name
            FROM skills
            ORDER BY skill_name ASC
        """)

        skills = cursor.fetchall()

        return jsonify({
            "skills": skills,
            "total": len(skills)
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# GET CURRENT USER'S SKILLS
# ==========================================

@skills_bp.route("/api/users/me/skills", methods=["GET"])
@login_required
def get_my_skills():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT s.skill_id, s.skill_name
            FROM user_skills AS us
            JOIN skills AS s
                ON us.skill_id = s.skill_id
            WHERE us.user_id = %s
            ORDER BY s.skill_name ASC
        """, (session["user_id"],))

        skills = cursor.fetchall()

        return jsonify({
            "user_id": session["user_id"],
            "skills": skills,
            "total": len(skills)
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# UPDATE CURRENT USER'S SKILLS
# ==========================================

@skills_bp.route("/api/users/me/skills", methods=["PUT"])
@login_required
def update_my_skills():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    skill_ids = data.get("skill_ids")

    if not isinstance(skill_ids, list):
        return jsonify({"error": "skill_ids must be a list"}), 400

    if (
        len(skill_ids) > 50
        or any(type(skill_id) is not int or skill_id <= 0
               for skill_id in skill_ids)
        or len(skill_ids) != len(set(skill_ids))
    ):
        return jsonify({"error": "Invalid or duplicate skill IDs"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        if skill_ids:
            placeholders = ", ".join(["%s"] * len(skill_ids))
            cursor.execute(
                f"SELECT skill_id FROM skills "
                f"WHERE skill_id IN ({placeholders})",
                tuple(skill_ids)
            )

            if len(cursor.fetchall()) != len(skill_ids):
                return jsonify({"error": "Unknown skill ID"}), 400

        cursor.execute(
            "DELETE FROM user_skills WHERE user_id = %s",
            (session["user_id"],)
        )

        if skill_ids:
            cursor.executemany("""
                INSERT INTO user_skills (user_id, skill_id)
                VALUES (%s, %s)
            """, [
                (session["user_id"], skill_id)
                for skill_id in skill_ids
            ])

        connection.commit()

        return jsonify({
            "message": "Skills updated successfully",
            "skill_ids": skill_ids
        }), 200

    except mysql.connector.Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ==========================================
# GET SKILLS REQUIRED FOR A TASK
# ==========================================

@skills_bp.route("/api/tasks/<int:task_id>/skills", methods=["GET"])
def get_task_skills(task_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT task_id FROM tasks WHERE task_id = %s",
            (task_id,)
        )

        if cursor.fetchone() is None:
            return jsonify({"error": "Task not found"}), 404

        cursor.execute("""
            SELECT s.skill_id, s.skill_name
            FROM task_skills AS ts
            JOIN skills AS s
                ON ts.skill_id = s.skill_id
            WHERE ts.task_id = %s
            ORDER BY s.skill_name ASC
        """, (task_id,))

        skills = cursor.fetchall()

        return jsonify({
            "task_id": task_id,
            "skills": skills,
            "total": len(skills)
        }), 200

    finally:
        cursor.close()
        connection.close()


# ==========================================
# UPDATE TASK SKILLS - CREATOR ONLY
# ==========================================

@skills_bp.route("/api/tasks/<int:task_id>/skills", methods=["PUT"])
@login_required
def update_task_skills(task_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    skill_ids = data.get("skill_ids")

    if not isinstance(skill_ids, list):
        return jsonify({"error": "skill_ids must be a list"}), 400

    if (
        len(skill_ids) > 50
        or any(type(s) is not int or s <= 0 for s in skill_ids)
        or len(skill_ids) != len(set(skill_ids))
    ):
        return jsonify({"error": "Invalid or duplicate skill IDs"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT creator_id FROM tasks WHERE task_id = %s",
            (task_id,)
        )
        task = cursor.fetchone()

        if task is None:
            return jsonify({"error": "Task not found"}), 404

        if task["creator_id"] != session["user_id"]:
            return jsonify({"error": "Permission denied"}), 403

        if skill_ids:
            placeholders = ", ".join(["%s"] * len(skill_ids))
            cursor.execute(
                f"SELECT skill_id FROM skills "
                f"WHERE skill_id IN ({placeholders})",
                tuple(skill_ids)
            )

            if len(cursor.fetchall()) != len(skill_ids):
                return jsonify({"error": "Unknown skill ID"}), 400

        cursor.execute(
            "DELETE FROM task_skills WHERE task_id = %s",
            (task_id,)
        )

        if skill_ids:
            cursor.executemany("""
                INSERT INTO task_skills (task_id, skill_id)
                VALUES (%s, %s)
            """, [(task_id, skill_id) for skill_id in skill_ids])

        connection.commit()

        return jsonify({
            "message": "Task skills updated successfully",
            "task_id": task_id,
            "skill_ids": skill_ids
        }), 200

    except mysql.connector.Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()
