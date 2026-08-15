# Scrapy Connection Tuning Guide

## Status

The site is reachable and not blocking scraper traffic (verified via direct HTTP
requests returning 200 with real content). No proxy or VPN is required for normal
operation. If `BanAwareThrottleMiddleware` starts logging repeated 403/429/503
responses or captcha markers, that's the signal something changed — see
"Troubleshooting" below before reaching for a proxy.

Idea pages are teaser-gated without login (company/ticker/date/author visible, full
report text hidden behind "sign up or log in"). Set `VIC_ENABLE_LOGIN=true` with
`VIC_USERNAME`/`VIC_PASSWORD` to scrape full report text if you have an account.

For the full backlog crawl, use `scripts/backfill_ideas.sh` (chunked, resumable,
never truncates the DB) rather than a single 40-hour `weekly_refresh.sh` run.

---

## Available Settings

This document describes the environment variables you can use to tune the ValueInvestorsClub scraper.

### Core Rate Limiting
- `DOWNLOAD_DELAY=3` - Delay between requests in seconds (default: 3)
- `CONCURRENT_REQUESTS_PER_DOMAIN=1` - Max concurrent requests per domain (default: 1)
- `RETRY_TIMES=10` - Number of retry attempts for failed requests (default: 10)
- `DOWNLOAD_TIMEOUT=120` - Timeout for downloads in seconds (default: 120)
- `DNS_TIMEOUT=60` - DNS resolution timeout in seconds (default: 60)

### Browser Emulation (ENABLED BY DEFAULT)
- `COOKIES_ENABLED=true` - Enable cookies to maintain session (default: true)
- `MODERN_USER_AGENT=true` - Use modern Chrome 120 UA instead of random old ones (default: true)
- `USER_AGENT="..."` - Override with specific user agent string

### robots.txt
- `ROBOTSTXT_OBEY=false` - Set to `false` to bypass robots.txt (default: false in weekly script)

## Advanced Settings

### AutoThrottle (Adaptive Rate Limiting)
- `AUTOTHROTTLE_ENABLED=true` - Enable automatic throttling based on server response
- `AUTOTHROTTLE_START_DELAY=5` - Initial download delay
- `AUTOTHROTTLE_MAX_DELAY=60` - Maximum download delay
- `AUTOTHROTTLE_TARGET_CONCURRENCY=1.0` - Average number of requests per remote server

### Proxy Support (optional — not required under normal conditions)
- `HTTP_PROXY=http://proxy.example.com:8080` - HTTP proxy URL
- `HTTPS_PROXY=https://proxy.example.com:8443` - HTTPS proxy URL
- Can also use `SCRAPY_HTTP_PROXY` and `SCRAPY_HTTPS_PROXY`

### Logging
- `LOG_LEVEL=DEBUG` - Set log verbosity (DEBUG, INFO, WARNING, ERROR)
- `LOGSTATS_INTERVAL=30` - How often to log stats in seconds
- `SCRAPY_UA_LOG_LEVEL=ERROR` - Log level for user-agent picker warnings

### Retry Configuration
- `RETRY_HTTP_CODES="500 502 503 504"` - Space-separated list of HTTP codes to retry

## Example Configurations

### Debug Mode
```bash
LOG_LEVEL=DEBUG \
LOGSTATS_INTERVAL=30 \
./scripts/weekly_refresh.sh
```

### With Login (full report text)
```bash
VIC_ENABLE_LOGIN=true \
VIC_USERNAME=your_username \
VIC_PASSWORD=your_password \
./scripts/weekly_refresh.sh
```

### With Proxy (only if the site starts blocking)
```bash
HTTP_PROXY=http://your-proxy:8080 \
HTTPS_PROXY=http://your-proxy:8080 \
./scripts/weekly_refresh.sh
```

## Troubleshooting

### Connection Lost Errors
If you see connection errors, first re-run the preflight check
(`vic_preflight_or_exit` in `scripts/lib_vic_scrape.sh`) manually to rule out a
transient local network issue before assuming a block:

```bash
docker-compose exec api sh -lc "curl -f -s -m 10 --head 'https://www.valueinvestorsclub.com/'"
```

If that also fails and `BanAwareThrottleMiddleware` logs are showing repeated
403/429/503 responses or captcha markers, then the site has started blocking —
at that point a proxy/VPN may be warranted.

### 0 Pages Scraped
Check the log for `Login appears ineffective` (falls back to teaser mode, not a
hard failure) vs. actual request failures. If requests are failing outright, run
the preflight check above first.

## Weekly Script Integration

All settings can be passed directly to the weekly refresh script:

```bash
DOWNLOAD_DELAY=5 \
CONCURRENT_REQUESTS_PER_DOMAIN=1 \
LOG_LEVEL=INFO \
./scripts/weekly_refresh.sh
```

The script automatically exports these to the Docker container running the spider.
