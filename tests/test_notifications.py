import unittest

from tests.test_backend import QuickVolunteerTests
from db import get_db_connection


class NotificationTests(unittest.TestCase):
    setUpClass = classmethod(
        lambda cls: QuickVolunteerTests.setUpClass()
    )

    setUp = QuickVolunteerTests.setUp
    csrf_headers = QuickVolunteerTests.csrf_headers
    post = QuickVolunteerTests.post
    patch = QuickVolunteerTests.patch
    register_user = QuickVolunteerTests.register_user
    login_user = QuickVolunteerTests.login_user
    create_task = QuickVolunteerTests.create_task
    prepare_application = QuickVolunteerTests.prepare_application

    def test_78_user_sees_only_own_notifications(self):
        self.assertEqual(
            self.register_user("first@test.com", "volunteer").status_code,
            201
        )
        self.assertEqual(
            self.register_user("second@test.com", "volunteer").status_code,
            201
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO notifications (user_id, title, content)
                SELECT user_id, 'Task Update', 'Your task has an update'
                FROM users
                WHERE email = %s
            """, ("first@test.com",))
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        self.assertEqual(
            self.login_user("first@test.com").status_code,
            200
        )

        response = self.client.get("/api/notifications")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.get_json()["notifications"]),
            1
        )

        self.assertEqual(
            self.login_user("second@test.com").status_code,
            200
        )

        response = self.client.get("/api/notifications")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["notifications"],
            []
        )

    def test_79_notification_read_permissions(self):
        self.assertEqual(
            self.register_user("first@test.com", "volunteer").status_code,
            201
        )
        self.assertEqual(
            self.register_user("second@test.com", "volunteer").status_code,
            201
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO notifications (user_id, title, content)
                SELECT user_id, 'New Alert', 'You have an update'
                FROM users
                WHERE email = %s
            """, ("first@test.com",))

            notification_id = cursor.lastrowid
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        self.assertEqual(
            self.login_user("second@test.com").status_code,
            200
        )

        denied = self.patch(
            f"/api/notifications/{notification_id}/read"
        )
        self.assertEqual(denied.status_code, 404)

        self.assertEqual(
            self.login_user("first@test.com").status_code,
            200
        )

        response = self.patch(
            f"/api/notifications/{notification_id}/read"
        )
        self.assertEqual(response.status_code, 200)

        listing = self.client.get("/api/notifications")
        self.assertEqual(listing.status_code, 200)

        notifications = listing.get_json()["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertIsNotNone(notifications[0]["read_at"])

    def test_80_accepted_application_creates_notification(self):
        task_id, application_id = self.prepare_application()

        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        response = self.patch(
            f"/api/applications/{application_id}/decision",
            {"decision": "accepted"}
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.login_user("volunteer@test.com").status_code,
            200
        )

        response = self.client.get("/api/notifications")
        self.assertEqual(response.status_code, 200)

        notifications = response.get_json()["notifications"]

        self.assertEqual(len(notifications), 1)
        self.assertEqual(
            notifications[0]["title"],
            "Application Accepted"
        )
        self.assertEqual(
            notifications[0]["task_application_id"],
            application_id
        )

    def test_81_rejected_application_creates_notification(self):
        task_id, application_id = self.prepare_application()

        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        response = self.patch(
            f"/api/applications/{application_id}/decision",
            {"decision": "rejected"}
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.login_user("volunteer@test.com").status_code,
            200
        )

        response = self.client.get("/api/notifications")
        self.assertEqual(response.status_code, 200)

        notifications = response.get_json()["notifications"]

        self.assertEqual(len(notifications), 1)
        self.assertEqual(
            notifications[0]["title"],
            "Application Rejected"
        )
        self.assertEqual(
            notifications[0]["task_application_id"],
            application_id
        )

    def test_82_other_applicant_notified_when_task_filled(self):
        task_id, first_application_id = self.prepare_application()

        self.assertEqual(
            self.register_user("second@test.com", "volunteer").status_code,
            201
        )

        self.assertEqual(
            self.login_user("second@test.com").status_code,
            200
        )

        response = self.post(f"/api/tasks/{task_id}/apply")
        self.assertEqual(response.status_code, 201)
        second_application_id = response.get_json()["application_id"]

        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        response = self.patch(
            f"/api/applications/{first_application_id}/decision",
            {"decision": "accepted"}
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.login_user("volunteer@test.com").status_code,
            200
        )

        response = self.client.get("/api/notifications")
        self.assertEqual(response.status_code, 200)
        first_notifications = response.get_json()["notifications"]

        self.assertEqual(len(first_notifications), 1)
        self.assertEqual(
            first_notifications[0]["title"],
            "Application Accepted"
        )

        self.assertEqual(
            self.login_user("second@test.com").status_code,
            200
        )

        response = self.client.get("/api/notifications")
        self.assertEqual(response.status_code, 200)
        second_notifications = response.get_json()["notifications"]

        self.assertEqual(len(second_notifications), 1)
        self.assertEqual(
            second_notifications[0]["title"],
            "Application Rejected"
        )
        self.assertEqual(
            second_notifications[0]["task_application_id"],
            second_application_id
        )
