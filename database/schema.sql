
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
    ) NOT NULL DEFAULT 'active',
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

CREATE TABLE reviews (
    review_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    application_id BIGINT UNSIGNED NOT NULL,
    reviewer_id BIGINT UNSIGNED NOT NULL,
    reviewed_user_id BIGINT UNSIGNED NOT NULL,
    rating TINYINT UNSIGNED NOT NULL,
    comment TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    moderation_status ENUM('visible', 'hidden')
        NOT NULL DEFAULT 'visible',
    moderated_by BIGINT UNSIGNED,
    moderated_at DATETIME,
    moderation_reason TEXT,

    CONSTRAINT chk_review_rating CHECK (rating BETWEEN 1 AND 5),
    UNIQUE KEY uq_review_application_reviewer (application_id, reviewer_id),

    FOREIGN KEY (application_id) REFERENCES task_applications(application_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (reviewer_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (reviewed_user_id) REFERENCES users(user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (moderated_by) REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE conversations (
    conversation_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE conversation_members (
    conversation_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_read_at DATETIME,

    PRIMARY KEY (conversation_id, user_id),

    FOREIGN KEY (conversation_id)
        REFERENCES conversations(conversation_id)
        ON DELETE CASCADE,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE messages (
    message_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED NOT NULL,
    sender_id BIGINT UNSIGNED NOT NULL,
    content TEXT NOT NULL,
    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (conversation_id)
        REFERENCES conversations(conversation_id)
        ON DELETE CASCADE,

    FOREIGN KEY (sender_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE notifications (
    notification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    task_application_id BIGINT UNSIGNED,
    title VARCHAR(120) NOT NULL,
    content TEXT NOT NULL,
    read_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    FOREIGN KEY (task_application_id)
        REFERENCES task_applications(application_id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE audit_logs (
    audit_log_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    actor_id BIGINT UNSIGNED,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT UNSIGNED,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (actor_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB;
