CREATE TABLE users (
    user_id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(256) NOT NULL,
    email VARCHAR(200) NOT NULL,
    password VARCHAR(64) NOT NULL,
    signature TINYTEXT DEFAULT NULL,

    PRIMARY KEY (user_id),
    UNIQUE KEY users_email_uk (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE sections (
    section_id INT NOT NULL AUTO_INCREMENT,
    title VARCHAR(256) NOT NULL,
    description TINYTEXT DEFAULT NULL,

    PRIMARY KEY (section_id),
    UNIQUE KEY title_uk (title)
) ENGINE InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE topics (
    topic_id INT NOT NULL AUTO_INCREMENT,
    section_id INT NOT NULL,
    title VARCHAR(256) NOT NULL,

    PRIMARY KEY (topic_id),
    INDEX section_id_ik (section_id),
    UNIQUE KEY section_id_title_uk (section_id, title),
    FOREIGN KEY section_id_fk (section_id)
        REFERENCES sections(section_id) ON DELETE CASCADE
) ENGINE InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE posts (
    post_id INT NOT NULL AUTO_INCREMENT,
    topic_id INT NOT NULL,
    parent VARCHAR(10) DEFAULT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INT NOT NULL,
    hexdigest VARCHAR(10) NOT NULL,
    body TINYTEXT NOT NULL,

    PRIMARY KEY (post_id),
    INDEX topic_id_ik (topic_id),
    FOREIGN KEY topic_id_fk (topic_id)
        REFERENCES topics(topic_id) ON DELETE CASCADE,
    INDEX parent_ik (parent),
    FOREIGN KEY parent_fk (parent)
        REFERENCES posts(hexdigest) ON DELETE CASCADE,
    INDEX user_id_ik (user_id),
    FOREIGN KEY user_id_fk (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX hexdigest_ik (hexdigest)
) ENGINE InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;


substring(sha2(post_id, '256'), 1, 10)


INSERT INTO users (name, email, password)
    VALUES ("Admin", "admin@poleom", "");
INSERT INTO sections (title) VALUES ("root");
