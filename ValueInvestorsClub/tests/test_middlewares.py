from types import SimpleNamespace

from scrapy.http import Request, Response, TextResponse
from twisted.internet.defer import Deferred

from ValueInvestorsClub.ValueInvestorsClub import settings
from ValueInvestorsClub.ValueInvestorsClub import middlewares
from ValueInvestorsClub.ValueInvestorsClub.middlewares import BanAwareThrottleMiddleware


def test_default_request_headers_do_not_advertise_brotli():
    assert settings.DEFAULT_REQUEST_HEADERS["Accept-Encoding"] == "gzip, deflate"


def test_ban_aware_middleware_precedes_default_retry_middleware():
    assert settings.DOWNLOADER_MIDDLEWARES[
        "ValueInvestorsClub.middlewares.BanAwareThrottleMiddleware"
    ] > 550


def test_binary_response_passes_through_without_text_attribute_error():
    middleware = BanAwareThrottleMiddleware()
    request = Request("https://hedgefollow.com/funds/Berkshire+Hathaway")
    response = Response(url=request.url, body=b"\x89PNG\r\n\x1a\n\x00\xff")

    assert not hasattr(response, "text")
    assert middleware.process_response(request, response) is response


def test_normal_cloudflare_turnstile_script_is_not_a_block_marker():
    middleware = BanAwareThrottleMiddleware()
    request = Request("https://hedgefollow.com/funds/Berkshire+Hathaway")
    response = TextResponse(
        url=request.url,
        body=b'<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script><script>challenge-platform</script>',
        encoding="utf-8",
    )

    assert middleware.process_response(request, response) is response


def test_blocked_response_schedules_retry_without_blocking_reactor(monkeypatch):
    middleware = BanAwareThrottleMiddleware()
    request = Request("https://hedgefollow.com/funds/Berkshire+Hathaway")
    response = Response(url=request.url, status=429, body=b"too many requests")
    scheduled = {}
    spider = SimpleNamespace(
        logger=SimpleNamespace(warning=lambda *args: None, error=lambda *args: None),
        crawler=SimpleNamespace(engine=SimpleNamespace(close_spider=lambda *args, **kwargs: None)),
    )

    monkeypatch.setattr(middlewares.random, "uniform", lambda _minimum, _maximum: 0)
    monkeypatch.setattr(
        middlewares,
        "reactor",
        SimpleNamespace(
            callLater=lambda delay, callback, *args: scheduled.update(
                delay=delay, callback=callback, args=args
            ),
        ),
        raising=False,
    )
    result = middleware.process_response(request, response, spider)

    assert isinstance(result, Deferred)
    assert scheduled["delay"] == 60
    assert scheduled["args"][0].meta["ban_retry_times"] == 1
