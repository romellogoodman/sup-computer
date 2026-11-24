"""fetch.py -- download every draw, from two independent sources per game.

Stage 1 of the lucky pipeline (fetch -> crosscheck -> prepare). Stdlib only.

Pick 3 (Maryland), evening since 1976 and midday since 1995:
  primary  mdlottery.com, the Maryland Lottery's own results search (the
           endpoint its Winning Numbers page calls), one request per year,
           then one request per day the yearly pass may have dropped
           (see gap_days)
  second   lotterycorner.com, a third-party archive, one page per draw
           time per year

Powerball, every draw under the 69/26 matrix (first draw 2015-10-07):
  primary  data.ny.gov, New York's open-data file (whites sorted)
  second   texaslottery.com, the Texas Lottery's file (whites in draw order)

Raw responses and the per-source parses (<game>.<source>.csv) land in
data/raw/ (gitignored). crosscheck.py compares the two sources and writes
the committed data/<game>/draws.csv plus provenance.json.

Run from the repo root:
    uv run python projects/lucky/data/fetch.py            # both games
    uv run python projects/lucky/data/fetch.py --game powerball
    uv run python projects/lucky/data/fetch.py --parse-only   # re-parse data/raw/

The Maryland site asks for a 10-second crawl delay; this script keeps it.
The yearly pass takes about ten minutes and the gap pass about ninety
(roughly 520 one-day requests). Both skip files already in data/raw/.
"""

import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
UA = "Mozilla/5.0 (research-fetch)"

MD_ENDPOINT = "https://www.mdlottery.com/wp-admin/admin-ajax.php"
LC_URL = "https://www.lotterycorner.com/md/pick-3-{time}/{year}"
NY_URL = "https://data.ny.gov/api/views/d6yy-54nr/rows.csv?accessType=DOWNLOAD"
TX_URL = "https://www.texaslottery.com/export/sites/lottery/Games/Powerball/Winning_Numbers/powerball.csv"

PICK3_FIRST_YEAR = 1976          # evening draws begin 29 Jul 1976
PICK3_MIDDAY_FIRST_YEAR = 1995   # midday draws begin 1 May 1995
POWERBALL_FIRST_DRAW = dt.date(2015, 10, 7)  # first draw under 69/26

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}


def get(url, path, delay, refetch=False):
    """Download url to path unless it is already there. Returns True if fetched."""
    if os.path.exists(path) and not refetch:
        return False
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    with open(path, "wb") as f:
        f.write(body)
    time.sleep(delay)
    return True


def md_url(year, today):
    end = today if year == today.year else dt.date(year, 12, 31)
    atts = {"game": "pick-3-4-5", "start": f"01/01/{year}",
            "end": end.strftime("%m/%d/%Y"), "method": "ANY"}
    q = {"action": "jquery_shortcode", "shortcode": "find_numbers", "atts": json.dumps(atts)}
    return MD_ENDPOINT + "?" + urllib.parse.urlencode(q)


def fetch_pick3(today, log):
    for year in range(PICK3_FIRST_YEAR, today.year + 1):
        # the current year is always refetched: its file grows
        cur = year == today.year
        url = md_url(year, today)
        if get(url, os.path.join(RAW, f"md-pick3-{year}.html"), 10, refetch=cur):
            log.append({"source": "mdlottery.com", "url": url, "year": year})
            print(f"mdlottery {year}", flush=True)
        for t in ("evening", "midday"):
            if t == "midday" and year < PICK3_MIDDAY_FIRST_YEAR:
                continue
            url = LC_URL.format(time=t, year=year)
            if get(url, os.path.join(RAW, f"lc-pick3-{t}-{year}.html"), 2, refetch=cur):
                log.append({"source": "lotterycorner.com", "url": url, "year": year})
                print(f"lotterycorner {t} {year}", flush=True)


def fetch_powerball(log):
    for name, url in (("ny-powerball.csv", NY_URL), ("tx-powerball.csv", TX_URL)):
        get(url, os.path.join(RAW, name), 1, refetch=True)
        log.append({"source": urllib.parse.urlparse(url).netloc, "url": url})
        print(name, flush=True)


# --- parsers -----------------------------------------------------------------

