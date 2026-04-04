-- Predefined Database Schema for ADK Root Agent
-- This schema creates tables for a sample application metrics system

-- Create metrics table
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_value NUMERIC(10, 2) NOT NULL,
    metric_unit VARCHAR(50),
    tags JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(255),
    CONSTRAINT metric_name_not_empty CHECK (metric_name <> '')
);

-- Create index for efficient time-series queries
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON metrics (recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics (metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_tags ON metrics USING GIN (tags);

-- Create aggregated metrics view
CREATE TABLE IF NOT EXISTS metrics_hourly (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    hour_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
    avg_value NUMERIC(10, 2),
    min_value NUMERIC(10, 2),
    max_value NUMERIC(10, 2),
    count_samples INTEGER,
    UNIQUE (metric_name, hour_bucket)
);

-- Create index for aggregated data
CREATE INDEX IF NOT EXISTS idx_metrics_hourly_bucket ON metrics_hourly (hour_bucket DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_hourly_name ON metrics_hourly (metric_name);

-- Create alerts table for threshold monitoring
CREATE TABLE IF NOT EXISTS metric_alerts (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    alert_condition VARCHAR(50) NOT NULL, -- e.g., 'above', 'below'
    threshold_value NUMERIC(10, 2) NOT NULL,
    severity VARCHAR(20) DEFAULT 'warning', -- 'info', 'warning', 'critical'
    triggered_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB
);

-- Create index for active alerts
CREATE INDEX IF NOT EXISTS idx_alerts_active ON metric_alerts (is_active, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_metric ON metric_alerts (metric_name);

-- Insert sample data
INSERT INTO metrics (metric_name, metric_value, metric_unit, tags, source) VALUES
    ('cpu_usage', 45.5, 'percent', '{"host": "web-01", "cluster": "production"}', 'node-exporter'),
    ('memory_usage', 2048, 'MB', '{"host": "web-01", "cluster": "production"}', 'node-exporter'),
    ('request_latency', 125.3, 'ms', '{"endpoint": "/api/v1/users", "method": "GET"}', 'api-gateway'),
    ('disk_io', 1024, 'KB/s', '{"device": "sda1", "host": "db-01"}', 'node-exporter'),
    ('http_requests', 1500, 'count', '{"status": "200", "endpoint": "/api/v1/users"}', 'api-gateway')
ON CONFLICT DO NOTHING;

-- Insert sample alert
INSERT INTO metric_alerts (metric_name, alert_condition, threshold_value, severity, triggered_at, is_active, metadata) VALUES
    ('cpu_usage', 'above', 80.0, 'warning', CURRENT_TIMESTAMP - INTERVAL '2 hours', TRUE, '{"notification_sent": true}')
ON CONFLICT DO NOTHING;

-- Add comments for documentation
COMMENT ON TABLE metrics IS 'Real-time metrics data from various sources';
COMMENT ON TABLE metrics_hourly IS 'Hourly aggregated metrics for historical analysis';
COMMENT ON TABLE metric_alerts IS 'Alert definitions and their current state';

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO aire;
