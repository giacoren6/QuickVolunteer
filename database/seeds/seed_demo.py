
import os
import mysql.connector

# QuickVolunteer fictional demonstration data
# Never run against the automated test database.

DATABASE_NAME = "quickvolunteer_db"


# Fictional accounts for the university demonstration.
# All email addresses use the reserved example.com domain.

DEMO_USERS = [
    ("Emma", "Wilson", "emma.wilson.demo@example.com",
     "help_seeker", "E15 1AA", "Needs occasional shopping assistance.", None),

    ("James", "Carter", "james.carter.demo@example.com",
     "volunteer", "NW1 1AA", "Shopping and community support.", "Weekends"),

    ("Sofia", "Martinez", "sofia.martinez.demo@example.com",
     "both", "HA9 0AA", "Technology help and digital skills.", "Evenings"),

    ("Oliver", "Brown", "oliver.brown.demo@example.com",
     "volunteer", "N1 1AA", "Community volunteering.", "Weekdays"),

    ("Amelia", "Taylor", "amelia.taylor.demo@example.com",
     "help_seeker", "SE10 8AA", "Needs help with digital devices.", None),

    ("Noah", "Williams", "noah.williams.demo@example.com",
     "volunteer", "E3 3AA", "Computer setup and software support.", "Weekends"),

    ("Isabella", "Clark", "isabella.clark.demo@example.com",
     "both", "SW11 1AA", "Education and community support.", "Afternoons"),

    ("Lucas", "Evans", "lucas.evans.demo@example.com",
     "help_seeker", "E20 1AA", "Needs assistance with everyday tasks.", None),

    ("Mia", "Roberts", "mia.roberts.demo@example.com",
     "volunteer", "E8 1AA", "Tutoring and study support.", "Evenings"),

    ("Ethan", "Walker", "ethan.walker.demo@example.com",
     "both", "NW10 1AA", "Shopping and technology support.", "Weekends"),

    ("Grace", "Harris", "grace.harris.demo@example.com",
     "help_seeker", "E17 1AA", "Needs help with shopping.", None),

    ("Daniel", "Lewis", "daniel.lewis.demo@example.com",
     "volunteer", "SE1 1AA", "Community and education support.", "Flexible"),
]



def get_connection():
    if os.getenv("QUICKVOLUNTEER_TESTING") == "1":
        raise RuntimeError("Demo data cannot run in test mode.")

    if not os.getenv("MYSQL_PASSWORD"):
        raise RuntimeError("MYSQL_PASSWORD is not configured.")

    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="quickvolunteer_app",
        password=os.environ["MYSQL_PASSWORD"],
        database=DATABASE_NAME,
    )


# Fictional volunteering tasks for the university demo.
# Format: creator email, category ID, title, description,
# location, delivery mode, duration, status.

DEMO_TASKS = [
    ("emma.wilson.demo@example.com", 1,
     "Help with weekly grocery shopping",
     "Looking for someone to help collect groceries from a local supermarket.",
     "Stratford, London", "in_person", 45, "open"),

    ("amelia.taylor.demo@example.com", 2,
     "Help setting up a new laptop",
     "Need assistance installing basic software and organising files.",
     "Greenwich, London", "in_person", 45, "open"),

    ("lucas.evans.demo@example.com", 3,
     "Help organising community supplies",
     "Looking for a volunteer to help sort donated supplies.",
     "Stratford, London", "in_person", 60, "open"),

    ("grace.harris.demo@example.com", 1,
     "Collect a few groceries",
     "Need help collecting essential groceries from a nearby shop.",
     "Walthamstow, London", "in_person", 30, "open"),

    ("sofia.martinez.demo@example.com", 2,
     "Help with email settings",
     "Need assistance organising email folders and account settings.",
     None, "remote", 30, "open"),

    ("isabella.clark.demo@example.com", 4,
     "Help preparing study notes",
     "Looking for help organising revision notes for an upcoming course.",
     None, "remote", 45, "open"),

    ("ethan.walker.demo@example.com", 2,
     "Help installing useful mobile apps",
     "Need help choosing and installing everyday mobile applications.",
     None, "remote", 30, "open"),

    ("emma.wilson.demo@example.com", 3,
     "Help preparing community event materials",
     "Need someone to help organise leaflets and event supplies.",
     "Stratford, London", "in_person", 60, "open"),

    ("amelia.taylor.demo@example.com", 4,
     "Help learning basic computer skills",
     "Looking for someone to explain basic document editing.",
     None, "remote", 45, "open"),

    ("lucas.evans.demo@example.com", 1,
     "Help collecting household essentials",
     "Need assistance collecting a few household items.",
     "East London", "in_person", 30, "open"),

    ("grace.harris.demo@example.com", 2,
     "Help connecting a printer",
     "Looking for someone to help connect a printer to a laptop.",
     "Walthamstow, London", "in_person", 30, "filled"),

    ("sofia.martinez.demo@example.com", 3,
     "Help sorting community donations",
     "Need assistance organising donated items for a local event.",
     "Wembley, London", "in_person", 60, "filled"),

    ("isabella.clark.demo@example.com", 4,
     "Help with online learning tools",
     "Looking for guidance using an online learning platform.",
     None, "remote", 45, "completed"),

    ("ethan.walker.demo@example.com", 1,
     "Help with supermarket collection",
     "Need help collecting a small grocery order.",
     "Willesden, London", "in_person", 30, "completed"),

    ("emma.wilson.demo@example.com", 2,
     "Help organising smartphone contacts",
     "Need assistance organising contacts and phone settings.",
     None, "remote", 30, "completed"),
]


