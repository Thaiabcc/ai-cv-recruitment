-- Add public Vietnam adapters after week-4.sql; safe to run again, preserves enabled preferences.
USE ai_cv_recruitment;
INSERT INTO recruitment_sources (name, domain, enabled)
VALUES ('CareerViet', 'careerviet.vn', TRUE), ('TopDev', 'topdev.vn', TRUE),
       ('VietnamWorks (chưa tích hợp)', 'www.vietnamworks.com', FALSE)
ON DUPLICATE KEY UPDATE name = VALUES(name);
