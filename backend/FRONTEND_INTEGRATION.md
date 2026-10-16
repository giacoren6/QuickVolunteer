
# QuickVolunteer — Frontend Integration Guide

## Technology

- Frontend: HTML, CSS and JavaScript
- Backend: Python Flask
- Database: MySQL 8.0
- Authentication: Flask sessions
- Security: CSRF protection

## Running the application

Flask serves the HTML pages and API from the same origin.

Frontend files:
- templates/ — HTML pages
- static/css/ — CSS files
- static/js/ — JavaScript files

Use relative URLs when calling the backend.

## 1. Browse available tasks

GET /api/tasks

Example JavaScript:

```javascript
const response = await fetch("/api/tasks");
const tasks = await response.json();

console.log(tasks);
```

The response is a JSON array of open tasks.

## 2. Get a CSRF token

GET /api/csrf-token

```javascript
async function getCsrfToken() {
    const response = await fetch("/api/csrf-token");
    const data = await response.json();
    return data.csrf_token;
}
```

Send this token in the X-CSRFToken header for
POST and PATCH requests.

## 3. Register a user

POST /api/register

Required JSON fields:
- first_name
- last_name
- email
- password (minimum 12 characters)
- account_type: volunteer, help_seeker or both

```javascript
const csrfToken = await getCsrfToken();

const response = await fetch("/api/register", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
    },
    body: JSON.stringify({
        first_name: "Alex",
        last_name: "Smith",
        email: "alex@example.com",
        password: "ExamplePassword123!",
        account_type: "volunteer"
    })
});

const result = await response.json();
```

## 4. Log in

POST /api/login

Required fields:
- email
- password

```javascript
const csrfToken = await getCsrfToken();

const response = await fetch("/api/login", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
    },
    body: JSON.stringify({
        email: "alex@example.com",
        password: "ExamplePassword123!"
    })
});

const result = await response.json();
```

Flask stores the logged-in user in a session cookie.

## 5. Check the logged-in user

GET /api/me

```javascript
const response = await fetch("/api/me");
const user = await response.json();

console.log(user);
```

## 6. Help seeker dashboard

GET /api/my-tasks

Returns tasks created by the logged-in help seeker.

## 7. Volunteer dashboard

GET /api/my-applications

Returns applications submitted by the logged-in volunteer.



## Task Categories

GET /api/categories

Authentication: Not required.

Returns all available task categories from MySQL,
ordered alphabetically by category name.

Example response:

[
  {
    "category_id": 1,
    "category_name": "Community Support"
  },
  {
    "category_id": 2,
    "category_name": "Shopping"
  }
]

JavaScript example:

```javascript
async function loadCategories() {
    const response = await fetch("/api/categories");

    if (!response.ok) {
        throw new Error("Unable to load categories");
    }

    return await response.json();
}

const categories = await loadCategories();
console.log(categories);
```

Use the selected category_id when sending
POST /api/tasks.

The actual categories depend on the records
stored in the MySQL database.


## 8. Create a task

POST /api/tasks

Requires help_seeker or both account.

Required fields:
- title
- description
- category_id
- delivery_mode: remote or in_person
- estimated_minutes: 15–60
- location_text: required for in_person

Include the CSRF token.

## 9. Apply for a task

POST /api/tasks/{task_id}/apply

Requires volunteer or both account.

No JSON request body required.

Include the CSRF token.

## 10. Review applications

GET /api/tasks/{task_id}/applications

Only the task creator can view these applications.

## 11. Accept or reject applications

PATCH /api/applications/{application_id}/decision

JSON body:

{
  "decision": "accepted"
}

Or:

{
  "decision": "rejected"
}

Include the CSRF token.

## 12. Confirm task completion

PATCH /api/tasks/{task_id}/complete

The accepted volunteer and task creator must both
confirm completion.

Include the CSRF token.

## Important integration notes

1. Use relative API URLs, such as /api/tasks.
2. Serve HTML through Flask, not by opening files directly.
3. Never place MySQL passwords in JavaScript.
4. Never store user passwords in localStorage.
5. POST and PATCH requests require X-CSRFToken.
6. Display backend error messages appropriately.
8. See backend/API_DOCUMENTATION.md for API details.

## 13. Cancel a task

Endpoint: PATCH /api/tasks/<task_id>/cancel

Authentication: Required.
Allowed account types: help_seeker and both.
Only the task creator can cancel their task.

A task can be cancelled when its status is:
- open
- filled

Requirements:
- Use the authenticated Flask session cookie.
- Include the X-CSRFToken header.
- No JSON request body is required.

Successful response: HTTP 200

{
  "message": "Task cancelled successfully",
  "task_id": 4,
  "status": "closed"
}

Frontend instructions:
- Show a Cancel Task button for the creator's open or filled tasks.
- Ask the user to confirm before cancelling.
- Send a PATCH request to the cancellation endpoint.
- Refresh the dashboard after successful cancellation.
- Hide completion actions when task_status is closed.
- Display API error messages when cancellation fails.

Pending applications are rejected automatically.
Previously accepted applications remain in the database
for history, but their associated task becomes closed.

See backend/API_DOCUMENTATION.md for additional details.
