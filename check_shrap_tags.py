# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • 动态抓 HTX hotWordList 接口 + 原始 BingX/Bybit 逻辑
· 第一步 GET HTX 页面，正则找出 hotWordList 接口路径
· 第二步 GET 该接口，解析 JSON 看 banner 文本
· BingX/Bybit：requests + Oxylabs 代理 + 宽松匹配
"""

import re, time, urllib.parse, argparse
from datetime import datetime
import requests

BOT_TOKEN = "7725811450:AAF9BQZEsBEfbq9sdfkjhCVTrcc"
CHAT_ID   = "1805436662"

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
    tags = []
    session = requests.Session()
    # 1. 拉取页面 HTML
    resp = session.get(url, headers=HEADERS, timeout=20, verify=False)
    html = resp.text

    # 2. 动态正则提取 hotWordList 接口路径
    #    匹配形如 "/hotWordList?r=162xxx..." 或 "/trade/hotWordList?..." 的片段
    m = re.search(r'(["\'])(/[^"\']*hotWordList\?r=\d+[^"\']*)\1', html)
    if not m:
        return tags  # 找不到接口，回空

    api_path = m.group(2)
    api_url  = urllib.parse.urljoin(url, api_path)
    # 3. 调用接口拿 JSON
    jresp = session.get(api_url, headers=HEADERS, timeout=10, verify=False)
    try:
        data = jresp.json().get("data", [])
    except ValueError:
        return tags

    # 4. 在返回的 data 列表里找 banner 文本
    for item in data:
        text = item.get("text", "").lower()
        if "innovation zone asset risk disclosure" in text:
            tags.append("Innovation Zone")
            break

    return tags

def detect(name: str, url: str):
    if name == "HTX":
        try:
            tags = detect_htx(url)
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]
    else:
        # BingX/Bybit：原始轻量逻辑
        try:
            r = requests.get(url, headers=HEADERS,
                             proxies=PROXIES, verify=False, timeout=20)
            text = r.text.lower()
            tags = []
            if "innovation" in text and ("zone" in text or "risk" in text):
                tags.append("Innovation Zone")
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]

    # ST 检测（所有站点通用）
    source = text if name != "HTX" else ""  # HTX banner 接口里没有 ST，所以跳过
    for m in re.finditer(r'\bst\b', source):
        w = source[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', w):
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
    print(f"[{now}] {line}")
    with open("shrap_tag_report.txt", "a", encoding="utf-8") as f:
        f.write(f"[{now}] {line}\n")
    if any(tags for _, tags in results):
        push_tg(f"[{now}] {line}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="仅测试 Telegram 推送")
    args = p.parse_args()
    main(test=args.test)
