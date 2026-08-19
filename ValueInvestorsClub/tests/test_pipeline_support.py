from types import SimpleNamespace

from ValueInvestorsClub.ValueInvestorsClub.pipeline_support import scrapy_close_reason


def test_shutdown_is_recorded_as_an_interrupted_crawl():
    spider = SimpleNamespace(
        crawler=SimpleNamespace(
            stats=SimpleNamespace(get_value=lambda key: "shutdown"),
        ),
    )

    assert scrapy_close_reason(spider) == "shutdown"
