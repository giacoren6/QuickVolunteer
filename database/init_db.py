
import sqlite3
from pathlib import Path

# Find the database folder
BASE_DIR = Path(__file__).resolve().parent

# Define the database and SQL file locations
DB_PATH = BASE_DIR / "quickvolunteer.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def create_database():
    # Connect to SQLite (creates the file if needed)
    connection = sqlite3.connect(DB_PATH)

    try:
        # Enable foreign key constraints
        connection.execute("PRAGMA foreign_keys = ON")

        # Read our SQL schema
        with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
            sql_script = file.read()

        # Execute all CREATE TABLE statements
        connection.executescript(sql_script)

        # Display the tables
        cursor = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)

        tables = cursor.fetchall()

        print("QuickVolunteer database created!")
        print("------------------------------")

        for table in tables:
            print("Table:", table[0])

        print("------------------------------")
        print("Total tables:", len(tables))

        # Verify foreign key relationships
        errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if errors:
            print("Foreign key problems:", errors)
        else:
            print("Foreign key check: PASSED")

    finally:
        connection.close()


if __name__ == "__main__":
    create_database()