# Fictional volunteer applications for the university demo.
# Format: task title, volunteer email, application status.

DEMO_APPLICATIONS = [
    # Open tasks: pending applications
    ("Help with weekly grocery shopping",
     "james.carter.demo@example.com", "pending"),

    ("Help with weekly grocery shopping",
     "oliver.brown.demo@example.com", "pending"),

    ("Help setting up a new laptop",
     "noah.williams.demo@example.com", "pending"),

    ("Help setting up a new laptop",
     "sofia.martinez.demo@example.com", "pending"),

    ("Help organising community supplies",
     "daniel.lewis.demo@example.com", "pending"),

    ("Collect a few groceries",
     "james.carter.demo@example.com", "pending"),

    ("Help with email settings",
     "noah.williams.demo@example.com", "pending"),

    ("Help preparing study notes",
     "mia.roberts.demo@example.com", "pending"),

    ("Help installing useful mobile apps",
     "noah.williams.demo@example.com", "pending"),

    ("Help preparing community event materials",
     "oliver.brown.demo@example.com", "pending"),

    ("Help learning basic computer skills",
     "mia.roberts.demo@example.com", "pending"),

    ("Help collecting household essentials",
     "james.carter.demo@example.com", "pending"),

    # Filled tasks: one accepted volunteer each
    ("Help connecting a printer",
     "noah.williams.demo@example.com", "accepted"),

    ("Help connecting a printer",
     "oliver.brown.demo@example.com", "rejected"),

    ("Help sorting community donations",
     "daniel.lewis.demo@example.com", "accepted"),

    # Completed tasks: one completed volunteer each
    ("Help with online learning tools",
     "mia.roberts.demo@example.com", "completed"),

    ("Help with online learning tools",
     "james.carter.demo@example.com", "rejected"),

    ("Help with supermarket collection",
     "james.carter.demo@example.com", "completed"),

    ("Help organising smartphone contacts",
     "noah.williams.demo@example.com", "completed"),

    ("Help organising smartphone contacts",
     "daniel.lewis.demo@example.com", "rejected"),
]




def seed_users(connection):
    from werkzeug.security import generate_password_hash
    import secrets

    cursor = connection.cursor()

    # Each new demo account receives a unique random password.
    # We only store its secure hash in MySQL.
    inserted = 0

    for (
        first_name,
        last_name,
        email,
        account_type,
        postcode,
        skills_summary,
        availability_notes,
    ) in DEMO_USERS:

        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s",
            (email,),
        )

        if cursor.fetchone():
            print(f"Already exists: {email}")
            continue

        password_hash = generate_password_hash(
            secrets.token_urlsafe(32)
        )

        cursor.execute(
            """
            INSERT INTO users (
                first_name,
                last_name,
                email,
                password_hash,
                postcode,
                preferred_language,
                account_type,
                skills_summary,
                availability_notes,
                account_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                first_name,
                last_name,
                email,
                password_hash,
                postcode,
                "en",
                account_type,
                skills_summary,
                availability_notes,
                "active",
            ),
        )

        inserted += 1

    print(f"New fictional users added: {inserted}")



def seed_tasks(connection):
    cursor = connection.cursor()
    inserted = 0

    for (
        creator_email,
        category_id,
        title,
        description,
        location_text,
        delivery_mode,
        estimated_minutes,
        status,
    ) in DEMO_TASKS:

        # Find the fictional task creator.
        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s",
            (creator_email,),
        )
        user = cursor.fetchone()

        if user is None:
            raise RuntimeError(
                f"Demo user not found: {creator_email}"
            )

        creator_id = user[0]

        # Prevent duplicates when the script runs again.
        cursor.execute(
            """
            SELECT task_id
            FROM tasks
            WHERE creator_id = %s
              AND title = %s
            """,
            (creator_id, title),
        )

        if cursor.fetchone():
            print(f"Already exists: {title}")
            continue

        cursor.execute(
            """
            INSERT INTO tasks (
                creator_id,
                category_id,
                title,
                description,
                location_text,
                delivery_mode,
                estimated_minutes,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                creator_id,
                category_id,
                title,
                description,
                location_text,
                delivery_mode,
                estimated_minutes,
                status,
            ),
        )

        inserted += 1

    cursor.close()
    print(f"New fictional tasks added: {inserted}")



