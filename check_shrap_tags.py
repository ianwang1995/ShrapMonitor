# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • Hybrid 最终修复版
· BingX/Bybit：requests+Oxylabs 代理 + 原始宽松匹配
· HTX：Playwright 渲染 + 强制英语头 + 等待 banner 出现
"""

import re, argparse
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── 代理（BingX/Bybit 用） ───
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

def fetch_htx_banner(url: str) -> str:
    """用 Playwright 打开 HTX，强制英语，等 banner 出现后抓 HTML"""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = ctx.new_page()

        # 屏蔽图片/样式/字体/媒体，加速
        page.route("**/*", lambda r, req: r.abort()
                   if req.resource_type in ("image","stylesheet","font","media")
                   else r.continue_())

        page.goto(url, wait_until="networkidle", timeout=60000)
        # 明确等待 banner 文本节点出现
        try:
            page.wait_for_selector("text=Innovation Zone Asset Risk Disclosure", timeout=10000)
        except:
            # 若超时，仍继续抓取当前状态
            pass

        html = page.content()
        browser.close()
        return html.lower()

def detect(name: str, url: str):
    """
    – HTX：Playwright 渲染 + banner 等待
    – 其余：requests+代理
    """
    try:
        if name == "HTX":
            text = fetch_htx_banner(url)
        else:
            resp = requests.get(url, headers=HEADERS,
                                proxies=PROXIES, verify=False, timeout=25)
            text = resp.text.lower()
    except Exception as e:
        return name, [f"fetch_error:{type(e).__name__}"]

    tags = []
    if name == "HTX":
        if "innovation zone asset risk disclosure" in text:
            tags.append("Innovation Zone")
    else:
        if "innovation" in text and ("zone" in text or "risk" in text):
            tags.append("Innovation Zone")

    # ST 检测
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
        push_tg(f"[{now}] ✅ Telegram 测试")
        print("测试消息已发")
        return

    results = [detect(n,u) for n,u in SITES]
    line = " | ".join(f"{n}: {'❗️'+','.join(t) if t else '✅ No tag'}"
                      for n,t in results)
    print(f"[{now}] {line}")
    with open("shrap_tag_report.txt","a",encoding="utf-8") as f:
        f.write(f"[{now}] {line}\n")
    if any(t for _,t in results):
        push_tg(f"[{now}] {line}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true")
    args = p.parse_args()
    main(test=args.test)
