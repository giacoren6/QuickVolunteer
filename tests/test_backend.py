
import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# IMPORTANT: Configure the isolated database before importing Flask.
# Do not allow this test module to connect to the development DB.
if os.environ.get("MYSQL_DATABASE") != "quickvolunteer_test_db":
    raise RuntimeError(
        "Set MYSQL_DATABASE=quickvolunteer_test_db before running tests"
    )

os.environ["QUICKVOLUNTEER_TESTING"] = "1"
os.environ["FLASK_SECRET_KEY"] = "automated-tests-only-secret-key"

from app import app
from db import get_db_connection


class QuickVolunteerTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True

    def setUp(self):
        # Reset only the dedicated test database.
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("DELETE FROM reports")
            cursor.execute("DELETE FROM task_applications")
            cursor.execute("DELETE FROM tasks")
            cursor.execute("DELETE FROM user_verifications")
            cursor.execute("DELETE FROM task_categories")
            cursor.execute("DELETE FROM users")

            cursor.execute("""
                INSERT INTO task_categories (category_id, category_name)
                VALUES (1, 'Community Support')
            """)

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()
            connection.close()

        self.client = app.test_client()

    def csrf_headers(self):
        response = self.client.get("/api/csrf-token")
        token = response.get_json()["csrf_token"]
        return {"X-CSRFToken": token}

    def post(self, path, json=None):
        return self.client.post(
            path,
            json=json,
            headers=self.csrf_headers()
        )

    def patch(self, path, json=None):
        return self.client.patch(
            path,
            json=json,
            headers=self.csrf_headers()
        )

    def register_user(self, email, account_type):
        return self.post("/api/register", {
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": "TestingPassword123!",
            "account_type": account_type
        })

    def login_user(self, email):
        return self.post("/api/login", {
            "email": email,
            "password": "TestingPassword123!"
        })

    def create_task(self):
        return self.post("/api/tasks", {
            "title": "Help with shopping",
            "description": "Collect groceries from a local shop.",
            "category_id": 1,
            "delivery_mode": "in_person",
            "location_text": "Stratford",
            "estimated_minutes": 30,
            "deadline_at": "2030-12-01 15:00:00"
        })

    def prepare_application(self):
        self.assertEqual(
            self.register_user("seeker@test.com", "help_seeker").status_code,
            201
        )
        self.assertEqual(
            self.register_user("volunteer@test.com", "volunteer").status_code,
            201
        )

        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        task_response = self.create_task()
        self.assertEqual(task_response.status_code, 201)
        task_id = task_response.get_json()["task_id"]

        self.assertEqual(
            self.login_user("volunteer@test.com").status_code,
            200
        )

        response = self.post(f"/api/tasks/{task_id}/apply")
        self.assertEqual(response.status_code, 201)
        application_id = response.get_json()["application_id"]

        return task_id, application_id

    def accept_application(self, application_id):
        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        response = self.patch(
            f"/api/applications/{application_id}/decision",
            {"decision": "accepted"}
        )
        self.assertEqual(response.status_code, 200)
        return response

    def task_status(self, task_id):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT status FROM tasks WHERE task_id = %s",
                (task_id,)
            )
            return cursor.fetchone()["status"]
        finally:
            cursor.close()
            connection.close()

    # ==========================================
    # AUTOMATED TESTS
    # ==========================================

    def test_01_registration(self):
        response = self.register_user("volunteer@test.com", "volunteer")
        self.assertEqual(response.status_code, 201)

    def test_02_login(self):
        self.register_user("volunteer@test.com", "volunteer")
        response = self.login_user("volunteer@test.com")
        self.assertEqual(response.status_code, 200)

    def test_03_volunteer_cannot_create_task(self):
        self.register_user("volunteer@test.com", "volunteer")
        self.login_user("volunteer@test.com")
        self.assertEqual(self.create_task().status_code, 403)

    def test_04_help_seeker_can_create_task(self):
        self.register_user("seeker@test.com", "help_seeker")
        self.login_user("seeker@test.com")
        self.assertEqual(self.create_task().status_code, 201)

    def test_05_volunteer_can_apply(self):
        _, application_id = self.prepare_application()
        self.assertGreater(application_id, 0)

    def test_06_duplicate_application_blocked(self):
        task_id, _ = self.prepare_application()
        response = self.post(f"/api/tasks/{task_id}/apply")
        self.assertEqual(response.status_code, 409)

    def test_07_accept_application(self):
        task_id, application_id = self.prepare_application()
        response = self.accept_application(application_id)
        self.assertEqual(response.get_json()["status"], "accepted")
        self.assertEqual(self.task_status(task_id), "filled")

    def test_08_dual_completion(self):
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        self.login_user("volunteer@test.com")
        first = self.patch(f"/api/tasks/{task_id}/complete")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.task_status(task_id), "filled")

        self.login_user("seeker@test.com")
        second = self.patch(f"/api/tasks/{task_id}/complete")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.task_status(task_id), "completed")

    def test_09_duplicate_completion_blocked(self):
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        first = self.patch(f"/api/tasks/{task_id}/complete")
        self.assertEqual(first.status_code, 200)

        duplicate = self.patch(f"/api/tasks/{task_id}/complete")
        self.assertEqual(duplicate.status_code, 409)

    def test_10_volunteer_cannot_complete_before_acceptance(self):
        task_id, _ = self.prepare_application()
        response = self.patch(f"/api/tasks/{task_id}/complete")
        self.assertEqual(response.status_code, 409)

    def test_11_reject_application(self):
        _, application_id = self.prepare_application()
        self.login_user("seeker@test.com")

        response = self.patch(
            f"/api/applications/{application_id}/decision",
            {"decision": "rejected"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "rejected")

    def test_12_unauthorised_user_cannot_review(self):
        _, application_id = self.prepare_application()

        self.register_user("other@test.com", "help_seeker")
        self.login_user("other@test.com")

        response = self.patch(
            f"/api/applications/{application_id}/decision",
            {"decision": "accepted"}
        )
        self.assertEqual(response.status_code, 403)

    def test_13_suspended_user_session_blocked(self):
        self.register_user("suspended@test.com", "volunteer")
        self.login_user("suspended@test.com")

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                UPDATE users
                SET account_status = 'suspended'
                WHERE email = %s
            """, ("suspended@test.com",))
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        response = self.client.get("/api/me")
        self.assertEqual(response.status_code, 401)

    def test_14_guest_cannot_create_task(self):
        self.assertEqual(self.create_task().status_code, 401)

    def test_15_guest_cannot_apply_for_task(self):
        response = self.post("/api/tasks/1/apply")
        self.assertEqual(response.status_code, 401)

    def test_16_other_user_cannot_complete_task(self):
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        self.register_user("other@test.com", "help_seeker")
        self.login_user("other@test.com")

        response = self.patch(f"/api/tasks/{task_id}/complete")
        self.assertEqual(response.status_code, 403)

    def test_17_missing_csrf_token_rejected(self):
        response = self.client.open(
            "/api/register",
            method="POST",
            json={
                "first_name": "Test",
                "last_name": "User",
                "email": "csrf@test.com",
                "password": "TestingPassword123!",
                "account_type": "volunteer"
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_18_both_account_has_both_permissions(self):
        self.register_user("both@test.com", "both")
        self.login_user("both@test.com")

        self.assertEqual(
            self.client.get("/api/tasks/permissions").status_code,
            200
        )
        self.assertEqual(
            self.client.get("/api/volunteer/permissions").status_code,
            200
        )

    def test_19_public_admin_registration_blocked(self):
        response = self.register_user("admin@test.com", "admin")
        self.assertEqual(response.status_code, 400)

    def test_20_own_task_application_blocked(self):
        self.register_user("both@test.com", "both")
        self.login_user("both@test.com")

        task_response = self.create_task()
        self.assertEqual(task_response.status_code, 201)
        task_id = task_response.get_json()["task_id"]

        response = self.post(f"/api/tasks/{task_id}/apply")
        self.assertEqual(response.status_code, 403)

    
    def test_21_task_creator_can_view_applications(self):
        task_id, application_id = self.prepare_application()

        self.login_user("seeker@test.com")

        response = self.client.get(
            f"/api/tasks/{task_id}/applications"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["task_id"], task_id)
        self.assertEqual(len(data["applications"]), 1)
        self.assertEqual(
            data["applications"][0]["application_id"],
            application_id
        )
        self.assertEqual(
            data["applications"][0]["first_name"],
            "Test"
        )

    def test_22_other_user_cannot_view_applications(self):
        task_id, _ = self.prepare_application()

        self.register_user("other@test.com", "help_seeker")
        self.login_user("other@test.com")

        response = self.client.get(
            f"/api/tasks/{task_id}/applications"
        )

        self.assertEqual(response.status_code, 403)

    def test_23_guest_cannot_view_applications(self):
        response = self.client.get(
            "/api/tasks/1/applications"
        )

        self.assertEqual(response.status_code, 401)

    
    def test_24_help_seeker_can_view_own_tasks(self):
        self.register_user("seeker@test.com", "help_seeker")
        self.login_user("seeker@test.com")

        created = self.create_task()
        self.assertEqual(created.status_code, 201)

        task_id = created.get_json()["task_id"]

        response = self.client.get("/api/my-tasks")

        self.assertEqual(response.status_code, 200)

        tasks = response.get_json()["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["task_id"], task_id)
        self.assertEqual(tasks[0]["status"], "open")

    def test_25_help_seeker_cannot_view_other_users_tasks(self):
        self.register_user("seeker@test.com", "help_seeker")
        self.register_user("other@test.com", "help_seeker")

        self.login_user("seeker@test.com")
        created = self.create_task()
        self.assertEqual(created.status_code, 201)

        self.login_user("other@test.com")
        response = self.client.get("/api/my-tasks")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["tasks"], [])

    def test_26_guest_cannot_view_my_tasks(self):
        response = self.client.get("/api/my-tasks")

        self.assertEqual(response.status_code, 401)

    
    def test_27_volunteer_can_view_own_applications(self):
        task_id, application_id = self.prepare_application()

        # prepare_application leaves the volunteer logged in.
        response = self.client.get("/api/my-applications")

        self.assertEqual(response.status_code, 200)

        applications = response.get_json()["applications"]

        self.assertEqual(len(applications), 1)
        self.assertEqual(
            applications[0]["application_id"],
            application_id
        )
        self.assertEqual(applications[0]["task_id"], task_id)
        self.assertEqual(
            applications[0]["application_status"],
            "pending"
        )
        self.assertEqual(
            applications[0]["task_status"],
            "open"
        )

    def test_28_volunteer_cannot_view_other_applications(self):
        self.prepare_application()

        self.register_user("other@test.com", "volunteer")
        self.login_user("other@test.com")

        response = self.client.get("/api/my-applications")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["applications"],
            []
        )

    def test_29_guest_cannot_view_my_applications(self):
        response = self.client.get("/api/my-applications")

        self.assertEqual(response.status_code, 401)
    
    def test_30_categories_endpoint_returns_200(self):
        response = self.client.get("/api/categories")

        self.assertEqual(response.status_code, 200)

    def test_31_categories_endpoint_returns_list(self):
        response = self.client.get("/api/categories")

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.get_json(), list)

    def test_32_categories_have_correct_fields(self):
        response = self.client.get("/api/categories")

        self.assertEqual(response.status_code, 200)

        categories = response.get_json()

        for category in categories:
            self.assertIn("category_id", category)
            self.assertIn("category_name", category)
            self.assertIsInstance(category["category_id"], int)
            self.assertIsInstance(category["category_name"], str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