def seed_applications(connection):
    cursor = connection.cursor()
    inserted = 0

    for task_title, volunteer_email, status in DEMO_APPLICATIONS:

        # Find the task and its creator.
        cursor.execute(
            """
            SELECT t.task_id, t.creator_id, t.status
            FROM tasks AS t
            JOIN users AS u ON u.user_id = t.creator_id
            WHERE t.title = %s
              AND u.email LIKE %s
            """,
            (task_title, "%.demo@example.com"),
        )
        task = cursor.fetchone()

        if task is None:
            raise RuntimeError(f"Demo task not found: {task_title}")

        task_id, creator_id, task_status = task

        # Find the volunteer and verify their role.
        cursor.execute(
            """
            SELECT user_id, account_type
            FROM users
            WHERE email = %s
            """,
            (volunteer_email,),
        )
        volunteer = cursor.fetchone()

        if volunteer is None:
            raise RuntimeError(
                f"Demo volunteer not found: {volunteer_email}"
            )

        volunteer_id, account_type = volunteer

        if account_type not in ("volunteer", "both"):
            raise RuntimeError("Account is not a volunteer.")

        if volunteer_id == creator_id:
            raise RuntimeError("Users cannot apply to their own tasks.")

        # Make sure the application status matches the task.
        if status == "accepted" and task_status != "filled":
            raise RuntimeError("Accepted application requires a filled task.")

        if status == "completed" and task_status != "completed":
            raise RuntimeError(
                "Completed application requires a completed task."
            )

        # Prevent duplicate applications.
        cursor.execute(
            """
            SELECT application_id
            FROM task_applications
            WHERE task_id = %s AND volunteer_id = %s
            """,
            (task_id, volunteer_id),
        )

        if cursor.fetchone():
            print(f"Already applied: {volunteer_email} -> {task_title}")
            continue

        cursor.execute(
            """
            INSERT INTO task_applications (
                task_id,
                volunteer_id,
                status,
                accepted_at,
                volunteer_completed_at,
                help_seeker_completed_at
            )
            VALUES (
                %s, %s, %s,
                CASE WHEN %s IN ('accepted', 'completed')
                     THEN NOW() ELSE NULL END,
                CASE WHEN %s = 'completed'
                     THEN NOW() ELSE NULL END,
                CASE WHEN %s = 'completed'
                     THEN NOW() ELSE NULL END
            )
            """,
            (
                task_id,
                volunteer_id,
                status,
                status,
                status,
                status,
            ),
        )

        inserted += 1

    cursor.close()
    print(f"New fictional applications added: {inserted}")








def seed_skills(connection):
    skills = [
        "Cooking",
        "IT Support",
        "Gardening",
        "Cleaning",
        "Shopping",
        "Tutoring",
        "Pet Care",
        "Translation",
        "DIY",
        "Digital Skills",
    ]

    cursor = connection.cursor()

    try:
        cursor.executemany(
            "INSERT IGNORE INTO skills (skill_name) VALUES (%s)",
            [(skill,) for skill in skills],
        )
        print("Available skills configured: 10")
    finally:
        cursor.close()



def main():
    connection = get_connection()

    try:
        seed_skills(connection)
        seed_users(connection)
        seed_tasks(connection)
        seed_applications(connection)

        connection.commit()

        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks")
        total_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM task_applications")
        total_applications = cursor.fetchone()[0]

        cursor.close()

        print(f"Total users: {total_users}")
        print(f"Total tasks: {total_tasks}")
        print(f"Total applications: {total_applications}")
        print("QuickVolunteer demo data setup completed!")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
