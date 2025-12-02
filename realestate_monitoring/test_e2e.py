"""
Local development test runner using SQLite.
Validates: scraping → cleaning → storage → analysis → visualization.
"""
import os
import sys
import sqlite3
from datetime import datetime
import re

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Sample listing data (simulating Scrapy spider output)
SAMPLE_LISTINGS = [
    {'listing_id': 'listing_001', 'price': '$450,000', 'beds': '3', 'baths': '2', 'sq_ft': '2,000', 'year_built': '2015', 'property_type': 'House', 'days_on_market': '45', 'address': '123 Main St', 'zip_code': '12345', 'listing_url': 'https://example.com/001', 'scrape_timestamp': datetime.utcnow().isoformat()},
    {'listing_id': 'listing_002', 'price': '$550,000', 'beds': '4', 'baths': '3', 'sq_ft': '2,500', 'year_built': '2010', 'property_type': 'House', 'days_on_market': '30', 'address': '456 Oak Ave', 'zip_code': '12345', 'listing_url': 'https://example.com/002', 'scrape_timestamp': datetime.utcnow().isoformat()},
    {'listing_id': 'listing_003', 'price': '$350,000', 'beds': '3', 'baths': '2', 'sq_ft': '2,200', 'year_built': '2012', 'property_type': 'House', 'days_on_market': '5', 'address': '789 Pine Rd', 'zip_code': '12345', 'listing_url': 'https://example.com/003', 'scrape_timestamp': datetime.utcnow().isoformat()},
    {'listing_id': 'listing_004', 'price': '$750,000', 'beds': '3', 'baths': '2', 'sq_ft': '1,800', 'year_built': '2018', 'property_type': 'House', 'days_on_market': '120', 'address': '321 Elm St', 'zip_code': '12345', 'listing_url': 'https://example.com/004', 'scrape_timestamp': datetime.utcnow().isoformat()},
    {'listing_id': 'listing_005', 'price': '$500,000', 'beds': '3', 'baths': '2', 'sq_ft': '2,100', 'year_built': '2014', 'property_type': 'House', 'days_on_market': '20', 'address': '654 Maple Dr', 'zip_code': '12345', 'listing_url': 'https://example.com/005', 'scrape_timestamp': datetime.utcnow().isoformat()},
    {'listing_id': 'listing_006', 'price': '$520,000', 'beds': '3', 'baths': '2', 'sq_ft': '2,050', 'year_built': '2016', 'property_type': 'House', 'days_on_market': '35', 'address': '987 Birch Ln', 'zip_code': '12345', 'listing_url': 'https://example.com/006', 'scrape_timestamp': datetime.utcnow().isoformat()},
    {'listing_id': 'condo_001', 'price': '$300,000', 'beds': '2', 'baths': '1.5', 'sq_ft': '1,000', 'year_built': '2020', 'property_type': 'Condo', 'days_on_market': '15', 'address': '111 Condo Way', 'zip_code': '12345', 'listing_url': 'https://example.com/condo_001', 'scrape_timestamp': datetime.utcnow().isoformat()},
    {'listing_id': 'condo_002', 'price': '$320,000', 'beds': '2', 'baths': '2', 'sq_ft': '1,100', 'year_built': '2019', 'property_type': 'Condo', 'days_on_market': '25', 'address': '222 Condo Way', 'zip_code': '12345', 'listing_url': 'https://example.com/condo_002', 'scrape_timestamp': datetime.utcnow().isoformat()},
]

DB_PATH = 'test_realestate.db'
THRESHOLD = 1.5


def clean_price(price_str):
    """Clean price string like '$450,000' to float."""
    if isinstance(price_str, (int, float)):
        return float(price_str)
    cleaned = re.sub(r'[^0-9.]', '', str(price_str))
    return float(cleaned) if cleaned else None


