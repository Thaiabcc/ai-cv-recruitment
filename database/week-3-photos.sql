-- Additive, re-runnable migration. Images are immutable assets owned by users.
USE ai_cv_recruitment;
CREATE TABLE IF NOT EXISTS cv_photos (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 user_id BIGINT UNSIGNED NOT NULL,
 data MEDIUMBLOB NOT NULL,
 sha256 VARCHAR(64) NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX ix_cv_photos_user_id (user_id),
 CONSTRAINT uq_cv_photo_owner_hash UNIQUE (user_id, sha256),
 FOREIGN KEY (user_id) REFERENCES users(id)
);
