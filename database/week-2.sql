-- Additive migration: preserves all existing tables and data. UTC timestamps.
USE ai_cv_recruitment;
CREATE TABLE IF NOT EXISTS auth_sessions (
 token_hash VARCHAR(64) PRIMARY KEY,
 user_id BIGINT UNSIGNED NOT NULL,
 expires_at DATETIME NOT NULL,
 INDEX ix_auth_sessions_user_id (user_id),
 INDEX ix_auth_sessions_expires_at (expires_at),
 FOREIGN KEY (user_id) REFERENCES users(id)
);
