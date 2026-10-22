import mysql.connector
from flask import Blueprint, jsonify, request, session

from auth import login_required
from db import get_db_connection


review_bp = Blueprint("reviews", __name__)


# Reviews can only be submitted by logged-in users.
# A review requires a completed task application.


@review_bp.route("/api/reviews", methods=["POST"])
@login_required
def submit_review():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    application_id = data.get("application_id")
    rating = data.get("rating")
    comment = data.get("comment", "")

    if type(application_id) is not int or application_id <= 0:
        return jsonify({"error": "Invalid application ID"}), 400

    if type(rating) is not int or not 1 <= rating <= 5:
        return jsonify({"error": "Rating must be between 1 and 5"}), 400

    if not isinstance(comment, str) or len(comment) > 2000:
        return jsonify({"error": "Invalid review comment"}), 400

    comment = comment.strip()
    reviewer_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                a.application_id,
                a.volunteer_id,
                a.status AS application_status,
                a.volunteer_completed_at,
                a.help_seeker_completed_at,
                t.creator_id,
                t.status AS task_status
            FROM task_applications AS a
            JOIN tasks AS t ON t.task_id = a.task_id
            WHERE a.application_id = %s
        """, (application_id,))

        application = cursor.fetchone()

        if application is None:
            return jsonify({"error": "Application not found"}), 404

        creator_id = application["creator_id"]
        volunteer_id = application["volunteer_id"]

        if reviewer_id not in (creator_id, volunteer_id):
            return jsonify({"error": "Permission denied"}), 403

        if (
            application["application_status"] != "completed"
            or application["task_status"] != "completed"
            or application["volunteer_completed_at"] is None
            or application["help_seeker_completed_at"] is None
        ):
            return jsonify({"error": "Task is not fully completed"}), 400

        reviewed_user_id = (
            volunteer_id if reviewer_id == creator_id else creator_id
        )

        try:
            cursor.execute("""
                INSERT INTO reviews (
                    application_id,
                    reviewer_id,
                    reviewed_user_id,
                    rating,
                    comment
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                application_id,
                reviewer_id,
                reviewed_user_id,
                rating,
                comment
            ))

            review_id = cursor.lastrowid
            connection.commit()

        except mysql.connector.IntegrityError as error:
            connection.rollback()

            if error.errno == 1062:
                return jsonify({
                    "error": "You have already reviewed this application"
                }), 409

            raise

        return jsonify({
            "message": "Review submitted successfully",
            "review_id": review_id
        }), 201

    finally:
        cursor.close()
        connection.close()


@review_bp.route("/api/users/<int:user_id>/reviews", methods=["GET"])
def get_user_reviews(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                r.review_id,
                r.rating,
                r.comment,
                r.created_at,
                u.first_name AS reviewer_first_name
            FROM reviews AS r
            JOIN users AS u
                ON u.user_id = r.reviewer_id
            WHERE r.reviewed_user_id = %s
              AND r.moderation_status = 'visible'
            ORDER BY r.created_at DESC, r.review_id DESC
        """, (user_id,))

        reviews = cursor.fetchall()

        for review in reviews:
            review["created_at"] = review["created_at"].isoformat()

        count = len(reviews)
        average = (
            round(sum(r["rating"] for r in reviews) / count, 2)
            if count else None
        )

        return jsonify({
            "user_id": user_id,
            "average_rating": average,
            "review_count": count,
            "reviews": reviews
        }), 200

    finally:
        cursor.close()
        connection.close()
