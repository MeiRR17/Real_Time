-- =============================================================================
-- UCCX Database Initialization Script
-- =============================================================================
-- This script initializes the database for Unified Contact Center Express metrics

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_uccx_metrics_timestamp_server ON uccx_metrics (timestamp DESC, server_name);
CREATE INDEX IF NOT EXISTS idx_uccx_metrics_agents ON uccx_metrics (logged_in_agents, available_agents);
CREATE INDEX IF NOT EXISTS idx_uccx_metrics_queue ON uccx_metrics (calls_in_queue, longest_wait_time_seconds);
CREATE INDEX IF NOT EXISTS idx_uccx_metrics_service_level ON uccx_metrics (service_level_percent);

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
