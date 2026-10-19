import os
import mysql.connector

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "quickvolunteer_app"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE", "quickvolunteer_db"),
}


def create_database():
    if not DB_CONFIG["password"]:
        raise RuntimeError("MYSQL_PASSWORD environment variable is required")

    connection = mysql.connector.connect(**DB_CONFIG)

    try:
        cursor = connection.cursor()

        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

        print("QuickVolunteer MySQL Database")
        print("------------------------------")

        for table in tables:
            print("Table:", table)

        print("------------------------------")
        print("Total tables:", len(tables))

        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND REFERENCED_TABLE_NAME IS NOT NULL
        """)

        foreign_key_count = cursor.fetchone()[0]
        print("Foreign key relationships:", foreign_key_count)

        if len(tables) == 12:
            print("Database structure: PASSED")
        else:
            print("Database structure: CHECK REQUIRED")

        cursor.close()

    finally:
        connection.close()


if __name__ == "__main__":
    create_database()
