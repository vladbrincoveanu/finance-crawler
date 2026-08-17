import scrapy


class HoldingItem(scrapy.Item):
    investor_name = scrapy.Field()
    investor_source = scrapy.Field()
    investor_slug = scrapy.Field()
    investor_profile_url = scrapy.Field()

    ticker = scrapy.Field()
    company_name = scrapy.Field()

    quarter_date = scrapy.Field()  # ISO "YYYY-MM-DD"
    shares = scrapy.Field()
    value_usd = scrapy.Field()
    pct_portfolio = scrapy.Field()
    activity = scrapy.Field()  # buy | add | reduce | hold

    source_url = scrapy.Field()
    source_observation_key = scrapy.Field()
    document_hash = scrapy.Field()
    exchange = scrapy.Field()
    share_class = scrapy.Field()
    portfolio_manager_name = scrapy.Field()
    raw_payload = scrapy.Field()

    def __repr__(self):
        return repr({"investor_slug": self.get("investor_slug"), "ticker": self.get("ticker"),
                      "quarter_date": self.get("quarter_date")})
