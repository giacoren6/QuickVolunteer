-- ============================================
-- QUICKVOLUNTEER - MYSQL DEMO DATA
-- CPU4106 Group Project
-- ============================================
--
-- Demo data is maintained by:
-- database/seeds/seed_demo.py
--
-- To load fictional users, tasks and applications:
--
--     python database/seeds/seed_demo.py
--
-- This file is intentionally read-only.
-- It contains no INSERT, UPDATE or DELETE statements.
--
-- View existing task categories:
SELECT category_id, category_name
FROM task_categories
ORDER BY category_id;
