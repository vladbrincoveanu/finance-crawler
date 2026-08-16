#!/usr/bin/env bash
# scripts/probe_dataroma.sh — verify Dataroma is reachable with browser-like headers
# before running DataromaSpider. Exits non-zero if blocked.
set -euo pipefail

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

status=$(curl -s -o /dev/null -w "%{http_code}" \
  -A "$UA" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
  -H "Accept-Language: en-US,en;q=0.9" \
  --compressed \
  "https://www.dataroma.com/m/home.php")

if [ "$status" != "200" ]; then
  echo "Error: Dataroma probe failed (HTTP $status). Site may be blocking automated requests." >&2
  exit 1
fi
echo "Dataroma reachable (HTTP 200)."
