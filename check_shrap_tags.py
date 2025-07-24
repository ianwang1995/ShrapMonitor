# ----- check_shrap_tags.py (POST JSON 正式版) -----
import re, argparse, json, urllib.parse
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth

# Telegram
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# Oxylabs credentials
API_USER = "ianwang_w8WVr"
API_PASS = "Snowdor961206~"
BASE = "https://104.17.8.22"          # ← 纯 IP
HOST_HEADER = {"Host": "pr.oxylabs.io"}

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
TIMEOUT = 90  # 单站最多等待 90 秒

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

def fetch_html(url: str) -> str:
    payload = {
        "url": url,
        "render": True,
        "country": "us"
    }
    r = requests.post(
        BASE,
        headers={**HEADERS, **HOST_HEADER, "Content-Type": "application/json"},
        auth=(API_USER, API_PASS),
        data=json.dumps(payload),
        verify=False,
        timeout=90
    )
    r.raise_for_status()
    return r.text.lower()

def detect(name: str, url: str):
    try:
        print(f"▼ fetching {name} …", flush=True)
        html = fetch_html(url)
        print(f"▲ done     {name}", flush=True)
    except requests.exceptions.Timeout:
        return name, ["fetch_error:timeout"]
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]

    tags = []
    if re.search(r'innovation.{0,30}zone|zone.{0,30}innovation', html):
        tags.append("Innovation Zone")
    for m in re.finditer(r'\bst\b', html):
        win = html[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', win):
            tags.append("ST"); break
    return name, tags

def push(msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            proxies={}, verify=False, timeout=15)
    except Exception as e:
        print("Telegram push fail:", e)

def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if test:
        push(f"[{now}] ✅ Telegram 手动测试成功")
        print("测试消息已发"); return

    res   = [detect(n, u) for n, u in SITES]
    alert = any(t and not t[0].startswith("fetch_error") for _, t in res)
    line  = " | ".join(f"{n}: {'❗️'+', '.join(t) if t else '✅ No tag'}" for n, t in res)
    log   = f"[{now}] {line}"
    print(log)
    with open("shrap_tag_report.txt", "a", encoding="utf-8") as f:
        f.write(log + "\n")
    if alert:
        push(log)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true",
                    help="发送一条 Telegram 测试消息后退出")
    args = ap.parse_args()
    main(test=args.test)
