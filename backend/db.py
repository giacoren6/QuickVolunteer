
import os

import mysql.connector
from mysql.connector import Error


def get_db_connection():
    database_name = os.environ.get(
        "MYSQL_DATABASE",
        "quickvolunteer_db"
    )

    # Automated tests must explicitly use the test database.
    if os.environ.get("QUICKVOLUNTEER_TESTING") == "1":
        if database_name != "quickvolunteer_test_db":
            raise RuntimeError(
                "Tests must use quickvolunteer_test_db"
            )

    try:
        connection = mysql.connector.connect(
            host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            user=os.environ.get("MYSQL_USER", "quickvolunteer_app"),
            password=os.environ["MYSQL_PASSWORD"],
            database=database_name
        )

        return connection

    except Error as error:
        print(f"MySQL connection error: {error}")
        raise
