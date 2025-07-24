# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • Hybrid 版
· HTX 用 Playwright 渲染（只这一个），其余两个站点继续走 requests+Oxylabs 代理
· 渲染完后提取 “Innovation Zone” / “ST”
"""

import re, argparse
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── Oxylabs 代理（BingX/Bybit） ───
PROXIES = {
    "http":  "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
    "https": "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
}
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─── 监控目标 ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

def fetch_htx_with_js(url: str) -> str:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_context(user_agent=HEADERS["User-Agent"]).new_page()
        # 屏蔽静态资源，加快加载
        page.route("**/*", lambda route, req: route.abort()
                   if req.resource_type in ("image", "stylesheet", "font", "media")
                   else route.continue_())
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(1500)  # 保证 JS 插入完
        html = page.content()
        browser.close()
        return html.lower()

def detect(name: str, url: str):
    """
    返回 (name, [tags])，
    HTX 用 Playwright，BingX/Bybit 用 requests+代理
    """
    try:
        if name == "HTX":
            text = fetch_htx_with_js(url)
        else:
            r = requests.get(url, headers=HEADERS,
                             proxies=PROXIES, verify=False, timeout=25)
            text = r.text.lower()
    except Exception as e:
        return name, [f"fetch_error:{type(e).__name__}"]

    tags = []
    if "innovation zone" in text:
        tags.append("Innovation Zone")
    for m in re.finditer(r'\bst\b', text):
        window = text[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break
    return name, tags

def push_tg(msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass

def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if test:
        push_tg(f"[{now}] ✅ Telegram test")
        print("Test sent")
        return

    results = [detect(n, u) for n, u in SITES]
    alert = any(tags and not tags[0].startswith("fetch_error") for _, tags in results)
    line = " | ".join(
        f"{n}: {'❗️'+','.join(tags) if tags else '✅ No tag'}"
        for n, tags in results
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
