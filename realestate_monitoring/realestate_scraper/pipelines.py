import os
import re
import hashlib
import logging
from datetime import datetime
from typing import Optional

from itemadapter import ItemAdapter
from sqlalchemy import text

# Import the shared ENGINE from config.py
from config import ENGINE

price_re = re.compile(r"[^0-9.]")
sqft_re = re.compile(r"[0-9,.]+")

# Data quality thresholds
MIN_SQ_FT = 500  # minimum plausible sqft
logger = logging.getLogger(__name__)


class PostgresPipeline:
    """Cleans items and inserts into PostgreSQL listings table.

    Expects environment variable DATABASE_URL.
    Includes data quality checks and enhanced logging.
    """

    def open_spider(self, spider):
        if ENGINE is None:
            raise RuntimeError('DATABASE_URL/ENGINE is not configured. Please configure DATABASE_URL in .env and re-run.')
        self.engine = ENGINE
        self.dq_fail_count = 0
        self.success_count = 0
        logger.info(f"PostgresPipeline opened for spider: {spider.name}")

    def close_spider(self, spider):
        logger.info(f"PostgresPipeline closed. Success: {self.success_count}, DQ Failures: {self.dq_fail_count}")
        return

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        cleaned = self.clean_item(adapter.as_dict())
        
        # Data Quality Check
        dq_result = self.check_data_quality(cleaned)
        if not dq_result['passed']:
            cleaned['dq_status'] = dq_result['reason']
            self.dq_fail_count += 1
            logger.warning(f"DQ_FAIL: {dq_result['reason']} | Price: {cleaned.get('price')}, SqFt: {cleaned.get('sq_ft')}, URL: {cleaned.get('listing_url')}")
            # Still insert but mark as failed for auditing
            self.upsert_listing(cleaned)
            return item
        
        # Compute price_per_sqft and basic locality extraction
        try:
            cleaned['price_per_sqft'] = float(cleaned['price']) / float(cleaned['sq_ft']) if (cleaned.get('price') and cleaned.get('sq_ft')) else None
        except Exception:
            cleaned['price_per_sqft'] = None

        # Extract city/locality if available, fallback to zip_code/local part of address
        if not cleaned.get('city'):
            # naive extraction: last token after comma
            addr = cleaned.get('address') or ''
            parts = [p.strip() for p in addr.split(',') if p.strip()]
            cleaned['city'] = parts[-1] if parts else None
        if not cleaned.get('locality'):
            addr = cleaned.get('address') or ''
            parts = [p.strip() for p in addr.split(',') if p.strip()]
            cleaned['locality'] = parts[0] if parts else cleaned.get('zip_code')

        # Log successful item processing
        self.success_count += 1
        price = cleaned.get('price')
        sqft = cleaned.get('sq_ft')
        ppsq = cleaned.get('price_per_sqft')
        logger.info(f"Processing listing: Price={price}, SqFt={sqft}, PriceSqFt={ppsq:.2f if ppsq else 'N/A'}, URL={cleaned.get('listing_url')}")
        
        cleaned['dq_status'] = 'PASS'
        self.upsert_listing(cleaned)
        return item

    def clean_item(self, raw: dict) -> dict:
        item = raw.copy()
        
        # normalize price
        price = item.get('price')
        if isinstance(price, str):
            price_val = float(price_re.sub('', price)) if price else None
        else:
            price_val = float(price) if price is not None else None
        item['price'] = price_val

        # sqft
        sqft = item.get('sq_ft')
        if isinstance(sqft, str):
            m = sqft_re.search(sqft)
            item['sq_ft'] = int(m.group(0).replace(',', '')) if m else None
        else:
            item['sq_ft'] = int(sqft) if sqft is not None else None

        # numeric conversions
        for fld in ('beds', 'baths', 'year_built', 'days_on_market', 'num_photos'):
            v = item.get(fld)
            try:
                if v is None or v == '':
                    item[fld] = None
                else:
                    item[fld] = int(float(str(v).strip()))
            except Exception:
                item[fld] = None

        # agent_name (string, default None)
        agent_name = item.get('agent_name')
        if agent_name and isinstance(agent_name, str):
            item['agent_name'] = agent_name.strip() if agent_name.strip() else None
        else:
            item['agent_name'] = None

        # listing_id fallback based on URL
        if not item.get('listing_id'):
            url = item.get('listing_url', '')
            item['listing_id'] = hashlib.sha1(url.encode('utf-8')).hexdigest() if url else None

        # scrape timestamp
        st = item.get('scrape_timestamp')
        if not st:
            item['scrape_timestamp'] = datetime.utcnow()
        elif isinstance(st, str):
            try:
                item['scrape_timestamp'] = datetime.fromisoformat(st)
            except Exception:
                item['scrape_timestamp'] = datetime.utcnow()

        return item

    def check_data_quality(self, item: dict) -> dict:
        """Validate listing data quality. Returns {'passed': bool, 'reason': str}"""
        
        # Check sq_ft
        sqft = item.get('sq_ft')
        if sqft is None or sqft == '':
            return {'passed': False, 'reason': 'Missing sq_ft'}
        if sqft < MIN_SQ_FT:
            return {'passed': False, 'reason': f'sq_ft ({sqft}) below minimum ({MIN_SQ_FT})'}
        
        # Check price
        price = item.get('price')
        if price is None or price == 0:
            return {'passed': False, 'reason': 'Missing or zero price'}
        
        # Check address
        address = item.get('address')
        if not address or not isinstance(address, str) or address.strip() == '':
            return {'passed': False, 'reason': 'Missing address'}
        
        return {'passed': True, 'reason': 'OK'}

    def upsert_listing(self, item: dict):
        """Use a named-parameter SQL statement and SQLAlchemy connection for upsert"""
        sql = text(
            """
            INSERT INTO listings(
                listing_id, price, beds, baths, sq_ft, year_built, price_per_sqft, property_type,
                days_on_market, address, city, locality, zip_code, listing_url, agent_name, num_photos, dq_status, scrape_timestamp
            ) VALUES (
                :listing_id, :price, :beds, :baths, :sq_ft, :year_built, :price_per_sqft, :property_type,
                :days_on_market, :address, :city, :locality, :zip_code, :listing_url, :agent_name, :num_photos, :dq_status, :scrape_timestamp
            )
            ON CONFLICT (listing_id) DO UPDATE SET
                price = EXCLUDED.price,
                beds = EXCLUDED.beds,
                baths = EXCLUDED.baths,
                sq_ft = EXCLUDED.sq_ft,
                price_per_sqft = EXCLUDED.price_per_sqft,
                year_built = EXCLUDED.year_built,
                property_type = EXCLUDED.property_type,
                days_on_market = EXCLUDED.days_on_market,
                address = EXCLUDED.address,
                city = EXCLUDED.city,
                locality = EXCLUDED.locality,
                zip_code = EXCLUDED.zip_code,
                listing_url = EXCLUDED.listing_url,
                agent_name = EXCLUDED.agent_name,
                num_photos = EXCLUDED.num_photos,
                dq_status = EXCLUDED.dq_status,
                scrape_timestamp = EXCLUDED.scrape_timestamp;
            """
        )

        params = {
            'listing_id': item.get('listing_id'),
            'price': item.get('price'),
            'beds': item.get('beds'),
            'baths': item.get('baths'),
            'sq_ft': item.get('sq_ft'),
            'price_per_sqft': item.get('price_per_sqft'),
            'year_built': item.get('year_built'),
            'property_type': item.get('property_type'),
            'days_on_market': item.get('days_on_market'),
            'address': item.get('address'),
            'city': item.get('city'),
            'locality': item.get('locality'),
            'zip_code': item.get('zip_code'),
            'listing_url': item.get('listing_url'),
            'agent_name': item.get('agent_name'),
            'num_photos': item.get('num_photos'),
            'dq_status': item.get('dq_status', 'UNKNOWN'),
            'scrape_timestamp': item.get('scrape_timestamp')
        }

        try:
            with self.engine.begin() as conn:
                conn.execute(sql, params)
        except Exception as e:
            logger.error(f"Failed to upsert listing {item.get('listing_id')}: {e}")
            raise

