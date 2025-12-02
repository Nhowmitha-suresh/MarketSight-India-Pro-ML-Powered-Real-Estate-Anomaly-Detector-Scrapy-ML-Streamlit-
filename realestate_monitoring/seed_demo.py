"""seed_demo.py
Create sample listings in the configured database (uses config.ENGINE).

Usage:
    .venv\Scripts\python.exe seed_demo.py 12345
If no ZIP is provided, defaults to '12345'.
"""
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from config import ENGINE


SAMPLES = [
    # (listing_id, price, beds, baths, sqft, year_built, ptype, dom, addr, agent, num_photos)
    ('demo_001', 450000, 3, 2, 2000, 1998, 'House', 5, '100 Demo Lane', 'John Smith', 12),
    ('demo_002', 550000, 4, 3, 2500, 2005, 'House', 12, '200 Demo Ave', 'Jane Doe', 15),
    ('demo_003', 350000, 3, 2, 2200, 1985, 'House', 2, '300 Demo Blvd', 'Bob Johnson', 8),
    ('demo_004', 750000, 5, 4, 1800, 2018, 'House', 30, '400 Demo Rd', 'Alice Chen', 20),
    ('demo_005', 500000, 4, 3, 2100, 2010, 'House', 8, '500 Demo St', 'Mike Brown', 18),
    ('demo_006', 520000, 4, 2, 2050, 2000, 'House', 7, '600 Demo Cir', 'Sarah Wilson', 14),
    ('condo_001', 300000, 2, 1, 1000, 1995, 'Condo', 4, '700 Demo Pl', 'Tom Harris', 10),
    ('condo_002', 320000, 2, 1, 1100, 2002, 'Condo', 6, '800 Demo Way', 'Emily White', 11),
]


def ensure_tables(engine):
    # Try to add new columns if they don't exist (for existing databases)
    with ENGINE.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE listings ADD COLUMN agent_name TEXT"))
        except:
            pass  # Column already exists
        try:
            conn.execute(text("ALTER TABLE listings ADD COLUMN num_photos INTEGER"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE listings ADD COLUMN dq_status TEXT"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE listings ADD COLUMN price_per_sqft NUMERIC"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE listings ADD COLUMN city TEXT"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE listings ADD COLUMN locality TEXT"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE listing_analysis ADD COLUMN predicted_price NUMERIC"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE listing_analysis ADD COLUMN deviation_percentage NUMERIC"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE listing_analysis ADD COLUMN dq_status TEXT"))
        except:
            pass
    
    # Create minimal listings, group_stats, listing_analysis tables if they don't exist
    create_listings = """
    CREATE TABLE IF NOT EXISTS listings (
        listing_id TEXT PRIMARY KEY,
        price REAL,
        beds INTEGER,
        baths INTEGER,
        sq_ft INTEGER,
        year_built INTEGER,
        price_per_sqft REAL,
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
        scrape_timestamp TEXT
    )
    """

    create_group_stats = """
    CREATE TABLE IF NOT EXISTS group_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zip_code TEXT,
        property_type TEXT,
        stat_date DATE,
        mean_ppsq REAL,
        std_ppsq REAL,
        count_listings INTEGER
    )
    """

    create_listing_analysis = """
    CREATE TABLE IF NOT EXISTS listing_analysis (
        listing_id TEXT PRIMARY KEY,
        price_per_sqft REAL,
        is_anomaly BOOLEAN,
        anomaly_type TEXT,
        mean_ppsq REAL,
        std_ppsq REAL,
        predicted_price REAL,
        deviation_percentage REAL,
        dq_status TEXT,
        analyzed_at TEXT
    )
    """

    with ENGINE.begin() as conn:
        conn.execute(text(create_listings))
        conn.execute(text(create_group_stats))
        conn.execute(text(create_listing_analysis))


def seed(zip_code: str = '12345'):
    ensure_tables(ENGINE)
    now = datetime.utcnow().isoformat()
    records = []
    for sid, price, beds, baths, sqft, yb, ptype, dom, addr, agent, num_photos in SAMPLES:
        # derive city/locality from address naively
        parts = [p.strip() for p in addr.split(',') if p.strip()]
        city = parts[-1] if parts else None
        locality = parts[0] if parts else None
        ppsq = float(price) / float(sqft) if sqft and sqft > 0 else None
        records.append({
            'listing_id': f"{sid}",
            'price': float(price),
            'beds': beds,
            'baths': baths,
            'sq_ft': sqft,
            'price_per_sqft': ppsq,
            'year_built': yb,
            'property_type': ptype,
            'days_on_market': dom,
            'address': addr,
            'city': city,
            'locality': locality,
            'zip_code': zip_code,
            'listing_url': f"http://demo/{sid}",
            'agent_name': agent,
            'num_photos': num_photos,
            'dq_status': 'PASS',
            'scrape_timestamp': now,
        })

    # dialect-specific upsert
    dialect = ENGINE.dialect.name
    with ENGINE.begin() as conn:
        for rec in records:
            if dialect == 'sqlite':
                conn.execute(text(
                    """
                    INSERT OR REPLACE INTO listings(listing_id, price, beds, baths, sq_ft, year_built, property_type, days_on_market, address, zip_code, listing_url, agent_name, num_photos, dq_status, scrape_timestamp)
                    VALUES (:listing_id, :price, :beds, :baths, :sq_ft, :year_built, :property_type, :days_on_market, :address, :zip_code, :listing_url, :agent_name, :num_photos, :dq_status, :scrape_timestamp)
                    """), rec)
            else:
                conn.execute(text(
                    """
                    INSERT INTO listings(listing_id, price, beds, baths, sq_ft, year_built, property_type, days_on_market, address, zip_code, listing_url, agent_name, num_photos, dq_status, scrape_timestamp)
                    VALUES (:listing_id, :price, :beds, :baths, :sq_ft, :year_built, :property_type, :days_on_market, :address, :zip_code, :listing_url, :agent_name, :num_photos, :dq_status, :scrape_timestamp)
                    ON CONFLICT (listing_id) DO UPDATE SET
                      price = EXCLUDED.price,
                      beds = EXCLUDED.beds,
                      baths = EXCLUDED.baths,
                      sq_ft = EXCLUDED.sq_ft,
                      year_built = EXCLUDED.year_built,
                      property_type = EXCLUDED.property_type,
                      days_on_market = EXCLUDED.days_on_market,
                      address = EXCLUDED.address,
                      zip_code = EXCLUDED.zip_code,
                      listing_url = EXCLUDED.listing_url,
                      agent_name = EXCLUDED.agent_name,
                      num_photos = EXCLUDED.num_photos,
                      dq_status = EXCLUDED.dq_status,
                      scrape_timestamp = EXCLUDED.scrape_timestamp;
                    """), rec)

    print(f"Inserted {len(records)} demo listings for ZIP {zip_code} into {ENGINE.dialect.name} database.")


if __name__ == '__main__':
    zip_arg = sys.argv[1] if len(sys.argv) > 1 else '12345'
    seed(zip_arg)
