import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import text

# Import shared ENGINE from config
from config import ENGINE

TARGET_ZIP = os.getenv('TARGET_ZIP')

THRESHOLD_MULTIPLIER = 1.5

engine = ENGINE

# Detect if we're using SQLite or Postgres
DB_DIALECT = engine.dialect.name if engine else 'sqlite'

def load_recent_listings(zip_code: str, days: int = 7):
    # loads listings from last `days` days (by scrape_timestamp)
    since = datetime.utcnow() - timedelta(days=days)
    query = text(
        "SELECT * FROM listings WHERE zip_code = :zip AND scrape_timestamp >= :since"
    )
    df = pd.read_sql(query, engine, params={'zip': zip_code, 'since': since})
    return df


def analyze_and_store(zip_code: str):
    # pull a reasonably recent window (e.g., 30 days) to compute stable stats
    df = pd.read_sql(text("SELECT * FROM listings WHERE zip_code = :zip"), engine, params={'zip': zip_code})
    if df.empty:
        print('No data to analyze')
        return

    # compute price per sqft
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['sq_ft'] = pd.to_numeric(df['sq_ft'], errors='coerce')
    df = df[df['sq_ft'] > 0]
    df['ppsq'] = df['price'] / df['sq_ft']

    # group by property_type and zip_code
    group_cols = ['zip_code', 'property_type']
    stats = df.groupby(group_cols)['ppsq'].agg(['mean', 'std', 'count']).reset_index()
    stats = stats.rename(columns={'mean': 'mu', 'std': 'sigma', 'count': 'n'})

    # store group stats (for today's date)
    stat_date = datetime.utcnow().date()
    gs_records = []
    for _, row in stats.iterrows():
        gs_records.append({
            'zip_code': row['zip_code'],
            'property_type': row['property_type'],
            'stat_date': stat_date,
            'mean_ppsq': float(row['mu']) if not pd.isna(row['mu']) else None,
            'std_ppsq': float(row['sigma']) if not pd.isna(row['sigma']) else None,
            'count_listings': int(row['n'])
        })
    if gs_records:
        with engine.begin() as conn:
            if DB_DIALECT == 'sqlite':
                # SQLite: INSERT OR REPLACE (upsert)
                for rec in gs_records:
                    conn.execute(text(
                        "INSERT OR REPLACE INTO group_stats (zip_code, property_type, stat_date, mean_ppsq, std_ppsq, count_listings) VALUES (:zip_code, :property_type, :stat_date, :mean_ppsq, :std_ppsq, :count_listings)"
                    ), rec)
            else:
                # PostgreSQL: ON CONFLICT DO UPDATE
                conn.execute(text(
                    "INSERT INTO group_stats (zip_code, property_type, stat_date, mean_ppsq, std_ppsq, count_listings) VALUES (:zip_code, :property_type, :stat_date, :mean_ppsq, :std_ppsq, :count_listings)"
                    " ON CONFLICT (zip_code, property_type, stat_date) DO UPDATE SET mean_ppsq = EXCLUDED.mean_ppsq, std_ppsq = EXCLUDED.std_ppsq, count_listings = EXCLUDED.count_listings"
                ), gs_records)

    # join stats back to listings and flag anomalies
    df = df.merge(stats, on=group_cols, how='left')
    df['is_anomaly'] = False
    df['anomaly_type'] = None

    def flag_row(r):
        if pd.isna(r['ppsq']) or pd.isna(r['mu']) or pd.isna(r['sigma']):
            return (False, None)
        upper = r['mu'] + THRESHOLD_MULTIPLIER * r['sigma']
        lower = r['mu'] - THRESHOLD_MULTIPLIER * r['sigma']
        if r['ppsq'] > upper:
            return (True, 'over-priced')
        elif r['ppsq'] < lower:
            return (True, 'under-priced')
        else:
            return (False, None)

    flags = df.apply(flag_row, axis=1, result_type='expand')
    df['is_anomaly'] = flags[0]
    df['anomaly_type'] = flags[1]

    # upsert into listing_analysis
    records = []
    for _, r in df.iterrows():
        records.append({
            'listing_id': r['listing_id'],
            'price_per_sqft': float(r['ppsq']) if not pd.isna(r['ppsq']) else None,
            'is_anomaly': bool(r['is_anomaly']),
            'anomaly_type': r['anomaly_type'],
            'mean_ppsq': float(r['mu']) if not pd.isna(r['mu']) else None,
            'std_ppsq': float(r['sigma']) if not pd.isna(r['sigma']) else None,
        })

    if records:
        with engine.begin() as conn:
            for rec in records:
                # add analyzed_at timestamp to record for DB-agnostic inserts
                rec['analyzed_at'] = datetime.utcnow().isoformat()
                if DB_DIALECT == 'sqlite':
                    # SQLite: INSERT OR REPLACE
                    conn.execute(text(
                        "INSERT OR REPLACE INTO listing_analysis(listing_id, price_per_sqft, is_anomaly, anomaly_type, mean_ppsq, std_ppsq, analyzed_at)"
                        " VALUES (:listing_id, :price_per_sqft, :is_anomaly, :anomaly_type, :mean_ppsq, :std_ppsq, :analyzed_at)"
                    ), rec)
                else:
                    # PostgreSQL: ON CONFLICT DO UPDATE
                    conn.execute(text(
                        "INSERT INTO listing_analysis(listing_id, price_per_sqft, is_anomaly, anomaly_type, mean_ppsq, std_ppsq, analyzed_at)"
                        " VALUES (:listing_id, :price_per_sqft, :is_anomaly, :anomaly_type, :mean_ppsq, :std_ppsq, :analyzed_at)"
                        " ON CONFLICT (listing_id) DO UPDATE SET price_per_sqft = EXCLUDED.price_per_sqft, is_anomaly = EXCLUDED.is_anomaly, anomaly_type = EXCLUDED.anomaly_type, mean_ppsq = EXCLUDED.mean_ppsq, std_ppsq = EXCLUDED.std_ppsq, analyzed_at = :analyzed_at"
                    ), rec)
    print(f'Analyzed {len(records)} listings for zip {zip_code}')


if __name__ == '__main__':
    zip_code = TARGET_ZIP or '12345'
    analyze_and_store(zip_code)
