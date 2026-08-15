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

    def __repr__(self):
        return repr({"investor_slug": self.get("investor_slug"), "ticker": self.get("ticker"),
                      "quarter_date": self.get("quarter_date")})
