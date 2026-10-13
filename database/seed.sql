
-- ============================================
-- QUICKVOLUNTEER - SAMPLE DATA
-- Version 1
-- ============================================

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- TABLE 1: ROLES
INSERT OR IGNORE INTO roles (role_name)
VALUES
    ('volunteer'),
    ('help_seeker'),
    ('organisation'),
    ('administrator');

-- TABLE 2: TASK CATEGORIES
INSERT OR IGNORE INTO task_categories (category_name)
VALUES
    ('Shopping'),
    ('Technology Support'),
    ('Education'),
    ('Community Support'),
    ('Environment'),
    ('Accessibility'),
    ('Social Support'),
    ('Other');

COMMIT;

-- Check inserted records
SELECT * FROM roles;
SELECT * FROM task_categories;
