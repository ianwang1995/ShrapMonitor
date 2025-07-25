# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • HTX Proxy + Playwright 集成版
· HTX: Playwright 渲染 + 代理绑定，拦截 hotWordList 响应
· BingX/Bybit: requests + Oxylabs 代理 + 宽松匹配
"""
import re
import argparse
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbq9sdfkjhCVTrcc"
CHAT_ID   = "1805436662"

# ─── Oxylabs Web-Unblocker 代理（仅用于 BingX/Bybit 的 requests 部分） ───
PROXIES = {
    "http":  "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
    "https": "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
}
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─── Playwright 专用代理（用于 HTX 浏览器环境） ───
PLAYWRIGHT_PROXY = "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000"

# ─── 监控目标 URL ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]


import httpx

def detect_htx():

    tags = []

    try:

        url = "https://www.htx.com/-/x/hbg/v1/hbg/open/message/currency/notice/message?currency=SHRAP"

        headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",
        'Accept': "application/json, text/plain, */*",
        'accept-language': "en-US",
        'cache-control': "no-cache",
        'pragma': "no-cache",
        'priority': "u=1, i",
        'referer': "https://www.htx.com/trade/shrap_usdt?type=spot",
        'sec-ch-ua': "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Microsoft Edge\";v=\"138\"",
        'sec-ch-ua-mobile': "?0",
        'sec-ch-ua-platform': "\"Windows\"",
        'sec-fetch-dest': "empty",
        'sec-fetch-mode': "cors",
        'sec-fetch-site': "same-origin",
        'webmark': "v10003"
        }

        client = httpx.Client(proxy="http://127.0.0.1:33333")

        response = client.get(url, headers=headers)
        body = response.json()
        if body.get('code', -1) != 200:
            raise Exception("Response code is not 200")
        
        msg = body.get('data', [{}])[0].get('messageBody', '')
        if 'Innovation Zone' in msg:
            tags.append('Innovation Zone')

    except Exception:
        pass
    return tags


if __name__ == "__main__":
    print(detect_htx())

    # BingX/Bybit 走最轻量逻辑
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            proxies=PROXIES,
            verify=False,
            timeout=20
        )
        text = resp.text.lower()
    except Exception as e:
    return name, [f"fetch_error:{type(e).__name__}"]

    tags = []
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
