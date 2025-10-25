-- Database schema for arbitrage analysis app

-- Create uploads table to track CSV uploads
CREATE TABLE IF NOT EXISTS uploads (
    id VARCHAR(255) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded', -- uploaded, processing, completed, failed
    total_items INTEGER,
    processed_items INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    manifest_id VARCHAR(255)
);

-- Create manifests table
CREATE TABLE IF NOT EXISTS manifests (
    id VARCHAR(255) PRIMARY KEY,
    upload_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_items INTEGER NOT NULL,
    total_msrp DECIMAL(12,2) NOT NULL,
    projected_revenue DECIMAL(12,2) NOT NULL,
    profit_margin DECIMAL(5,4) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE CASCADE
);

-- Create items table
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    manifest_id VARCHAR(255) NOT NULL,
    item_number VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    msrp DECIMAL(10,2) NOT NULL,
    estimated_sale_price DECIMAL(10,2) NOT NULL,
    profit DECIMAL(10,2) NOT NULL,
    demand VARCHAR(20) NOT NULL,
    sales_time VARCHAR(50) NOT NULL,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manifest_id) REFERENCES manifests(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);
CREATE INDEX IF NOT EXISTS idx_uploads_created_at ON uploads(created_at);
CREATE INDEX IF NOT EXISTS idx_items_manifest_id ON items(manifest_id);
CREATE INDEX IF NOT EXISTS idx_items_item_number ON items(item_number);
CREATE INDEX IF NOT EXISTS idx_manifests_created_at ON manifests(created_at);
CREATE INDEX IF NOT EXISTS idx_manifests_upload_id ON manifests(upload_id);

-- Create a view for summary statistics
CREATE OR REPLACE VIEW manifest_summary AS
SELECT 
    m.id,
    m.created_at,
    m.total_items,
    m.total_msrp,
    m.projected_revenue,
    m.profit_margin,
    COUNT(i.id) as actual_items_count,
    AVG(i.profit) as avg_item_profit,
    COUNT(CASE WHEN i.demand = 'High' THEN 1 END) as high_demand_items,
    COUNT(CASE WHEN i.demand = 'Medium' THEN 1 END) as medium_demand_items,
    COUNT(CASE WHEN i.demand = 'Low' THEN 1 END) as low_demand_items
FROM manifests m
LEFT JOIN items i ON m.id = i.manifest_id
GROUP BY m.id, m.created_at, m.total_items, m.total_msrp, m.projected_revenue, m.profit_margin;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update the updated_at column
CREATE TRIGGER update_uploads_updated_at 
    BEFORE UPDATE ON uploads 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_manifests_updated_at 
    BEFORE UPDATE ON manifests 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for testing
INSERT INTO manifests (id, total_items, total_msrp, projected_revenue, profit_margin) 
VALUES ('sample_manifest_001', 3, 4714.68, 2828.81, 0.4)
ON CONFLICT (id) DO NOTHING;

INSERT INTO items (manifest_id, item_number, title, msrp, estimated_sale_price, profit, demand, sales_time, reasoning)
VALUES 
    ('sample_manifest_001', '3ya47', 'HANKISON HPR50 Refrigerated Air Dryer', 3215.93, 1930.00, -1285.93, 'Medium', '2-4 months', 'Industrial equipment with steady demand'),
    ('sample_manifest_001', '4zc05', 'SOUTHWORTH L-250 Manual Mobile Scissor-Lift Table', 1277.61, 766.00, -511.61, 'High', '1-2 months', 'Workshop equipment with high demand'),
    ('sample_manifest_001', '3kn35', 'EAGLE 1698 Cross-Brace Drum Dolly', 221.14, 132.00, -89.14, 'Medium', '2-3 months', 'Utility equipment with moderate demand')
ON CONFLICT DO NOTHING;
