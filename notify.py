# 每日稀有鳥推播：GitHub Actions 每天跑一次這支程式
# 1. 讀 config.json 裡的地點  2. 向 eBird 要附近的稀有鳥  3. 濾掉 lifelist.txt 裡看過的
# 4. 濾掉之前已經推播過的（記在 notified.json）  5. 用 ntfy 推到手機
import json, os, math, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

KEY, TOPIC = os.environ["EBIRD_KEY"], os.environ["NTFY_TOPIC"]
cfg = json.load(open("config.json", encoding="utf-8"))

def binom(s):
    return " ".join(str(s).strip().split()[:2]).lower()

life = set()
if os.path.exists("lifelist.txt"):
    life = {binom(l) for l in open("lifelist.txt", encoding="utf-8") if l.strip() and not l.startswith("#")}

seen = json.load(open("notified.json", encoding="utf-8")) if os.path.exists("notified.json") else {}
today = datetime.now(timezone.utc).date()
seen = {k: d for k, d in seen.items() if datetime.fromisoformat(d).date() > today - timedelta(days=14)}  # 只記 14 天

def ebird(p, loc):
    q = urllib.parse.urlencode({"lat": p["lat"], "lng": p["lng"], "dist": p.get("dist", 30),
                                "back": cfg.get("back", 2), "detail": "simple", "sppLocale": loc})
    req = urllib.request.Request("https://api.ebird.org/v2/data/obs/geo/recent/notable?" + q, headers={"X-eBirdApiToken": KEY})
    return json.load(urllib.request.urlopen(req, timeout=30))

def km(a, b, c, d):
    r = math.radians
    h = math.sin(r(c - a) / 2) ** 2 + math.cos(r(a)) * math.cos(r(c)) * math.sin(r(d - b) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))

def push(title, msg):
    body = json.dumps({"topic": TOPIC, "title": title, "message": msg, "tags": ["bird"],
                       "click": cfg.get("site", "")}).encode()
    urllib.request.urlopen(urllib.request.Request("https://ntfy.sh/", data=body,
                           headers={"Content-Type": "application/json"}), timeout=30)

for p in cfg["places"]:
    rows = ebird(p, "en")
    zh = {o["speciesCode"]: o["comName"] for o in ebird(p, "zh")}
    new = {}
    for o in rows:
        if cfg.get("only_new", True) and life and binom(o["sciName"]) in life:
            continue
        k = f'{o["subId"]}:{o["speciesCode"]}'
        if k in seen:
            continue
        seen[k] = today.isoformat()
        o["km"] = km(p["lat"], p["lng"], o["lat"], o["lng"])
        s = new.setdefault(o["speciesCode"], o)          # 同一種鳥只列最近的那筆
        if o["km"] < s["km"]:
            new[o["speciesCode"]] = o
    if not new:
        print(p["name"], "沒有新的紀錄")
        continue
    lines = []
    for o in sorted(new.values(), key=lambda x: x["km"]):
        name = zh.get(o["speciesCode"], o["comName"])
        if name != o["comName"]:
            name = f'{name} {o["comName"]}'
        lines.append(f'• {name}｜{o["locName"]}｜{o["km"]:.0f} km｜{o["obsDt"][5:10]}')
    label = "種新種" if life and cfg.get("only_new", True) else "種稀有鳥"
    push(f'{p["name"]}：{len(new)} {label}', "\n".join(lines[:15]) + ("\n…還有更多" if len(lines) > 15 else ""))
    print(p["name"], "已推播", len(new), "種")

json.dump(seen, open("notified.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
