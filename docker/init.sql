-- txsftp database initialization
-- Run automatically by PostgreSQL Docker image on first start.
-- All DDL uses IF NOT EXISTS so this script is safe to re-run.

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

CREATE TABLE IF NOT EXISTS sftp_user (
    id              bigserial PRIMARY KEY,
    username        character varying(255) NOT NULL,
    password        character varying(255),
    gpg_public_key  text,
    ssh_public_key  text,
    home_directory  character varying(255) NOT NULL,
    last_login      timestamp without time zone,
    last_logout     timestamp without time zone
);

CREATE UNIQUE INDEX IF NOT EXISTS sftp_user_username_key
    ON sftp_user (username);

CREATE INDEX IF NOT EXISTS sftp_user_username_password_key
    ON sftp_user (username, password);
