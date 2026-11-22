import os, re, json, time, base64, smtplib
from io import BytesIO
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup
from PIL import Image
from google import genai
from google.genai import types

EST = timezone(timedelta(hours=-5))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

DEFAULT_STYLES = [
    {"slug": "tory-burch-lee-radziwill", "brand": "Tory Burch", "name": "Lee Radziwill bag", "median": 345, "p25": 295, "conservative": 295, "sold90": 85, "active": 120, "sell_through": 0.41, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "filson-mackinaw-cruiser", "brand": "Filson", "name": "Mackinaw Cruiser", "median": 290, "p25": 247.49, "conservative": 247.49, "sold90": 110, "active": 145, "sell_through": 0.43, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "burberry-quilted-jacket", "brand": "Burberry", "name": "Quilted trench / jacket", "median": 235, "p25": 200, "conservative": 200, "sold90": 190, "active": 310, "sell_through": 0.38, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "sezane-clyde-trench", "brand": "Sézane", "name": "Clyde trench", "median": 230, "p25": 195, "conservative": 195, "sold90": 65, "active": 50, "sell_through": 0.56, "max_all_in": 50, "cls": "Hot", "note": ""},
    {"slug": "coach-tabby-bag", "brand": "Coach", "name": "Tabby bag", "median": 225, "p25": 192, "conservative": 192, "sold90": 420, "active": 610, "sell_through": 0.41, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "burberry-vintage-wool-trench", "brand": "Burberry", "name": "Vintage wool trench", "median": 210, "p25": 175, "conservative": 175, "sold90": 95, "active": 180, "sell_through": 0.35, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "burberry-trench-coat", "brand": "Burberry", "name": "Trench coat", "median": 200, "p25": 170, "conservative": 170, "sold90": 340, "active": 1200, "sell_through": 0.22, "max_all_in": 50, "cls": "Promising", "note": "Retail listings inflate active"},
    {"slug": "arcteryx-beta-jacket", "brand": "Arc'teryx", "name": "Beta jacket", "median": 195, "p25": 160, "conservative": 160, "sold90": 280, "active": 340, "sell_through": 0.45, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "carhartt-detroit-jacket", "brand": "Carhartt", "name": "Detroit jacket (vintage)", "median": 230, "p25": 160, "conservative": 160, "sold90": 2634, "active": 4659, "sell_through": 0.36, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "barbour-waxed-jacket", "brand": "Barbour", "name": "Waxed jacket (Bedale/Beaufort)", "median": 185, "p25": 155, "conservative": 155, "sold90": 310, "active": 420, "sell_through": 0.42, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "mackage-wool-coat", "brand": "Mackage", "name": "Wool or down coat", "median": 185, "p25": 155, "conservative": 155, "sold90": 140, "active": 220, "sell_through": 0.39, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "polo-bear-sweater", "brand": "Polo Ralph Lauren", "name": "Polo Bear knit sweater", "median": 175, "p25": 150, "conservative": 150, "sold90": 260, "active": 380, "sell_through": 0.41, "max_all_in": 50, "cls": "Promising", "note": "Knit only, no fleece"},
    {"slug": "aritzia-super-puff", "brand": "Aritzia", "name": "Super Puff jacket", "median": 170, "p25": 145, "conservative": 145, "sold90": 390, "active": 410, "sell_through": 0.49, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "arcteryx-atom-jacket", "brand": "Arc'teryx", "name": "Atom jacket / hoody", "median": 165, "p25": 140, "conservative": 140, "sold90": 410, "active": 450, "sell_through": 0.48, "max_all_in": 50, "cls": "Promising", "note": ""},
    {"slug": "north-face-nuptse", "brand": "The North Face", "name": "1996 Retro Nuptse jacket", "median": 165, "p25": 138, "conservative": 138, "sold90": 520, "active": 680, "sell_through": 0.43, "max_all_in": 50, "cls": "Promising", "note": "Jackets only"},
    {"slug": "doen-dress", "brand": "Dôen", "name": "Mainline dress", "median": 165, "p25": 135, "conservative": 135, "sold90": 210, "active": 240, "sell_through": 0.47, "max_all_in": 50, "cls": "Promising", "note": "No Gap x Doen"}
]

BAD_KEYWORDS = [
    "stain", "spot", "mark", "discolor", "dirt", "needs cleaning", "spot clean",
    "hole", "burn", "tear", "rip", "snag", "pilling", "fading", "rust",
    "missing belt", "missing hood", "missing button", "broken zipper", "odor",
    "smoke", "flaw", "as is", "xxs", "2xl", "xxl", "3xl", "1x", "2x", "3x",
    "kids", "youth", "toddler", "gap x", "dupe", "inspired", "iso ", "liner only", "for parts"
]

ALLOWED_SIZES = {
    "xs", "s", "m", "l", "xl", "small", "medium", "large", "x-small", "x-large",
    "0", "2", "4", "6", "8", "10", "12", "14", "16",
    "36", "38", "40", "42", "44", "46", "28", "30", "32", "34"
}

def net_resale(r):
    return r * (1.0 - 0.136) - 0.40 - 9.0 - 1.50

