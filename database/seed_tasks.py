
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).resolve().parent / "quickvolunteer.db"

connection = sqlite3.connect(DB_PATH)
connection.execute("PRAGMA foreign_keys = ON")
connection.row_factory = sqlite3.Row


def get_user_id(email):
    row = connection.execute(
        "SELECT user_id FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if row is None:
        raise ValueError(f"User not found: {email}")

    return row["user_id"]


def get_category_id(name):
    row = connection.execute(
        "SELECT category_id FROM task_categories WHERE category_name = ?",
        (name,)
    ).fetchone()

    if row is None:
        raise ValueError(f"Category not found: {name}")

    return row["category_id"]


# Fictional volunteering opportunities
tasks = [
    {
        "creator": "nadia@example.com",
        "category": "Shopping",
        "title": "Help with grocery shopping",
        "description": "Collect a few essential groceries for a local resident.",
        "location": "Stratford, London",
        "mode": "in_person",
        "contact": "in_app",
        "minutes": 30,
    },
    {
        "creator": "leila@example.com",
        "category": "Technology Support",
        "title": "Help someone set up their email",
        "description": "Provide basic guidance on creating and using an email account.",
        "location": None,
        "mode": "remote",
        "contact": "video_call",
        "minutes": 45,
    },
    {
        "creator": "leila@example.com",
        "category": "Environment",
        "title": "Community park clean-up",
        "description": "Help collect litter and tidy a local community green space.",
        "location": "Victoria Park, London",
        "mode": "in_person",
        "contact": "in_app",
        "minutes": 60,
    },
    {
        "creator": "nadia@example.com",
        "category": "Education",
        "title": "Help with basic computer skills",
        "description": "Explain how to organise files and use a web browser.",
        "location": None,
        "mode": "remote",
        "contact": "video_call",
        "minutes": 30,
    },
]


try:
    with connection:
        # Insert tasks
        for task in tasks:
            creator_id = get_user_id(task["creator"])
            category_id = get_category_id(task["category"])

            existing = connection.execute("""
                SELECT task_id
                FROM tasks
                WHERE creator_id = ?
                  AND title = ?
            """, (creator_id, task["title"])).fetchone()

            if existing:
                continue

            deadline = (
                datetime.now() + timedelta(days=14)
            ).strftime("%Y-%m-%d %H:%M:%S")

            connection.execute("""
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
                creator_id,
                category_id,
                task["title"],
                task["description"],
                task["location"],
                task["mode"],
                task["contact"],
                task["minutes"],
                deadline,
                1,
                "open"
            ))

        # Adam applies for three tasks
        adam_id = get_user_id("adam@example.com")

        for title in [
            "Help with grocery shopping",
            "Help someone set up their email",
            "Community park clean-up"
        ]:
            task_row = connection.execute(
                "SELECT task_id FROM tasks WHERE title = ?",
                (title,)
            ).fetchone()

            if task_row is None:
                raise ValueError(f"Task not found: {title}")

            connection.execute("""
                INSERT OR IGNORE INTO task_applications (
                    task_id,
                    volunteer_id,
                    status
                )
                VALUES (?, ?, 'pending')
            """, (task_row["task_id"], adam_id))

    print("Sample tasks and applications created!")

    print("\nVOLUNTEERING TASKS")
    for row in connection.execute("""
        SELECT
            task_id,
            title,
            delivery_mode,
            estimated_minutes,
            status
        FROM tasks
        ORDER BY task_id
    """):
        print(tuple(row))

    print("\nVOLUNTEER APPLICATIONS")
    for row in connection.execute("""
        SELECT
            a.application_id,
            u.first_name,
            t.title,
            a.status
        FROM task_applications AS a
        JOIN users AS u
            ON a.volunteer_id = u.user_id
        JOIN tasks AS t
            ON a.task_id = t.task_id
        ORDER BY a.application_id
    """):
        print(tuple(row))

finally:
    connection.close()
