
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent / "quickvolunteer.db"

# Fictional accounts for testing
users = [
    ("Adam", "Taylor", "adam@example.com", "volunteer"),
    ("Nadia", "Khan", "nadia@example.com", "help_seeker"),
    ("Leila", "Morgan", "leila@example.com", "organisation"),
    ("Daniel", "Brooks", "daniel@example.com", "administrator"),
]

connection = sqlite3.connect(DB_PATH)
connection.execute("PRAGMA foreign_keys = ON")

try:
    with connection:
        for first_name, last_name, email, role in users:

            # Check whether the account already exists
            existing = connection.execute(
                "SELECT user_id FROM users WHERE email = ?",
                (email,)
            ).fetchone()

            if existing:
                user_id = existing[0]
            else:
                password_hash = generate_password_hash(
                    "QuickVolunteerDemo123!"
                )

                cursor = connection.execute("""
                    INSERT INTO users (
                        first_name,
                        last_name,
                        email,
                        password_hash,
                        account_status
                    )
                    VALUES (?, ?, ?, ?, 'active')
                """, (
                    first_name,
                    last_name,
                    email,
                    password_hash
                ))

                user_id = cursor.lastrowid

            # Find the role ID
            role_row = connection.execute(
                "SELECT role_id FROM roles WHERE role_name = ?",
                (role,)
            ).fetchone()

            if role_row is None:
                raise ValueError(f"Missing role: {role}")

            # Assign the role to the user
            connection.execute("""
                INSERT OR IGNORE INTO user_roles
                (user_id, role_id)
                VALUES (?, ?)
            """, (user_id, role_row[0]))

    print("Sample users created successfully!")

    for row in connection.execute("""
        SELECT
            u.user_id,
            u.first_name,
            u.last_name,
            u.email,
            r.role_name
        FROM users AS u
        JOIN user_roles AS ur
            ON u.user_id = ur.user_id
        JOIN roles AS r
            ON ur.role_id = r.role_id
        ORDER BY u.user_id
    """):
        print(row)

finally:
    connection.close()
