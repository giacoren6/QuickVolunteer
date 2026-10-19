
-- QuickVolunteer V1 - MySQL 8
-- Based on Database_Normalisation.xlsx

CREATE TABLE users (
    user_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(30),
    postcode VARCHAR(10),
    preferred_language VARCHAR(10),
    account_type ENUM(
        'help_seeker', 'volunteer', 'both', 'admin'
    ) NOT NULL,
    skills_summary TEXT,
    availability_notes VARCHAR(255),
    account_status ENUM(
        'pending', 'active', 'suspended'
    ) NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE user_verifications (
    verification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    reviewed_by BIGINT UNSIGNED,
    verification_type ENUM('account', 'dbs') NOT NULL,
    status ENUM('pending', 'approved', 'rejected')
        NOT NULL DEFAULT 'pending',
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE task_categories (
    category_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(80) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE tasks (
    task_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    creator_id BIGINT UNSIGNED NOT NULL,
    category_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(160) NOT NULL,
    description TEXT NOT NULL,
    location_text VARCHAR(160),
    delivery_mode ENUM('in_person', 'remote') NOT NULL,
    estimated_minutes SMALLINT UNSIGNED NOT NULL,
    deadline_at DATETIME,
    status ENUM('open', 'filled', 'completed', 'closed')
        NOT NULL DEFAULT 'open',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_task_duration
        CHECK (estimated_minutes BETWEEN 15 AND 60),
    FOREIGN KEY (creator_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (category_id) REFERENCES task_categories(category_id)
        ON DELETE RESTRICT,
    INDEX idx_tasks_creator (creator_id),
    INDEX idx_tasks_category_status (category_id, status)
) ENGINE=InnoDB;

CREATE TABLE task_applications (
    application_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT UNSIGNED NOT NULL,
    volunteer_id BIGINT UNSIGNED NOT NULL,
    status ENUM('pending', 'accepted', 'rejected', 'completed')
        NOT NULL DEFAULT 'pending',
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accepted_at DATETIME,
    volunteer_completed_at DATETIME,
    help_seeker_completed_at DATETIME,
    UNIQUE KEY uq_task_volunteer (task_id, volunteer_id),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        ON DELETE CASCADE,
    FOREIGN KEY (volunteer_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,
    INDEX idx_applications_volunteer (volunteer_id)
) ENGINE=InnoDB;

CREATE TABLE reports (
    report_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    reporter_id BIGINT UNSIGNED NOT NULL,
    reported_user_id BIGINT UNSIGNED,
    task_id BIGINT UNSIGNED,
    reviewed_by BIGINT UNSIGNED,
    reason TEXT NOT NULL,
    status ENUM('open', 'reviewing', 'closed')
        NOT NULL DEFAULT 'open',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME,
    
        FOREIGN KEY (reporter_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_reports_reported_user
        FOREIGN KEY (reported_user_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_reports_task
        FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
        ON DELETE SET NULL,

    CONSTRAINT chk_reports_one_target
        CHECK (
            (reported_user_id IS NOT NULL AND task_id IS NULL)
            OR
            (reported_user_id IS NULL AND task_id IS NOT NULL)
        ),

    INDEX idx_reports_status (status)
) ENGINE=InnoDB;
