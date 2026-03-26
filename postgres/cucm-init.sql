-- =============================================================================
-- CUCM Database Initialization Script
-- =============================================================================
-- This script initializes the database for Cisco Unified Communications Manager metrics

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_cucm_metrics_timestamp_server ON cucm_metrics (timestamp DESC, server_name);
CREATE INDEX IF NOT EXISTS idx_cucm_metrics_active_calls ON cucm_metrics (active_calls);
CREATE INDEX IF NOT EXISTS idx_cucm_metrics_cpu_memory ON cucm_metrics (cpu_usage_percent, memory_usage_percent);

-- Create collection jobs table
CREATE TABLE IF NOT EXISTS collection_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL,
    server_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT,
    metrics_collected INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for collection jobs
CREATE INDEX IF NOT EXISTS idx_collection_jobs_status_server ON collection_jobs (status, server_name);
CREATE INDEX IF NOT EXISTS idx_collection_jobs_started_at ON collection_jobs (started_at);
CREATE INDEX IF NOT EXISTS idx_collection_jobs_next_retry ON collection_jobs (next_retry_at);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
