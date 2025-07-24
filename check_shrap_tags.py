# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • 混合 requests + requests-html 版
· BingX/Bybit 用 requests (Bybit 继续用代理)
· HTX 用 huobi.br.com/es-la 域名静态页面（包含 Innovation Zone 文本）避免 JS 注入问题
"""

import re, argparse
from datetime import datetime
import requests
from requests_html import HTMLSession
import warnings

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── 代理（仅给 requests） ───
PROXY = "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000"
PROXIES = {"http": PROXY, "https": PROXY}

# ─── 目标站（HTX 用 es-la 域名） ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?invite_code=shrap2025"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# requests-html session（只给 Bybit 渲染用）
session = HTMLSession()

def detect(name: str, url: str):
    """
    返回 (name, [tags...])，tags 包括 "Innovation Zone" / "ST"
    """
    try:
        if name == "HTX":
            # 直接抓西班牙语版静态页面
            htx_es = "https://www.huobi.br.com/es-la/trade/shrap_usdt"
            r = requests.get(htx_es, headers=HEADERS,
                             proxies=PROXIES, verify=False, timeout=25)
            text = r.text.lower()  # 包含 “Innovation Zone Asset Risk Disclosure” :contentReference[oaicite:0]{index=0}
        elif name == "Bybit":
            # 需渲染的 Bybit
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")
            r = session.get(url, headers=HEADERS, timeout=30)
            r.html.render(timeout=30, sleep=2)
            text = r.html.html.lower()
        else:  # BingX
            r = requests.get(url, headers=HEADERS,
                             proxies=PROXIES, verify=False, timeout=25)
            text = r.text.lower()
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]

    tags = []
    if "innovation zone" in text:
        tags.append("Innovation Zone")
    # ST 检测：找 “st” 并在上下文检测关键字
    for m in re.finditer(r'\bst\b', text):
        window = text[max(0, m.start() - 15) : m.end() + 15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break

    return name, tags

def push_tg(msg: str):
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

    results = [detect(name, url) for name, url in SITES]
    alert = any(tags and not tags[0].startswith("fetch_error") for _, tags in results)

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
