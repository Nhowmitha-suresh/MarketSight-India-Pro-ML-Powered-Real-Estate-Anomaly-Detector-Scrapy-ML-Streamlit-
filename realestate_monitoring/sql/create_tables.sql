-- Listings table
CREATE TABLE IF NOT EXISTS listings (
    listing_id TEXT PRIMARY KEY,
    price NUMERIC,
    beds INTEGER,
    baths INTEGER,
    sq_ft INTEGER,
    year_built INTEGER,
    price_per_sqft NUMERIC,
    property_type TEXT,
    days_on_market INTEGER,
    address TEXT,
    city TEXT,
    locality TEXT,
    zip_code TEXT,
    listing_url TEXT,
    agent_name TEXT,
    num_photos INTEGER,
    dq_status TEXT,
    scrape_timestamp TIMESTAMP
);

-- Group stats per day (per zip and property type)
CREATE TABLE IF NOT EXISTS group_stats (
    id SERIAL PRIMARY KEY,
    zip_code TEXT NOT NULL,
    property_type TEXT NOT NULL,
    stat_date DATE NOT NULL,
    mean_ppsq NUMERIC,
    std_ppsq NUMERIC,
    count_listings INTEGER,
    created_at TIMESTAMP DEFAULT now()
);

-- Per-listing analysis/flag table
CREATE TABLE IF NOT EXISTS listing_analysis (
    listing_id TEXT PRIMARY KEY REFERENCES listings(listing_id),
    price_per_sqft NUMERIC,
    is_anomaly BOOLEAN,
    anomaly_type TEXT,
    mean_ppsq NUMERIC,
    std_ppsq NUMERIC,
    predicted_price NUMERIC,
    deviation_percentage NUMERIC,
    dq_status TEXT,
    analyzed_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_listings_zip ON listings(zip_code);
CREATE INDEX IF NOT EXISTS idx_group_stats_zip_date ON group_stats(zip_code, stat_date);
