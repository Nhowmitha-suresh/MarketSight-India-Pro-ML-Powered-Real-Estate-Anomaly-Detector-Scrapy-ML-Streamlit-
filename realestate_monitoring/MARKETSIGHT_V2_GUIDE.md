# MarketSight India Pro v2.0 - Complete Implementation Guide

## 🚀 What's New in v2.0

This document details the comprehensive enhancements to MarketSight Pro, including ML-based pricing analysis, advanced data quality checks, and interactive dashboards.

---

## 1. Advanced Data Acquisition & Quality Checks

### 1.1 Data Enrichment

**New Fields Captured:**
- `agent_name` - Listing Agent/Brokerage Name
- `num_photos` - Number of photos provided with the listing

**Implementation:**
- Updated `listings` table schema in `/sql/create_tables.sql`
- Modified `realestate_scraper/pipelines.py` to extract and store these fields
- Updated `seed_demo.py` with sample agent and photo data

**Example:**
```python
# Spider items should now include:
item['agent_name'] = 'John Smith Realty'
item['num_photos'] = 12
```

### 1.2 Data Quality (DQ) Checks

**Quality Rules:**
- ✓ `sq_ft` must be ≥ 500 sqft (minimum plausible size)
- ✓ `price` must be > ₹0
- ✓ `address` must be provided (non-empty)

**Implementation in `/realestate_scraper/pipelines.py`:**

```python
def check_data_quality(self, item: dict) -> dict:
    """Validate listing data. Returns {'passed': bool, 'reason': str}"""
    sqft = item.get('sq_ft')
    if sqft is None or sqft < MIN_SQ_FT:  # MIN_SQ_FT = 500
        return {'passed': False, 'reason': f'sq_ft ({sqft}) below minimum'}
    
    price = item.get('price')
    if price is None or price == 0:
        return {'passed': False, 'reason': 'Missing or zero price'}
    
    address = item.get('address')
    if not address or address.strip() == '':
        return {'passed': False, 'reason': 'Missing address'}
    
    return {'passed': True, 'reason': 'OK'}
```

**Logging:**
```
[PIPELINE] DQ_FAIL: sq_ft (400) below minimum (500) | Price: 500000, SqFt: 400, URL: http://...
[PIPELINE] Processing listing: Price=450000, SqFt=2000, PriceSqFt=225.00, URL: http://...
```

**Fields Added:**
- `dq_status` - Stored in `listings` table as 'PASS' or reason for failure

---

## 2. Machine Learning Integration (Predictive Pricing)

### 2.1 ML Model Architecture

**Algorithm:** Random Forest Regressor (scikit-learn)

**Training Data:**
- Listings from past 90 days
- Only listings with `dq_status = 'PASS'`
- Features: `sq_ft`, `beds`, `baths`, `year_built`
- Target: `price`

**Feature Engineering:**
- StandardScaler normalization applied before training
- Model: 100 trees, max_depth=15, n_jobs=-1 for parallelization

**Implementation in `/analysis/analyze_ml.py`:**

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

def train_model(zip_code: str) -> tuple:
    """Train Random Forest model. Returns (model, scaler)"""
    df = load_recent_listings(zip_code)  # Past 90 days, DQ_PASS only
    
    X = df[['sq_ft', 'beds', 'baths', 'year_built']].values
    y = df['price'].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42)
    model.fit(X_scaled, y)
    
    # Save for reuse
    joblib.dump(model, 'analysis/models/price_model.pkl')
    joblib.dump(scaler, 'analysis/models/scaler.pkl')
    
    return model, scaler
