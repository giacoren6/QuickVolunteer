import os
from pathlib import Path
import mysql.connector

BASE_DIR = Path(__file__).resolve().parent

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "quickvolunteer_app"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE", "quickvolunteer_db"),
}


def run_queries():
    if not DB_CONFIG["password"]:
        raise RuntimeError("MYSQL_PASSWORD environment variable is required")

    connection = mysql.connector.connect(**DB_CONFIG)

    try:
        sql = (BASE_DIR / "queries.sql").read_text(encoding="utf-8")

        statements = [
            statement.strip()
            for statement in sql.split(";")
            if statement.strip() and not statement.strip().startswith("--")
        ]

        # Keep queries that begin with SQL comments.
        statements = []
        for section in sql.split(";"):
            lines = [
                line for line in section.splitlines()
                if line.strip() and not line.strip().startswith("--")
            ]
            statement = "\n".join(lines).strip()
            if statement:
                statements.append(statement)

        for number, statement in enumerate(statements, 1):
            print(f"\n{'=' * 45}")
            print(f"QUERY {number}")
            print("=" * 45)

            cursor = connection.cursor()

            try:
                cursor.execute(statement)

                for row in cursor.fetchall():
                    print(row)

            finally:
                cursor.close()

        print(f"\nSuccessfully executed {len(statements)} MySQL queries.")

    finally:
        connection.close()


if __name__ == "__main__":
    run_queries()
