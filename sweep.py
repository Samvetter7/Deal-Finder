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
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

BAD_KEYWORDS = [
    "stain", "spot", "mark", "discolor", "dirt", "needs cleaning", "spot clean",
    "hole", "burn", "tear", "rip", "snag", "pilling", "fading", "rust",
    "missing belt", "missing hood", "missing button", "broken zipper", "odor",
    "smoke", "flaw", "as is", "xxs", "2xl", "xxl", "3xl", "1x", "2x", "3x",
    "kids", "youth", "toddler", "gap x", "dupe", "inspired", "iso ", "liner only"
]

ALLOWED_SIZES = {
    "xs", "s", "m", "l", "xl", "small", "medium", "large", "x-small", "x-large",
    "0", "2", "4", "6", "8", "10", "12", "14", "16",
    "36", "38", "40", "42", "44", "46", "28", "30", "32", "34"
}

def net_resale(r):
    return r * (1.0 - 0.136) - 0.40 - 9.0 - 1.50

def load_html():
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    m = re.search(r'<!--DATA-START--><script id="sweep-data" type="application/json">(.*?)</script><!--DATA-END-->', html, re.S)
    return html, json.loads(m.group(1))

def save_html(html, data):
    raw_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    new_html = re.sub(
        r'<!--DATA-START--><script id="sweep-data" type="application/json">.*?</script><!--DATA-END-->',
        f'<!--DATA-START--><script id="sweep-data" type="application/json">{raw_json}</script><!--DATA-END-->',
        html, flags=re.S
    )
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_html)

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

def search_poshmark(query):
    url = f"https://poshmark.com{requests.utils.quote(query)}&sort_by=added_desc&availability=available&price%5B%5D=-55"
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return [], "Poshmark blocked/unavailable"
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for tile in soup.select(".tiles_container__tile--redesign, [data-et-name='listing']")[:12]:
        a = tile.select_one("a[href*='/listing/']")
        if not a:
            continue
        href = "https://poshmark.com" + a["href"].split("?")[0]
        lid = "poshmark:" + href.split("-")[-1]
        text = tile.get_text(" | ", strip=True)
        pm = re.search(r'\$(\d+(?:\.\d+)?)', text)
        if not pm:
            continue
        price = float(pm.group(1))
        items.append({"id": lid, "marketplace": "Poshmark", "url": href, "title": text.split("|")[0][:90], "price": price, "shipping": 7.97, "fees": 0.0})
    return items, None

def inspect_poshmark_listing(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    full_text = soup.get_text(" ", strip=True).lower()
    photos = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if "/posts/" in src and ("l_" in src or "m_" in src) and src not in photos:
            photos.append(src)
    og = soup.find("meta", property="og:image")
    og_url = og["content"] if og and og.get("content") else (photos[0] if photos else None)
    size_m = re.search(r'size[:\s]+([a-z0-9\-\.]+)', full_text)
    size = size_m.group(1).lower() if size_m else ""
    return full_text[:1500], size, photos, og_url

def main():
    html, data = load_html()
    seen = set(data.get("seen", []))
    styles = data.get("styles", [])
    rot = data.get("rotation", 0)
    batch = [styles[(rot + i) % len(styles)] for i in range(min(5, len(styles)))]
    data["rotation"] = (rot + len(batch)) % max(1, len(styles))

    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else None

    new_alerts, new_offers, new_rejected = [], [], []
    pages_read, candidates_checked = 0, 0
    notes_list = []

    for st in batch:
        q = f"{st['brand']} {st['name'].split('(')[0].strip()}"
        time.sleep(1.5)
        try:
            listings, err = search_poshmark(q)
            pages_read += 1
            if err:
                notes_list.append(err)
                continue
        except Exception as e:
            notes_list.append(f"Poshmark error: {str(e)[:40]}")
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
                desc, size, photos, og_url = inspect_poshmark_listing(item["url"])
                pages_read += 1
            except Exception:
                continue

            if any(bad in desc for bad in BAD_KEYWORDS):
                new_rejected.append({"marketplace": item["marketplace"], "title": f"{item['title']} - ${item['price']:.0f}", "why": "Description or size triggered keyword filter.", "url": item["url"]})
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
"flags": [], "reasons": [reason], "found": now_iso
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

    data["deals"] = (new_alerts + new_offers + data.get("deals", []))[:40]
    seen_rej = {r["url"] for r in new_rejected}
    data["rejected"] = (new_rejected + [r for r in data.get("rejected", []) if r["url"] not in seen_rej])[:40]
    data["seen"] = list(seen)[-3000:]
    data["updated"] = datetime.now(EST).isoformat(timespec="seconds")
    note = f"Checked {candidates_checked} listings across {len(batch)} priority styles." + (" " + "; ".join(set(notes_list)) if notes_list else "")
    data["sweeps"] = ([{
        "at": data["updated"], "sites": ["Poshmark"],
        "searched": [s["brand"] for s in batch], "pages": pages_read,
        "candidates": candidates_checked, "alerts": len(new_alerts),
        "offers": len(new_offers), "notes": note
    }] + data.get("sweeps", []))[:100]

    save_html(html, data)
    if new_alerts:
        send_email(new_alerts)

if __name__ == "__main__":
    main()
main()
