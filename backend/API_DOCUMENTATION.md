
# QuickVolunteer — Backend API Documentation

## 1. Overview

QuickVolunteer is a volunteering platform for small tasks lasting
15–60 minutes.

Backend: Python, Flask
Database: MySQL 8.0
API format: JSON
Authentication: Flask sessions (cookies)
CSRF protection: Flask-WTF

The frontend should communicate with the Flask backend using
the endpoints documented below.

## 2. Authentication and CSRF

Before sending POST or PATCH requests, obtain a CSRF token:

GET /api/csrf-token

Expected JSON field:

{
  "csrf_token": "TOKEN_VALUE"
}

Include the token in the request header:

X-CSRFToken: TOKEN_VALUE

For JSON requests, also use:

Content-Type: application/json

Authentication uses Flask session cookies.

When frontend and backend are on different origins,
the browser must be configured to send credentials,
and the backend must explicitly support the required
cross-origin requests.

## 3. Register

POST /api/register

Request:

{
  "first_name": "Alex",
  "last_name": "Smith",
  "email": "alex@example.com",
  "password": "SecurePassword123!",
  "account_type": "volunteer"
}

Allowed account types:
- volunteer
- help_seeker
- both

Password: minimum 12 characters.

Success: HTTP 201

{
  "message": "Account created successfully",
  "user_id": 1,
  "account_type": "volunteer"
}

Possible errors:
- 400: Invalid or missing fields
- 409: Email already registered or invalid account details

Public administrator registration is not permitted.

Current development behaviour: new accounts are immediately
activated. The verification workflow is not yet implemented.

## 4. Login

POST /api/login

Request:

{
  "email": "alex@example.com",
  "password": "SecurePassword123!"
}

Success: HTTP 200

{
  "message": "Login successful",
  "user": {
    "user_id": 1,
    "first_name": "Alex",
    "email": "alex@example.com",
    "account_type": "volunteer"
  }
}

Possible errors:
- 400: Missing email or password
- 401: Invalid credentials
- 403: Account not active

Login creates a Flask session cookie.

## 5. Current User

GET /api/me

Requires authentication.

Success: HTTP 200

{
  "user": {
    "user_id": 1,
    "first_name": "Alex",
    "last_name": "Smith",
    "email": "alex@example.com",
    "account_type": "volunteer"
  }
}

Error:
- 401: Not logged in or invalid session

## 6. Logout

POST /api/logout

Requires authentication and CSRF token.

Success: HTTP 200

{
  "message": "Logged out successfully"
}

## 7. Task Permissions

GET /api/tasks/permissions

Available to help_seeker and both accounts.

Success: HTTP 200

{
  "message": "You have permission to create tasks",
  "user_id": 1
}

## 8. Volunteer Permissions

GET /api/volunteer/permissions

Available to volunteer and both accounts.

Success: HTTP 200

{
  "message": "You have permission to apply for tasks",
  "user_id": 2
}

## 9. Browse Open Tasks

GET /api/tasks

Returns the list of open tasks.

The exact response fields should be checked against
backend/app.py before implementing frontend parsing.

## 10. Create a Task

POST /api/tasks

Requires help_seeker or both account.

Request:

{
  "title": "Help with shopping",
  "description": "Collect groceries from a local shop.",
  "category_id": 1,
  "delivery_mode": "in_person",
  "location_text": "Stratford",
  "estimated_minutes": 30,
  "deadline_at": "2030-12-01 15:00:00"
}

Required:
- title
- description
- category_id
- delivery_mode
- estimated_minutes

For in_person tasks, location_text is also required.

delivery_mode:
- in_person
- remote

estimated_minutes:
- Integer between 15 and 60

deadline_at:
- Optional
- Must be in the future
- ISO-format datetime without timezone information

category_id:
- Must reference an existing category in the database

Success: HTTP 201

{
  "message": "Task created successfully",
  "task_id": 1
}

Possible errors:
- 400: Invalid task details or category
- 401: Not logged in
- 403: Insufficient permissions

## 11. Apply for a Task

POST /api/tasks/{task_id}/apply

Requires volunteer or both account.

No JSON body required.

Success: HTTP 201

{
  "message": "Application submitted successfully",
  "application_id": 1,
  "task_id": 1,
  "status": "pending"
}

Possible errors:
- 401: Not logged in
- 403: Insufficient permissions or own task
- 404: Task not found
- 409: Duplicate application, unavailable task,
       or expired deadline

## 12. Accept or Reject an Application

PATCH /api/applications/{application_id}/decision

Requires the help seeker who created the task.

Accept:

{
  "decision": "accepted"
}

Reject:

{
  "decision": "rejected"
}

Success: HTTP 200

{
  "message": "Application reviewed successfully",
  "application_id": 1,
  "status": "accepted"
}

When an application is accepted:
- Task status changes from open to filled
- The selected application becomes accepted
- Other pending applications are rejected

Only one volunteer can be accepted per task.

Possible errors:
- 400: Invalid decision
- 401: Not logged in
- 403: Not authorised
- 404: Application or task not found
- 409: Already reviewed or invalid task status

## 13. Confirm Task Completion

PATCH /api/tasks/{task_id}/complete

Requires the task creator or accepted volunteer.

No JSON body required.

The task must be filled before confirmation.

First confirmation:

{
  "message": "Completion confirmed; waiting for the other person",
  "task_id": 1,
  "status": "filled",
  "volunteer_confirmed": true,
  "help_seeker_confirmed": false
}

After both confirm:

{
  "message": "Task completed successfully",
  "task_id": 1,
  "status": "completed",
  "volunteer_confirmed": true,
  "help_seeker_confirmed": true
}

The order of confirmation can be reversed.

Possible errors:
- 401: Not logged in
- 403: Not authorised
- 404: Task not found
- 409: Invalid task status, duplicate confirmation,
       or already completed

## 14. Task Status Workflow

open
  |
  | Volunteer applies
  v
Application: pending
  |
  | Help seeker accepts
  v
Task: filled
Application: accepted
  |
  | Volunteer and help seeker both confirm
  v
Task: completed
Application: completed

## 15. Frontend Integration Notes

- Use account_type rather than role.
- Preserve the Flask session cookie after login.
- Include CSRF tokens for modifying requests.
- Handle HTTP errors using the JSON error field.
- Display task status based on API responses.
- Do not store MySQL credentials in frontend code.
- Do not assume a task is completed after only one
  confirmation.
- Use category IDs that exist in the MySQL database.

## 16. Current V1 Limitations

The following features are not yet implemented:
- Email/account verification workflow
- Reviews and ratings
- Messaging
- Notifications
- Public task-category listing endpoint
- Task-application listing endpoints

The frontend should not depend on these features until
the backend endpoints have been implemented and tested.
