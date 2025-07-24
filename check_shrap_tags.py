# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • Playwright 版 (2025-07-24)
· Playwright 渲染所有 JS，获取页面完整内容
· HTX 走 huobi.br.com/es-la 静态页，其它交易所走代理无头浏览器
"""

import re, argparse, warnings
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── Oxylabs Web-Unblocker 代理 ───
PROXY = "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000"

# ─── 目标站 ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    # HTX: 我们换成 huobi.br.com/es-la 的静态页，它自带 “Innovation Zone Asset Risk Disclosure”
    ("HTX",   "https://www.huobi.br.com/es-la/trade/shrap_usdt"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def fetch_full_html(url: str) -> str:
    """用 Playwright 无头浏览器打开并返回完整渲染后的 HTML（小写）"""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
            proxy={"server": PROXY}
        )
        ctx = browser.new_context(user_agent=USER_AGENT)
        page = ctx.new_page()
        page.goto(url, timeout=60000)
        html = page.content()
        browser.close()
        return html.lower()

def detect(name: str, url: str):
    """
    返回 (name, [tags…])，tags 可能包含 "Innovation Zone" / "ST"，
    fetch_error:XXX 代表抓取失败
    """
    try:
        text = fetch_full_html(url)
    except Exception as e:
        return name, [f"fetch_error:{type(e).__name__}"]

    tags = []
    if "innovation zone" in text:
        tags.append("Innovation Zone")
    # ST: 找 “st” 并在附近上下文匹配关键字
    for m in re.finditer(r'\bst\b', text):
        window = text[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break
    return name, tags

def push_tg(msg: str):
    """推送到 Telegram"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=15
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
