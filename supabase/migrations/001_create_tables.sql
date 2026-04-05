-- =====================================================
-- DROOMVRIENDJES DATABASE SCHEMA
-- Supabase PostgreSQL
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- PRODUCTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku VARCHAR(50) UNIQUE,
    item_id VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255),
    description TEXT,
    short_description TEXT,
    price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2),
    image TEXT,
    gallery JSONB DEFAULT '[]'::jsonb,
    in_stock BOOLEAN DEFAULT true,
    stock_quantity INTEGER DEFAULT 100,
    item_category VARCHAR(100) DEFAULT 'Knuffels',
    item_category2 VARCHAR(100) DEFAULT 'Slaapknuffels',
    item_category3 VARCHAR(100) DEFAULT 'Baby',
    
    -- SEO fields
    meta_title VARCHAR(255),
    meta_description TEXT,
    seo_alt_text TEXT,
    seo_keywords TEXT[],
    
    -- Advanced editor fields
    sections JSONB DEFAULT '[]'::jsonb,
    features JSONB DEFAULT '[]'::jsonb,
    specifications JSONB DEFAULT '{}'::jsonb,
    
    -- Badges
    badges JSONB DEFAULT '[]'::jsonb,
    
    -- Stats
    view_count INTEGER DEFAULT 0,
    order_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for product searches
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_slug ON products(slug);

-- =====================================================
-- CUSTOMERS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    phone VARCHAR(50),
    
    -- Address
    address TEXT,
    city VARCHAR(100),
    zipcode VARCHAR(20),
    country VARCHAR(50) DEFAULT 'NL',
    
    -- Marketing
    email_subscribed BOOLEAN DEFAULT true,
    marketing_consent BOOLEAN DEFAULT false,
    
    -- Stats
    total_orders INTEGER DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0,
    last_order_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);

-- =====================================================
-- ORDERS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(50) UNIQUE,
    
    -- Customer info
    customer_id UUID REFERENCES customers(id),
    customer_email VARCHAR(255) NOT NULL,
    customer_name VARCHAR(255),
    customer_phone VARCHAR(50),
    
    -- Shipping address
    shipping_address TEXT,
    shipping_city VARCHAR(100),
    shipping_zipcode VARCHAR(20),
    shipping_country VARCHAR(50) DEFAULT 'NL',
    customer_comment TEXT,
    
    -- Order items (stored as JSONB)
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Pricing
    subtotal DECIMAL(10,2) NOT NULL,
    discount DECIMAL(10,2) DEFAULT 0,
    discount_code VARCHAR(50),
    discount_amount DECIMAL(10,2) DEFAULT 0,
    coupon_code VARCHAR(50),
    coupon_discount DECIMAL(10,2) DEFAULT 0,
    shipping_cost DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    
    -- Payment
    payment_status VARCHAR(50) DEFAULT 'pending',
    payment_method VARCHAR(50),
    mollie_payment_id VARCHAR(100),
    paid_at TIMESTAMPTZ,
    
    -- Order status
    status VARCHAR(50) DEFAULT 'pending',
    shipped_at TIMESTAMPTZ,
    tracking_number VARCHAR(100),
    tracking_url TEXT,
    delivered_at TIMESTAMPTZ,
    
    -- Review request
    review_requested BOOLEAN DEFAULT false,
    review_requested_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_email ON orders(customer_email);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_mollie ON orders(mollie_payment_id);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at DESC);

-- =====================================================
-- REVIEWS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id),
    product_name VARCHAR(255),
    order_id UUID REFERENCES orders(id),
    
    -- Review content
    author_name VARCHAR(255) NOT NULL,
    author_email VARCHAR(255),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    content TEXT,
    
    -- Source
    source VARCHAR(50) DEFAULT 'website',
    verified_purchase BOOLEAN DEFAULT false,
    
    -- Visibility
    visible BOOLEAN DEFAULT true,
    featured BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);
CREATE INDEX IF NOT EXISTS idx_reviews_visible ON reviews(visible);

-- =====================================================
-- DISCOUNT CODES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS discount_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,
    
    -- Discount type: 'percentage', 'fixed', 'free_shipping'
    discount_type VARCHAR(50) NOT NULL DEFAULT 'percentage',
    discount_value DECIMAL(10,2) NOT NULL,
    
    -- Limits
    min_order_amount DECIMAL(10,2) DEFAULT 0,
    max_uses INTEGER,
    current_uses INTEGER DEFAULT 0,
    uses_per_customer INTEGER DEFAULT 1,
    
    -- Validity
    active BOOLEAN DEFAULT true,
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    
    -- Restrictions
    product_ids UUID[],
    customer_emails TEXT[],
    first_order_only BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discount_codes_code ON discount_codes(code);
CREATE INDEX IF NOT EXISTS idx_discount_codes_active ON discount_codes(active);

