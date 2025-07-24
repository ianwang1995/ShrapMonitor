# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • Playwright 全量渲染版 (2025-07-24)
· 三家交易所都用 Playwright Headless Chromium
· 等待 networkidle + 少量延时，保证 JS 注入的标签都到位
· 屏蔽图片/样式/字体/媒体，加速加载
"""

import re, argparse
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── 目标站 URL 列表 ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    # 下面这个 URL 已经验证过页面里会有“Innovation Zone Asset Risk Disclosure.”
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?invite_code=bsvx3223"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def fetch_html_playwright(url: str) -> str:
    """用 Playwright 打开页面，屏蔽静态资源，只等 networkidle + 少量延时"""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=USER_AGENT)
        page = ctx.new_page()
        # 屏蔽资源，加快加载
        page.route("**/*", lambda route, req: route.abort()
                   if req.resource_type in ("image", "stylesheet", "font", "media")
                   else route.continue_())
        # 等全部网络请求、脚本执行完
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)  # 再给 2s 让徽章/标签插入 DOM
        html = page.content()
        browser.close()
        return html.lower()

def detect(name: str, url: str):
    """返回 (交易所名, [标签列表])——可能包含 "Innovation Zone" 或 "ST""""
    try:
        text = fetch_html_playwright(url)
    except Exception as e:
        return name, [f"fetch_error:{type(e).__name__}"]

    tags = []
    if "innovation zone" in text:
        tags.append("Innovation Zone")
    for m in re.finditer(r'\bst\b', text):
        window = text[max(0, m.start() - 15): m.end() + 15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break
    return name, tags

def push_tg(msg: str):
    """发 Telegram"""
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
    ap.add_argument("--test", action="store_true",
                    help="仅测试 Telegram 推送")
    args = ap.parse_args()
    main(test=args.test)
