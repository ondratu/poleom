CREATE TABLE languages (
    lang CHAR(3) NOT NULL, -- ISO_639-1 / ISO_639-2
    locale CHAR(6) NOT NULL, -- en_US
    language VARCHAR(40) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE KEY lang_uk (lang)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE users (
    user_id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(200) NOT NULL,
    password CHAR(64) NOT NULL,
    signature VARCHAR(255) DEFAULT NULL,
    terms TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state ENUM("ACTIVE", "REGISTERED", "BANNED", "DELETED") NOT NULL,
    role ENUM("MEMBER", "MODERATOR", "ADMIN") NOT NULL,
    data JSON NOT NULL,

    PRIMARY KEY user_id_pk (user_id),
    UNIQUE KEY email_uk (email)
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
    lang CHAR(3) NOT NULL,
    description VARCHAR(255) DEFAULT NULL,
    state ENUM("OPEN", "LOCKED", "ARCHIVED") NOT NULL DEFAULT "OPEN",
    weight INT NOT NULL,
    private BOOLEAN NOT NULL DEFAULT FALSE,

    PRIMARY KEY sections_id_pk (section_id),
    UNIQUE KEY path_lang_uk (path, lang),
    INDEX lang_ik (lang),
    FOREIGN KEY sections_lang_fk (lang)
        REFERENCES languages(lang)
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

    PRIMARY KEY toupic_id_pk (topic_id),
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

    PRIMARY KEY post_id_pk (post_id),
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
    data JSON NOT NULL,

    INDEX post_id_ik (post_id),
    FOREIGN KEY attachements_posts_id_fk (post_id)
        REFERENCES posts(post_id) ON DELETE CASCADE,
    UNIQUE KEY hexdigest_uk (hexdigest)
) ENGINE InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci;

-- default data
INSERT INTO users (name, email, password, state, role, data) VALUES
    ("Admin", "root@localhost", "", "ACTIVE", "ADMIN", "{}");

INSERT INTO languages (lang, locale, language) VALUES
    ("en", "en_US", "English"),
    ("cs", "cs_CZ", "Česky");

INSERT INTO sections (title, lang, path, description, state, weight) VALUES
    ("Announcements", "en", "announcements", "Updates from maintainers", "LOCKED", 0),
    ("Oznámení", "cs", "oznameni", "Aktualizace od správců", "LOCKED", 0);

INSERT INTO sections (title, lang, path, description, weight) VALUES
    ("General", "en", "general", "Chat about anything and everything here", 0),
    ("Ideas", "en", "ideas", "Share ideas for new features", 0),
    ("Q&A", "en", "q-a", "Ask the community for help", 0),
    ("Show and tell", "en", "show-and-tell", "Show off something you've made", 0),

    ("Všeobecné", "cs", "vseobecne", "Diskuze o čemkoli", 0),
    ("Nápady", "cs", "napady", "Nápady a podměty", 0),
    ("Otázky a Odpovědi", "cs", "otazky-a-odpovedi", "Ptejte se komunity", 0),
    ("Pochlub se", "cs", "pochlub-se", "Ukaž, co jsi vytvořil", 0);
UPDATE sections SET weight=section_id;
