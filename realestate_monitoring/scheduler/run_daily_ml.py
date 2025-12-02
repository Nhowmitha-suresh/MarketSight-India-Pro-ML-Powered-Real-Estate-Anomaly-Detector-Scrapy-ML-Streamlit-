"""
Enhanced Scheduler for MarketSight Real Estate Pipeline (v2.0)
Orchestrates: Scrape -> Analyze (ML) -> Report Generation
Uses APScheduler for reliable recurring jobs with full reporting.
"""

import os
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SCRAPE_INTERVAL_HOURS = int(os.getenv('SCRAPE_INTERVAL_HOURS', '24'))
TARGET_ZIP = os.getenv('TARGET_ZIP', '12345')

sched = BlockingScheduler()


def run_pipeline():
    """Execute complete pipeline: Scrape -> ML Analyze -> Report Generation"""
    try:
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings
        from analysis.analyze_ml import analyze_and_store
        from analysis.report import generate_report, print_report
        
        logger.info(f"\n{'='*80}")
        logger.info(f"[PIPELINE] Starting execution for ZIP: {TARGET_ZIP}")
        logger.info(f"[PIPELINE] Time: {datetime.utcnow().isoformat()}")
        logger.info(f"{'='*80}\n")
        
        # Step 1: Scrape
        logger.info("[STEP 1/3] Scraping listings from web...")
        try:
            settings = get_project_settings()
            process = CrawlerProcess(settings)
            process.crawl('listings', zip=TARGET_ZIP)
            process.start()
            logger.info("[✓] Scrape completed successfully\n")
        except Exception as e:
            logger.error(f"[✗] Scrape failed: {e}")
            return
        
        # Step 2: ML Analysis
        logger.info("[STEP 2/3] Running ML-based analysis...")
        try:
            report_data = analyze_and_store(TARGET_ZIP)
            logger.info("[✓] Analysis completed successfully")
            logger.info(f"    - Listings processed:   {report_data.get('total_new_listings', 0)}")
            logger.info(f"    - DQ failures:          {report_data.get('dq_failures', 0)}")
            logger.info(f"    - ML anomalies:         {report_data.get('ml_anomalies', 0)}")
            logger.info(f"    - Opportunities:        {report_data.get('ml_opportunities', 0)}")
            logger.info(f"    - Risks:                {report_data.get('ml_risks', 0)}\n")
        except Exception as e:
            logger.error(f"[✗] Analysis failed: {e}\n")
            return
        
        # Step 3: Generate Report
        logger.info("[STEP 3/3] Generating reports...")
        try:
            report_paths = generate_report(report_data, TARGET_ZIP, output_format='both')
            print_report(report_data, TARGET_ZIP)
            logger.info("[✓] Reports generated successfully:")
            for fmt, path in report_paths.items():
                logger.info(f"    - {fmt}: {path}\n")
        except Exception as e:
            logger.error(f"[✗] Report generation failed: {e}\n")
        
        logger.info(f"{'='*80}")
        logger.info("[PIPELINE] Execution COMPLETED")
        logger.info(f"{'='*80}\n")
        
    except Exception as e:
        logger.error(f"[PIPELINE ERROR] Unexpected error: {e}\n")


@sched.scheduled_job('interval', hours=SCRAPE_INTERVAL_HOURS, id='ml_pipeline_job')
def scheduled_pipeline():
    """APScheduler recurring job"""
    run_pipeline()


def start_scheduler():
    """Start the scheduler (blocking)"""
    try:
        logger.info("\n" + "="*80)
        logger.info("MarketSight Pro Scheduler v2.0 - Starting")
        logger.info("="*80 + "\n")
        
        # Run once immediately on startup
        logger.info("Running initial pipeline execution on startup...\n")
        run_pipeline()
        
        # Schedule recurring jobs
        logger.info("="*80)
        logger.info(f"Scheduler configured. Recurring every {SCRAPE_INTERVAL_HOURS} hours")
        logger.info("TARGET_ZIP:", TARGET_ZIP)
        logger.info("Next runs will include: Scrape -> ML Analysis -> Reports")
        logger.info("Press Ctrl+C to stop the scheduler")
        logger.info("="*80 + "\n")
        
        sched.start()
    except KeyboardInterrupt:
        logger.info("\n[SCHEDULER] Stopped by user (Ctrl+C)")
        sched.shutdown()
    except Exception as e:
        logger.error(f"[SCHEDULER ERROR] {e}")
        sched.shutdown()


if __name__ == '__main__':
    start_scheduler()
