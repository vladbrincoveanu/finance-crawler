import os

# Scrapy settings for ValueInvestorsClub project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "ValueInvestorsClub"

SPIDER_MODULES = ["ValueInvestorsClub.spiders"]
NEWSPIDER_MODULE = "ValueInvestorsClub.spiders"


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "ValueInvestorsClub (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = os.getenv("ROBOTSTXT_OBEY", "true").lower() in {"1", "true", "yes"}

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = float(os.getenv("DOWNLOAD_DELAY", "10"))  # Increased from 3 to 10 seconds

# Add randomness to download delay (0.5 = ±50% variation)
# This makes 10s delay vary between 5-15 seconds randomly
RANDOMIZE_DOWNLOAD_DELAY = os.getenv("RANDOMIZE_DOWNLOAD_DELAY", "true").lower() in {"1", "true", "yes"}

# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
CONCURRENT_REQUESTS_PER_DOMAIN = int(os.getenv("CONCURRENT_REQUESTS_PER_DOMAIN", "1"))  # Reduced from 8 to 1

RETRY_TIMES = int(os.getenv("RETRY_TIMES", "6"))
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "60"))
DNS_TIMEOUT = int(os.getenv("DNS_TIMEOUT", "60"))

# Connection pool settings
CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", "1"))
DOWNLOAD_MAXSIZE = int(os.getenv("DOWNLOAD_MAXSIZE", str(1024 * 1024 * 50)))  # 50MB
DOWNLOAD_WARNSIZE = int(os.getenv("DOWNLOAD_WARNSIZE", str(1024 * 1024 * 30)))  # 30MB

# Retry HTTP codes (space-separated or default)
_retry_codes = os.getenv("RETRY_HTTP_CODES", "403 408 429 500 502 503 504 522 524")
RETRY_HTTP_CODES = [int(c.strip()) for c in _retry_codes.split() if c.strip().isdigit()]

# Proxy support
HTTP_PROXY = os.getenv("HTTP_PROXY") or os.getenv("SCRAPY_HTTP_PROXY")
HTTPS_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("SCRAPY_HTTPS_PROXY")

# Enable cookies to maintain session
COOKIES_ENABLED = os.getenv("COOKIES_ENABLED", "true").lower() in {"1", "true", "yes"}

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers to look like a real browser
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "ValueInvestorsClub.middlewares.ValueinvestorsclubSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    "ValueInvestorsClub.middlewares.ValueinvestorsclubDownloaderMiddleware": 543,
#}
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'ValueInvestorsClub.middlewares.ModernUserAgentMiddleware': 400,
    'ValueInvestorsClub.middlewares.BanAwareThrottleMiddleware': 543,
}

# Use modern user agent by default (set MODERN_USER_AGENT=false to use random old ones)
RANDOM_UA_TYPE = os.getenv("RANDOM_UA_TYPE", "desktop.chrome")

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
#
# Default behavior: export best-effort teaser + comments to filesystem grouped by ticker.
# SQL ingestion runs only when enabled (PIPELINE_MODE includes "sql") and items have required fields.
_pipeline_mode = (os.getenv("PIPELINE_MODE", "file").strip().lower() or "file")
_pipelines = {}
if "file" in _pipeline_mode or _pipeline_mode in {"fs", "filesystem"}:
    _pipelines["ValueInvestorsClub.pipelines.FileExportPipeline"] = 200
if "sql" in _pipeline_mode or _pipeline_mode in {"db", "database"}:
    _pipelines["ValueInvestorsClub.pipelines.SqlPipeline"] = 300
if "holdings" in _pipeline_mode:
    _pipelines["ValueInvestorsClub.holding_pipeline.HoldingPipeline"] = 300
ITEM_PIPELINES = _pipelines

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = os.getenv("AUTOTHROTTLE_ENABLED", "true").lower() in {"1", "true", "yes"}  # Changed to true by default
# The initial download delay
AUTOTHROTTLE_START_DELAY = float(os.getenv("AUTOTHROTTLE_START_DELAY", "10"))  # Increased from 5 to 10
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = float(os.getenv("AUTOTHROTTLE_MAX_DELAY", "60"))  # Can go up to 60 seconds if needed
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = float(os.getenv("AUTOTHROTTLE_TARGET_CONCURRENCY", "1.0"))  # Only 1 request at a time
# Enable showing throttling stats for every response received:
AUTOTHROTTLE_DEBUG = os.getenv("AUTOTHROTTLE_DEBUG", "false").lower() in {"1", "true", "yes"}
AUTOTHROTTLE_MAX_DELAY = float(os.getenv("AUTOTHROTTLE_MAX_DELAY", "60"))
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = float(os.getenv("AUTOTHROTTLE_TARGET_CONCURRENCY", "1.0"))
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "scrapy_user_agents.user_agent_picker": {
            "level": os.getenv("SCRAPY_UA_LOG_LEVEL", "ERROR"),
        },
    },
}

# Log level and stats interval
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGSTATS_INTERVAL = int(os.getenv("LOGSTATS_INTERVAL", "60"))
