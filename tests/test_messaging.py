import unittest

from tests.test_backend import QuickVolunteerTests


class MessagingTests(unittest.TestCase):
    setUpClass = classmethod(
        lambda cls: QuickVolunteerTests.setUpClass()
    )

    setUp = QuickVolunteerTests.setUp
    csrf_headers = QuickVolunteerTests.csrf_headers
    post = QuickVolunteerTests.post
    patch = QuickVolunteerTests.patch
    put = QuickVolunteerTests.put
    register_user = QuickVolunteerTests.register_user
    login_user = QuickVolunteerTests.login_user
    create_task = QuickVolunteerTests.create_task
    prepare_application = QuickVolunteerTests.prepare_application

    def test_73_accepted_volunteer_creates_conversation(self):
        task_id, application_id = self.prepare_application()

        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        decision = self.patch(
            f"/api/applications/{application_id}/decision",
            {"decision": "accepted"}
        )
        self.assertEqual(decision.status_code, 200)

        self.assertEqual(
            self.login_user("volunteer@test.com").status_code,
            200
        )

        response = self.post(
            "/api/conversations",
            {"task_id": task_id}
        )
        self.assertEqual(response.status_code, 201)

        conversation_id = response.get_json()["conversation_id"]
        self.assertGreater(conversation_id, 0)

        duplicate = self.post(
            "/api/conversations",
            {"task_id": task_id}
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(
            duplicate.get_json()["conversation_id"],
            conversation_id
        )

    def test_74_send_and_read_messages(self):
        task_id, application_id = self.prepare_application()

        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        decision = self.patch(
            f"/api/applications/{application_id}/decision",
            {"decision": "accepted"}
        )
        self.assertEqual(decision.status_code, 200)

        conversation = self.post(
            "/api/conversations",
            {"task_id": task_id}
        )
        self.assertEqual(conversation.status_code, 201)
        conversation_id = conversation.get_json()["conversation_id"]

        self.assertEqual(
            self.login_user("volunteer@test.com").status_code,
            200
        )

        sent = self.post(
            f"/api/conversations/{conversation_id}/messages",
            {"content": "Hello, I can help with this task!"}
        )
        self.assertEqual(sent.status_code, 201)

        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        response = self.client.get(
            f"/api/conversations/{conversation_id}/messages"
        )
        self.assertEqual(response.status_code, 200)

        messages = response.get_json()["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            messages[0]["content"],
            "Hello, I can help with this task!"
        )

    def test_75_unrelated_user_cannot_access_conversation(self):
        task_id, application_id = self.prepare_application()

        self.assertEqual(
            self.register_user("outsider@test.com", "volunteer").status_code,
            201
        )

        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        decision = self.patch(
            f"/api/applications/{application_id}/decision",
            {"decision": "accepted"}
        )
        self.assertEqual(decision.status_code, 200)

        conversation = self.post(
            "/api/conversations",
            {"task_id": task_id}
        )
        self.assertEqual(conversation.status_code, 201)
        conversation_id = conversation.get_json()["conversation_id"]

        self.assertEqual(
            self.login_user("outsider@test.com").status_code,
            200
        )

        creation = self.post(
            "/api/conversations",
            {"task_id": task_id}
        )
        self.assertEqual(creation.status_code, 403)

        reading = self.client.get(
            f"/api/conversations/{conversation_id}/messages"
        )
        self.assertEqual(reading.status_code, 404)

        sending = self.post(
            f"/api/conversations/{conversation_id}/messages",
            {"content": "I should not be allowed here"}
        )
        self.assertEqual(sending.status_code, 404)

        listing = self.client.get("/api/conversations")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            listing.get_json()["conversations"],
            []
        )

    def test_76_rejected_volunteer_cannot_create_conversation(self):
        task_id, application_id = self.prepare_application()

        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        decision = self.patch(
            f"/api/applications/{application_id}/decision",
            {"decision": "rejected"}
        )
        self.assertEqual(decision.status_code, 200)

        self.assertEqual(
            self.login_user("volunteer@test.com").status_code,
            200
        )

        response = self.post(
            "/api/conversations",
            {"task_id": task_id}
        )
        self.assertEqual(response.status_code, 409)

        listing = self.client.get("/api/conversations")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            listing.get_json()["conversations"],
            []
        )

    def test_77_invalid_messages_are_rejected(self):
        task_id, application_id = self.prepare_application()

        self.assertEqual(
            self.login_user("seeker@test.com").status_code,
            200
        )

        decision = self.patch(
            f"/api/applications/{application_id}/decision",
            {"decision": "accepted"}
        )
        self.assertEqual(decision.status_code, 200)

        conversation = self.post(
            "/api/conversations",
            {"task_id": task_id}
        )
        self.assertEqual(conversation.status_code, 201)

        conversation_id = conversation.get_json()["conversation_id"]
        endpoint = f"/api/conversations/{conversation_id}/messages"

        for invalid_content in ("", "   ", 123, None):
            response = self.post(
                endpoint,
                {"content": invalid_content}
            )
            self.assertEqual(response.status_code, 400)

        too_long = self.post(
            endpoint,
            {"content": "A" * 5001}
        )
        self.assertEqual(too_long.status_code, 400)

        messages = self.client.get(endpoint)
        self.assertEqual(messages.status_code, 200)
        self.assertEqual(
            messages.get_json()["messages"],
            []
        )
