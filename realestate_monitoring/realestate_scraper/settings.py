# Scrapy settings for realestate_scraper
BOT_NAME = 'realestate_scraper'

SPIDER_MODULES = ['realestate_scraper.spiders']
NEWSPIDER_MODULE = 'realestate_scraper.spiders'

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 1

ITEM_PIPELINES = {
    'realestate_scraper.pipelines.PostgresPipeline': 300,
}

# Optional Playwright settings (for dynamic sites). To use, set USE_PLAYWRIGHT=True in your env and install scrapy-playwright.
PLAYWRIGHT_LAUNCH_OPTIONS = {'headless': True}
