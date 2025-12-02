import scrapy

class ListingItem(scrapy.Item):
    listing_id = scrapy.Field()
    price = scrapy.Field()
    beds = scrapy.Field()
    baths = scrapy.Field()
    sq_ft = scrapy.Field()
    year_built = scrapy.Field()
    property_type = scrapy.Field()
    days_on_market = scrapy.Field()
    address = scrapy.Field()
    zip_code = scrapy.Field()
    listing_url = scrapy.Field()
    scrape_timestamp = scrapy.Field()
