
import os
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"

sys.path.insert(0, str(BACKEND_DIR))

# Configure a separate database before importing Flask
temp_dir = tempfile.TemporaryDirectory()
TEST_DB = Path(temp_dir.name) / "test.db"

os.environ["QUICKVOLUNTEER_DB_PATH"] = str(TEST_DB)
os.environ["FLASK_SECRET_KEY"] = "test-only-secret-key"

from app import app


class QuickVolunteerTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True

    def setUp(self):
        # Start each test with a fresh database
        if TEST_DB.exists():
            TEST_DB.unlink()

        connection = sqlite3.connect(TEST_DB)
        connection.execute("PRAGMA foreign_keys = ON")

        schema = (BASE_DIR / "database" / "schema.sql").read_text()
        connection.executescript(schema)

        connection.executemany(
            "INSERT INTO roles (role_name) VALUES (?)",
            [
                ("volunteer",),
                ("help_seeker",),
                ("organisation",),
                ("administrator",)
            ]
        )

        connection.execute("""
            INSERT INTO task_categories (category_name)
            VALUES ('Community Support')
        """)

        connection.commit()
        connection.close()

        self.client = app.test_client()

    def tearDown(self):
        # Close the test client's session after each test
        self.client = None

    def register_user(self, email, role):
        return self.client.post("/api/register", json={
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": "TestingPassword123!",
            "role": role
        })

    def login_user(self, email):
        return self.client.post("/api/login", json={
            "email": email,
            "password": "TestingPassword123!"
        })

    def create_task(self):
        return self.client.post("/api/tasks", json={
            "title": "Help with shopping",
            "description": "Collect groceries from a local shop.",
            "category_id": 1,
            "delivery_mode": "in_person",
            "location_text": "Stratford",
            "contact_method": "in_app",
            "estimated_minutes": 30,
            "deadline_at": "2030-12-01 15:00:00"
        })

    def prepare_application(self):
        # Create a Help Seeker and a Volunteer
        self.register_user("seeker@test.com", "help_seeker")
        self.register_user("volunteer@test.com", "volunteer")

        # Help Seeker creates a task
        self.login_user("seeker@test.com")
        task_response = self.create_task()
        self.assertEqual(task_response.status_code, 201)
        task_id = task_response.get_json()["task_id"]

        # Volunteer applies
        self.login_user("volunteer@test.com")
        response = self.client.post(
            f"/api/tasks/{task_id}/apply"
        )
        self.assertEqual(response.status_code, 201)

        application_id = response.get_json()["application_id"]

        return task_id, application_id

    # =====================================
    # AUTOMATED TESTS
    # =====================================

    def test_01_registration(self):
        response = self.register_user(
            "volunteer@test.com", "volunteer"
        )
        self.assertEqual(response.status_code, 201)

    def test_02_login(self):
        self.register_user("volunteer@test.com", "volunteer")
        response = self.login_user("volunteer@test.com")
        self.assertEqual(response.status_code, 200)

    def test_03_volunteer_cannot_create_task(self):
        self.register_user("volunteer@test.com", "volunteer")
        self.login_user("volunteer@test.com")
        response = self.create_task()
        self.assertEqual(response.status_code, 403)

    def test_04_help_seeker_can_create_task(self):
        self.register_user("seeker@test.com", "help_seeker")
        self.login_user("seeker@test.com")
        response = self.create_task()
        self.assertEqual(response.status_code, 201)

    def test_05_volunteer_can_apply(self):
        task_id, application_id = self.prepare_application()
        self.assertGreater(application_id, 0)

    def test_06_duplicate_application_blocked(self):
        task_id, application_id = self.prepare_application()

        response = self.client.post(
            f"/api/tasks/{task_id}/apply"
        )
        self.assertEqual(response.status_code, 409)

    def test_07_accept_application(self):
        task_id, application_id = self.prepare_application()

        self.login_user("seeker@test.com")
        response = self.client.patch(
            f"/api/applications/{application_id}/decision",
            json={"decision": "accepted"}
        )
        self.assertEqual(response.status_code, 200)

    def test_08_complete_task(self):
        task_id, application_id = self.prepare_application()

        self.login_user("seeker@test.com")
        self.client.patch(
            f"/api/applications/{application_id}/decision",
            json={"decision": "accepted"}
        )

        response = self.client.patch(
            f"/api/tasks/{task_id}/complete"
        )
        self.assertEqual(response.status_code, 200)

    def test_09_duplicate_completion_blocked(self):
        task_id, application_id = self.prepare_application()

        self.login_user("seeker@test.com")
        self.client.patch(
            f"/api/applications/{application_id}/decision",
            json={"decision": "accepted"}
        )
        self.client.patch(f"/api/tasks/{task_id}/complete")

        response = self.client.patch(
            f"/api/tasks/{task_id}/complete"
        )
        self.assertEqual(response.status_code, 409)

    def test_10_volunteer_cannot_complete_task(self):
        task_id, application_id = self.prepare_application()

        # prepare_application leaves Volunteer logged in
        response = self.client.patch(
            f"/api/tasks/{task_id}/complete"
        )
        self.assertEqual(response.status_code, 403)

    def test_11_reject_application(self):
        task_id, application_id = self.prepare_application()

        self.login_user("seeker@test.com")
        response = self.client.patch(
            f"/api/applications/{application_id}/decision",
            json={"decision": "rejected"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["status"], "rejected"
        )

    def test_12_unauthorised_user_cannot_review(self):
        task_id, application_id = self.prepare_application()

        # Register another Help Seeker who does not own the task
        self.register_user("other@test.com", "help_seeker")
        self.login_user("other@test.com")

        response = self.client.patch(
            f"/api/applications/{application_id}/decision",
            json={"decision": "accepted"}
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
