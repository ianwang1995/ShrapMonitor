# ----- check_shrap_tags.py  (Web Unblocker API 版) -----
"""
SHRAP Tag Monitor · 2025-07-24
• 直接调用 Oxylabs Web-Unblocker API (render=true) → 后端执行 JS、过 Cloudflare
• 无 Selenium 依赖，CI 环境稳定
"""

import re, argparse, urllib.parse
from datetime import datetime
import requests

# ───────── Telegram ─────────
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ───────── Web-Unblocker 凭据 ─────────
API_USER = "ianwang_w8WVr"
API_PASS = "Snowdor961206~"
BASE     = "https://pr.oxylabs.io"                  # API 入口

PARAMS   = (
    f"username={API_USER}&password={API_PASS}"
    "&country=us"          # 出口国家，可改 cc 参数
    "&render=true"         # 执行 JS，返回最终 DOM
)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ───────── 目标站 ─────────
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

# ───────── 抓取函数 ─────────
def fetch_html(url: str) -> str:
    api = f"{BASE}/?{PARAMS}&url={urllib.parse.quote_plus(url)}"
    r = requests.get(api, headers=HEADERS, verify=False, timeout=40)
    r.raise_for_status()
    return r.text.lower()

# ───────── 标签检测 ─────────
def detect(name: str, url: str):
    try:
        html = fetch_html(url)
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]

    tags = []
    if re.search(r'innovation.{0,30}zone|zone.{0,30}innovation', html):
        tags.append("Innovation Zone")

    for m in re.finditer(r'\bst\b', html):
        window = html[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST"); break

    return name, tags

# ───────── Telegram 推送 ─────────
def push(msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            proxies={}, verify=False, timeout=15
        )
    except Exception as e:
        print("Telegram push fail:", e)

# ───────── 主流程 ─────────
def main(test=False):
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

# ───────── CLI ─────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true",
                    help="发送一条 Telegram 测试消息后退出")
    args = ap.parse_args()
    main(test=args.test)
