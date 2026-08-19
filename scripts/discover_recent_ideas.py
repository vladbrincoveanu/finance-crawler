"""Walk VIC's /ideas/loadideas endpoint newest-first and collect idea links
until hitting a date cutoff. Writes one URL per line, newest first, to stdout
and to the path given as sys.argv[1].
"""
import os
import sys
import time
from datetime import datetime, timedelta

import requests

BASE = "https://www.valueinvestorsclub.com"
CUTOFF_DAYS = int(os.environ.get("CUTOFF_DAYS", "365"))


def parse_cookies(cookie_header: str) -> dict:
    cookies = {}
    for part in cookie_header.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        cookies[k.strip()] = v.strip()
    return cookies


def main():
    out_path = sys.argv[1]
    cookie_header = os.environ["VIC_SESSION_COOKIE"]
    cookies = parse_cookies(cookie_header)
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})

    cutoff = datetime.utcnow() - timedelta(days=CUTOFF_DAYS)

    links = []
    page = 1
    while True:
        data = {
            "show": "all", "daterange": "", "ls": "", "loc": "", "sort": "date_desc",
            "marketcap_l": "", "marketcap_h": "", "rtr_l": "", "rtr_h": "",
            "country": "", "state": "", "aum": "", "yio": "", "gotodate": "",
            "page": page, "end_page": page, "is_login": 1, "show_alt_msgb": "",
        }
        resp = session.post(f"{BASE}/ideas/loadideas", data=data, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("result") or []
        if not items:
            break

        hit_cutoff = False
        for item in items:
            add_date = datetime.strptime(item["add_date"], "%Y-%m-%d %H:%M:%S")
            if add_date < cutoff:
                hit_cutoff = True
                break
            url = f"{BASE}/idea/{item['encode_company_name']}/{item['keyid']}"
            links.append((add_date, url))

        print(f"page={page} items={len(items)} total_collected={len(links)} oldest_so_far={items[-1]['add_date']}", file=sys.stderr)

        if hit_cutoff:
            break
        page += 1
        time.sleep(1.5)

    with open(out_path, "w") as f:
        for _, url in links:
            f.write(url + "\n")

    print(f"DONE: {len(links)} idea links written to {out_path}", file=sys.stderr)
    print(f"cutoff={cutoff.isoformat()}", file=sys.stderr)


if __name__ == "__main__":
    main()
