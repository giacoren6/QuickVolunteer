
-- ============================================
-- QUICKVOLUNTEER - SQL TEST QUERIES
-- CPU4106 Group Project
-- ============================================

-- QUERY 1: Display all registered users
SELECT user_id, first_name, last_name, email
FROM users
ORDER BY user_id;


-- QUERY 2: Show users with their roles
SELECT
    u.first_name,
    u.last_name,
    u.email,
    u.account_type AS role_name
FROM users AS u
ORDER BY u.first_name;


-- QUERY 3: Show all available volunteering tasks
SELECT
    t.title,
    c.category_name,
    t.delivery_mode,
    t.estimated_minutes,
    t.location_text
FROM tasks AS t
JOIN task_categories AS c
    ON t.category_id = c.category_id
WHERE t.status = 'open'
ORDER BY t.deadline_at;


-- QUERY 4: Show applications and volunteer names
SELECT
    CONCAT(u.first_name, ' ', u.last_name) AS volunteer,
    t.title AS task,
    a.status AS application_status
FROM task_applications AS a
JOIN users AS u
    ON a.volunteer_id = u.user_id
JOIN tasks AS t
    ON a.task_id = t.task_id
ORDER BY t.title;


-- QUERY 5: Count applications for each task
SELECT
    t.title,
    COUNT(a.application_id) AS total_applications
FROM tasks AS t
LEFT JOIN task_applications AS a
    ON t.task_id = a.task_id
GROUP BY t.task_id, t.title
ORDER BY total_applications DESC;


-- QUERY 6: Find remote tasks lasting 30 minutes
SELECT
    title,
    estimated_minutes,
    status
FROM tasks
WHERE delivery_mode = 'remote'
  AND estimated_minutes = 30
  AND status = 'open';


-- QUERY 7: Show tasks published by each creator
SELECT
    CONCAT(u.first_name, ' ', u.last_name) AS creator,
    t.title,
    t.status
FROM tasks AS t
JOIN users AS u
    ON t.creator_id = u.user_id
ORDER BY creator, t.title;


-- QUERY 8: Count tasks by category
SELECT
    c.category_name,
    COUNT(t.task_id) AS total_tasks
FROM task_categories AS c
LEFT JOIN tasks AS t
    ON c.category_id = t.category_id
GROUP BY c.category_id, c.category_name
ORDER BY total_tasks DESC;


-- QUERY 9: Find pending applications
SELECT
    a.application_id,
    u.first_name,
    t.title,
    a.applied_at
FROM task_applications AS a
JOIN users AS u
    ON a.volunteer_id = u.user_id
JOIN tasks AS t
    ON a.task_id = t.task_id
WHERE a.status = 'pending';


-- QUERY 10: Check database relationships
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE()
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, COLUMN_NAME;
