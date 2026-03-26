-- =============================================================================
-- Superset Database Initialization Script
-- =============================================================================
-- This script initializes the database for Apache Superset metadata

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Superset will create its own tables automatically when initialized
-- This script ensures the database is ready and has proper permissions

-- Create a simple health check table
CREATE TABLE IF NOT EXISTS superset_health (
    id SERIAL PRIMARY KEY,
    check_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'healthy'
);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
