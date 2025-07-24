# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • NextData JSON 版（2025-07-24）
· HTX：解析 __NEXT_DATA__ JSON，直接读 innovationZone 字段
· BingX/Bybit：requests + Oxylabs 代理 + 宽松匹配
"""

import re, json, argparse
from datetime import datetime
import requests

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbq9sdfkjhCVTrcc"
CHAT_ID   = "1805436662"

# ─── 代理（BingX/Bybit 用） ───
PROXIES = {
    "http":  "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
    "https": "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
}
HEADERS = {"User-Agent": "Mozilla/5.0"}

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

def detect(name: str, url: str):
    tags = []

    if name == "HTX":
        try:
            r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            html = r.text
            # 抽取 __NEXT_DATA__ 脚本中的 JSON
            m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
            if m:
                data = json.loads(m.group(1))
                # 路径可能略有不同，这里举例常见结构
                md = data.get("props", {}) \
                         .get("pageProps", {}) \
                         .get("marketDetail", {}) 
                # 如果有 innovationZone 标志，添标签
                if md.get("innovationZone") or md.get("riskDisclosureUrl"):
                    tags.append("Innovation Zone")
            else:
                # 回退到页面文本搜一把
                lower = html.lower()
                if "innovation zone" in lower or "创新专区" in lower:
                    tags.append("Innovation Zone")
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]

    else:
        # BingX/Bybit 用代理走原始宽松匹配
        try:
            r = requests.get(url, headers=HEADERS, proxies=PROXIES,
                             verify=False, timeout=20)
            lower = r.text.lower()
            if "innovation" in lower and ("zone" in lower or "risk" in lower):
                tags.append("Innovation Zone")
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]

    # ST 标签通用
    source = (md if name=="HTX" else lower) if name=="HTX" else lower
    for m in re.finditer(r'\bst\b', source):
        w = source[max(0, m.start()-15):m.end()+15]
        if re.search(r'risk|special|treatment', w):
            tags.append("ST")
            break

    return name, tags

def push_tg(msg: str):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except:
        pass

def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if test:
        push_tg(f"[{now}] ✅ Telegram 测试")
        print("测试消息已发")
        return

    results = [detect(n, u) for n, u in SITES]
    line = " | ".join(f"{n}: {'❗️'+','.join(tags) if tags else '✅ No tag'}"
                      for n, tags in results)
    print(f"[{now}] {line}")
    with open("shrap_tag_report.txt","a",encoding="utf-8") as f:
        f.write(f"[{now}] {line}\n")
    if any(tags for _,tags in results):
        push_tg(f"[{now}] {line}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="仅测试 Telegram")
    args = p.parse_args()
    main(test=args.test)
