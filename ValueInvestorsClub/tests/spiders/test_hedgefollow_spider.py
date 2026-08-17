from ValueInvestorsClub.ValueInvestorsClub.spiders.HedgeFollowSpider import HedgeFollowSpider


def test_hedgefollow_spider_starts_selected_berkshire_fund():
    spider = HedgeFollowSpider(fund="Berkshire Hathaway")

    requests = list(spider.start_requests())

    assert len(requests) == 1
    assert requests[0].url == "https://hedgefollow.com/funds/Berkshire+Hathaway"
