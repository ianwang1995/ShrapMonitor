# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • Hybrid 最终版
· HTX：Playwright 渲染 + 等待 “Innovation Zone” 超链接
· BingX/Bybit：requests + Oxylabs 代理 + 宽松匹配
"""

import re
import argparse
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── 代理（BingX/Bybit） ───
PROXIES = {
    "http":  "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
    "https": "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
}
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─── 监控目标 URL ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

def fetch_htx_with_js(url: str) -> str:
    """
    用 Playwright 打开 HTX，强制英文环境，
    等待那个 “Innovation Zone” 可点击链接出现，然后返回渲染后的 HTML（小写）
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )
        page = ctx.new_page()
        # 屏蔽图片/样式/字体/媒体，加速加载
        page.route("**/*", lambda route, req: route.abort()
                   if req.resource_type in ("image","stylesheet","font","media")
                   else route.continue_())
        page.goto(url, wait_until="networkidle", timeout=60000)
        try:
            # 等待那个可点击的“Innovation Zone”链接节点出现
            page.wait_for_selector('a:has-text("Innovation Zone")', timeout=15000)
        except PlaywrightTimeout:
            pass
        html = page.content().lower()
        browser.close()
        return html

def detect(name: str, url: str):
    """
    – HTX：Playwright 渲染 + 等待“Innovation Zone”链接
    – BingX/Bybit：requests + Oxylabs 代理 + 原始宽松匹配
    """
    tags = []
    if name == "HTX":
        try:
            text = fetch_htx_with_js(url)
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]
        if "innovation zone" in text:
            tags.append("Innovation Zone")
    else:
        try:
            resp = requests.get(url, headers=HEADERS,
                                proxies=PROXIES, verify=False, timeout=25)
            text = resp.text.lower()
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]
        if "innovation" in text and ("zone" in text or "risk" in text):
            tags.append("Innovation Zone")

    # ST 标签检测（所有站点通用）
    try:
        source = text
    except UnboundLocalError:
        source = ""
    for m in re.finditer(r'\bst\b', source):
        snippet = source[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', snippet):
            tags.append("ST")
            break

    return name, tags

def push_tg(msg: str):
    """发送 Telegram 报警"""
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
        push_tg(f"[{now}] ✅ Telegram 测试")
        print("测试消息已发")
        return

    results = [detect(n, u) for n, u in SITES]
    line = " | ".join(
        f"{n}: {'❗️'+','.join(tags) if tags else '✅ No tag'}"
        for n, tags in results
    )
    log = f"[{now}] {line}"
    print(log)
    with open("shrap_tag_report.txt", "a", encoding="utf-8") as f:
        f.write(log + "\n")
    if any(tags for _, tags in results):
        push_tg(log)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="仅测试 Telegram 推送")
    args = parser.parse_args()
    main(test=args.test)
