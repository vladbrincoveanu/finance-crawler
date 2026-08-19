"""
The following inserts all scraped links into a postgres sql database. 
Unfortunately, this creates some duplicates.
To view those we make a query that selects duplicate ideas where the user, ticker and date are all the same.

select * from ideas full outer join companies full outer join where date in (select date from ideas group by id having count(*) > 1);
"""

import os
import re
from pathlib import Path

import scrapy

try:
    from ValueInvestorsClub.items import ValueinvestorsclubItem
except ImportError:
    # Same dual-context shim as models/*.py: works whether this module is
    # imported as the standalone scrapy project or nested under tests/.
    from ValueInvestorsClub.ValueInvestorsClub.items import ValueinvestorsclubItem


class IdeaSpider(scrapy.Spider):
    name = 'IdeaSpider'
    source = "valueinvestorsclub"
    parser_version = "idea-pipeline-v1"
    allowed_domains = ['valueinvestorsclub.com']
    login_url = "https://www.valueinvestorsclub.com/login"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default: do not attempt login. We'll scrape teaser context and strip boilerplate.
        self._enable_login = os.getenv("VIC_ENABLE_LOGIN", "false").lower() in {"1", "true", "yes"}
        # Manual-assist auth: reuse a session cookie captured from a real browser login
        # (you solve the site's login challenge yourself, then export cookies here).
        # Format: "name1=value1; name2=value2" (same shape as a browser's document.cookie).
        self._session_cookie_header = os.getenv("VIC_SESSION_COOKIE", "").strip()

    def _parse_session_cookies(self) -> dict:
        cookies = {}
        for part in self._session_cookie_header.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            name, value = part.split("=", 1)
            name = name.strip()
            value = value.strip()
            if name:
                cookies[name] = value
        return cookies

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        lines = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            lower = line.lower()
            # Strip boilerplate / UI chrome
            if any(
                phrase in lower
                for phrase in (
                    "sign up or log in",
                    "already have an account",
                    "log in to read the full report",
                    "to read the full report",
                    "read the full report",
                    "guest access",
                    "45-day delay",
                    "read full reports",
                    "read full report",
                    "log in",
                    "signup",
                    "sign up",
                    "favorites",
                    "report abuse",
                )
            ):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def _section_text(self, response: scrapy.http.Response, header: str) -> str:
        h = response.xpath(f"//div[@id='description']//h4[normalize-space()='{header}']")
        if not h:
            return ""
        parts = []
        for sib in h.xpath("following-sibling::*"):
            if sib.xpath("self::h4").get():
                break
            parts.extend(sib.xpath(".//text()").getall())
        return self._clean_text("\n".join(parts))

    def _date_iso(self, date_text: str) -> str:
        if not date_text:
            return ""
        m = re.search(r"([A-Za-z]+\s+\d{1,2},\s+\d{4})", date_text)
        if not m:
            return ""
        try:
            from datetime import datetime

            dt = datetime.strptime(m.group(1), "%B %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ""

    def _idea_id_from_url(self, url: str) -> str:
        m = re.search(r"/idea/[^/]+/(\d+)", url or "")
        return m.group(1) if m else ""

    def _extract_comments(self, response: scrapy.http.Response):
        """
        Best-effort comment extraction. Without login, VIC often hides or redirects;
        when present, keep it simple and resilient.
        """
        out = []
        # Prefer explicit comment container if present.
        roots = response.xpath(
            "//*[@id='comments' or contains(@id,'comment') or contains(@class,'comment')]"
        )
        if not roots:
            return out
        seen = set()
        for root in roots[:25]:
            # Candidate blocks: div/li with 'comment' in class OR any element under a comment-ish root.
            blocks = root.xpath(
                ".//*[self::div or self::li][contains(concat(' ', normalize-space(@class), ' '), ' comment ') or contains(@id,'comment')]"
            )
            if not blocks:
                blocks = [root]
            for b in blocks[:50]:
                text = self._clean_text(" ".join(b.xpath(".//text()").getall()))
                if not text:
                    continue
                # Avoid duplicating huge root texts.
                key = text[:200]
                if key in seen:
                    continue
                seen.add(key)
                author = (b.xpath(".//a[contains(@href,'/user')]/text()").get() or "").strip()
                when = (b.xpath(".//time/@datetime").get() or "").strip()
                out.append({"author": author, "when": when, "text": text})
        return out

    def _extract_photos(self, response: scrapy.http.Response):
        """Collect absolute URLs for images embedded in the idea body/description."""
        urls = response.xpath("//div[@id='description']//img/@src").getall()
        out = []
        seen = set()
        for src in urls:
            src = (src or "").strip()
            if not src:
                continue
            abs_url = response.urljoin(src)
            if abs_url in seen:
                continue
            seen.add(abs_url)
            out.append(abs_url)
        return out

    def load_idea_links(self):
        # load the idea links from the file
        idea_links = []
        link_file = os.getenv('IDEA_LINKS_FILE')
        if not link_file:
            link_file = Path(__file__).resolve().parents[3] / 'idea_links_no_duplicates.txt'
        with open(link_file, 'r') as f:
            for line in f:
                idea_links.append(line.strip())
        return idea_links

    def _selected_links(self):
        idea_links = self.load_idea_links()
        start_index = int(os.getenv("IDEA_LINKS_START", "0"))
        link_limit = int(os.getenv("IDEA_LINKS_LIMIT", "0"))
        link_mode = os.getenv("IDEA_LINKS_MODE", "tail").strip().lower()

        if start_index < 0:
            start_index = 0
        if start_index >= len(idea_links):
            self.logger.warning(
                "IDEA_LINKS_START=%s is out of range (%s links); starting from 0.",
                start_index,
                len(idea_links),
            )
            start_index = 0

        selected_links = idea_links[start_index:]
        if link_limit > 0:
            if link_mode == "tail" and start_index == 0:
                selected_links = selected_links[-link_limit:]
            else:
                selected_links = selected_links[:link_limit]

        self.logger.info(
            "Loaded %d idea links, start_index=%d, limit=%d, mode=%s; crawling %d links",
            len(idea_links),
            start_index,
            link_limit,
            link_mode,
            len(selected_links),
        )
        return selected_links

    def _is_gated(self, response: scrapy.http.Response) -> bool:
        text = (response.text or "").lower()
        if "sign up or log in" in text:
            return True
        if "already have an account" in text and "log in" in text:
            return True
        if "log in to read the full report" in text:
            return True
        return False

    async def start(self):
        """
        Scrapy 2.13+ entrypoint. We keep this to avoid deprecated start_requests().
        """
        if self._session_cookie_header:
            # Manual-assist auth: skip the login flow entirely and crawl directly
            # with the cookies from an already-authenticated browser session.
            session_cookies = self._parse_session_cookies()
            self.logger.info(
                "Using manual session cookies (%d cookie names); skipping login flow.",
                len(session_cookies),
            )
            test_url = os.getenv("LOGIN_TEST_URL", "").strip() or "https://www.valueinvestorsclub.com/idea/InPost/5698302853"
            yield scrapy.Request(
                test_url,
                callback=self.verify_login,
                meta={"cookiejar": 1},
                cookies=session_cookies,
                dont_filter=True,
            )
            return

        vic_user = os.getenv("VIC_USERNAME", "").strip()
        vic_pass = os.getenv("VIC_PASSWORD", "").strip()

        if self._enable_login and vic_user and vic_pass:
            # Use a dedicated cookiejar so session cookies persist.
            yield scrapy.Request(
                self.login_url,
                callback=self.parse_login,
                meta={"cookiejar": 1},
                dont_filter=True,
            )
            return

        for link in self._selected_links():
            yield scrapy.Request(link, callback=self.parse, meta={"cookiejar": 1})

    def parse_login(self, response):
        if response.status != 200:
            self.logger.error("Login page returned status=%s; aborting.", response.status)
            self.crawler.engine.close_spider(self, reason="login_page_failed")
            return
        set_cookies = response.headers.getlist("Set-Cookie")
        if set_cookies:
            cookie_names = [c.decode("utf-8", "ignore").split("=", 1)[0] for c in set_cookies]
            self.logger.info("Login GET set-cookie: %s", cookie_names)

        token = response.xpath("//form//input[@name='_token']/@value").get()
        if not token:
            self.logger.error("Could not find CSRF _token on login page; aborting.")
            self.crawler.engine.close_spider(self, reason="login_token_missing")
            return

        vic_user = os.getenv("VIC_USERNAME", "").strip()
        vic_pass = os.getenv("VIC_PASSWORD", "").strip()
        if not vic_user or not vic_pass:
            self.logger.error("VIC_USERNAME/VIC_PASSWORD not set; cannot login.")
            self.crawler.engine.close_spider(self, reason="login_credentials_missing")
            return

        # Submit login form. Keep same cookiejar.
        yield scrapy.FormRequest(
            self.login_url,
            formdata={
                "_token": token,
                "login[login_name]": vic_user,
                "login[password]": vic_pass,
                "login[remember_me]": "1",
            },
            callback=self.after_login,
            meta=response.meta,
            dont_filter=True,
        )

    def after_login(self, response):
        # Login might redirect or return a page. Verify by fetching one idea link.
        if response.status not in {200, 302}:
            self.logger.error("Login submit returned status=%s; aborting.", response.status)
            self.crawler.engine.close_spider(self, reason="login_submit_failed")
            return

        # If we stayed on /login with a 200, it likely contains an error message.
        if response.status == 200 and "/login" in (response.url or ""):
            text = (response.text or "").lower()
            hints = [
                "these credentials",
                "invalid",
                "incorrect",
                "too many",
                "captcha",
                "try again",
                "error",
            ]
            present = [h for h in hints if h in text]
            if present:
                self.logger.error("Login POST appears to have failed; hints=%s", present)
            # Try to extract any visible error/alert text, if present.
            err_text = " ".join(
                t.strip()
                for t in response.xpath(
                    "//*[contains(@class,'alert') or contains(@class,'error') or contains(@class,'help') or contains(@class,'danger')]//text()"
                ).getall()
                if t and t.strip()
            )
            if err_text:
                self.logger.error("Login POST error text: %s", err_text[:400])
            else:
                # Last resort: dump a small snippet for debugging without leaking full HTML.
                snippet = " ".join((response.xpath("//body//text()").getall() or [])).strip()
                snippet = re.sub(r"\s+", " ", snippet)
                if snippet:
                    self.logger.error("Login POST body snippet: %s", snippet[:400])

        set_cookies = response.headers.getlist("Set-Cookie")
        if set_cookies:
            cookie_names = [c.decode("utf-8", "ignore").split("=", 1)[0] for c in set_cookies]
            self.logger.info("Login POST set-cookie: %s", cookie_names)

        test_url = os.getenv("LOGIN_TEST_URL", "").strip() or "https://www.valueinvestorsclub.com/idea/InPost/5698302853"
        yield scrapy.Request(
            test_url,
            callback=self.verify_login,
            meta=response.meta,
            dont_filter=True,
        )

    def verify_login(self, response):
        # If login didn't work, still proceed with teaser scraping.
        test_url = os.getenv("LOGIN_TEST_URL", "").strip() or "https://www.valueinvestorsclub.com/idea/InPost/5698302853"
        redirected = "/idea/" not in (response.url or "")
        if self._is_gated(response) or redirected:
            self.logger.error(
                "Login appears ineffective (test_url=%s final_url=%s). Continuing with teaser scraping.",
                test_url,
                response.url,
            )

        self.logger.info("Login verified; starting idea crawl.")
        for link in self._selected_links():
            yield scrapy.Request(link, callback=self.parse, meta=response.meta)

    def parse(self, response):
        # Even if the page is login-gated, we still scrape whatever teaser content exists.

        # get the link with authors username and the link to the authors page
        # get the company name
        # get the company ticker
        # get the date
        # get the idea description
        # get the idea catalysts
        # get if the user is short
        # get if the post is contestWinner

        # The idea name and ticker are in a div with a class: idea_name
        # in that is a span with class vich1. There is top level text with the company name.
        # The ticker is in a span nested inside of that span

        # the current page that is being scraped
        link = response.url
        idea_id = self._idea_id_from_url(link)

        company_name = response.xpath("//div[@class='idea_name']/span[@class='vich1']/text()").get()
        company_ticker = response.xpath("//div[@class='idea_name']/span[@class='vich1']/span/text()").get()
        if not company_name or not company_ticker:
            # Fallback: parse from <title> like "Value Investors Club / COMPANY (TICKER)"
            title = (response.xpath("//title/text()").get() or "").replace("\n", " ").strip()
            m = re.search(r"/\s*(.*?)\s*\(([^)]+)\)", title)
            if m:
                company_name = company_name or m.group(1).strip()
                company_ticker = company_ticker or m.group(2).strip()
        company_name = (company_name or "").strip()
        company_ticker = (company_ticker or "").strip()

        # the date is in a div with class "idea_by" and is the text in the first nested div
        date = response.xpath("//div[@class='idea_by']/div/text()").get()
        if not date:
            idea_by = response.xpath("normalize-space(//div[@class='idea_by'])").get() or ""
            # ex: "January 28, 2020 - 3:56pm EST by member"
            if " est by" in idea_by.lower():
                date = idea_by.split(" by ", 1)[0].strip() + " by"
        # the user is in the text of a link in the same idea_by div.
        # The link is the first link in the div
        username = response.xpath("//div[@class='idea_by']/a/text()").get()
        # also get the actual link to the username from that link tag
        username_link = response.xpath("//div[@class='idea_by']/a/@href").get()
        if not username:
            idea_by = response.xpath("normalize-space(//div[@class='idea_by'])").get() or ""
            if " by " in idea_by.lower():
                username = idea_by.split(" by ", 1)[-1].strip()

        description = self._section_text(response, "Description")
        catalysts = self._section_text(response, "Catalyst")
        if not description and not catalysts:
            raw = "\n ".join(response.xpath("//div[@id='description']/descendant-or-self::*/text()").getall())
            raw = self._clean_text(raw)
            # The raw join includes the literal "Description" <h4> label as its own
            # line; strip it so it doesn't end up prefixed onto the real content.
            lines = raw.split("\n", 1)
            if lines and lines[0].strip().lower() == "description":
                raw = lines[1].lstrip("\n") if len(lines) > 1 else ""
            parts = raw.split("Catalyst")
            if len(parts) >= 2:
                description = "Catalyst".join(parts[:-1]).strip()
                catalysts = parts[-1].strip()
            else:
                description = raw.strip()
                catalysts = ""

        # Final fallback: meta description is often the only useful non-auth context.
        if not description:
            meta_desc = response.xpath("//meta[@name='description']/@content").get() or ""
            meta_desc = meta_desc.strip()
            if meta_desc.lower().startswith("investment thesis for"):
                description = meta_desc

        comments = self._extract_comments(response)
        messages = "\n\n".join(c.get("text", "") for c in comments if c.get("text"))
        photos = self._extract_photos(response)
        date_iso = self._date_iso(date or "")

        # Emit a rejection item so the ingestion run can count this parser outcome.
        if not company_name or not company_ticker or not date:
            self.logger.warning(
                "Skipping page missing core fields: url=%s ticker=%r company=%r date=%r",
                response.url,
                company_ticker,
                company_name,
                date,
            )
            missing = [
                name
                for name, value in (
                    ("companyName", company_name),
                    ("ticker", company_ticker),
                    ("date", date),
                )
                if not value
            ]
            yield ValueinvestorsclubItem(
                link=link,
                parse_error=f"missing core fields: {', '.join(missing)}",
            )
            return
        # check if this is a short position. a span with class "label label-short" signifies it.
        short = response.xpath("//span[@class='label label-short']").getall()
        if len(short) == 0:
            short = False
        else:
            short = True

        contest_winner = response.xpath("//span[@class='label label-success']").getall()
        if len(contest_winner) == 0:
            contest_winner = False
        else:
            contest_winner = True


        yield ValueinvestorsclubItem(
            ticker=company_ticker,
            link=link,
            companyName=company_name,
            date = date,
            date_iso=date_iso,
            username=username,
            userLink=username_link,
            isShort=short,
            isContestWinner=contest_winner,
            description=description,
            catalysts=catalysts,
            comments=comments,
            messages=messages,
            photos=photos,
            idea_id=idea_id,
        )
