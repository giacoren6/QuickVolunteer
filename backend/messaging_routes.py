from flask import Blueprint, jsonify, session

from auth import login_required
from db import get_db_connection


messaging_bp = Blueprint("messaging", __name__)


@messaging_bp.route("/api/conversations", methods=["GET"])
@login_required
def list_conversations():
    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                c.conversation_id,
                c.task_id,
                t.title AS task_title,
                c.created_at,
                cm.last_read_at
            FROM conversations AS c
            JOIN conversation_members AS cm
                ON cm.conversation_id = c.conversation_id
            JOIN tasks AS t
                ON t.task_id = c.task_id
            WHERE cm.user_id = %s
            ORDER BY c.created_at DESC, c.conversation_id DESC
        """, (user_id,))

        conversations = cursor.fetchall()

        for conversation in conversations:
            conversation["created_at"] = (
                conversation["created_at"].isoformat()
            )
            if conversation["last_read_at"] is not None:
                conversation["last_read_at"] = (
                    conversation["last_read_at"].isoformat()
                )

        return jsonify({"conversations": conversations}), 200

    finally:
        cursor.close()
        connection.close()


@messaging_bp.route(
    "/api/conversations/<int:conversation_id>/messages",
    methods=["GET"]
)
@login_required
def get_messages(conversation_id):
    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT 1
            FROM conversation_members
            WHERE conversation_id = %s
              AND user_id = %s
        """, (conversation_id, user_id))

        if cursor.fetchone() is None:
            return jsonify({
                "error": "Conversation not found or access denied"
            }), 404

        cursor.execute("""
            SELECT
                message_id,
                conversation_id,
                sender_id,
                content,
                sent_at
            FROM messages
            WHERE conversation_id = %s
            ORDER BY sent_at ASC, message_id ASC
        """, (conversation_id,))

        messages = cursor.fetchall()

        for message in messages:
            message["sent_at"] = message["sent_at"].isoformat()

        return jsonify({"messages": messages}), 200

    finally:
        cursor.close()
        connection.close()


@messaging_bp.route(
    "/api/conversations/<int:conversation_id>/messages",
    methods=["POST"]
)
@login_required
def send_message(conversation_id):
    from flask import request

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    content = data.get("content")

    if not isinstance(content, str) or not content.strip():
        return jsonify({"error": "Message cannot be empty"}), 400

    content = content.strip()

    if len(content) > 5000:
        return jsonify({"error": "Message is too long"}), 400

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT 1
            FROM conversation_members
            WHERE conversation_id = %s
              AND user_id = %s
        """, (conversation_id, user_id))

        if cursor.fetchone() is None:
            return jsonify({
                "error": "Conversation not found or access denied"
            }), 404

        cursor.execute("""
            INSERT INTO messages (
                conversation_id,
                sender_id,
                content
            )
            VALUES (%s, %s, %s)
        """, (conversation_id, user_id, content))

        message_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Message sent successfully",
            "message_id": message_id
        }), 201

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


@messaging_bp.route("/api/conversations", methods=["POST"])
@login_required
def create_conversation():
    from flask import request

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400

    task_id = data.get("task_id")

    if type(task_id) is not int or task_id <= 0:
        return jsonify({"error": "Valid task_id required"}), 400

    user_id = session["user_id"]
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute("""
            SELECT task_id, creator_id
            FROM tasks
            WHERE task_id = %s
            FOR UPDATE
        """, (task_id,))

        task = cursor.fetchone()

        if task is None:
            return jsonify({"error": "Task not found"}), 404

        cursor.execute("""
            SELECT volunteer_id
            FROM task_applications
            WHERE task_id = %s
              AND status IN ('accepted', 'completed')
            LIMIT 1
        """, (task_id,))

        application = cursor.fetchone()

        if application is None:
            return jsonify({
                "error": "No accepted volunteer for this task"
            }), 409

        volunteer_id = application["volunteer_id"]
        creator_id = task["creator_id"]

        if user_id not in (creator_id, volunteer_id):
            return jsonify({"error": "Permission denied"}), 403

        cursor.execute("""
            SELECT conversation_id
            FROM conversations
            WHERE task_id = %s
            LIMIT 1
        """, (task_id,))

        existing = cursor.fetchone()

        if existing is not None:
            connection.commit()
            return jsonify({
                "conversation_id": existing["conversation_id"],
                "message": "Conversation already exists"
            }), 200

        cursor.execute("""
            INSERT INTO conversations (task_id)
            VALUES (%s)
        """, (task_id,))

        conversation_id = cursor.lastrowid

        cursor.executemany("""
            INSERT INTO conversation_members (
                conversation_id, user_id
            )
            VALUES (%s, %s)
        """, [
            (conversation_id, creator_id),
            (conversation_id, volunteer_id)
        ])

        connection.commit()

        return jsonify({
            "conversation_id": conversation_id,
            "message": "Conversation created successfully"
        }), 201

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()
