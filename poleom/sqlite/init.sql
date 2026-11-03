CREATE TABLE languages (
    lang CHAR(3) NOT NULL UNIQUE, -- ISO_639-1 / ISO_639-2
    locale CHAR(6) NOT NULL, -- en_US
    language VARCHAR(40) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE users (
    user_id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    password CHAR(64) NOT NULL,
    signature VARCHAR(255) DEFAULT NULL,
    terms TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state TEXT CHECK (state IN ("ACTIVE", "REGISTERED", "BANNED", "DELETED")) NOT NULL,
    role TEXT CHECK (role IN ("MEMBER", "MODERATOR", "ADMIN")) NOT NULL,
    data JSON NOT NULL
);

CREATE TABLE change_request (
    user_id INT NOT NULL REFERENCES users (user_id),
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accepted TIMESTAMP DEFAULT NULL,
    hexdigest CHAR(64) NOT NULL UNIQUE,
    state TEXT CHECK (state IN ("REGISTER", "PASSWORD", "INFO_CHANGED", "INFO_BANNED",
               "INFO_ACTIVATED", "INFO_DELETED")) NOT NULL,
    data JSON NOT NULL
);

CREATE TABLE sections (
    section_id INTEGER NOT NULL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL UNIQUE,
    lang CHAR(3) NOT NULL REFERENCES languages (lang),
    description VARCHAR(255) DEFAULT NULL,
    state TEXT CHECK (state IN ( "OPEN", "LOCKED", "ARCHIVED")) NOT NULL DEFAULT "OPEN",
    weight INT NOT NULL,
    private BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE sections_users (
    section_id INT NOT NULL REFERENCES sections (section_id),
    user_id INT NOT NULL REFERENCES users (user_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS
    sections_users_section_id_user_id_uk
        on sections_users (section_id, user_id);

CREATE TABLE topics (
    topic_id INTEGER NOT NULL PRIMARY KEY,
    section_id INT NOT NULL REFERENCES sections (section_id),
    title VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL,
    state TEXT CHECK (state IN ("OPEN", "LOCKED", "ARCHIVED")) NOT NULL DEFAULT "OPEN",
    pinned BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE UNIQUE INDEX IF NOT EXISTS
    topics_section_id_path_uk
        on topics (section_id, path);

CREATE TABLE posts (
    post_id INTEGER NOT NULL PRIMARY KEY,
    topic_id INT NOT NULL REFERENCES topics (topic_id),
    parent CHAR(64) DEFAULT NULL REFERENCES posts (hexdigest),
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified TIMESTAMP DEFAULT NULL,
    user_id INT NOT NULL REFERENCES users (user_id),
    hexdigest CHAR(64) NOT NULL UNIQUE,
    state TEXT CHECK (state IN ("VISIBLE", "ARCHIVED")) NOT NULL DEFAULT "VISIBLE",
    body TEXT NOT NULL -- 65535 chars
);

CREATE TABLE attachments (
    post_id INT NOT NULL REFERENCES posts(post_id),
    uploaded TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    mime_type VARCHAR(255) NOT NULL,
    file_name VARCHAR(1024) NOT NULL,
    hexdigest CHAR(64) NOT NULL UNIQUE,
    data JSON NOT NULL
);

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