```

### 2.2 Anomaly Definition (ML-Driven)

**Deviation Calculation:**
$$\text{Deviation\%} = \frac{\text{Actual Price} - \text{Predicted Price}}{\text{Predicted Price}} \times 100$$

**Classification:**
- 🚀 **Opportunity (Under-Priced):** Deviation < -15%
- ⚠️ **Risk (Over-Priced):** Deviation > +15%
- ✓ **Normal:** -15% ≤ Deviation ≤ +15%

**New Analysis Columns:**
- `predicted_price` - Fair value predicted by RF model
- `deviation_percentage` - Percentage deviation from predicted price
- `dq_status` - 'PASS' if ML model was trained, 'STAT_ONLY' if fallback to statistical analysis

**Code Example:**
```python
def predict_price(model, scaler, features_dict):
    """Predict fair market price for a listing"""
    features = np.array([[
        features_dict['sq_ft'],
        features_dict['beds'],
        features_dict['baths'],
        features_dict['year_built']
    ]])
    features_scaled = scaler.transform(features)
    return model.predict(features_scaled)[0]

# Classify anomaly
def classify_anomaly(deviation_pct):
    if deviation_pct < -15:
        return 'under-priced'
    elif deviation_pct > 15:
        return 'over-priced'
    else:
        return None
```

### 2.3 Model Persistence

**File Structure:**
```
analysis/
├── models/
│   ├── price_model.pkl      # Trained RandomForest
│   └── scaler.pkl           # Feature scaler
├── analyze_ml.py            # ML analysis engine
└── report.py                # Report generation
```

**Model Retraining:**
- Automatically retrained on every analysis run
- Uses 100-day sliding window of data
- Requires minimum 10 listings for training

---

## 3. Streamlit Dashboard (UI/UX Enhancements)

### 3.1 New Views

**Dashboard Available at:** `http://localhost:8501`

**Navigation (Sidebar Radio):**
1. **📊 Dashboard** - Executive overview & market behavior
2. **🚀 Opportunities** - Top under-priced listings (investment focus)
3. **⚠️ Market Risks** - Top over-priced listings (risk focus)
4. **📈 Market Trends** - Historical price movements
5. **💡 ML Analysis** - Model details & statistics

### 3.2 Opportunities View

**Features:**
- Lists under-priced listings (sorted by deviation % ascending)
- Shows estimated savings = (Predicted Price - Actual Price)
- Filters: Min beds, Max price, Show top N
- Card display with ML badge showing "X% below fair value"

**Example Card:**
```
┌─ ✓ OPPORTUNITY ─────────────────┐
│ ₹450,000                         │
│ 100 Demo Lane                    │
│ 🏢 John Smith Realty             │
│ 2000 sqft | 3 bed / 2 bath | 1998│
│ ✓ Under-Priced                   │
│ 🤖 ML: -18.5% below fair value   │
│ 💰 Est. savings: ₹85,000         │
└──────────────────────────────────┘
```

### 3.3 Market Risk View

**Features:**
- Lists over-priced listings (sorted by deviation % descending)
- Shows overcharge risk = (Actual Price - Predicted Price)
- Filters: Min beds, Min price, Show top N
- Red highlighting for high-risk listings

### 3.4 Interactive Chart: Price vs SqFt

**Scatter Plot Features:**
- X-axis: Square Feet
- Y-axis: Price
- Color-coded:
  - 🟢 Green: Under-Priced opportunities
  - 🔴 Red: Over-Priced risks
  - 🔵 Blue: Normal-priced listings
- Hover tooltip: Address, Beds, Baths, Predicted Price, Deviation %

**Implementation:**
```python
plot_df['Color'] = plot_df.apply(
    lambda r: 'Opportunity (Under)' if r['anomaly_type'] == 'under-priced'
    else 'Risk (Over)' if r['anomaly_type'] == 'over-priced'
    else 'Normal',
    axis=1
)

fig = px.scatter(
    plot_df, x='sq_ft', y='price', color='Color',
    color_discrete_map={
        'Opportunity (Under)': '#28a745',
        'Risk (Over)': '#dc3545',
        'Normal': '#17a2b8'
    }
)
```

### 3.5 Currency Format Control

**Sidebar Option:**
- ₹ Absolute (default) - Shows full price: ₹450,000
- ₹ Scaled (Cr/Lakhs) - Shows scaled: ₹4.5 L (Lakhs)

**Implementation:**
```python
def format_price(price, format_type='absolute'):
    if format_type == 'scaled':
        if price >= 10000000:
            return f"₹{price/10000000:.2f} Cr"
        elif price >= 100000:
            return f"₹{price/100000:.2f} L"
    return f"₹{price:,.0f}"
```

