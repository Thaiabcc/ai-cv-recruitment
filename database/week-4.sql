-- Apply once after week 3. No candidate data is removed.
USE ai_cv_recruitment;
ALTER TABLE search_runs ADD COLUMN started_at DATETIME NULL;
CREATE INDEX search_queue ON search_runs (status, id);
CREATE TABLE search_run_jobs (
 search_run_id BIGINT UNSIGNED NOT NULL,
 job_id BIGINT UNSIGNED NOT NULL,
 snapshot JSON NOT NULL,
 PRIMARY KEY (search_run_id, job_id),
 FOREIGN KEY (search_run_id) REFERENCES search_runs(id),
 FOREIGN KEY (job_id) REFERENCES jobs(id)
);
INSERT INTO recruitment_sources (name, domain, enabled)
VALUES ('Arbeitnow (Germany / international)', 'www.arbeitnow.com', TRUE)
ON DUPLICATE KEY UPDATE name = VALUES(name);
