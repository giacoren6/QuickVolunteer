import unittest

from tests.test_backend import QuickVolunteerTests
from db import get_db_connection


class AuditTests(unittest.TestCase):
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

    def test_83_accepted_application_creates_audit_log(self):
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

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT a.actor_id, a.action,
                       a.entity_type, a.entity_id,
                       u.user_id AS expected_actor_id
                FROM audit_logs a
                JOIN users u ON u.email = %s
                WHERE a.entity_type = 'task_application'
                  AND a.entity_id = %s
            """, ("seeker@test.com", application_id))

            records = cursor.fetchall()
        finally:
            cursor.close()
            connection.close()

        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0]["action"],
            "application_accepted"
        )
        self.assertEqual(
            records[0]["entity_type"],
            "task_application"
        )
        self.assertEqual(
            records[0]["actor_id"],
            records[0]["expected_actor_id"]
        )

    def test_84_rejected_application_creates_audit_log(self):
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

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT actor_id, action, entity_type, entity_id
                FROM audit_logs
                WHERE entity_type = 'task_application'
                  AND entity_id = %s
            """, (application_id,))

            records = cursor.fetchall()

            cursor.execute("""
                SELECT user_id
                FROM users
                WHERE email = %s
            """, ("seeker@test.com",))

            expected_actor_id = cursor.fetchone()["user_id"]

        finally:
            cursor.close()
            connection.close()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["action"], "application_rejected")
        self.assertEqual(records[0]["entity_type"], "task_application")
        self.assertEqual(records[0]["entity_id"], application_id)
        self.assertEqual(records[0]["actor_id"], expected_actor_id)
