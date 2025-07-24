# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • Hybrid 修复版 (2025-07-24)
· HTX 用 Playwright + 严格匹配
· BingX/Bybit 走 requests+代理 + 原始宽松匹配
"""

import re, argparse
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── 代理（只给 BingX/Bybit） ───
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

def fetch_htx_js(url: str) -> str:
    """只给 HTX 做一次 Playwright 渲染，拿到 JS 动态插入的标签"""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=HEADERS["User-Agent"])
        page = ctx.new_page()
        # 屏蔽图片/样式/字体/媒体，加速
        page.route("**/*", lambda r, req: r.abort()
                   if req.resource_type in ("image","stylesheet","font","media")
                   else r.continue_())
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(1500)
        html = page.content()
        browser.close()
        return html.lower()

def detect(name: str, url: str):
    """
    返回 (交易所名, [tags])  
    – HTX：Playwright + 严格匹配 “innovation zone”  
    – BingX/Bybit：requests+代理 + 宽松匹配 “innovation” & (“zone” or “risk”)
    """
    try:
        if name == "HTX":
            text = fetch_htx_js(url)
        else:
            resp = requests.get(url,
                                headers=HEADERS,
                                proxies=PROXIES,
                                verify=False,
                                timeout=25)
            text = resp.text.lower()
    except Exception as e:
        return name, [f"fetch_error:{type(e).__name__}"]

    tags = []
    if name == "HTX":
        # HTX 必须精确匹配
        if "innovation zone asset risk disclosure" in text or "innovation zone" in text:
            tags.append("Innovation Zone")
    else:
        # 原始宽松匹配
        if "innovation" in text and ("zone" in text or "risk" in text):
            tags.append("Innovation Zone")

    # ST 检测（同逻辑）
    for m in re.finditer(r'\bst\b', text):
        snippet = text[max(0, m.start()-15) : m.end()+15]
        if re.search(r'risk|special|treatment', snippet):
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
        push_tg(f"[{now}] ✅ Telegram 测试")
        print("测试消息已发")
        return

    results = [detect(n, u) for n, u in SITES]
    line = " | ".join(
        f"{n}: {'❗️'+','.join(tags) if tags else '✅ No tag'}"
        for n, tags in results
    )
    print(f"[{now}] {line}")
    with open("shrap_tag_report.txt", "a", encoding="utf-8") as f:
        f.write(f"[{now}] {line}\n")
    if any(tags for _,tags in results):
        push_tg(f"[{now}] {line}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="仅测试 Telegram")
    args = p.parse_args()
    main(test=args.test)
