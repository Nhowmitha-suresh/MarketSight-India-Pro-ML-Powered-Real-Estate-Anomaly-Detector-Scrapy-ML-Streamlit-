import os
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from analysis.analyze import analyze_and_store

SCRAPE_INTERVAL_HOURS = int(os.getenv('SCRAPE_INTERVAL_HOURS', '24'))
TARGET_ZIP = os.getenv('TARGET_ZIP')

sched = BlockingScheduler()


def run_spider():
    print(f"Starting scrape at {datetime.utcnow().isoformat()} for zip {TARGET_ZIP}")
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl('listings', zip=TARGET_ZIP)
    process.start()  # blocks until finished
    print('Scrape finished, running analysis...')
    analyze_and_store(TARGET_ZIP)


@sched.scheduled_job('interval', hours=SCRAPE_INTERVAL_HOURS)
def scheduled_job():
    try:
        run_spider()
    except Exception as e:
        print('Error during scheduled run:', e)


if __name__ == '__main__':
    # run once immediately
    run_spider()
    print(f'Scheduling recurring runs every {SCRAPE_INTERVAL_HOURS} hours')
    sched.start()
