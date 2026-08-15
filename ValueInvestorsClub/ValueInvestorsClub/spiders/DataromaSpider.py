import scrapy


class DataromaSpider(scrapy.Spider):
    name = "DataromaSpider"
    allowed_domains = ["dataroma.com"]
    start_urls = ["https://www.dataroma.com/m/home.php"]

    async def start(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse_home)

    def parse_home(self, response):
        for link in response.xpath("//li/a[contains(@href, 'holdings.php?m=')]"):
            href = link.xpath("./@href").get() or ""
            slug = href.split("m=", 1)[-1]
            name = (link.xpath("./text()").get() or "").strip()
            if not slug or not name:
                continue
            yield scrapy.Request(
                response.urljoin(href),
                callback=self.parse_holdings,
                meta={
                    "investor_slug": slug,
                    "investor_name": name,
                    "investor_profile_url": response.urljoin(href),
                },
            )

    def parse_holdings(self, response):
        investor_slug = response.meta["investor_slug"]
        for row in response.xpath("//table[@id='grid']/tbody/tr"):
            hist_href = row.xpath("./td[@class='hist']/a/@href").get()
            ticker = row.xpath("./td[@class='stock']/a/text()").get()
            company_name = row.xpath("./td[@class='stock']/a/span/text()").get() or ""
            if not hist_href or not ticker:
                continue
            yield scrapy.Request(
                response.urljoin(hist_href),
                callback=self.parse_stock_history,
                meta={
                    "investor_slug": investor_slug,
                    "investor_name": response.meta["investor_name"],
                    "investor_profile_url": response.meta["investor_profile_url"],
                    "ticker": ticker.strip(),
                    "company_name": company_name.lstrip("- ").strip(),
                },
            )

    def parse_stock_history(self, response):
        # Implemented in Task 5
        return
        yield  # pragma: no cover
