"""
MarketSight ML Analysis Module (v2.0)
- ML-based pricing using Random Forest
- Predictive pricing and anomaly detection
- Data quality reporting
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import text
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib

# Import shared ENGINE from config
from config import ENGINE

TARGET_ZIP = os.getenv('TARGET_ZIP')
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

engine = ENGINE
DB_DIALECT = engine.dialect.name if engine else 'sqlite'

# ML thresholds
DEVIATION_THRESHOLD = 15  # Flag as anomaly if deviation > 15%
MODEL_FILE = 'analysis/models/price_model.pkl'
SCALER_FILE = 'analysis/models/scaler.pkl'
MIN_TRAIN_SIZE = 500  # Minimum number of listings required to train ML model (v3.0 requirement)


def load_recent_listings(zip_code: str, days: int = 90):
    """Load listings from recent days for ML training"""
    since = datetime.utcnow() - timedelta(days=days)
    query = text(
        "SELECT * FROM listings WHERE zip_code = :zip AND scrape_timestamp >= :since AND dq_status = 'PASS'"
    )
    df = pd.read_sql(query, engine, params={'zip': zip_code, 'since': since})
    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare features for ML model"""
    df = df.copy()
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['sq_ft'] = pd.to_numeric(df['sq_ft'], errors='coerce')
    df['beds'] = pd.to_numeric(df['beds'], errors='coerce')
    df['baths'] = pd.to_numeric(df['baths'], errors='coerce')
    df['year_built'] = pd.to_numeric(df['year_built'], errors='coerce')
    
    # Remove invalid rows
    df = df[(df['sq_ft'] > 0) & (df['price'] > 0) & (df['beds'] > 0)]
    
    # Fill missing values
    df['beds'] = df['beds'].fillna(df['beds'].median())
    df['baths'] = df['baths'].fillna(df['baths'].median())
    df['year_built'] = df['year_built'].fillna(df['year_built'].median())
    
    return df


def train_model(zip_code: str) -> tuple:
    """Train Random Forest model on historical data"""
    df = load_recent_listings(zip_code)
    if df.empty:
        logger.warning("No listings found for training.")
        return None, None
    
    df = prepare_features(df)

    if df.empty:
        logger.error("No valid data after feature preparation")
        return None, None

    # Enforce minimum training size for v3.0
    if len(df) < MIN_TRAIN_SIZE:
        logger.warning(f"Insufficient data for training. Found {len(df)} listings; need at least {MIN_TRAIN_SIZE} to train.")
        return None, None

    # Features for model
    features = ['sq_ft', 'beds', 'baths', 'year_built']
    X = df[features].values
    y = df['price'].values
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train Random Forest
    model = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
    model.fit(X_scaled, y)
    
    logger.info(f"Model trained on {len(df)} listings. R² Score: {model.score(X_scaled, y):.3f}")
    
    # Save model
    models_dir = os.path.join('analysis', 'models')
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(model, os.path.join(models_dir, os.path.basename(MODEL_FILE)))
    joblib.dump(scaler, os.path.join(models_dir, os.path.basename(SCALER_FILE)))
    logger.info(f"Model saved to {MODEL_FILE}")
    
    return model, scaler


def predict_price(model, scaler, features_dict: dict) -> float:
    """Predict price for a listing"""
    if model is None or scaler is None:
        return None
    
    features = np.array([[
        features_dict.get('sq_ft', 0),
        features_dict.get('beds', 0),
        features_dict.get('baths', 0),
        features_dict.get('year_built', 2000)
    ]])
    
    features_scaled = scaler.transform(features)
    predicted_price = model.predict(features_scaled)[0]
    return max(predicted_price, 0)  # Ensure non-negative


def calculate_deviation(actual_price: float, predicted_price: float) -> float:
    """Calculate percentage deviation from predicted price"""
    if predicted_price == 0:
        return 0
    return ((actual_price - predicted_price) / predicted_price) * 100