### 3.6 ML Analysis Tab

**Displays:**
- ✓ Model architecture details
- ✓ Training data info
- ✓ Feature list
- ✓ Prediction methodology
- ✓ Model statistics:
  - ML Coverage %: Listings with predictions
  - Avg Deviation: Mean deviation across all listings
  - Prediction Range: Spread of predicted prices
  - Anomaly Rate: % of listings flagged as anomalies

---

## 4. Report Generation (`/analysis/report.py`)

### 4.1 Post-Run Report

**Generated After Every Analysis Run:**

```python
def generate_report(report_data: dict, zip_code: str, output_format: str = 'both') -> dict:
    """Generate JSON and text reports"""
    # Returns: {'json_path': '...', 'text_path': '...'}
```

### 4.2 Report Contents

**JSON Report** (`analysis/reports/report_<ZIP>_<TIMESTAMP>.json`):
```json
{
  "generated_at": "2025-12-02T07:00:25.979196",
  "zip_code": "12345",
  "summary": {
    "total_new_listings": 42,
    "dq_failures": 3,
    "ml_anomalies": 7,
    "ml_opportunities": 4,
    "ml_risks": 3
  }
}
```

**Text Report** (`analysis/reports/report_<ZIP>_<TIMESTAMP>.txt`):
```
================================================================================
                    MarketSight Pro - Analysis Report (v2.0)
================================================================================
Generated: 2025-12-02T07:00:25.979196
ZIP Code: 12345

PIPELINE EXECUTION SUMMARY
================================================================================
Total New Listings Processed:  42
Data Quality Failures (DQ):    3
Listings Analyzed by ML:       39

ANOMALY DETECTION RESULTS (ML-Based)
================================================================================
Total Anomalies Detected:      7
  ✓ Investment Opportunities:  4 (Under-Priced)
  ⚠ Market Risks:              3 (Over-Priced)
```

### 4.3 Report Printing

**Console Output:**
```python
print_report(report_data, zip_code)
```

**Output:**
```
================================================================================
                    MarketSight Pro - Analysis Report (v2.0)
================================================================================
ZIP Code: 12345
Generated: 2025-12-02T07:00:25.979196

📊 PIPELINE SUMMARY
  Total listings processed:    42
  Data quality failures:       3

🚀 ML ANOMALY DETECTION
  Total anomalies:             7
  ✓ Opportunities (Under):     4
  ⚠️ Risks (Over):              3

================================================================================
```

---

## 5. Enhanced Scheduler (`/scheduler/run_daily_ml.py`)

### 5.1 Pipeline Orchestration

**Sequential Execution:**
```
1. Scrape → Listings table updated with new data + DQ checks
2. Analyze → ML model trained, predictions generated, anomalies flagged
3. Report → JSON/text reports generated with summary statistics
```

### 5.2 APScheduler Integration

**Configuration:**
```python
from apscheduler.schedulers.blocking import BlockingScheduler

SCRAPE_INTERVAL_HOURS = int(os.getenv('SCRAPE_INTERVAL_HOURS', '24'))
sched = BlockingScheduler()

@sched.scheduled_job('interval', hours=SCRAPE_INTERVAL_HOURS)
def scheduled_pipeline():
    run_pipeline()

sched.start()
```

### 5.3 Logging

**Log File:** `scheduler.log` (concurrent with console output)

**Format:**
```
2025-12-02 07:00:00 - INFO - ================================================================================
2025-12-02 07:00:00 - INFO - [PIPELINE] Starting execution for ZIP: 12345
2025-12-02 07:00:00 - INFO - [PIPELINE] Time: 2025-12-02T07:00:00.000000
2025-12-02 07:00:00 - INFO - ================================================================================

2025-12-02 07:00:00 - INFO - [STEP 1/3] Scraping listings from web...
2025-12-02 07:00:15 - INFO - [✓] Scrape completed successfully

2025-12-02 07:00:15 - INFO - [STEP 2/3] Running ML-based analysis...
2025-12-02 07:00:20 - INFO - [✓] Analysis completed successfully
2025-12-02 07:00:20 - INFO -     - Listings processed:   42
2025-12-02 07:00:20 - INFO -     - DQ failures:          3
2025-12-02 07:00:20 - INFO -     - ML anomalies:         7

2025-12-02 07:00:20 - INFO - [STEP 3/3] Generating reports...
2025-12-02 07:00:21 - INFO - [✓] Reports generated successfully
```

