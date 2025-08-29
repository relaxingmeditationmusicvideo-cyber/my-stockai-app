-- init.sql - Database Initialization Script
-- Create database if not exists
CREATE DATABASE IF NOT EXISTS stockai_db;

-- Connect to the database
\c stockai_db;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_stock_data_symbol_timestamp ON stock_data(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_watchlists_user_symbol ON watchlists(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_user_active ON alerts(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_stock_data_ai_score ON stock_data(ai_score DESC);
CREATE INDEX IF NOT EXISTS idx_stock_data_sentiment ON stock_data(sentiment);

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for timestamp updates
CREATE TRIGGER update_portfolios_updated_at 
    BEFORE UPDATE ON portfolios 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_holdings_updated_at 
    BEFORE UPDATE ON holdings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample stock data
INSERT INTO stocks (symbol, name, sector, industry, market_cap_category, exchange) VALUES
('RELIANCE', 'Reliance Industries Limited', 'Energy', 'Oil & Gas', 'large', 'NSE'),
('TCS', 'Tata Consultancy Services Limited', 'IT', 'Software Services', 'large', 'NSE'),
('HDFCBANK', 'HDFC Bank Limited', 'Banking', 'Private Banks', 'large', 'NSE'),
('INFY', 'Infosys Limited', 'IT', 'Software Services', 'large', 'NSE'),
('ICICIBANK', 'ICICI Bank Limited', 'Banking', 'Private Banks', 'large', 'NSE'),
('HINDUNILVR', 'Hindustan Unilever Limited', 'FMCG', 'Personal Care', 'large', 'NSE'),
('KOTAKBANK', 'Kotak Mahindra Bank Limited', 'Banking', 'Private Banks', 'large', 'NSE'),
('BHARTIARTL', 'Bharti Airtel Limited', 'Telecom', 'Telecommunications', 'large', 'NSE'),
('ITC', 'ITC Limited', 'FMCG', 'Tobacco & Cigarettes', 'large', 'NSE'),
('SBIN', 'State Bank of India', 'Banking', 'Public Banks', 'large', 'NSE'),
('LT', 'Larsen & Toubro Limited', 'Capital Goods', 'Construction & Engineering', 'large', 'NSE'),
('BAJFINANCE', 'Bajaj Finance Limited', 'Financial Services', 'NBFCs', 'large', 'NSE'),
('HCLTECH', 'HCL Technologies Limited', 'IT', 'Software Services', 'large', 'NSE'),
('ASIANPAINT', 'Asian Paints Limited', 'Consumer Durables', 'Paints', 'large', 'NSE'),
('MARUTI', 'Maruti Suzuki India Limited', 'Automobile', 'Passenger Cars', 'large', 'NSE'),
('AXISBANK', 'Axis Bank Limited', 'Banking', 'Private Banks', 'large', 'NSE'),
('TITAN', 'Titan Company Limited', 'Consumer Durables', 'Gems & Jewellery', 'large', 'NSE'),
('SUNPHARMA', 'Sun Pharmaceutical Industries Limited', 'Healthcare', 'Pharmaceuticals', 'large', 'NSE'),
('ULTRACEMCO', 'UltraTech Cement Limited', 'Construction Materials', 'Cement', 'large', 'NSE'),
('WIPRO', 'Wipro Limited', 'IT', 'Software Services', 'large', 'NSE'),
('NESTLEIND', 'Nestle India Limited', 'FMCG', 'Packaged Foods', 'large', 'NSE'),
('POWERGRID', 'Power Grid Corporation of India Limited', 'Utilities', 'Power Transmission', 'large', 'NSE'),
('NTPC', 'NTPC Limited', 'Utilities', 'Power Generation', 'large', 'NSE'),
('ONGC', 'Oil and Natural Gas Corporation Limited', 'Energy', 'Oil & Gas', 'large', 'NSE'),
('TATAMOTORS', 'Tata Motors Limited', 'Automobile', 'Commercial Vehicles', 'large', 'NSE'),
('TECHM', 'Tech Mahindra Limited', 'IT', 'Software Services', 'large', 'NSE'),
('BAJAJFINSV', 'Bajaj Finserv Limited', 'Financial Services', 'NBFCs', 'large', 'NSE'),
('DRREDDY', 'Dr. Reddys Laboratories Limited', 'Healthcare', 'Pharmaceuticals', 'large', 'NSE'),
('INDUSINDBK', 'IndusInd Bank Limited', 'Banking', 'Private Banks', 'large', 'NSE'),
('CIPLA', 'Cipla Limited', 'Healthcare', 'Pharmaceuticals', 'large', 'NSE')
ON CONFLICT (symbol) DO NOTHING;

-- Create stored procedures for common operations
CREATE OR REPLACE FUNCTION get_user_portfolio_summary(user_id_param INTEGER)
RETURNS TABLE(
    total_invested NUMERIC,
    current_value NUMERIC,
    total_return NUMERIC,
    total_return_percent NUMERIC,
    holdings_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(h.invested_amount), 0) as total_invested,
        COALESCE(SUM(h.current_value), 0) as current_value,
        COALESCE(SUM(h.unrealized_pnl), 0) as total_return,
        CASE 
            WHEN COALESCE(SUM(h.invested_amount), 0) > 0 
            THEN (COALESCE(SUM(h.unrealized_pnl), 0) / COALESCE(SUM(h.invested_amount), 1)) * 100
            ELSE 0 
        END as total_return_percent,
        COUNT(h.id)::INTEGER as holdings_count
    FROM portfolios p
    LEFT JOIN holdings h ON p.id = h.portfolio_id
    WHERE p.user_id = user_id_param;
END;
$$ LANGUAGE plpgsql;

-- Create function to calculate portfolio metrics
CREATE OR REPLACE FUNCTION update_portfolio_metrics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update portfolio totals when holdings change
    UPDATE portfolios 
    SET 
        total_invested = (
            SELECT COALESCE(SUM(invested_amount), 0) 
            FROM holdings 
            WHERE portfolio_id = NEW.portfolio_id
        ),
        current_value = (
            SELECT COALESCE(SUM(current_value), 0) 
            FROM holdings 
            WHERE portfolio_id = NEW.portfolio_id
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.portfolio_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for portfolio updates
CREATE TRIGGER trigger_update_portfolio_metrics
    AFTER INSERT OR UPDATE OR DELETE ON holdings
    FOR EACH ROW EXECUTE FUNCTION update_portfolio_metrics();

-- Create materialized view for stock rankings
CREATE MATERIALIZED VIEW IF NOT EXISTS stock_rankings AS
SELECT 
    s.symbol,
    s.name,
    s.sector,
    sd.ai_score,
    sd.sentiment_score,
    sd.trend_prediction,
    sd.close_price,
    sd.change_percent,
    sd.volume,
    sd.rsi,
    sd.pe_ratio,
    sd.roe,
    ROW_NUMBER() OVER (ORDER BY sd.ai_score DESC) as ai_rank,
    ROW_NUMBER() OVER (ORDER BY sd.change_percent DESC) as momentum_rank,
    ROW_NUMBER() OVER (ORDER BY sd.volume DESC) as volume_rank,
    sd.timestamp
FROM stocks s
JOIN LATERAL (
    SELECT *
    FROM stock_data
    WHERE symbol = s.symbol
    ORDER BY timestamp DESC
    LIMIT 1
) sd ON true
WHERE s.is_active = true;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_rankings_symbol ON stock_rankings(symbol);
CREATE INDEX IF NOT EXISTS idx_stock_rankings_ai_score ON stock_rankings(ai_score DESC);
CREATE INDEX IF NOT EXISTS idx_stock_rankings_sector ON stock_rankings(sector);

-- Refresh materialized view function
CREATE OR REPLACE FUNCTION refresh_stock_rankings()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY stock_rankings;
END;
$$ LANGUAGE plpgsql;

-- Create user activity log table
CREATE TABLE IF NOT EXISTS user_activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_created_at ON user_activity_log(created_at DESC);

-- Create performance monitoring table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    metadata JSONB,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_name_time ON performance_metrics(metric_name, recorded_at DESC);

-- Insert initial performance tracking
INSERT INTO performance_metrics (metric_name, metric_value, metadata) VALUES
('api_response_time_avg', 150, '{"unit": "ms", "endpoint": "all"}'),
('active_users_daily', 0, '{"date": "' || CURRENT_DATE || '"}'),
('database_connections', 0, '{"max_connections": 100}');

-- Create function to log user activity
CREATE OR REPLACE FUNCTION log_user_activity(
    user_id_param INTEGER,
    action_param VARCHAR(100),
    details_param JSONB DEFAULT NULL,
    ip_param INET DEFAULT NULL,
    user_agent_param TEXT DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    INSERT INTO user_activity_log (user_id, action, details, ip_address, user_agent)
    VALUES (user_id_param, action_param, details_param, ip_param, user_agent_param);
END;
$$ LANGUAGE plpgsql;

-- Create cleanup function for old data
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Delete stock data older than 1 year
    DELETE FROM stock_data 
    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '1 year';
    
    -- Delete old user activity logs (keep 3 months)
    DELETE FROM user_activity_log 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '3 months';
    
    -- Delete old performance metrics (keep 6 months)
    DELETE FROM performance_metrics 
    WHERE recorded_at < CURRENT_TIMESTAMP - INTERVAL '6 months';
    
    -- Vacuum and analyze tables
    VACUUM ANALYZE stock_data;
    VACUUM ANALYZE user_activity_log;
    VACUUM ANALYZE performance_metrics;
END;
$$ LANGUAGE plpgsql;