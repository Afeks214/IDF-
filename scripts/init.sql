-- IDF Database Init with Hebrew UTF-8 Support
SET timezone = 'Asia/Jerusalem';
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Hebrew collation
CREATE COLLATION IF NOT EXISTS hebrew_collation (
    provider = icu,
    locale = 'he-IL-u-kn-true'
);

-- Audit trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- Schema tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version varchar(255) PRIMARY KEY,
    applied_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations (version) 
VALUES ('001_initial_hebrew_setup')
ON CONFLICT DO NOTHING;

-- DB config for Hebrew
ALTER DATABASE idf_testing SET timezone TO 'Asia/Jerusalem';
ALTER DATABASE idf_testing SET default_text_search_config TO 'hebrew';