-- =====================================================
-- GIFT CARDS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS gift_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,
    
    amount DECIMAL(10,2) NOT NULL,
    remaining_amount DECIMAL(10,2) NOT NULL,
    
    -- Sender/Recipient
    sender_name VARCHAR(255),
    sender_email VARCHAR(255),
    recipient_name VARCHAR(255),
    recipient_email VARCHAR(255),
    message TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    purchased_at TIMESTAMPTZ,
    redeemed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gift_cards_code ON gift_cards(code);

-- =====================================================
-- EMAIL QUEUE TABLE (for marketing campaigns)
-- =====================================================
CREATE TABLE IF NOT EXISTS email_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Recipient
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    
    -- Source tracking
    source VARCHAR(100),
    
    -- Status: 'pending', 'sent', 'failed', 'unsubscribed'
    status VARCHAR(50) DEFAULT 'pending',
    
    -- Email details (filled when sent)
    template_id UUID,
    subject VARCHAR(255),
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_queue_email ON email_queue(email);
CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status);
CREATE INDEX IF NOT EXISTS idx_email_queue_source ON email_queue(source);

-- =====================================================
-- EMAIL CAMPAIGNS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS email_campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    
    -- Template
    template_id UUID,
    html_content TEXT,
    text_content TEXT,
    
    -- Status: 'draft', 'scheduled', 'sending', 'sent', 'paused'
    status VARCHAR(50) DEFAULT 'draft',
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Stats
    total_recipients INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    open_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    unsubscribe_count INTEGER DEFAULT 0,
    
    -- Calculated rates
    open_rate DECIMAL(5,2) DEFAULT 0,
    click_rate DECIMAL(5,2) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_campaigns_status ON email_campaigns(status);

-- =====================================================
-- EMAIL LOGS TABLE (individual email tracking)
-- =====================================================
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Recipient
    to_email VARCHAR(255) NOT NULL,
    customer_name VARCHAR(255),
    
    -- Email details
    subject VARCHAR(255),
    email_type VARCHAR(100),
    campaign_id UUID REFERENCES email_campaigns(id),
    order_id UUID,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    
    -- Tracking
    opens INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    first_opened_at TIMESTAMPTZ,
    last_opened_at TIMESTAMPTZ,
    first_clicked_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_logs_email ON email_logs(to_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_type ON email_logs(email_type);
CREATE INDEX IF NOT EXISTS idx_email_logs_campaign ON email_logs(campaign_id);

-- =====================================================
-- EMAIL TEMPLATES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    
    -- Content
    html_content TEXT NOT NULL,
    text_content TEXT,
    
    -- Type: 'marketing', 'transactional', 'review_request', 'abandoned_cart'
    template_type VARCHAR(50) DEFAULT 'marketing',
    
    -- Status
    active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- ABANDONED CARTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS abandoned_carts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    session_id VARCHAR(100),
    customer_email VARCHAR(255),
    
    -- Cart contents
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_amount DECIMAL(10,2),
    
    -- Recovery
    recovery_email_sent BOOLEAN DEFAULT false,
    recovery_email_sent_at TIMESTAMPTZ,
    recovered BOOLEAN DEFAULT false,
    recovered_order_id UUID,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_abandoned_carts_email ON abandoned_carts(customer_email);
CREATE INDEX IF NOT EXISTS idx_abandoned_carts_session ON abandoned_carts(session_id);

-- =====================================================
-- UNSUBSCRIBES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS unsubscribes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    reason TEXT,
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_unsubscribes_email ON unsubscribes(email);

-- =====================================================
-- CONTACT SUBMISSIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS contact_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    naam VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    telefoon VARCHAR(50),
    onderwerp VARCHAR(255),
    bericht TEXT,
    page_url TEXT,
    replied BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- FUNNEL EVENTS TABLE (analytics)
-- =====================================================
CREATE TABLE IF NOT EXISTS funnel_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    session_id VARCHAR(100),
    product_id UUID,
    product_name VARCHAR(255),
    customer_email VARCHAR(255),
    cart_total DECIMAL(10,2),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_funnel_events_type ON funnel_events(event_type);
CREATE INDEX IF NOT EXISTS idx_funnel_events_created ON funnel_events(created_at DESC);

-- =====================================================
-- TRIGGER FOR UPDATED_AT
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_reviews_updated_at BEFORE UPDATE ON reviews FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_discount_codes_updated_at BEFORE UPDATE ON discount_codes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_gift_cards_updated_at BEFORE UPDATE ON gift_cards FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_email_queue_updated_at BEFORE UPDATE ON email_queue FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_email_campaigns_updated_at BEFORE UPDATE ON email_campaigns FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_email_templates_updated_at BEFORE UPDATE ON email_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_abandoned_carts_updated_at BEFORE UPDATE ON abandoned_carts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- INSERT DEFAULT DISCOUNT CODE
-- =====================================================
INSERT INTO discount_codes (code, discount_type, discount_value, active, valid_until)
VALUES ('EENMALIG2026', 'percentage', 10, true, '2026-12-31')
ON CONFLICT (code) DO NOTHING;

INSERT INTO discount_codes (code, discount_type, discount_value, active)
VALUES ('WELKOM10', 'percentage', 10, true)
ON CONFLICT (code) DO NOTHING;
