-- Apply once after week-4-vietnam.sql. Existing search/CV data and legacy evaluations are preserved.
USE ai_cv_recruitment;
CREATE TABLE evaluation_batches (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 user_id BIGINT UNSIGNED NOT NULL,
 search_run_id BIGINT UNSIGNED NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'queued',
 model VARCHAR(200) NOT NULL,
 rubric_version VARCHAR(50) NOT NULL,
 total_jobs INT NOT NULL,
 worker_token VARCHAR(36),
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 started_at DATETIME, heartbeat_at DATETIME, finished_at DATETIME,
 INDEX (user_id), INDEX (search_run_id), INDEX (status),
 FOREIGN KEY (user_id) REFERENCES users(id),
 FOREIGN KEY (search_run_id) REFERENCES search_runs(id)
);
ALTER TABLE evaluations
 ADD COLUMN batch_id BIGINT UNSIGNED NULL,
 ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'completed',
 ADD COLUMN attempts INT NOT NULL DEFAULT 0,
 ADD COLUMN information_coverage DECIMAL(5,2) NULL,
 ADD COLUMN details JSON NULL,
 MODIFY COLUMN score DECIMAL(5,2) NULL,
 DROP INDEX unique_run_job,
 ADD UNIQUE KEY uq_evaluation_batch_job (batch_id, job_id),
 ADD INDEX (batch_id),
 ADD CONSTRAINT fk_evaluations_batch FOREIGN KEY (batch_id) REFERENCES evaluation_batches(id);
