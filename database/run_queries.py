
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

connection = sqlite3.connect(
    BASE_DIR / "quickvolunteer.db"
)

connection.execute("PRAGMA foreign_keys = ON")

sql = (BASE_DIR / "queries.sql").read_text(
    encoding="utf-8"
)

try:
    statements = [
        statement.strip()
        for statement in sql.split(";")
        if statement.strip()
    ]

    for number, statement in enumerate(statements, 1):
        print(f"\n{'=' * 45}")
        print(f"QUERY {number}")
        print("=" * 45)

        cursor = connection.execute(statement)

        for row in cursor.fetchall():
            print(row)

finally:
    connection.close()
