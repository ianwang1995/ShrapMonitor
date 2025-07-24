# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • 混合 requests + Playwright 版 (2025-07-24)
· Bybit 用 Playwright 渲染（资源屏蔽、DOMContentLoaded）
· HTX 走 huobi.br.com/es-la 静态页
· BingX 走普通 requests + 代理
"""

import re, argparse, warnings
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── 代理（仅给 requests） ───
PROXY = "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000"
PROXIES = {"http": PROXY, "https": PROXY}

# ─── 目标站 ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.huobi.br.com/es-la/trade/shrap_usdt"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def fetch_bybit_html(url: str) -> str:
    """Playwright 渲染 Bybit，屏蔽静态资源，只等 DOMContentLoaded"""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
            proxy={"server": PROXY}
        )
        ctx = browser.new_context(user_agent=USER_AGENT)
        page = ctx.new_page()
        # 屏蔽图片、样式、字体、媒体
        page.route("**/*", lambda route, req: route.abort() 
                   if req.resource_type in ("image", "stylesheet", "font", "media") 
                   else route.continue_())
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # 给少量时间让标签注入
        page.wait_for_timeout(1000)
        html = page.content()
        browser.close()
        return html.lower()

def detect(name: str, url: str):
    """返回 (name, [tags...])"""
    try:
        if name == "Bybit":
            text = fetch_bybit_html(url)
        else:
            # HTX & BingX 全用 requests
            r = requests.get(url, headers={"User-Agent": USER_AGENT},
                             proxies=PROXIES, verify=False, timeout=20)
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
    except Exception:
        pass

def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if test:
        push_tg(f"[{now}] ✅ Telegram 测试消息")
        print("测试消息已发")
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
    ap.add_argument("--test", action="store_true", help="仅测试 Telegram 推送")
    args = ap.parse_args()
    main(test=args.test)