def analyze_and_store(zip_code: str) -> dict:
    """Run full ML analysis pipeline and store results. Returns summary report."""
    
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'zip_code': zip_code,
        'total_new_listings': 0,
        'dq_failures': 0,
        'model_trained': False,
        'ml_anomalies': 0,
        'ml_opportunities': 0,
        'ml_risks': 0
    }
    
    # Count DQ failures
    query_dq = text("SELECT COUNT(*) as cnt FROM listings WHERE zip_code = :zip AND dq_status != 'PASS'")
    result = engine.execute(query_dq, {'zip': zip_code}) if hasattr(engine, 'execute') else None
    if result is None:
        with engine.connect() as conn:
            result = conn.execute(query_dq, {'zip': zip_code})
            dq_count = result.fetchone()[0]
    else:
        dq_count = result.fetchone()[0]
    report['dq_failures'] = dq_count
    logger.info(f"DQ Failures: {dq_count}")
    
    # Train ML model
    logger.info("Training ML model...")
    model, scaler = train_model(zip_code)
    if model is None:
        logger.warning("Could not train model; proceeding with statistical analysis only")
        report['model_trained'] = False
    else:
        report['model_trained'] = True
    
    # Load all listings (including DQ_PASS)
    df = load_recent_listings(zip_code)
    if df.empty:
        logger.warning('No data to analyze')
        return report
    
    df = prepare_features(df)
    report['total_new_listings'] = len(df)
    
    # Make predictions for ML-based anomalies
    if model is not None:
        df['predicted_price'] = df.apply(
            lambda r: predict_price(model, scaler, {
                'sq_ft': r['sq_ft'],
                'beds': r['beds'],
                'baths': r['baths'],
                'year_built': r['year_built']
            }),
            axis=1
        )
        df['deviation_percentage'] = df.apply(
            lambda r: calculate_deviation(r['price'], r['predicted_price']),
            axis=1
        )
        df['is_anomaly'] = df['deviation_percentage'].abs() > DEVIATION_THRESHOLD
        df['anomaly_type'] = df.apply(
            lambda r: 'over-priced' if r['deviation_percentage'] > DEVIATION_THRESHOLD else (
                'under-priced' if r['deviation_percentage'] < -DEVIATION_THRESHOLD else None
            ),
            axis=1
        )
    else:
        # Fallback to statistical analysis
        df['predicted_price'] = None
        df['deviation_percentage'] = None
        df['is_anomaly'] = False
        df['anomaly_type'] = None
    
    # Statistical analysis (for comparison)
    df['price_per_sqft'] = df['price'] / df['sq_ft']
    group_stats = df.groupby('property_type')['price_per_sqft'].agg(['mean', 'std']).reset_index()
    df = df.merge(group_stats, on='property_type', how='left')
    
    # Upsert into listing_analysis
    records = []
    anomaly_count = 0
    opportunity_count = 0
    risk_count = 0
    
    for _, r in df.iterrows():
        is_anom = r['is_anomaly'] if not pd.isna(r['is_anomaly']) else False
        if is_anom:
            anomaly_count += 1
            if r['anomaly_type'] == 'under-priced':
                opportunity_count += 1
            elif r['anomaly_type'] == 'over-priced':
                risk_count += 1
        
        records.append({
            'listing_id': r['listing_id'],
            'price_per_sqft': float(r['price_per_sqft']) if not pd.isna(r['price_per_sqft']) else None,
            'is_anomaly': bool(is_anom),
            'anomaly_type': r['anomaly_type'],
            'mean_ppsq': float(r['mean']) if not pd.isna(r['mean']) else None,
            'std_ppsq': float(r['std']) if not pd.isna(r['std']) else None,
            'predicted_price': float(r['predicted_price']) if (model is not None and not pd.isna(r['predicted_price'])) else None,
            'deviation_percentage': float(r['deviation_percentage']) if (model is not None and not pd.isna(r['deviation_percentage'])) else None,
            # dq_status reflects model analysis status for this run; STAT_ONLY when model skipped
            'dq_status': 'PASS' if model is not None else 'STAT_ONLY'
        })
    
    # Batch insert/update
    if records:
        with engine.begin() as conn:
            for rec in records:
                rec['analyzed_at'] = datetime.utcnow().isoformat()
                
                if DB_DIALECT == 'sqlite':
                    # SQLite: INSERT OR REPLACE
                    conn.execute(text(
                        "INSERT OR REPLACE INTO listing_analysis(listing_id, price_per_sqft, is_anomaly, anomaly_type, mean_ppsq, std_ppsq, predicted_price, deviation_percentage, dq_status, analyzed_at)"
                        " VALUES (:listing_id, :price_per_sqft, :is_anomaly, :anomaly_type, :mean_ppsq, :std_ppsq, :predicted_price, :deviation_percentage, :dq_status, :analyzed_at)"
                    ), rec)
                else:
                    # PostgreSQL: ON CONFLICT DO UPDATE
                    conn.execute(text(
                        "INSERT INTO listing_analysis(listing_id, price_per_sqft, is_anomaly, anomaly_type, mean_ppsq, std_ppsq, predicted_price, deviation_percentage, dq_status, analyzed_at)"
                        " VALUES (:listing_id, :price_per_sqft, :is_anomaly, :anomaly_type, :mean_ppsq, :std_ppsq, :predicted_price, :deviation_percentage, :dq_status, :analyzed_at)"
                        " ON CONFLICT (listing_id) DO UPDATE SET price_per_sqft = EXCLUDED.price_per_sqft, is_anomaly = EXCLUDED.is_anomaly, anomaly_type = EXCLUDED.anomaly_type, mean_ppsq = EXCLUDED.mean_ppsq, std_ppsq = EXCLUDED.std_ppsq, predicted_price = EXCLUDED.predicted_price, deviation_percentage = EXCLUDED.deviation_percentage, dq_status = EXCLUDED.dq_status, analyzed_at = :analyzed_at"
                    ), rec)
    
    report['ml_anomalies'] = anomaly_count
    report['ml_opportunities'] = opportunity_count
    report['ml_risks'] = risk_count
    
    logger.info(f"Analysis complete: {len(records)} listings analyzed")
    logger.info(f"Anomalies detected: {anomaly_count} (Opportunities: {opportunity_count}, Risks: {risk_count})")
    
    return report


if __name__ == '__main__':
    zip_code = TARGET_ZIP or '12345'
    report = analyze_and_store(zip_code)
    print(f"\n=== Analysis Report for ZIP {zip_code} ===")
    for key, value in report.items():
        print(f"{key}: {value}")
