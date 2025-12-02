"""
Setup helper for configuring the Real Estate Monitoring Pipeline.
"""
import os
import sys

def create_env_file():
    """Create a .env file from the template."""
    template = '.env.example'
    target = '.env'
    
    if os.path.exists(target):
        print(f'ℹ️  {target} already exists. Skipping...')
        return
    
    if not os.path.exists(template):
        print(f'❌ {template} not found.')
        return
    
    with open(template, 'r') as f:
        content = f.read()
    
    with open(target, 'w') as f:
        f.write(content)
    
    print(f'✅ Created {target} from {template}')
    print('\n📝 IMPORTANT: Edit .env and configure:')
    print('   - DATABASE_URL (PostgreSQL connection string)')
    print('   - TARGET_ZIP (the ZIP code to scrape)')


def print_setup_guide():
    """Print setup instructions."""
    guide = '''
╔════════════════════════════════════════════════════════════════════════════╗
║                  REAL ESTATE MONITORING PIPELINE SETUP                     ║
╚════════════════════════════════════════════════════════════════════════════╝

✅ WHAT WAS TESTED:
   ✓ Data ingestion & cleaning (Scrapy pipeline simulation)
   ✓ Price/sqft calculation & normalization
   ✓ Statistical analysis (mean, std deviation)
   ✓ Anomaly detection (1.5σ threshold)
   ✓ Database persistence
   ✓ Analysis result storage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 NEXT STEPS TO DEPLOY:

1️⃣  INSTALL DEPENDENCIES
    python -m venv .venv
    .venv\\Scripts\\Activate.ps1  # on Windows PowerShell
    pip install -r requirements.txt

2️⃣  CONFIGURE DATABASE
    Option A: Use PostgreSQL (Recommended)
      • Install PostgreSQL and create a database
      • Create .env and set DATABASE_URL
      • Run SQL schema:
        psql -U <user> -d <dbname> -f sql/create_tables.sql
    
    Option B: Use SQLite (For Testing)
      • Set DATABASE_URL to: sqlite:///./realestate.db
      • Schema tables are auto-created if not exists

3️⃣  CONFIGURE .env FILE
    Copy .env.example to .env and edit:
      DATABASE_URL=postgresql://user:password@localhost/realestate_db
      TARGET_ZIP=<your_target_zip>
      SCRAPE_INTERVAL_HOURS=24

4️⃣  CUSTOMIZE SCRAPER
    Edit realestate_scraper/spiders/listings_spider.py:
      • Update CSS selectors to match your target website
      • Modify SCRAPY_START_URL in .env
      • If site uses JavaScript, set USE_PLAYWRIGHT=True

5️⃣  RUN THE PIPELINE

    a) ONE-TIME SCRAPE:
       scrapy crawl listings -a zip=<target_zip>

    b) AUTOMATED DAILY SCRAPING:
       python scheduler/run_daily.py
       (keeps running; scrapes + analyzes every 24 hours)

    c) MANUAL ANALYSIS (after scraping):
       python analysis/analyze.py

    d) VIEW DASHBOARD:
       streamlit run app/streamlit_app.py
       (Open http://localhost:8501 in browser)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 DASHBOARD FEATURES:

  • Executive Overview: Total listings, anomalies, avg $/sqft, avg days on market
  • Anomaly Finder: Filterable list of under/over-priced properties
  • Market Trends: Time-series charts of market statistics
  • Alert Settings: Placeholder for custom alerts (future feature)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️  PROJECT STRUCTURE:

  realestate_monitoring/
  ├── realestate_scraper/          # Scrapy spider & pipelines
  │   ├── spiders/listings_spider.py
  │   ├── pipelines.py
  │   ├── items.py
  │   └── settings.py
  ├── analysis/
  │   └── analyze.py               # Statistical analysis & anomaly detection
  ├── scheduler/
  │   └── run_daily.py             # APScheduler for automated runs
  ├── app/
  │   ├── streamlit_app.py         # High-end dashboard UI
  │   └── utils.py                 # Helper functions
  ├── sql/
  │   └── create_tables.sql        # PostgreSQL schema
  ├── requirements.txt             # Python dependencies
  ├── .env.example                 # Template env vars
  ├── README.md                    # This file
  └── test_e2e.py                 # End-to-end test harness

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 QUICK TIPS:

  • Use test_e2e.py to validate your setup locally before deploying
  • The pipeline cleans & normalizes raw data automatically
  • Anomalies are flagged using statistical Z-score (1.5σ threshold)
  • Group stats are stored for time-series trending
  • Streamlit auto-caches queries for 5 minutes (configurable)
  • The scheduler can run 24/7 for continuous market monitoring

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  LEGAL & ETHICAL CONSIDERATIONS:

  • Always check robots.txt and terms of service before scraping
  • Respect rate limits (current: 1 sec delay, 8 concurrent requests)
  • Do not scrape sites that explicitly forbid automated access
  • Use official APIs when available
  • Consider obtaining explicit permission for commercial use
  • Ensure GDPR/privacy compliance when storing personal data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
'''
    print(guide)


if __name__ == '__main__':
    print('\n🚀 Setting up Real Estate Monitoring Pipeline...\n')
    create_env_file()
    print()
    print_setup_guide()
