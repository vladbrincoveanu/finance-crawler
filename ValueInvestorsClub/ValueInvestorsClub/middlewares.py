# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import os
import random

from scrapy import signals
from scrapy.exceptions import IgnoreRequest
from scrapy_user_agents.middlewares import RandomUserAgentMiddleware
from twisted.internet import reactor
from twisted.internet.defer import Deferred

# useful for handling different item types with a single interface


class ValueinvestorsclubSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class ValueinvestorsclubDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class CompatRandomUserAgentMiddleware(RandomUserAgentMiddleware):
    def process_request(self, request, spider=None):
        return super().process_request(request, spider)


class ModernUserAgentMiddleware:
    """
    Use a modern, realistic user agent instead of old/random ones.
    Enabled via MODERN_USER_AGENT=true env var.
    """
    
    def __init__(self):
        self.enabled = os.getenv("MODERN_USER_AGENT", "true").lower() in {"1", "true", "yes"}
        self.user_agent = os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    
    def process_request(self, request, spider=None):
        if self.enabled:
            request.headers['User-Agent'] = self.user_agent


class BanAwareThrottleMiddleware:
    """
    Detects ban/challenge responses and backs off aggressively.
    This avoids repeatedly hitting the site when it starts blocking requests.
    """

    BLOCK_STATUS_CODES = {403, 429, 503}
    BLOCK_TEXT_MARKERS = (
        "access denied",
        "too many requests",
        "temporarily blocked",
        "just a moment...",
        "attention required! | cloudflare",
        "enable javascript and cookies to continue",
        "cf-chl-",
    )

    def __init__(self):
        self.enabled = os.getenv("BAN_AWARE_THROTTLE_ENABLED", "true").lower() in {"1", "true", "yes"}
        self.base_wait_seconds = int(os.getenv("BAN_BACKOFF_BASE_SECONDS", "60"))
        self.max_wait_seconds = int(os.getenv("BAN_BACKOFF_MAX_SECONDS", "900"))
        self.max_retries = int(os.getenv("BAN_MAX_RETRIES_PER_REQUEST", "2"))
        self.abort_after_hits = int(os.getenv("BAN_ABORT_AFTER_HITS", "8"))
        self.block_hits = 0
        self._crawler = None

    @classmethod
    def from_crawler(cls, crawler):
        inst = cls()
        inst._crawler = crawler
        return inst

    def process_response(self, request, response, spider=None):
        # Scrapy is deprecating passing spider into middleware methods.
        if spider is None and self._crawler is not None:
            spider = getattr(self._crawler, "spider", None)

        if not self.enabled:
            return response

        # Never treat the login page itself as a ban signal; let the spider handle it.
        # (Some sites include "captcha"/challenge wording on login pages.)
        req_url = (getattr(request, "url", "") or "").lower()
        if "/login" in req_url:
            return response

        try:
            body_text = bytes(getattr(response, "body", b"")).decode(
                "utf-8", errors="ignore"
            ).lower()
        except (AttributeError, TypeError, ValueError):
            body_text = ""
        matched_marker = next((m for m in self.BLOCK_TEXT_MARKERS if m in body_text), None)
        blocked = response.status in self.BLOCK_STATUS_CODES or matched_marker is not None
        if not blocked:
            return response

        retries = request.meta.get("ban_retry_times", 0)
        self.block_hits += 1

        if retries >= self.max_retries:
            spider.logger.warning(
                "Blocked response for %s (status=%s marker=%s) after %s retries. Skipping request.",
                request.url,
                response.status,
                matched_marker,
                retries,
            )
            if self.block_hits >= self.abort_after_hits:
                spider.logger.error(
                    "Observed %s blocked responses. Closing spider to avoid further pressure.",
                    self.block_hits,
                )
                spider.crawler.engine.close_spider(spider, reason="repeated_blocked_responses")
            raise IgnoreRequest("Blocked response exceeded retry budget")

        sleep_seconds = min(
            self.max_wait_seconds,
            self.base_wait_seconds * (2 ** retries),
        ) + random.uniform(0, 5)
        spider.logger.warning(
            "Blocked response for %s (status=%s marker=%s). Sleeping %.1fs before retry %s/%s.",
            request.url,
            response.status,
            matched_marker,
            sleep_seconds,
            retries + 1,
            self.max_retries,
        )
        retry_request = request.copy()
        retry_request.dont_filter = True
        retry_request.meta["ban_retry_times"] = retries + 1
        retry_request.priority = request.priority - 10
        delayed_retry = Deferred()
        reactor.callLater(sleep_seconds, delayed_retry.callback, retry_request)
        return delayed_retry
