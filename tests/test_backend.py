
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
            cursor.execute("DELETE FROM task_skills")
            cursor.execute("DELETE FROM user_skills")
            cursor.execute("DELETE FROM reviews")
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

            cursor.execute("""
                INSERT INTO skills (skill_id, skill_name)
                VALUES
                    (1, 'Cooking'),
                    (2, 'IT Support'),
                    (7, 'Pet Care')
                ON DUPLICATE KEY UPDATE
                    skill_name = VALUES(skill_name)
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

    def put(self, path, json=None):
        return self.client.put(
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
            "visit_location_type": "public",
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

    def test_71_unapproved_dbs_blocks_protected_task(self):
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

        response = self.post("/api/tasks", {
            "title": "Help at home",
            "description": "Help organise items at home.",
            "category_id": 1,
            "delivery_mode": "in_person",
            "visit_location_type": "home",
            "requires_dbs": False,
            "location_text": "Stratford",
            "estimated_minutes": 30
        })

        self.assertEqual(response.status_code, 201)
        task_id = response.get_json()["task_id"]

        self.assertEqual(
            self.login_user("volunteer@test.com").status_code,
            200
        )

        response = self.post(f"/api/tasks/{task_id}/apply")

        self.assertEqual(response.status_code, 403)
        self.assertIn("DBS", response.get_json()["error"])

    def test_72_approved_dbs_allows_protected_task(self):
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

        response = self.post("/api/tasks", {
            "title": "Help at home",
            "description": "Help organise items at home.",
            "category_id": 1,
            "delivery_mode": "in_person",
            "visit_location_type": "home",
            "requires_dbs": False,
            "location_text": "Stratford",
            "estimated_minutes": 30
        })

        self.assertEqual(response.status_code, 201)
        task_id = response.get_json()["task_id"]

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO user_verifications (
                    user_id, verification_type, status
                )
                SELECT user_id, 'dbs', 'approved'
                FROM users
                WHERE email = %s
            """, ("volunteer@test.com",))
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        self.assertEqual(
            self.login_user("volunteer@test.com").status_code,
            200
        )

        response = self.post(f"/api/tasks/{task_id}/apply")
        self.assertEqual(response.status_code, 201)

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


    def test_33_creator_can_cancel_open_task(self):
        self.register_user("seeker@test.com", "help_seeker")
        self.login_user("seeker@test.com")

        task_id = self.create_task().get_json()["task_id"]

        response = self.patch(f"/api/tasks/{task_id}/cancel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "closed")
        self.assertEqual(self.task_status(task_id), "closed")

    def test_34_other_user_cannot_cancel_task(self):
        self.register_user("seeker@test.com", "help_seeker")
        self.register_user("other@test.com", "help_seeker")

        self.login_user("seeker@test.com")
        task_id = self.create_task().get_json()["task_id"]

        self.login_user("other@test.com")
        response = self.patch(f"/api/tasks/{task_id}/cancel")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.task_status(task_id), "open")

    def test_35_completed_task_cannot_be_cancelled(self):
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        self.login_user("volunteer@test.com")
        self.assertEqual(
            self.patch(f"/api/tasks/{task_id}/complete").status_code,
            200
        )

        self.login_user("seeker@test.com")
        self.assertEqual(
            self.patch(f"/api/tasks/{task_id}/complete").status_code,
            200
        )

        response = self.patch(f"/api/tasks/{task_id}/cancel")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.task_status(task_id), "completed")

    def test_36_cancelled_task_not_publicly_listed(self):
        self.register_user("seeker@test.com", "help_seeker")
        self.login_user("seeker@test.com")

        task_id = self.create_task().get_json()["task_id"]

        self.assertEqual(
            self.patch(f"/api/tasks/{task_id}/cancel").status_code,
            200
        )

        response = self.client.get("/api/tasks")

        self.assertEqual(response.status_code, 200)
        public_task_ids = [
            task["task_id"] for task in response.get_json()
        ]
        self.assertNotIn(task_id, public_task_ids)

    def test_37_cancellation_rejects_pending_application(self):
        task_id, application_id = self.prepare_application()

        self.login_user("seeker@test.com")
        response = self.patch(f"/api/tasks/{task_id}/cancel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.task_status(task_id), "closed")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT status
                FROM task_applications
                WHERE application_id = %s
            """, (application_id,))

            application = cursor.fetchone()
            self.assertEqual(application["status"], "rejected")

        finally:
            cursor.close()
            connection.close()


    def test_38_creator_can_cancel_filled_task(self):
        task_id, application_id = self.prepare_application()

        self.accept_application(application_id)

        self.assertEqual(self.task_status(task_id), "filled")

        response = self.patch(f"/api/tasks/{task_id}/cancel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "closed")
        self.assertEqual(self.task_status(task_id), "closed")

        # Volunteer should see that the task is closed.
        self.login_user("volunteer@test.com")

        response = self.client.get("/api/my-applications")

        self.assertEqual(response.status_code, 200)

        application = next(
            item for item in response.get_json()["applications"]
            if item["application_id"] == application_id
        )

        self.assertEqual(application["task_status"], "closed")
        self.assertEqual(application["application_status"], "accepted")


    def test_39_guest_cannot_view_admin_reports(self):
        response = self.client.get("/api/admin/reports")

        self.assertEqual(response.status_code, 401)



    def test_40_volunteer_cannot_view_admin_reports(self):
        response = self.register_user(
            "volunteer40@test.com",
            "volunteer"
        )
        self.assertEqual(response.status_code, 201)

        response = self.login_user("volunteer40@test.com")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/admin/reports")

        self.assertEqual(response.status_code, 403)




    def test_41_volunteer_can_submit_report(self):
        self.assertEqual(
            self.register_user("reporter41@test.com", "volunteer").status_code,
            201
        )

        self.assertEqual(
            self.register_user("reported41@test.com", "volunteer").status_code,
            201
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s",
                ("reported41@test.com",)
            )
            reported_user_id = cursor.fetchone()[0]
        finally:
            cursor.close()
            connection.close()

        self.assertEqual(
            self.login_user("reporter41@test.com").status_code,
            200
        )

        response = self.post("/api/reports", {
            "reported_user_id": reported_user_id,
            "reason": "TEST - Inappropriate behaviour"
        })

        self.assertEqual(response.status_code, 201)



    def test_42_volunteer_cannot_report_themselves(self):
        self.assertEqual(
            self.register_user("reporter42@test.com", "volunteer").status_code,
            201
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s",
                ("reporter42@test.com",)
            )
            user_id = cursor.fetchone()[0]
        finally:
            cursor.close()
            connection.close()

        self.assertEqual(
            self.login_user("reporter42@test.com").status_code,
            200
        )

        response = self.post("/api/reports", {
            "reported_user_id": user_id,
            "reason": "TEST - Attempting to report myself"
        })

        self.assertEqual(response.status_code, 400)




    def test_43_admin_can_view_reports(self):
        from werkzeug.security import generate_password_hash

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (
                    first_name,
                    last_name,
                    email,
                    password_hash,
                    account_type,
                    account_status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                "Test",
                "Administrator",
                "admin43@test.com",
                generate_password_hash("TestingPassword123!"),
                "admin",
                "active"
            ))

            connection.commit()

        finally:
            cursor.close()
            connection.close()

        response = self.login_user("admin43@test.com")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/admin/reports")

        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIn("reports", data)
        self.assertIn("total", data)



    def test_44_admin_can_update_report_status(self):
        from werkzeug.security import generate_password_hash

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            users = [
                ("Administrator", "admin44@test.com", "admin"),
                ("Reporter", "reporter44@test.com", "volunteer"),
                ("Reported", "reported44@test.com", "volunteer")
            ]

            user_ids = {}

            for name, email, role in users:
                cursor.execute("""
                    INSERT INTO users (
                        first_name, last_name, email,
                        password_hash, account_type, account_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    "Test",
                    name,
                    email,
                    generate_password_hash("TestingPassword123!"),
                    role,
                    "active"
                ))

                user_ids[name] = cursor.lastrowid

            cursor.execute("""
                INSERT INTO reports (
                    reporter_id, reported_user_id, reason, status
                )
                VALUES (%s, %s, %s, %s)
            """, (
                user_ids["Reporter"],
                user_ids["Reported"],
                "TEST - Report moderation",
                "open"
            ))

            report_id = cursor.lastrowid
            connection.commit()

        finally:
            cursor.close()
            connection.close()

        self.assertEqual(
            self.login_user("admin44@test.com").status_code,
            200
        )

        response = self.patch(
            f"/api/admin/reports/{report_id}/status",
            {"status": "reviewing"}
        )

        self.assertEqual(response.status_code, 200)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                SELECT status, reviewed_by, reviewed_at
                FROM reports
                WHERE report_id = %s
            """, (report_id,))

            result = cursor.fetchone()
            self.assertIsNotNone(result)

            status, reviewed_by, reviewed_at = result

            self.assertEqual(status, "reviewing")
            self.assertEqual(
                reviewed_by,
                user_ids["Administrator"]
            )
            self.assertIsNotNone(reviewed_at)

        finally:
            cursor.close()
            connection.close()

    def test_45_guest_cannot_moderate_reviews(self):
        response = self.patch(
            "/api/admin/reviews/1/moderation",
            {
                "status": "hidden",
                "reason": "TEST - Unauthorised moderation attempt"
            }
        )

        self.assertEqual(response.status_code, 401)


    def test_46_volunteer_cannot_moderate_reviews(self):
        response = self.register_user(
            "volunteer46@test.com",
            "volunteer"
        )
        self.assertEqual(response.status_code, 201)

        response = self.login_user("volunteer46@test.com")
        self.assertEqual(response.status_code, 200)

        response = self.patch(
            "/api/admin/reviews/1/moderation",
            {
                "status": "hidden",
                "reason": "TEST - Volunteer moderation attempt"
            }
        )

        self.assertEqual(response.status_code, 403)



    def test_47_admin_can_hide_review(self):
        from werkzeug.security import generate_password_hash

        # Create a real application using existing test helpers.
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        # Both users confirm task completion.
        self.login_user("volunteer@test.com")
        self.assertEqual(
            self.patch(f"/api/tasks/{task_id}/complete").status_code,
            200
        )

        self.login_user("seeker@test.com")
        self.assertEqual(
            self.patch(f"/api/tasks/{task_id}/complete").status_code,
            200
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                SELECT user_id, email
                FROM users
                WHERE email IN (%s, %s)
            """, ("seeker@test.com", "volunteer@test.com"))

            user_ids = {
                email: user_id
                for user_id, email in cursor.fetchall()
            }

            cursor.execute("""
                INSERT INTO users (
                    first_name, last_name, email,
                    password_hash, account_type, account_status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                "Test", "Administrator", "admin47@test.com",
                generate_password_hash("TestingPassword123!"),
                "admin", "active"
            ))
            admin_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO reviews (
                    application_id, reviewer_id,
                    reviewed_user_id, rating, comment
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                application_id,
                user_ids["seeker@test.com"],
                user_ids["volunteer@test.com"],
                5,
                "TEST - Review moderation"
            ))
            review_id = cursor.lastrowid

            connection.commit()

        finally:
            cursor.close()
            connection.close()

        # Administrator hides the review.
        self.assertEqual(
            self.login_user("admin47@test.com").status_code,
            200
        )

        response = self.patch(
            f"/api/admin/reviews/{review_id}/moderation",
            {
                "status": "hidden",
                "reason": "TEST - Review requires moderation"
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify the changes were saved in MySQL.
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                SELECT moderation_status, moderated_by,
                       moderated_at, moderation_reason
                FROM reviews
                WHERE review_id = %s
            """, (review_id,))

            result = cursor.fetchone()
            self.assertIsNotNone(result)

            status, moderated_by, moderated_at, reason = result

            self.assertEqual(status, "hidden")
            self.assertEqual(moderated_by, admin_id)
            self.assertIsNotNone(moderated_at)
            self.assertEqual(
                reason,
                "TEST - Review requires moderation"
            )

        finally:
            cursor.close()
            connection.close()


    def test_48_admin_can_restore_review(self):
        # First create and hide a review using Test 47's setup.
        self.test_47_admin_can_hide_review()

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                SELECT review_id
                FROM reviews
                WHERE moderation_status = 'hidden'
                ORDER BY review_id DESC
                LIMIT 1
            """)

            result = cursor.fetchone()
            self.assertIsNotNone(result)
            review_id = result[0]

        finally:
            cursor.close()
            connection.close()

        # Restore the hidden review.
        response = self.patch(
            f"/api/admin/reviews/{review_id}/moderation",
            {
                "status": "visible",
                "reason": "TEST - Review approved for restoration"
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify the updated review in MySQL.
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                SELECT moderation_status, moderation_reason
                FROM reviews
                WHERE review_id = %s
            """, (review_id,))

            result = cursor.fetchone()
            self.assertIsNotNone(result)

            status, reason = result

            self.assertEqual(status, "visible")
            self.assertEqual(
                reason,
                "TEST - Review approved for restoration"
            )

        finally:
            cursor.close()
            connection.close()


    def test_49_admin_cannot_use_invalid_review_status(self):
        # Create a review and log in as administrator.
        self.test_47_admin_can_hide_review()

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                SELECT review_id
                FROM reviews
                ORDER BY review_id DESC
                LIMIT 1
            """)
            review_id = cursor.fetchone()[0]
        finally:
            cursor.close()
            connection.close()

        response = self.patch(
            f"/api/admin/reviews/{review_id}/moderation",
            {
                "status": "deleted",
                "reason": "TEST - Invalid moderation status"
            }
        )

        self.assertEqual(response.status_code, 400)

        # Invalid requests must not change the review.
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                SELECT moderation_status
                FROM reviews
                WHERE review_id = %s
            """, (review_id,))

            self.assertEqual(cursor.fetchone()[0], "hidden")
        finally:
            cursor.close()
            connection.close()




    def test_volunteer_can_save_and_retrieve_skills(self):
        response = self.register_user(
            "skills-volunteer@test.com",
            "volunteer"
        )
        self.assertEqual(response.status_code, 201)

        response = self.login_user(
            "skills-volunteer@test.com"
        )
        self.assertEqual(response.status_code, 200)

        response = self.put(
            "/api/users/me/skills",
            {"skill_ids": [1, 2, 7]}
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            "/api/users/me/skills"
        )
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["total"], 3)

        saved_ids = {
            skill["skill_id"]
            for skill in data["skills"]
        }
        self.assertEqual(saved_ids, {1, 2, 7})

    def test_public_can_list_skills(self):
        response = self.client.get("/api/skills")

        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        skill_names = {
            skill["skill_name"]
            for skill in data["skills"]
        }

        self.assertTrue({
            "Cooking",
            "IT Support",
            "Pet Care"
        }.issubset(skill_names))


    def test_only_task_owner_can_update_skills(self):
        self.assertEqual(
            self.register_user("owner@test.com", "help_seeker").status_code,
            201
        )
        self.assertEqual(
            self.register_user("other@test.com", "volunteer").status_code,
            201
        )

        self.login_user("owner@test.com")
        task_id = self.create_task().get_json()["task_id"]

        response = self.put(
            f"/api/tasks/{task_id}/skills",
            {"skill_ids": [2]}
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/api/tasks/{task_id}/skills")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 1)

        self.login_user("other@test.com")
        response = self.put(
            f"/api/tasks/{task_id}/skills",
            {"skill_ids": [1]}
        )
        self.assertEqual(response.status_code, 403)


    def test_rejects_unknown_skill_id(self):
        self.assertEqual(
            self.register_user(
                "invalid-skills@test.com",
                "volunteer"
            ).status_code,
            201
        )

        self.assertEqual(
            self.login_user(
                "invalid-skills@test.com"
            ).status_code,
            200
        )

        response = self.put(
            "/api/users/me/skills",
            {"skill_ids": [999999]}
        )

        self.assertEqual(response.status_code, 400)

    def test_54_volunteer_can_review_completed_task(self):
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        self.login_user("volunteer@test.com")
        self.assertEqual(
            self.patch(f"/api/tasks/{task_id}/complete").status_code,
            200
        )

        self.login_user("seeker@test.com")
        self.assertEqual(
            self.patch(f"/api/tasks/{task_id}/complete").status_code,
            200
        )

        self.login_user("volunteer@test.com")
        response = self.post("/api/reviews", {
            "application_id": application_id,
            "rating": 5,
            "comment": "Great experience helping with this task!"
        })

        self.assertEqual(response.status_code, 201)
        self.assertIn("review_id", response.get_json())


    def test_55_duplicate_review_blocked(self):
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        self.login_user("volunteer@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")

        self.login_user("seeker@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")

        self.login_user("volunteer@test.com")

        review = {
            "application_id": application_id,
            "rating": 5,
            "comment": "Excellent experience!"
        }

        first = self.post("/api/reviews", review)
        self.assertEqual(first.status_code, 201)

        duplicate = self.post("/api/reviews", review)
        self.assertEqual(duplicate.status_code, 409)


    def test_56_unrelated_user_cannot_review(self):
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        self.login_user("volunteer@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")

        self.login_user("seeker@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")

        self.register_user("outsider@test.com", "volunteer")
        self.login_user("outsider@test.com")

        response = self.post("/api/reviews", {
            "application_id": application_id,
            "rating": 5,
            "comment": "I was not involved in this task."
        })

        self.assertEqual(response.status_code, 403)


    def test_57_review_before_completion_blocked(self):
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        self.login_user("volunteer@test.com")

        response = self.post("/api/reviews", {
            "application_id": application_id,
            "rating": 5,
            "comment": "Trying to review too early."
        })

        self.assertEqual(response.status_code, 400)


    def test_58_invalid_review_ratings_blocked(self):
        _, application_id = self.prepare_application()

        for rating in [0, 6, -1, "five", True]:
            response = self.post("/api/reviews", {
                "application_id": application_id,
                "rating": rating,
                "comment": "Testing invalid ratings"
            })

            self.assertEqual(response.status_code, 400)


    def test_59_public_reviews_show_average_rating(self):
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        self.login_user("volunteer@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")

        self.login_user("seeker@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")

        self.login_user("volunteer@test.com")
        review = self.post("/api/reviews", {
            "application_id": application_id,
            "rating": 5,
            "comment": "Excellent experience!"
        })
        self.assertEqual(review.status_code, 201)

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s",
                ("seeker@test.com",)
            )
            seeker_id = cursor.fetchone()[0]
        finally:
            cursor.close()
            connection.close()

        response = self.client.get(
            f"/api/users/{seeker_id}/reviews"
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["review_count"], 1)
        self.assertEqual(data["average_rating"], 5.0)
        self.assertEqual(data["reviews"][0]["rating"], 5)


    def test_60_hidden_reviews_not_public(self):
        task_id, application_id = self.prepare_application()
        self.accept_application(application_id)

        self.login_user("volunteer@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")

        self.login_user("seeker@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")

        self.login_user("volunteer@test.com")
        response = self.post("/api/reviews", {
            "application_id": application_id,
            "rating": 5,
            "comment": "This review will be hidden."
        })
        self.assertEqual(response.status_code, 201)

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "UPDATE reviews SET moderation_status = 'hidden' "
                "WHERE review_id = %s",
                (response.get_json()["review_id"],)
            )
            cursor.execute(
                "SELECT reviewed_user_id FROM reviews WHERE review_id = %s",
                (response.get_json()["review_id"],)
            )
            reviewed_user_id = cursor.fetchone()[0]
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        public = self.client.get(
            f"/api/users/{reviewed_user_id}/reviews"
        )
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.get_json()["review_count"], 0)
        self.assertIsNone(public.get_json()["average_rating"])
        self.assertEqual(public.get_json()["reviews"], [])


    def test_61_volunteer_can_request_account_verification(self):
        response = self.register_user(
            "verification@test.com",
            "volunteer"
        )
        self.assertEqual(response.status_code, 201)

        self.login_user("verification@test.com")

        response = self.post("/api/verifications", {
            "verification_type": "account"
        })

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["status"], "pending")
        self.assertIn("verification_id", data)

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT status, verification_type
                FROM user_verifications
                WHERE verification_id = %s
            """, (data["verification_id"],))
            saved = cursor.fetchone()

            self.assertIsNotNone(saved)
            self.assertEqual(saved["status"], "pending")
            self.assertEqual(saved["verification_type"], "account")
        finally:
            cursor.close()
            connection.close()


    def test_62_duplicate_verification_request_blocked(self):
        self.assertEqual(
            self.register_user(
                "duplicate-verification@test.com",
                "volunteer"
            ).status_code,
            201
        )

        self.login_user("duplicate-verification@test.com")

        first = self.post("/api/verifications", {
            "verification_type": "account"
        })
        self.assertEqual(first.status_code, 201)

        duplicate = self.post("/api/verifications", {
            "verification_type": "account"
        })
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(
            duplicate.get_json()["status"],
            "pending"
        )


    def test_63_invalid_verification_type_rejected(self):
        self.assertEqual(
            self.register_user(
                "invalid-verification@test.com",
                "volunteer"
            ).status_code,
            201
        )

        self.login_user("invalid-verification@test.com")

        for verification_type in ["passport", "unknown", "", None]:
            response = self.post("/api/verifications", {
                "verification_type": verification_type
            })
            self.assertEqual(response.status_code, 400)


    def test_64_user_can_view_own_verification_status(self):
        self.assertEqual(
            self.register_user(
                "verification-status@test.com",
                "volunteer"
            ).status_code,
            201
        )

        self.login_user("verification-status@test.com")

        created = self.post("/api/verifications", {
            "verification_type": "dbs"
        })
        self.assertEqual(created.status_code, 201)

        response = self.client.get("/api/verifications/me")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(
            data["verifications"][0]["verification_type"],
            "dbs"
        )
        self.assertEqual(
            data["verifications"][0]["status"],
            "pending"
        )


    def test_65_admin_can_approve_verification(self):
        from werkzeug.security import generate_password_hash

        self.assertEqual(
            self.register_user("verify65@test.com", "volunteer").status_code,
            201
        )
        self.assertEqual(self.login_user("verify65@test.com").status_code, 200)

        response = self.post("/api/verifications", {
            "verification_type": "account"
        })
        self.assertEqual(response.status_code, 201)
        verification_id = response.get_json()["verification_id"]

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (
                    first_name, last_name, email,
                    password_hash, account_type, account_status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                "Test", "Admin", "admin65@test.com",
                generate_password_hash("TestingPassword123!"),
                "admin", "active"
            ))
            admin_id = cursor.lastrowid
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        self.assertEqual(self.login_user("admin65@test.com").status_code, 200)

        response = self.patch(
            f"/api/admin/verifications/{verification_id}/decision",
            json={"status": "approved"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "approved")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT status, reviewed_by, reviewed_at
                FROM user_verifications
                WHERE verification_id = %s
            """, (verification_id,))
            saved = cursor.fetchone()

            self.assertEqual(saved["status"], "approved")
            self.assertEqual(saved["reviewed_by"], admin_id)
            self.assertIsNotNone(saved["reviewed_at"])
        finally:
            cursor.close()
            connection.close()


    def test_70_volunteer_cannot_list_admin_verifications(self):
        response = self.register_user(
            "verify70@test.com", "volunteer"
        )
        self.assertEqual(response.status_code, 201)

        response = self.login_user("verify70@test.com")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            "/api/admin/verifications?status=pending"
        )

        self.assertEqual(response.status_code, 403)

    def test_69_admin_can_list_pending_verifications(self):
        from werkzeug.security import generate_password_hash

        self.assertEqual(
            self.register_user("verify69@test.com", "volunteer").status_code,
            201
        )
        self.assertEqual(self.login_user("verify69@test.com").status_code, 200)

        response = self.post("/api/verifications", {
            "verification_type": "account"
        })
        self.assertEqual(response.status_code, 201)
        verification_id = response.get_json()["verification_id"]

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (
                    first_name, last_name, email,
                    password_hash, account_type, account_status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                "Test", "Admin", "admin69@test.com",
                generate_password_hash("TestingPassword123!"),
                "admin", "active"
            ))
            admin_id = cursor.lastrowid
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        self.assertEqual(self.login_user("admin69@test.com").status_code, 200)


        response = self.client.get(
            "/api/admin/verifications?status=pending"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertGreaterEqual(data["total"], 1)

        ids = [
            item["verification_id"]
            for item in data["verifications"]
        ]

        self.assertIn(verification_id, ids)

        for item in data["verifications"]:
            self.assertEqual(item["status"], "pending")

    def test_68_admin_cannot_decide_twice(self):
        from werkzeug.security import generate_password_hash

        self.assertEqual(
            self.register_user("verify68@test.com", "volunteer").status_code,
            201
        )
        self.assertEqual(self.login_user("verify68@test.com").status_code, 200)

        response = self.post("/api/verifications", {
            "verification_type": "account"
        })
        self.assertEqual(response.status_code, 201)
        verification_id = response.get_json()["verification_id"]

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (
                    first_name, last_name, email,
                    password_hash, account_type, account_status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                "Test", "Admin", "admin68@test.com",
                generate_password_hash("TestingPassword123!"),
                "admin", "active"
            ))
            admin_id = cursor.lastrowid
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        self.assertEqual(self.login_user("admin68@test.com").status_code, 200)

        response = self.patch(
            f"/api/admin/verifications/{verification_id}/decision",
            json={"status": "approved"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "approved")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT status, reviewed_by, reviewed_at
                FROM user_verifications
                WHERE verification_id = %s
            """, (verification_id,))
            saved = cursor.fetchone()

            self.assertEqual(saved["status"], "approved")
            self.assertEqual(saved["reviewed_by"], admin_id)
            self.assertIsNotNone(saved["reviewed_at"])
        finally:
            cursor.close()
            connection.close()

        second_response = self.patch(
            f"/api/admin/verifications/{verification_id}/decision",
            {"status": "approved"}
        )
        self.assertEqual(second_response.status_code, 409)

    def test_66_admin_can_reject_verification(self):
        from werkzeug.security import generate_password_hash

        self.assertEqual(
            self.register_user("verify66@test.com", "volunteer").status_code,
            201
        )
        self.assertEqual(self.login_user("verify66@test.com").status_code, 200)

        response = self.post("/api/verifications", {
            "verification_type": "account"
        })
        self.assertEqual(response.status_code, 201)
        verification_id = response.get_json()["verification_id"]

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (
                    first_name, last_name, email,
                    password_hash, account_type, account_status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                "Test", "Admin", "admin66@test.com",
                generate_password_hash("TestingPassword123!"),
                "admin", "active"
            ))
            admin_id = cursor.lastrowid
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        self.assertEqual(self.login_user("admin66@test.com").status_code, 200)

        response = self.patch(
            f"/api/admin/verifications/{verification_id}/decision",
            json={"status": "rejected"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "rejected")

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT status, reviewed_by, reviewed_at
                FROM user_verifications
                WHERE verification_id = %s
            """, (verification_id,))
            saved = cursor.fetchone()

            self.assertEqual(saved["status"], "rejected")
            self.assertEqual(saved["reviewed_by"], admin_id)
            self.assertIsNotNone(saved["reviewed_at"])
        finally:
            cursor.close()
            connection.close()


    def test_67_volunteer_cannot_approve_verification(self):
        self.assertEqual(
            self.register_user("verify67@test.com", "volunteer").status_code,
            201
        )

        self.assertEqual(
            self.login_user("verify67@test.com").status_code,
            200
        )

        created = self.post("/api/verifications", {
            "verification_type": "account"
        })
        self.assertEqual(created.status_code, 201)

        verification_id = created.get_json()["verification_id"]

        response = self.patch(
            f"/api/admin/verifications/{verification_id}/decision",
            {"status": "approved"}
        )

        self.assertEqual(response.status_code, 403)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                "SELECT status FROM user_verifications WHERE verification_id = %s",
                (verification_id,)
            )
            self.assertEqual(cursor.fetchone()[0], "pending")
        finally:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    unittest.main(verbosity=2)