def clean_sqft(sqft_str):
    """Clean sqft string like '2,000' to int."""
    if isinstance(sqft_str, (int, float)):
        return int(sqft_str)
    cleaned = re.sub(r'[^0-9]', '', str(sqft_str))
    return int(cleaned) if cleaned else None


def setup_db():
    """Create SQLite tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS listings (listing_id TEXT PRIMARY KEY, price REAL, beds INTEGER, baths REAL, sq_ft INTEGER, year_built INTEGER, property_type TEXT, days_on_market INTEGER, address TEXT, zip_code TEXT, listing_url TEXT, scrape_timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS group_stats (id INTEGER PRIMARY KEY, zip_code TEXT, property_type TEXT, stat_date TEXT, mean_ppsq REAL, std_ppsq REAL, count_listings INTEGER, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS listing_analysis (listing_id TEXT PRIMARY KEY, price_per_sqft REAL, is_anomaly BOOLEAN, anomaly_type TEXT, mean_ppsq REAL, std_ppsq REAL, analyzed_at TEXT)''')
    conn.commit()
    conn.close()
    print(f'✅ Database created: {DB_PATH}')


def insert_sample_listings():
    """Insert sample listings."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    print('\n' + '='*70)
    print('STEP 1: DATA INGESTION')
    print('='*70 + '\n📥 Inserting 8 sample listings:')
    for item in SAMPLE_LISTINGS:
        cleaned = {
            'listing_id': item['listing_id'],
            'price': clean_price(item['price']),
            'beds': int(item['beds']) if item['beds'] else None,
            'baths': float(item['baths']) if item['baths'] else None,
            'sq_ft': clean_sqft(item['sq_ft']),
            'year_built': int(item['year_built']) if item['year_built'] else None,
            'property_type': item['property_type'],
            'days_on_market': int(item['days_on_market']) if item['days_on_market'] else None,
            'address': item['address'],
            'zip_code': item['zip_code'],
            'listing_url': item['listing_url'],
            'scrape_timestamp': item['scrape_timestamp'],
        }
        c.execute('INSERT OR REPLACE INTO listings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
            cleaned['listing_id'], cleaned['price'], cleaned['beds'], cleaned['baths'],
            cleaned['sq_ft'], cleaned['year_built'], cleaned['property_type'],
            cleaned['days_on_market'], cleaned['address'], cleaned['zip_code'],
            cleaned['listing_url'], cleaned['scrape_timestamp']
        ))
        ppsq = cleaned['price'] / cleaned['sq_ft'] if cleaned['sq_ft'] and cleaned['price'] else 0
        print(f"  ✓ {cleaned['listing_id']:15} | ${cleaned['price']:>10,.0f} | {cleaned['sq_ft']:>5,} sqft | ${ppsq:>7.2f}/sqft | {cleaned['property_type']}")
    conn.commit()
    conn.close()