def load_data():
    if os.path.exists("data.json"):
        with open("data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "updated": datetime.now(EST).isoformat(timespec="seconds"),
        "deals": list(),
        "rejected": list(),
        "styles": DEFAULT_STYLES,
        "sweeps": list(),
        "seen": list(),
        "rotation": 0
    }

def save_data(data):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))

def make_thumbnail(img_url):
    try:
        r = requests.get(img_url, headers=HEADERS, timeout=10)
        im = Image.open(BytesIO(r.content)).convert("RGB")
        im.thumbnail((240, 240))
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=78)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None

def inspect_with_gemini(client, title, brand_target, desc, photo_urls):
    if len(photo_urls) < 4:
        return False, f"Fewer than 4 photos ({len(photo_urls)} found)."
    parts = [
        f"You are a strict luxury/vintage clothing authenticator and condition inspector. "
        f"Target style: {brand_target}. Listing title: {title}. Description: {desc}. "
        f"Inspect these listing photos carefully. Reject if: "
        f"(1) Brand tag or style does not genuinely match {brand_target} (or is a fleece/diffusion/wrong model), "
        f"(2) Any photo shows stains, yellowing, dirt, holes, repairs, tears, heavy pilling, worn cuffs/collar, or missing belt/hood/buttons, "
        f"(3) Photos are too blurry to judge. "
        f"Reply ONLY in JSON: {{\"pass\": true/false, \"reason\": \"short 1-sentence reason\"}}"
    ]
    loaded = 0
    for u in photo_urls[:6]:
        try:
            resp = requests.get(u, headers=HEADERS, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 2000:
                parts.append(types.Part.from_bytes(data=resp.content, mime_type="image/jpeg"))
                loaded += 1
        except Exception:
            continue
    if loaded < 4:
        return False, f"Could not load at least 4 clear photos ({loaded} loaded)."
    try:
        res = client.models.generate_content(model="gemini-2.5-flash", contents=parts)
        txt = res.text.strip()
        m = re.search(r'\{.*\}', txt, re.S)
        verdict = json.loads(m.group(0))
        if verdict.get("pass"):
            return True, f"Photos checked: no stains or damage seen ({loaded} photos)"
        return False, verdict.get("reason", "Failed visual inspection.")
    except Exception as e:
        return False, f"AI photo check skipped/error: {str(e)[:60]}"

def send_email(alerts):
    sender = os.environ.get("EMAIL_SENDER")
    pwd = os.environ.get("EMAIL_APP_PASSWORD")
    recipient = os.environ.get("EMAIL_RECIPIENT") or sender
    pages_url = os.environ.get("DASHBOARD_URL", "https://github.io")
    if not (sender and pwd and alerts):
        return
    lines = ["BUY ALERT - New profitable flips passed all rules:\n"]
    for a in alerts:
        lines.append(f"- {a['title']} ({a['marketplace']}) - All-in: ${a['total']:.2f} | Est. Profit: +${a['net_profit']:.2f}\n  Link: {a['url']}\n")
    lines.append(f"\nDashboard: {pages_url}")
    msg = MIMEText("\n".join(lines))
    msg["Subject"] = f"Deal Finder: {len(alerts)} New Buy Alert(s)!"
    msg["From"] = sender
    msg["To"] = recipient
    with smtplib.SMTP_SSL("://gmail.com", 465) as s:
        s.login(sender, pwd)
        s.send_message(msg)

def search_ebay(query):
    url = f"https://ebay.com{requests.utils.quote(query)}&LH_BIN=1&LH_ItemCondition=3000&_sop=10&_udhi=55"
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return list(), "eBay unavailable"
    soup = BeautifulSoup(r.text, "html.parser")
    items = list()
    for li in soup.select("li.s-item, li.s-card")[:12]:
        a = li.select_one("a[href*='/itm/']")
        if not a:
            continue
        href = a["href"].split("?").pop(0).split("#").pop(0)
        m_id = re.search(r'/itm/(\d+)', href)
        if not m_id:
            continue
        lid = "ebay:" + m_id.group(1)
        t_el = li.select_one(".s-item__title, .s-card__title")
        title = t_el.get_text(" ", strip=True) if t_el else ""
        if not title or "shop on ebay" in title.lower():
            continue
        p_el = li.select_one(".s-item__price, .s-card__price")
        pm = re.search(r'\$(\d+(?:\.\d+)?)', p_el.get_text() if p_el else "")
        if not pm:
            continue
        price = float(pm.group(1))
        s_el = li.select_one(".s-item__shipping, .s-item__logisticsCost")
      sm = re.search(r'$(\d+(?:.\d+)?)', s_el.get_text() if s_el else "")
ship = float(sm.group(1)) if sm else 0.0
items.append({"id": lid, "marketplace": "eBay", "url": href, "title": title[:95], "price": price, "shipping": ship, "fees": 0.0})
return items, None
def inspect_ebay_listing(url):
r = requests.get(url, headers=HEADERS, timeout=15)
soup = BeautifulSoup(r.text, "html.parser")
full_text = soup.get_text(" ", strip=True).lower()
photos = list()
for img in soup.find_all("img"):
src = img.get("src") or img.get("data-src") or ""
if "ebayimg.com" in src:
hi = re.sub(r's-l\d+.', 's-l800.', src)
if hi not in photos:
photos.append(hi)
og = soup.find("meta", property="og:image")
og_url = og["content"] if og and og.get("content") else (photos.pop(0) if photos else None)
size_m = re.search(r'size[:\s]+([a-z0-9-.]+)', full_text)
size = size_m.group(1).lower() if size_m else ""
return full_text[:1500], size, photos, og_url
def main():
data = load_data()
seen = set(data.get("seen", list()))
styles = data.get("styles") or DEFAULT_STYLES
data["styles"] = styles
rot = data.get("rotation", 0)
batch = [styles[(rot + i) % len(styles)] for i in range(min(5, len(styles)))]
data["rotation"] = (rot + len(batch)) % max(1, len(styles))
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
new_alerts, new_offers, new_rejected = list(), list(), list()
pages_read, candidates_checked = 0, 0
notes_list = list()
for st in batch:
q = f"{st['brand']} {st['name'].split('(').pop(0).strip()}"
time.sleep(1.5)
try:
listings, err = search_ebay(q)
pages_read += 1
if err:
notes_list.append(err)
continue
except Exception as e:
notes_list.append(f"Search error: {str(e)[:40]}")
continue
for item in listings:
if item["id"] in seen:
continue
seen.add(item["id"])
candidates_checked += 1
total = round((item["price"] + item["shipping"]) * 1.08 + item["fees"], 2)
if total > 65:
continue
time.sleep(1.5)
try:
desc, size, photos, og_url = inspect_ebay_listing(item["url"])
pages_read += 1
except Exception:
continue
if any(bad in desc for bad in BAD_KEYWORDS) or any(bad in item["title"].lower() for bad in BAD_KEYWORDS):
new_rejected.append({"marketplace": item["marketplace"], "title": f"{item['title']} - ${item['price']:.0f}", "why": "Title or description triggered flaw/kids/size filter.", "url": item["url"]})
continue
if size and size not in ALLOWED_SIZES:
new_rejected.append({"marketplace": item["marketplace"], "title": f"{item['title']} - ${item['price']:.0f}", "why": f"Excluded size ({size}).", "url": item["url"]})
continue
if client:
passed, reason = inspect_with_gemini(client, item["title"], f"{st['brand']} {st['name']}", desc[:500], photos)
if not passed:
new_rejected.append({"marketplace": item["marketplace"], "title": f"{item['title']} - ${item['price']:.0f}", "why": reason, "url": item["url"]})
continue
else:
reason = "Keyword and price check passed"
resale = st["conservative"]
profit = round(net_resale(resale) - total, 2)
offer_at = round((50.0 - item["fees"]) / 1.08 - item["shipping"], 2)
profit_at_offer = round(net_resale(resale) - 50.0, 2)
now_iso = datetime.now(EST).isoformat(timespec="seconds")
record = {
"id": item["id"], "marketplace": item["marketplace"], "title": item["title"],
"url": item["url"], "img": make_thumbnail(og_url) if og_url else None,
"price": item["price"], "shipping": item["shipping"], "fees": item["fees"],
"total": total, "style": st["slug"], "resale": resale, "net_profit": profit,
"offer_at": offer_at if total > 50 else None,
"profit_at_offer": profit_at_offer if total > 50 else None,
"flags": list(), "reasons": [reason], "found": now_iso
}
if total <= 50 and profit >= 40 and st["sell_through"] >= 0.25:
record["decision"] = "ALERT"
new_alerts.append(record)
elif total > 50 and offer_at >= 0.70 * item["price"] and profit_at_offer >= 40:
record["decision"] = "OFFER"
new_offers.append(record)
elif total <= 50 and profit >= 30:
record["decision"] = "REVIEW"
new_offers.append(record)
else:
new_rejected.append({"marketplace": item["marketplace"], "title": f"{item['title']} - ${item['price']:.0f}", "why": f"Profit too low (${profit:.2f} net at ${total:.2f} all-in).", "url": item["url"]})
data["deals"] = (new_alerts + new_offers + data.get("deals", list()))[:40]
seen_rej = {r["url"] for r in new_rejected}
data["rejected"] = (new_rejected + [r for r in data.get("rejected", list()) if r["url"] not in seen_rej])[:40]
data["seen"] = list(seen)[-3000:]
data["updated"] = datetime.now(EST).isoformat(timespec="seconds")
note = f"Checked {candidates_checked} listings across {len(batch)} priority styles." + (" " + "; ".join(set(notes_list)) if notes_list else "")
data["sweeps"] = ([{
"at": data["updated"], "sites": ["eBay"],
"searched": [s["brand"] for s in batch], "pages": pages_read,
"candidates": candidates_checked, "alerts": len(new_alerts),
"offers": len(new_offers), "notes": note
}] + data.get("sweeps", list()))[:100]
save_data(data)
if new_alerts:
send_email(new_alerts)
if name == "main":
main()
