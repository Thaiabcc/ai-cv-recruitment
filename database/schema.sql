-- Week 1 design. Apply manually only to a new development database.
-- Requires MySQL 8.0.16+ for enforced CHECK constraints.
CREATE DATABASE IF NOT EXISTS ai_cv_recruitment CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_cv_recruitment;
CREATE TABLE users (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 email VARCHAR(254) NOT NULL UNIQUE,
 password_hash VARCHAR(255) NOT NULL,
 role ENUM('candidate','admin') NOT NULL DEFAULT 'candidate',
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE profiles (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 user_id BIGINT UNSIGNED NOT NULL UNIQUE,
 full_name VARCHAR(200) NOT NULL,
 contact JSON,
 education JSON,
 skills JSON,
 experience JSON,
 projects JSON,
 preferences JSON,
 updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE cvs (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 user_id BIGINT UNSIGNED NOT NULL,
 profile_snapshot JSON NOT NULL,
 content JSON NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE recruitment_sources (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(100) NOT NULL,
 domain VARCHAR(253) NOT NULL UNIQUE,
 enabled BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE jobs (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 source_id BIGINT UNSIGNED NOT NULL,
 url TEXT NOT NULL,
 url_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
 title VARCHAR(255) NOT NULL,
 company VARCHAR(255),
 location VARCHAR(255),
 salary_text VARCHAR(255),
 description MEDIUMTEXT NOT NULL,
 requirements JSON,
 expires_at DATETIME,
 fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (source_id) REFERENCES recruitment_sources(id)
);
CREATE TABLE search_runs (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 user_id BIGINT UNSIGNED NOT NULL,
 cv_id BIGINT UNSIGNED NOT NULL,
 status ENUM('queued','running','completed','partial','failed') NOT NULL DEFAULT 'queued',
 query_snapshot JSON NOT NULL,
 source_errors JSON,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 finished_at DATETIME,
 FOREIGN KEY (user_id) REFERENCES users(id),
 FOREIGN KEY (cv_id) REFERENCES cvs(id)
);
CREATE TABLE evaluations (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 search_run_id BIGINT UNSIGNED NOT NULL,
 job_id BIGINT UNSIGNED NOT NULL,
 score DECIMAL(5,2) NOT NULL,
 rubric_version VARCHAR(50) NOT NULL,
 matched JSON NOT NULL,
 missing JSON NOT NULL,
 unknown_criteria JSON NOT NULL,
 explanation TEXT NOT NULL,
 suggestions JSON NOT NULL,
 evaluated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT score_range CHECK (score >= 0 AND score <= 100),
 UNIQUE KEY unique_run_job (search_run_id, job_id),
 INDEX ranked_results (search_run_id, score),
 FOREIGN KEY (search_run_id) REFERENCES search_runs(id),
 FOREIGN KEY (job_id) REFERENCES jobs(id)
);
-- Source is a candidate only; no live adapter implemented or enabled.
INSERT INTO recruitment_sources (name, domain, enabled) VALUES ('TopCV', 'www.topcv.vn', FALSE);