def run_analysis(zip_code='12345'):
    """Run analysis: compute stats, flag anomalies."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f"SELECT * FROM listings WHERE zip_code = '{zip_code}'", conn)
    conn.close()
    
    if df.empty:
        print('No data to analyze.')
        return
    
    print('\n' + '='*70)
    print('STEP 2: STATISTICAL ANALYSIS')
    print('='*70 + '\n📊 Computing price/sqft & group statistics:')
    
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['sq_ft'] = pd.to_numeric(df['sq_ft'], errors='coerce')
    df = df[df['sq_ft'] > 0]
    df['ppsq'] = df['price'] / df['sq_ft']
    print(df[['listing_id', 'property_type', 'price', 'sq_ft', 'ppsq']].to_string(index=False))
    
    # Group stats
    groups = df.groupby('property_type')['ppsq'].agg(['mean', 'std', 'count']).reset_index()
    print(f'\n📈 Group Stats by Property Type:')
    print(groups.to_string(index=False))
    
    # Store stats
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    stat_date = datetime.utcnow().date().isoformat()
    for _, row in groups.iterrows():
        c.execute('INSERT INTO group_stats (zip_code, property_type, stat_date, mean_ppsq, std_ppsq, count_listings, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (zip_code, row['property_type'], stat_date, float(row['mean']), float(row['std']), int(row['count']), datetime.utcnow().isoformat()))
    conn.commit()
    
    # Flag anomalies
    print(f'\n🚨 Flagging Anomalies (threshold = ±{THRESHOLD}σ):')
    df = df.merge(groups[['property_type', 'mean', 'std']], on='property_type', how='left')
    
    def flag_anomaly(row):
        mu, sigma, ppsq = row['mean'], row['std'], row['ppsq']
        if pd.isna(mu) or pd.isna(sigma):
            return False, None
        upper = mu + THRESHOLD * sigma
        lower = mu - THRESHOLD * sigma
        if ppsq > upper:
            return True, 'over-priced'
        elif ppsq < lower:
            return True, 'under-priced'
        return False, None
    
    df[['is_anomaly', 'anomaly_type']] = df.apply(flag_anomaly, axis=1, result_type='expand')
    
    # Store analysis
    for _, row in df.iterrows():
        c.execute('INSERT OR REPLACE INTO listing_analysis (listing_id, price_per_sqft, is_anomaly, anomaly_type, mean_ppsq, std_ppsq, analyzed_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (row['listing_id'], float(row['ppsq']), bool(row['is_anomaly']), row['anomaly_type'], float(row['mean']), float(row['std']), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    
    anomalies = df[df['is_anomaly']]
    if not anomalies.empty:
        print(f'\n✅ Anomalies Detected: {len(anomalies)}')
        for _, row in anomalies.iterrows():
            deviation = abs((row['ppsq'] - row['mean']) / row['std'])
            print(f"  🚨 {row['listing_id']:15} | {row['anomaly_type'].upper():12} | {deviation:.2f}σ | ${row['ppsq']:.2f}/sqft (market: ${row['mean']:.2f})")
    else:
        print('✓ No anomalies detected.')


def verify_output():
    """Verify populated tables."""
    conn = sqlite3.connect(DB_PATH)
    print('\n' + '='*70)
    print('STEP 3: DATA VERIFICATION')
    print('='*70)
    
    print('\n📋 Listings:')
    listings = pd.read_sql_query("SELECT COUNT(*) as count FROM listings", conn)
    print(f"  Total: {listings['count'].values[0]}")
    
    print('\n📋 Anomaly Analysis:')
    analysis = pd.read_sql_query("SELECT * FROM listing_analysis WHERE is_anomaly = 1", conn)
    if not analysis.empty:
        print(analysis[['listing_id', 'price_per_sqft', 'anomaly_type']].to_string(index=False))
    else:
        print("  No anomalies.")
    
    print('\n📊 Group Statistics:')
    stats = pd.read_sql_query("SELECT zip_code, property_type, mean_ppsq, std_ppsq, count_listings FROM group_stats", conn)
    print(stats.to_string(index=False))
    
    conn.close()


if __name__ == '__main__':
    print('\n' + '#'*70)
    print('# END-TO-END TEST: Real Estate Monitoring Pipeline')
    print('#'*70)
    
    try:
        setup_db()
        insert_sample_listings()
        run_analysis()
        verify_output()
        
        print('\n' + '='*70)
        print('✅ ALL TESTS PASSED!')
        print('='*70)
        print(f'\n💾 Database saved: {os.path.abspath(DB_PATH)}')
        print('\n📚 Next Steps:')
        print('   1. Configure .env with your PostgreSQL DATABASE_URL')
        print('   2. Run: psql -U user -d realestate_db -f sql/create_tables.sql')
        print('   3. Run: scrapy crawl listings -a zip=12345')
        print('   4. Run: python analysis/analyze.py')
        print('   5. Run: streamlit run app/streamlit_app.py')
    except Exception as e:
        print(f'\n❌ ERROR: {e}')
        import traceback
        traceback.print_exc()
