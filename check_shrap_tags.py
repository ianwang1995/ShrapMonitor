# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • requests 轻量版 (2025-07-24)
· 仅对 HTX 强制英文 Accept-Language、直连；BingX/Bybit 继续走 Oxylabs 代理
· 仅用 requests 获取页面 → 正则判 “Innovation Zone” / “ST”
"""

import re
import argparse
from datetime import datetime
import requests

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ─── Oxylabs Web-Unblocker 代理（仅给 BingX/Bybit） ───
PROXY = "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000"
PROXIES = {"http": PROXY, "https": PROXY}

# ─── 默认 User-Agent ───
BASE_HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─── 监控站点列表 ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

def detect(url: str, name: str):
    # 准备 headers 和 proxies
    headers = BASE_HEADERS.copy()
    if name == "HTX":
        # 强制英文，不走代理
        headers["Accept-Language"] = "en-US,en;q=0.9"
        proxies = None
    else:
        # BingX/Bybit 走 Oxylabs 代理
        proxies = PROXIES

    # 发请求
    try:
        r = requests.get(url,
                         headers=headers,
                         proxies=proxies,
                         verify=False,
                         timeout=25)
        text = r.text.lower()
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]

    # 匹配标签
    tags = []
    # English or Chinese for Innovation Zone
    if "innovation zone" in text or "创新专区" in text:
        tags.append("Innovation Zone")

    # ST 标签：找 “st” 并在附近匹配风险关键字
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
        push_tg(f"[{now}] ✅ Telegram 测试成功")
        print("测试消息已发")
        return

    results = [detect(u, n) for n, u in SITES]
    alert = any(tags and not tags[0].startswith("fetch_error") for _, tags in results)

    line = " | ".join(
        f"{name}: {'❗️'+', '.join(tags) if tags else '✅ No tag'}"
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
    ap.add_argument("--test", action="store_true", help="仅测试 Telegram 推送")
    args = ap.parse_args()
    main(test=args.test)
