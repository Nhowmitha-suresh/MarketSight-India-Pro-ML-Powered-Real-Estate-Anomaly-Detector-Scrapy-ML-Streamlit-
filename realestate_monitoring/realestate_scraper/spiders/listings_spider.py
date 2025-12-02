import os
import scrapy
from datetime import datetime
from urllib.parse import urljoin

from realestate_scraper.items import ListingItem

# NOTE: This spider uses placeholder selectors for demonstration.
# You MUST update the CSS/XPath selectors to match your target site's page structure.
# If the site renders with JavaScript, set USE_PLAYWRIGHT=True in your environment and
# adapt this spider to use the scrapy-playwright integration.

class ListingsSpider(scrapy.Spider):
    name = 'listings'
    custom_settings = {}

    def start_requests(self):
        target_zip = getattr(self, 'zip', os.getenv('TARGET_ZIP'))
        mode = getattr(self, 'mode', os.getenv('SCRAPY_MODE', 'live'))

        # Demo mode: generate synthetic listings locally without performing HTTP requests
        if str(mode).lower() == 'demo':
            for item in self._generate_demo_listings(target_zip):
                yield item
            return

        start_url_template = os.getenv('SCRAPY_START_URL', 'https://example-realestate.com/search?zip={zip}')
        start_url = start_url_template.format(zip=target_zip)
        yield scrapy.Request(start_url, callback=self.parse_listing_page)

    def _generate_demo_listings(self, zip_code):
        """Yield a few synthetic ListingItem objects for local testing/demo mode."""
        now = datetime.utcnow().isoformat()
        samples = [
            {'listing_id': 'demo_001', 'price': '$450,000', 'beds': '3', 'baths': '2', 'sq_ft': '2,000', 'year_built': '1998', 'property_type': 'House', 'days_on_market': '5', 'address': '100 Demo Lane', 'zip_code': zip_code, 'listing_url': 'http://demo/listing/001', 'scrape_timestamp': now},
            {'listing_id': 'demo_002', 'price': '$550,000', 'beds': '4', 'baths': '3', 'sq_ft': '2,500', 'year_built': '2005', 'property_type': 'House', 'days_on_market': '12', 'address': '200 Demo Ave', 'zip_code': zip_code, 'listing_url': 'http://demo/listing/002', 'scrape_timestamp': now},
            {'listing_id': 'demo_003', 'price': '$350,000', 'beds': '3', 'baths': '2', 'sq_ft': '2,200', 'year_built': '1985', 'property_type': 'House', 'days_on_market': '2', 'address': '300 Demo Blvd', 'zip_code': zip_code, 'listing_url': 'http://demo/listing/003', 'scrape_timestamp': now},
            {'listing_id': 'demo_004', 'price': '$750,000', 'beds': '5', 'baths': '4', 'sq_ft': '1,800', 'year_built': '2018', 'property_type': 'House', 'days_on_market': '30', 'address': '400 Demo Rd', 'zip_code': zip_code, 'listing_url': 'http://demo/listing/004', 'scrape_timestamp': now},
            {'listing_id': 'demo_005', 'price': '$500,000', 'beds': '4', 'baths': '3', 'sq_ft': '2,100', 'year_built': '2010', 'property_type': 'House', 'days_on_market': '8', 'address': '500 Demo St', 'zip_code': zip_code, 'listing_url': 'http://demo/listing/005', 'scrape_timestamp': now},
            {'listing_id': 'demo_006', 'price': '$520,000', 'beds': '4', 'baths': '2', 'sq_ft': '2,050', 'year_built': '2000', 'property_type': 'House', 'days_on_market': '7', 'address': '600 Demo Cir', 'zip_code': zip_code, 'listing_url': 'http://demo/listing/006', 'scrape_timestamp': now},
            {'listing_id': 'demo_007', 'price': '$300,000', 'beds': '2', 'baths': '1', 'sq_ft': '1,000', 'year_built': '1995', 'property_type': 'Condo', 'days_on_market': '4', 'address': '700 Demo Pl', 'zip_code': zip_code, 'listing_url': 'http://demo/listing/007', 'scrape_timestamp': now},
            {'listing_id': 'demo_008', 'price': '$320,000', 'beds': '2', 'baths': '1', 'sq_ft': '1,100', 'year_built': '2002', 'property_type': 'Condo', 'days_on_market': '6', 'address': '800 Demo Way', 'zip_code': zip_code, 'listing_url': 'http://demo/listing/008', 'scrape_timestamp': now},
        ]
        for s in samples:
            item = ListingItem()
            for k, v in s.items():
                item[k] = v
            yield item

    def parse_listing_page(self, response):
        # Example listing blocks selector - replace with actual selector
        listing_blocks = response.css('.listing')
        for b in listing_blocks:
            item = ListingItem()
            # Replace these selectors to match the real page
            item['listing_id'] = b.attrib.get('data-id') or None
            item['price'] = b.css('.price::text').get()
            item['beds'] = b.css('.beds::text').re_first(r"\d+")
            item['baths'] = b.css('.baths::text').re_first(r"\d+")
            item['sq_ft'] = b.css('.sqft::text').get()
            item['year_built'] = b.css('.year::text').get()
            item['property_type'] = b.css('.ptype::text').get()
            item['days_on_market'] = b.css('.dom::text').re_first(r"\d+")
            item['address'] = b.css('.address::text').get()
            # attempt to parse zip code from address or set from argument
            item['zip_code'] = b.css('.zip::text').get() or getattr(self, 'zip', os.getenv('TARGET_ZIP'))
            rel_url = b.css('a::attr(href)').get()
            item['listing_url'] = urljoin(response.url, rel_url) if rel_url else response.url
            item['scrape_timestamp'] = datetime.utcnow().isoformat()
            yield item

        # Pagination - replace selector with site's next page link
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_listing_page)