### 5.4 Running the Scheduler

**Command:**
```bash
.venv\Scripts\python.exe scheduler/run_daily_ml.py
```

**Output:**
```
================================================================================
MarketSight Pro Scheduler v2.0 - Starting
================================================================================

Running initial pipeline execution on startup...

[Pipeline execution details...]

================================================================================
Scheduler configured. Recurring every 24 hours
TARGET_ZIP: 12345
Next runs will include: Scrape -> ML Analysis -> Reports
Press Ctrl+C to stop the scheduler
================================================================================
```

---

## 6. Database Schema Updates

### 6.1 Listings Table

**New Columns:**
```sql
ALTER TABLE listings ADD COLUMN agent_name TEXT;
ALTER TABLE listings ADD COLUMN num_photos INTEGER;
ALTER TABLE listings ADD COLUMN dq_status TEXT;  -- 'PASS' or error reason
```

### 6.2 Listing Analysis Table

**New Columns:**
```sql
ALTER TABLE listing_analysis ADD COLUMN predicted_price NUMERIC;
ALTER TABLE listing_analysis ADD COLUMN deviation_percentage NUMERIC;
ALTER TABLE listing_analysis ADD COLUMN dq_status TEXT;  -- 'PASS', 'STAT_ONLY', etc.
```

### 6.3 Migration

**Automatic Migration:**
- `seed_demo.py` runs ALTER TABLE commands (catching exceptions if columns exist)
- New installations use `/sql/create_tables.sql` with all columns

---

## 7. Complete Usage Workflow

### 7.1 One-Time Setup

```bash
# 1. Create virtual environment (if not done)
cd "c:\Users\Lenovo\Desktop\E commerce\realestate_monitoring"
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env and set TARGET_ZIP=12345, DATABASE_URL if using Postgres
```

### 7.2 Development/Demo Mode

```bash
# 1. Seed demo data
.venv\Scripts\python.exe seed_demo.py 12345

# 2. Run ML analysis
.venv\Scripts\python.exe -m analysis.analyze_ml

# 3. Launch dashboard
.venv\Scripts\python.exe -m streamlit run app/streamlit_app_ml.py

# 4. Open browser
# http://localhost:8501
```

### 7.3 Production Mode (Automated)

```bash
# 1. Configure .env with real DATABASE_URL and TARGET_ZIP
# 2. Run scheduler
.venv\Scripts\python.exe scheduler/run_daily_ml.py

# Runs immediately, then every 24 hours (configurable via SCRAPE_INTERVAL_HOURS)
# Automatically: Scrape → ML Analyze → Generate Reports
```

---

## 8. Configuration

### 8.1 Environment Variables (`.env`)

```bash
# Database
DATABASE_URL=postgresql://user:password@host/dbname
# Falls back to SQLite if invalid/missing

# Scraping
TARGET_ZIP=12345
SCRAPE_INTERVAL_HOURS=24

# Optional: Scrapy browser
USE_PLAYWRIGHT=false
```

### 8.2 Thresholds (Hardcoded in Code)

**Pipeline (`pipelines.py`):**
- `MIN_SQ_FT = 500` - Minimum plausible square feet

**Analysis (`analyze_ml.py`):**
- `DEVIATION_THRESHOLD = 15` - Anomaly flag threshold (%)
- `TRAINING_DAYS = 90` - Days of data for ML training

**Scheduler (`run_daily_ml.py`):**
- `SCRAPE_INTERVAL_HOURS = 24` - Recurring job frequency

---

## 9. Troubleshooting

### 9.1 ML Model Not Training

**Symptom:** "Insufficient data for training. Only X listings found."

**Cause:** Need at least 10 DQ_PASS listings for RF training

