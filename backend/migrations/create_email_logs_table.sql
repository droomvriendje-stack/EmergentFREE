-- Create email_logs table for tracking all sent emails
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    to_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    email_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'sent',
    order_id VARCHAR(100),
    customer_name VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index for common queries
CREATE INDEX IF NOT EXISTS idx_email_logs_created_at ON email_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_logs_email_type ON email_logs(email_type);
CREATE INDEX IF NOT EXISTS idx_email_logs_to_email ON email_logs(to_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_order_id ON email_logs(order_id);

-- Add comments
COMMENT ON TABLE email_logs IS 'Log van alle verzonden emails voor admin dashboard';
COMMENT ON COLUMN email_logs.email_type IS 'Type email: order_confirmation, review_request, marketing, etc.';
COMMENT ON COLUMN email_logs.status IS 'Status: sent, failed, bounced';
