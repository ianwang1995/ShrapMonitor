# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • requests 轻量版 (2025-07-24)
· Oxylabs 代理继续给 BingX/Bybit
· HTX 换成 /en-us/ 路径直连，拿英文页面
· 只用 requests + 正则判 “Innovation Zone” / “ST”
"""

import re, argparse
from datetime import datetime
import requests

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── Oxylabs Web-Unblocker 代理（BingX/Bybit 用） ───
PROXIES = {
    "http":  "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
    "https": "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─── 监控站点列表 ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    # 这里改成 /en-us/ 路径，让 HTX 返回英文版
    ("HTX",   "https://www.htx.com/en-us/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

def detect(name: str, url: str):
    # BingX/Bybit 走代理，HTX 直连
    proxies = None if name == "HTX" else PROXIES

    try:
        r = requests.get(
            url,
            headers=HEADERS,
            proxies=proxies,
            verify=False,
            timeout=25
        )
        text = r.text.lower()
    except Exception as e:
        return name, [f"fetch_error:{type(e).__name__}"]

    tags = []
    # 英文 innovation zone 或中文 创新专区
    if "innovation zone" in text or "创新专区" in text:
        tags.append("Innovation Zone")

    # ST 附近匹配 risk/special/treatment
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
        push_tg(f"[{now}] ✅ Telegram 测试成功")
        print("测试消息已发")
        return

    results = [detect(n, u) for n, u in SITES]
    alert = any(tags and not tags[0].startswith("fetch_error") for _, tags in results)
    line = " | ".join(
        f"{n}: {'❗️'+', '.join(tags) if tags else '✅ No tag'}"
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
