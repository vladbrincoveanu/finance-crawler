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
        # Implemented in Task 4
        return
        yield  # pragma: no cover
