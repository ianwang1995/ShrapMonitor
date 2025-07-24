# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • HTX API 多端点探测 + 回退 HTML 正则
· HTX：尝试 /hotWordList 和 /trade/hotWordList，拿 JSON 里 banner 文本
        — 如都失败，再从 HTML 正则查 “innovation zone” / “创新专区”
· BingX/Bybit：requests + Oxylabs 代理 + 原始宽松匹配
"""

import re
import time
import argparse
from datetime import datetime
import requests

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbq9sdfkjhCVTrcc"
CHAT_ID   = "1805436662"

# ─── Oxylabs 代理（仅给 BingX/Bybit） ───
PROXIES = {
    "http":  "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
    "https": "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
}

HEADERS = {
    "User-Agent":      "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

def detect_htx(url: str):
    """
    多端点探测 HTX hotWordList 接口拿 banner 文本 
    回退到 HTML 正则
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    # 预先 GET 主页面设置 Cookie
    try:
        resp_page = session.get(url, timeout=20, verify=False)
        html = resp_page.text
    except Exception:
        html = ""
    # 可能的 API 路径
    endpoints = [
        "https://www.htx.com/hotWordList",
        "https://www.htx.com/trade/hotWordList",
    ]
    # 第一优先：接口 JSON
    for api in endpoints:
        try:
            r = session.get(
                api,
                params={"r": str(int(time.time()*1000))},
                timeout=10,
                verify=False
            )
            if r.status_code != 200:
                continue
            data = r.json().get("data", [])
        except Exception:
            continue
        # 搜 banner 文本
        for item in data:
            text = item.get("text", "").lower()
            if "innovation zone" in text or "创新专区" in text:
                return ["Innovation Zone"]
    # 第二优先：HTML 正则
    lower = html.lower()
    if "innovation zone" in lower or "创新专区" in lower:
        return ["Innovation Zone"]
    return []

def detect(name: str, url: str):
    tags = []
    if name == "HTX":
        tags = detect_htx(url)
    else:
        # BingX/Bybit：原始轻量匹配
        try:
            r = requests.get(
                url,
                headers=HEADERS,
                proxies=PROXIES,
                verify=False,
                timeout=20
            )
            text = r.text.lower()
            if "innovation" in text and ("zone" in text or "risk" in text):
                tags.append("Innovation Zone")
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]
    # ST 通用检测
    source = text if name != "HTX" else ""  # HTX 上没 ST
    for m in re.finditer(r'\bst\b', source):
        window = source[max(0, m.start()-15): m.end()+15]
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
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="仅测试 Telegram 推送")
    args = p.parse_args()
    main(test=args.test)
