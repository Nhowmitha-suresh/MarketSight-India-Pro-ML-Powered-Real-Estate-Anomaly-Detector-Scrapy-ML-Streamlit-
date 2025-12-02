# DEPLOYMENT & PRODUCTION CHECKLIST

## ✅ Pre-Deployment Verification

### Code Quality
- [x] All Python files follow PEP 8 conventions
- [x] Error handling implemented for database operations
- [x] Logging configured for debugging
- [x] Type hints added where applicable
- [x] SQL injection prevention (parameterized queries)

### Testing
- [x] End-to-end test passes (test_e2e.py)
- [x] Pipeline successfully:
  - [x] Ingests sample data (8 listings)
  - [x] Cleans & normalizes prices and sqft
  - [x] Computes price/sqft accurately
  - [x] Calculates group statistics (mean, std)
  - [x] Flags anomalies using 1.5σ threshold
  - [x] Stores results in database
- [x] Dashboard loads without errors

### Configuration
- [ ] .env file created and configured
- [ ] DATABASE_URL points to PostgreSQL instance
- [ ] TARGET_ZIP set to desired target
- [ ] PostgreSQL database created
- [ ] SQL schema deployed (create_tables.sql)

### Infrastructure
- [ ] PostgreSQL 12+ installed and running
- [ ] Python 3.9+ available
- [ ] Virtual environment created
- [ ] All dependencies installed
- [ ] File permissions correct

---

## 🚀 DEPLOYMENT STEPS

### Step 1: Prepare Environment
```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import scrapy, pandas, streamlit; print('✅ All imports successful')"
```

### Step 2: Configure Database
```powershell
# For PostgreSQL:
# 1. Create database
# createdb realestate_db

# 2. Apply schema
# psql -U username -d realestate_db -f sql/create_tables.sql

# For development/testing with SQLite:
# Set DATABASE_URL in .env to: sqlite:///./realestate.db
```

### Step 3: Configure Application
```powershell
# Copy template
Copy-Item .env.example .env

# Edit .env with your values:
# - DATABASE_URL (PostgreSQL connection)
# - TARGET_ZIP (ZIP code to scrape)
# - SCRAPE_INTERVAL_HOURS (default: 24)
```

### Step 4: Customize Scraper
Edit `realestate_scraper/spiders/listings_spider.py`:
- Update CSS selectors to match target website
- Modify start_url parameter
- Test with a small sample first
- For JavaScript-heavy sites, enable Playwright

### Step 5: Test Scraper
```powershell
# Run a test scrape
scrapy crawl listings -a zip=12345 -L INFO

# Verify data in database
# psql -c "SELECT COUNT(*) FROM listings;"
```

### Step 6: Run Analysis
```powershell
# Compute statistics and flag anomalies
python analysis/analyze.py
```

### Step 7: Launch Dashboard
```powershell
# Start Streamlit development server
streamlit run app/streamlit_app.py

# Access at http://localhost:8501
```

### Step 8 (Optional): Enable Automated Scheduling
```powershell
# Run scheduler in background (runs scrape + analysis daily)
python scheduler/run_daily.py

# Or schedule via Windows Task Scheduler / CRON (Linux)
```

---

## 📋 MONITORING & MAINTENANCE

### Daily
- [ ] Check dashboard for new anomalies
- [ ] Monitor database disk usage
- [ ] Review days_on_market trends

### Weekly
- [ ] Verify scraper is collecting data
- [ ] Check for anomalies in group statistics
- [ ] Review error logs (if any)

### Monthly
- [ ] Analyze market trends
- [ ] Adjust anomaly threshold if needed (currently 1.5σ)
- [ ] Backup database

### As Needed
- [ ] Update scraper selectors if target site changes
- [ ] Add new ZIP codes to TARGET_ZIP
- [ ] Adjust SCRAPE_INTERVAL_HOURS for market volatility

---

## 🐛 TROUBLESHOOTING

### Database Connection Error
```
Error: "DATABASE_URL not set"
Solution: Ensure .env exists and DATABASE_URL is correct format
  postgresql://user:password@host:5432/dbname
```

### Scraper Not Collecting Data
```
Solution 1: Update CSS selectors in listings_spider.py
Solution 2: Check if site requires JavaScript (enable Playwright)
Solution 3: Verify robots.txt and rate limiting rules
```

### No Anomalies Detected
```
Normal if market is stable. Check:
- Sample size (need >5 listings per property_type)
- Threshold setting (1.5σ is default)
- Price/sqft variance in your target market
```

### PostgreSQL Connection Issues
```
Solution 1: Verify PostgreSQL is running
Solution 2: Check credentials in DATABASE_URL
Solution 3: Ensure database and tables exist (run create_tables.sql)
Solution 4: Check firewall/network connectivity
```

### Streamlit App Won't Start
```
Solution 1: Verify pandas/plotly installed (pip install -r requirements.txt)
Solution 2: Check database connection (run test_e2e.py first)
Solution 3: Ensure port 8501 is available (default Streamlit port)
```

---

## 📊 EXPECTED RESULTS

After a successful scrape + analysis for a market with 100+ listings:

| Metric | Expected |
|--------|----------|
| Data Ingestion Rate | 1-2 listings/sec |
| Pipeline Success Rate | >95% |
| Anomalies Found | 5-15% of listings |
| Under-Priced | ~2-5% (best opportunities) |
| Over-Priced | ~3-10% (caution zone) |
| Avg Analysis Time | <5 seconds for 100 listings |

---

## 🔒 SECURITY BEST PRACTICES

1. **Database Security**
   - [ ] Use strong passwords in DATABASE_URL
   - [ ] Restrict database access to localhost/VPN only
   - [ ] Enable PostgreSQL SSL connections
   - [ ] Regularly backup database

2. **Scraper Security**
   - [ ] Respect robots.txt and rate limits
   - [ ] Set appropriate DOWNLOAD_DELAY
   - [ ] Rotate user agents
   - [ ] Never scrape personal data

3. **Application Security**
   - [ ] Use environment variables for secrets
   - [ ] Never commit .env to version control
   - [ ] Validate/sanitize all inputs
   - [ ] Keep dependencies updated

4. **Data Privacy**
   - [ ] Ensure compliance with local data protection laws
   - [ ] Don't store PII longer than necessary
   - [ ] Implement data retention policies
   - [ ] Audit data access logs

---

## 📞 SUPPORT & DOCUMENTATION

### Key Files
- `README.md` - Project overview
- `DEPLOYMENT.md` - This file
- `.env.example` - Configuration template
- `test_e2e.py` - End-to-end test harness
- `setup.py` - Setup helper script

### Running Tests
```powershell
# End-to-end test (no DB required)
python test_e2e.py

# Run analysis manually
python analysis/analyze.py

# View dashboard
streamlit run app/streamlit_app.py
```

### Getting Help
1. Check logs in terminal output
2. Run test_e2e.py to isolate issues
3. Review SQL schema in sql/create_tables.sql
4. Check Scrapy spider selectors match target site
5. Verify database connectivity

---

## 🎯 SUCCESS CRITERIA

The project is successfully deployed when:

1. ✅ Scraper runs without errors
2. ✅ Data is stored in PostgreSQL
3. ✅ Analysis completes and flags anomalies
4. ✅ Dashboard loads and displays data
5. ✅ Scheduler runs on schedule (if enabled)
6. ✅ User can identify market opportunities

---

**Last Updated:** December 2, 2025
**Version:** 1.0
**Status:** Production Ready ✨
