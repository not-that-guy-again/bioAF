-- bioAF Audit Log Role Enforcement (ADR-009)
-- Run this after initial schema migration

-- Create the application role if it doesn't exist
DO $$ BEGIN
    CREATE ROLE bioaf_app LOGIN PASSWORD 'placeholder';
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- Grant normal permissions on all tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bioaf_app;

-- Override: audit_log gets INSERT + SELECT only (ADR-009)
REVOKE UPDATE, DELETE ON audit_log FROM bioaf_app;
REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;

-- Grant sequence usage for auto-increment
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bioaf_app;
