
-- =============================================
-- QUICKVOLUNTEER DATABASE
-- Version 1 - SQLite
-- CPU4106 Group Project
-- =============================================

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;


-- =============================================
-- TABLE 1: USERS
-- =============================================

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,

    first_name TEXT NOT NULL
        CHECK(length(trim(first_name)) BETWEEN 1 AND 50),

    last_name TEXT NOT NULL
        CHECK(length(trim(last_name)) BETWEEN 1 AND 50),

    email TEXT NOT NULL COLLATE NOCASE UNIQUE
        CHECK(email LIKE '%_@_%._%' AND length(email) <= 254),

    password_hash TEXT NOT NULL,

    phone TEXT
        CHECK(phone IS NULL OR length(phone) <= 30),

    postcode TEXT
        CHECK(postcode IS NULL OR length(postcode) <= 8),

    preferred_language TEXT DEFAULT 'en',

    account_status TEXT NOT NULL DEFAULT 'pending'
        CHECK(account_status IN ('pending', 'active', 'suspended')),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- =============================================
-- TABLE 2: ROLES
-- =============================================

CREATE TABLE IF NOT EXISTS roles (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,

    role_name TEXT NOT NULL UNIQUE
        CHECK(length(role_name) BETWEEN 1 AND 30)
);


-- =============================================
-- TABLE 3: USER ROLES
-- =============================================

CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,

    role_id INTEGER NOT NULL
        REFERENCES roles(role_id) ON DELETE RESTRICT,

    PRIMARY KEY (user_id, role_id)
);


-- =============================================
-- TABLE 4: TASK CATEGORIES
-- =============================================

CREATE TABLE IF NOT EXISTS task_categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,

    category_name TEXT NOT NULL UNIQUE
        CHECK(length(category_name) BETWEEN 1 AND 80)
);


-- =============================================
-- TABLE 5: TASKS
-- =============================================

CREATE TABLE IF NOT EXISTS tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,

    creator_id INTEGER NOT NULL
        REFERENCES users(user_id) ON DELETE RESTRICT,

    category_id INTEGER NOT NULL
        REFERENCES task_categories(category_id) ON DELETE RESTRICT,

    title TEXT NOT NULL
        CHECK(length(trim(title)) BETWEEN 1 AND 160),

    description TEXT NOT NULL,

    location_text TEXT,

    delivery_mode TEXT NOT NULL
        CHECK(delivery_mode IN ('in_person', 'remote')),

    contact_method TEXT NOT NULL,

    required_device TEXT,

    estimated_minutes INTEGER NOT NULL
        CHECK(estimated_minutes BETWEEN 15 AND 60),

    deadline_at TEXT NOT NULL,

    volunteer_capacity INTEGER NOT NULL DEFAULT 1
        CHECK(volunteer_capacity >= 1),

    status TEXT NOT NULL DEFAULT 'open'
        CHECK(status IN ('open', 'filled', 'completed', 'closed')),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK(datetime(deadline_at) IS NOT NULL),

    CHECK(datetime(deadline_at) > datetime(created_at))
);


-- =============================================
-- TABLE 6: TASK APPLICATIONS
-- =============================================

CREATE TABLE IF NOT EXISTS task_applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,

    task_id INTEGER NOT NULL
        REFERENCES tasks(task_id) ON DELETE CASCADE,

    volunteer_id INTEGER NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,

    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN (
            'pending',
            'accepted',
            'rejected',
            'completed'
        )),

    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    accepted_at TEXT,

    completed_at TEXT,

    UNIQUE(task_id, volunteer_id),

    CHECK(
        accepted_at IS NULL
        OR datetime(accepted_at) IS NOT NULL
    ),

    CHECK(
        completed_at IS NULL
        OR datetime(completed_at) IS NOT NULL
    )
);


-- =============================================
-- TABLE 7: USER VERIFICATIONS
-- =============================================

CREATE TABLE IF NOT EXISTS user_verifications (
    verification_id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,

    reviewed_by INTEGER
        REFERENCES users(user_id) ON DELETE SET NULL,

    verification_type TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'approved', 'rejected')),

    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    reviewed_at TEXT
);


-- =============================================
-- INDEXES - IMPROVE QUERY PERFORMANCE
-- =============================================

CREATE INDEX IF NOT EXISTS idx_tasks_creator
ON tasks(creator_id);

CREATE INDEX IF NOT EXISTS idx_tasks_category_status
ON tasks(category_id, status);

CREATE INDEX IF NOT EXISTS idx_applications_volunteer
ON task_applications(volunteer_id);

CREATE INDEX IF NOT EXISTS idx_verifications_user
ON user_verifications(user_id);
