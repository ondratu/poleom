-- Upgrade from 0.1.0 to 0.2.0: users of an external authentication plugin.
ALTER TABLE users
    MODIFY password CHAR(64) DEFAULT NULL,
    ADD COLUMN auth_sub VARCHAR(255) DEFAULT NULL,
    ADD UNIQUE KEY auth_sub_uk (auth_sub);
