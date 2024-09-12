CREATE TABLE users (
    user_id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(200) NOT NULL,
    password CHAR(64) NOT NULL,
    signature VARCHAR(255) DEFAULT NULL,
    terms TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state ENUM("ACTIVE", "REGISTERED", "BANNED", "DELETED") NOT NULL,
    role ENUM("MEMBER", "MODERATOR", "ADMIN") NOT NULL,
    data JSON NOT NULL DEFAULT "{}",

    PRIMARY KEY (user_id),
    UNIQUE KEY users_email_uk (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE change_request (
    user_id INT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accepted TIMESTAMP DEFAULT NULL,
    hexdigest CHAR(64) NOT NULL,
    state ENUM("REGISTER", "PASSWORD", "INFO_CHANGED", "INFO_BANNED",
               "INFO_ACTIVATED", "INFO_DELETED") NOT NULL,
    data JSON NOT NULL,

    INDEX user_id_ik (user_id),
    FOREIGN KEY change_request_user_id_fk (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY hexdigest_uk (hexdigest)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE sections (
    section_id INT NOT NULL AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL,
    description VARCHAR(255) DEFAULT NULL,
    state ENUM("OPEN", "LOCKED", "ARCHIVED") NOT NULL DEFAULT "OPEN",
    weight INT NOT NULL,
    private BOOLEAN NOT NULL DEFAULT FALSE,

    PRIMARY KEY (section_id),
    UNIQUE KEY path_uk (path)
) ENGINE InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE sections_users (
    section_id INT NOT NULL,
    user_id INT NOT NULL,

    UNIQUE KEY section_id_user_id_uk (section_id, user_id),
    FOREIGN KEY sections_users_section_id_fk (section_id)
        REFERENCES sections(section_id) ON DELETE CASCADE,
    FOREIGN KEY sections_users_user_id_fk (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE topics (
    topic_id INT NOT NULL AUTO_INCREMENT,
    section_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL,
    state ENUM("OPEN", "LOCKED", "ARCHIVED") NOT NULL DEFAULT "OPEN",
    pinned BOOLEAN NOT NULL DEFAULT FALSE,

    PRIMARY KEY (topic_id),
    INDEX section_id_ik (section_id),
    UNIQUE KEY section_id_path_uk (section_id, path),
    FOREIGN KEY topics_section_id_fk (section_id)
        REFERENCES sections(section_id) ON DELETE CASCADE
) ENGINE InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE posts (
    post_id INT NOT NULL AUTO_INCREMENT,
    topic_id INT NOT NULL,
    parent CHAR(64) DEFAULT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT NULL,
    user_id INT NOT NULL,
    hexdigest CHAR(64) NOT NULL,
    state ENUM("VISIBLE", "ARCHIVED") NOT NULL DEFAULT "VISIBLE",
    body TEXT NOT NULL, -- 65535 chars

    PRIMARY KEY (post_id),
    INDEX topic_id_ik (topic_id),
    FOREIGN KEY posts_topic_id_fk (topic_id)
        REFERENCES topics(topic_id) ON DELETE CASCADE,
    INDEX parent_ik (parent),
    FOREIGN KEY posts_parent_fk (parent)
        REFERENCES posts(hexdigest) ON DELETE CASCADE,
    INDEX user_id_ik (user_id),
    FOREIGN KEY posts_user_id_fk (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY hexdigest_uk (hexdigest)
) ENGINE InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


CREATE TABLE attachments (
    post_id INT NOT NULL,
    uploaded TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    mime_type VARCHAR(255) NOT NULL,
    file_name VARCHAR(1024) NOT NULL,
    hexdigest CHAR(64) NOT NULL,
    data JSON NOT NULL DEFAULT "{}",

    INDEX post_id_ik (post_id),
    FOREIGN KEY attachements_posts_id_fk (post_id)
        REFERENCES posts(post_id) ON DELETE CASCADE,
    UNIQUE KEY hexdigest_uk (hexdigest)
) ENGINE InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

-- default data
INSERT INTO users (name, email, password, state, role)
    VALUES ("Admin", "root@localhost", "", "ACTIVE", "ADMIN");

INSERT INTO sections (title, path, description, state, weight) VALUES
    ("Announcements", "announcements", "Updates from maintainers", "LOCKED", 1);
INSERT INTO sections (title, path, description, weight) VALUES
    ("General", "general", "Chat about anything and everything here", 2),
    ("Ideas", "ideas", "Share ideas for new features", 3),
    ("Q&A", "q-a", "Ask the community for help", 4),
    ("Show and tell", "show-and-tell", "Show off something you've made", 5);
