# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • requests-html 版 (2025-07-24)
· 用 Requests-HTML 渲染前端 JS，抓取 “Innovation Zone” / “ST”
· 仅对需要渲染的站点跑 .render()，其它继续走轻量 requests
"""

import re, argparse, warnings
from datetime import datetime
import requests
from requests_html import HTMLSession

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── 代理（仅给 requests） ───
PROXY = "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000"
PROXIES = {"http": PROXY, "https": PROXY}

# ─── 目标站（HTX/BingX 需要渲染 JS；Bybit 直接 requests 即可） ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt"),      # Next.js 前端渲染
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 全局 Requests-HTML 会话
session = HTMLSession()

def detect(url: str, name: str):
    """返回 (exchange, [tags...])，tags 可能含 "Innovation Zone" / "ST""""
    try:
        if name in ("BingX", "HTX"):
            # 渲染 JS
            r = session.get(url, headers=HEADERS, timeout=30)
            # 忽略 HTTPS 警告
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")
            r.html.render(timeout=30, sleep=2)
            text = r.html.html.lower()
        else:
            # Bybit 走普通 requests+代理
            r = requests.get(url, headers=HEADERS,
                             proxies=PROXIES, verify=False, timeout=25)
            text = r.text.lower()
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]
    tags = []

    # 完整短语匹配 “innovation zone”
    if "innovation zone" in text:
        tags.append("Innovation Zone")

    # 原 ST 逻辑：找“st”并在上下文判断
    for m in re.finditer(r'\bst\b', text):
        window = text[max(0, m.start() - 15) : m.end() + 15]
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
            timeout=15
        )
    except Exception as e:
        print("Telegram 推送失败:", e)

def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if test:
        push_tg(f"[{now}] ✅ Telegram 手动测试成功")
        print("测试消息已发")
        return

    results = [detect(u, n) for n, u in SITES]
    alert = any(tags and not tags[0].startswith("fetch_error")
                for _, tags in results)

    line = " | ".join(
        f"{name}: {'❗️'+','.join(tags) if tags else '✅ No tag'}"
        for name, tags in results
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