def parse_md(path):
    """One mdlottery response -> [(date, 'midday'|'evening', 'ddd')]. A draw that
    did not happen renders as grey X's and is skipped."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    out = []
    for cls, mm, dd, yy, body in re.findall(
            r'<tr class="(mid|eve)"><td class="date">(\d\d)/(\d\d)/(\d\d)&nbsp;.*?<ul class="pick-3">(.*?)</ul>',
            text, re.S):
        digits = re.findall(r"<li>(\d)</li>", body)
        if len(digits) != 3:
            continue
        year = (1900 if int(yy) >= 76 else 2000) + int(yy)
        out.append((dt.date(year, int(mm), int(dd)).isoformat(),
                    "midday" if cls == "mid" else "evening", "".join(digits)))
    return out


def gap_days(rows, today):
    """Dates the yearly pass may have dropped.

    The endpoint omits a day that has an evening draw but no midday draw
    whenever the queried range also holds midday draws (found 2026-11-23:
    the 1995 query returned nothing before 1 May, and no Sunday evening from
    1995 to 2004, though a one-day query returns each). So every date from
    1995 on with no evening draw in the yearly pass is asked for again.
    """
    have = {d for d, t, _ in rows if t == "evening"}
    day, out = dt.date(PICK3_MIDDAY_FIRST_YEAR, 1, 1), []
    while day <= today:
        if day.isoformat() not in have:
            out.append(day)
        day += dt.timedelta(days=1)
    return out


def md_range_url(start, end):
    atts = {"game": "pick-3-4-5", "start": start.strftime("%m/%d/%Y"),
            "end": end.strftime("%m/%d/%Y"), "method": "ANY"}
    q = {"action": "jquery_shortcode", "shortcode": "find_numbers", "atts": json.dumps(atts)}
    return MD_ENDPOINT + "?" + urllib.parse.urlencode(q)


def fetch_pick3_gaps(today):
    """Second pass over mdlottery: one request per gap day, except the run
    before the first midday draw (1 May 1995), which is safe as one range."""
    rows = [r for y in range(PICK3_FIRST_YEAR, today.year + 1) for r in parse_md(md_path(y))]
    days = gap_days(rows, today)
    midday_start = dt.date(1995, 5, 1)
    early = [d for d in days if d < midday_start]
    if early:
        get(md_range_url(early[0], early[-1]), os.path.join(RAW, "md-pick3-gap-early-1995.html"), 10)
    late = [d for d in days if d >= midday_start]
    for i, d in enumerate(late):
        if get(md_range_url(d, d), os.path.join(RAW, f"md-pick3-gap-{d.isoformat()}.html"), 10):
            print(f"mdlottery gap day {d} ({i + 1}/{len(late)})", flush=True)
    print("GAPS DONE", flush=True)


def md_path(year):
    return os.path.join(RAW, f"md-pick3-{year}.html")


def parse_lc(t, year):
    path = os.path.join(RAW, f"lc-pick3-{t}-{year}.html")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text)
    out = {}
    for mon, day, yr, a, b, c in re.findall(
            r"day, (\w+) (\d{1,2}), (\d{4}) (\d) (\d) (\d)(?= |$)", text):
        if int(yr) != year or mon not in MONTHS:
            continue
        out[dt.date(year, MONTHS[mon], int(day)).isoformat()] = a + b + c
    return [(d, t, n) for d, n in out.items()]


def parse_ny():
    out = []
    with open(os.path.join(RAW, "ny-powerball.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m, d, y = row["Draw Date"].split("/")
            date = dt.date(int(y), int(m), int(d))
            if date < POWERBALL_FIRST_DRAW:
                continue
            nums = [int(x) for x in row["Winning Numbers"].split()]
            out.append((date.isoformat(), nums[:5], nums[5]))
    return out


def parse_tx():
    out = []
    with open(os.path.join(RAW, "tx-powerball.csv"), encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or row[0] != "Powerball":
                continue
            date = dt.date(int(row[3]), int(row[1]), int(row[2]))
            if date < POWERBALL_FIRST_DRAW:
                continue
            nums = [int(x) for x in row[4:10]]
            out.append((date.isoformat(), nums[:5], nums[5]))
    return out


def write_pick3(name, rows):
    order = {"midday": 0, "evening": 1}
    rows = sorted(set(rows), key=lambda r: (r[0], order[r[1]]))
    path = os.path.join(RAW, name)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "draw", "digits"])
        w.writerows(rows)
    print(f"{path}: {len(rows)} draws")


def write_powerball(name, rows, sort_whites):
    rows = sorted(rows, key=lambda r: r[0])
    path = os.path.join(RAW, name)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "w1", "w2", "w3", "w4", "w5", "red"])
        for date, whites, red in rows:
            w.writerow([date, *(sorted(whites) if sort_whites else whites), red])
    print(f"{path}: {len(rows)} draws")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game", choices=["pick3", "powerball", "all"], default="all")
    ap.add_argument("--parse-only", action="store_true")
    args = ap.parse_args()
    os.makedirs(RAW, exist_ok=True)
    today = dt.date.today()
    log_path = os.path.join(RAW, "fetch-log.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else {}

    if args.game in ("pick3", "all"):
        if not args.parse_only:
            reqs = []
            fetch_pick3(today, reqs)
            log["pick3"] = {"fetched": today.isoformat()}
            fetch_pick3_gaps(today)
        years = [y for y in range(PICK3_FIRST_YEAR, today.year + 1) if os.path.exists(md_path(y))]
        md_files = [md_path(y) for y in years] + sorted(
            os.path.join(RAW, n) for n in os.listdir(RAW) if n.startswith("md-pick3-gap-"))
        write_pick3("pick3.mdlottery.csv", [r for p in md_files for r in parse_md(p)])
        write_pick3("pick3.lotterycorner.csv",
                    [r for y in years for t in ("midday", "evening") for r in parse_lc(t, y)])
    if args.game in ("powerball", "all"):
        if not args.parse_only:
            reqs = []
            fetch_powerball(reqs)
            log["powerball"] = {"fetched": today.isoformat()}
        # NY publishes sorted whites; Texas publishes draw order. Both are
        # kept as fetched; crosscheck compares them as sets.
        write_powerball("powerball.ny.csv", parse_ny(), sort_whites=True)
        write_powerball("powerball.texas.csv", parse_tx(), sort_whites=False)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)


if __name__ == "__main__":
    main()