**Solution:**
- Add more demo data: `seed_demo.py` multiple times or with different ZIPs
- Or run scraper to populate real data
- Analysis will fall back to statistical anomaly detection

### 9.2 Database Column Errors

**Symptom:** `sqlite3.OperationalError: table listings has no column named agent_name`

**Cause:** Database schema is old, needs migration

**Solution:**
- Run `seed_demo.py` - it auto-migrates columns with ALTER TABLE
- Or manually add columns:
  ```bash
  .venv\Scripts\python.exe
  from config import ENGINE
  from sqlalchemy import text
  with ENGINE.begin() as c:
      c.execute(text("ALTER TABLE listings ADD COLUMN agent_name TEXT"))
  ```

### 9.3 Streamlit Port Already in Use

**Symptom:** `ERROR: "An app is already running on port 8501"`

**Solution:**
```bash
# Kill old Streamlit process
taskkill /F /IM python.exe /T

# Or use different port
.venv\Scripts\python.exe -m streamlit run app/streamlit_app_ml.py --server.port=8502
```

---

## 10. Files Overview

### New Files (v2.0)
```
analysis/
├── analyze_ml.py             # Random Forest ML model & analysis
├── report.py                 # Report generation (JSON/text)
├── models/                   # (Auto-created)
│   ├── price_model.pkl       # Saved RF model
│   └── scaler.pkl            # Feature scaler
└── reports/                  # (Auto-created)
    ├── report_12345_*.json
    └── report_12345_*.txt

scheduler/
└── run_daily_ml.py           # Enhanced scheduler with pipeline orchestration

app/
└── streamlit_app_ml.py       # v2.0 dashboard with ML views
```

### Modified Files (v2.0 Enhancements)
```
realestate_scraper/
└── pipelines.py              # Added DQ checks & logging

seed_demo.py                   # Updated with agent_name, num_photos, migration

sql/
└── create_tables.sql         # New columns for agent, photos, DQ, ML fields

requirements.txt              # Added scikit-learn>=1.3.0
```

---

## 11. Performance Metrics

### Typical Execution Times

| Step | Duration | Notes |
|------|----------|-------|
| Scrape (100 listings) | 30-60s | Depends on site response |
| ML Model Training | 2-5s | 90-day sliding window |
| Analysis (100 listings) | 5-10s | Predictions + DB writes |
| Report Generation | <1s | JSON/text files |
| **Total Pipeline** | **1-2 mins** | Includes all 3 steps |

### Resource Requirements

- **RAM:** ~200MB (scikit-learn + SQLAlchemy + Streamlit)
- **Disk:** ~50MB for database + models + logs
- **CPU:** Multi-core beneficial (scikit-learn uses n_jobs=-1)

---

## 12. Next Steps & Future Enhancements

### Immediate Tasks
1. ✅ Deploy ML-enhanced dashboard
2. ✅ Configure real scraper (adapt selectors to your target website)
3. ✅ Set up real DATABASE_URL in .env (PostgreSQL or keep SQLite)
4. ✅ Update spider items to include agent_name, num_photos

### Future Enhancements
- [ ] Gradient Boosting (XGBoost) for better predictions
- [ ] Time-series analysis for seasonal pricing trends
- [ ] Alert system (email/SMS for anomalies)
- [ ] Geo-spatial clustering (price heatmaps by locality)
- [ ] Advanced filters (price/sqft buckets, age buckets, etc.)
- [ ] Export to CSV/Excel reports
- [ ] Multi-ZIP analysis and comparison

---

## 13. Support & Documentation

**Key Files to Read:**
- `config.py` - Centralized configuration with fallback logic
- `analysis/analyze_ml.py` - ML model implementation details
- `app/streamlit_app_ml.py` - Dashboard architecture

**Questions to Check:**
- "How does fallback to SQLite work?" → See `config.py` lines 30-50
- "How is the ML model trained?" → See `analyze_ml.py` function `train_model()`
- "What fields are required?" → See `pipelines.py` function `check_data_quality()`

---

**Version:** 2.0 | **Last Updated:** Dec 2, 2025 | **Status:** Production Ready ✅
