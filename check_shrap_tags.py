# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • 全 Playwright 版 (2025-07-24)
· 三个交易所都用 Playwright 渲染
· 屏蔽静态资源，等待 DOMContentLoaded + 少量延时
· 不再使用任何代理
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
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?invite_code=bsvx3223"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def fetch_html_playwright(url: str) -> str:
    """用 Playwright 打开页面，屏蔽静态资源，只等 DOMContentLoaded"""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=USER_AGENT)
        page = ctx.new_page()
        # 拦截静态资源，加快加载
        page.route("**/*", lambda route, req: route.abort()
                   if req.resource_type in ("image", "stylesheet", "font", "media")
                   else route.continue_())
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1000)  # 给前端脚本一点时间插入标签
        html = page.content()
        browser.close()
        return html.lower()

def detect(name: str, url: str):
    """检测单个交易所页面里的 Innovation Zone / ST 标记"""
    try:
        text = fetch_html_playwright(url)
    except Exception as e:
        return name, [f"fetch_error:{type(e).__name__}"]

    tags = []
    if "innovation zone" in text:
        tags.append("Innovation Zone")
    # ST：找 “st” 并在附近上下文匹配关键字
    for m in re.finditer(r'\bst\b', text):
        window = text[max(0, m.start() - 15): m.end() + 15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break
    return name, tags

def push_tg(msg: str):
    """发 Telegram 报警"""
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
    alert = any(tags and not tags[0].startswith("fetch_error")
                for _, tags in results)
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
