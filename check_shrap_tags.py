# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • requests 轻量版 (2025-07-24)
· Oxylabs Web-Unblocker 代理直连，绕过 Cloudflare
· 仅用 requests 获取页面 → 正则判 “Innovation Zone” / “ST”
"""

import re, argparse
from datetime import datetime
import requests

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── Oxylabs Web-Unblocker 代理 ───
PROXY = "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000"
PROXIES = {"http": PROXY, "https": PROXY}

# ─── 目标站 ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

HEADERS = {"User-Agent": "Mozilla/5.0"}

def detect(url: str, name: str):
    try:
        r = requests.get(url, headers=HEADERS,
                         proxies=PROXIES, verify=False, timeout=25)
        text = r.text.lower()
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]

    tags = []
    if "innovation" in text and ("zone" in text or "risk" in text):
        tags.append("Innovation Zone")

    for m in re.finditer(r'\bst\b', text):
        window = text[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break
    return name, tags

def push_tg(msg: str):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    except Exception as e:
        print("Telegram 推送失败:", e)

def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if test:
        push_tg(f"[{now}] ✅ Telegram 手动测试成功")
        print("测试消息已发")
        return

    results = [detect(u, n) for n, u in SITES]
    alert = any(t and not t[0].startswith("fetch_error") for _, t in results)
    line = " | ".join(
        f"{n}: {'❗️'+', '.join(t) if t else '✅ No tag'}"
        for n, t in results
    )
    log = f"[{now}] {line}"
    print(log)

    with open("shrap_tag_report.txt", "a", encoding="utf-8") as f:
        f.write(log + "\n")

    if alert:
        push_tg(log)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    main(test=args.test)
