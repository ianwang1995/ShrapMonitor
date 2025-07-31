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
import httpx
# from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:"
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

        client = httpx.Client(verify=False, proxy="http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000")
        # client = httpx.Client(proxy="http://127.0.0.1:33333")

        response = client.get(url, headers=headers)
        body = response.json()
        if body.get('code', -1) != 200:
            raise Exception("Response code is not 200")
        
        msg = body.get('data', [{}])[0].get('messageBody', '')
        if 'Innovation Zone' in msg:
            tags.append('Innovation Zone')

    except Exception as ex:
        raise Exception(f"HTX detection failed: {str(ex)}")
    return tags


# if __name__ == "__main__":
#     print(detect_htx())


def detect(name: str, url: str):
    """
    统一检测入口：
    - HTX: Playwright + 代理拦截
    - 其他: requests + Oxylabs 代理 + 宽松匹配
    返回 (name, [tags])
    """
    if name == "HTX":
        try:
            tags = detect_htx()
            return name, tags
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]

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

    # Innovation Zone 检测（忽略大小写）
    txt_lower = text.lower()
    if "innovation" in txt_lower and ("zone" in txt_lower or "risk" in txt_lower):
        tags.append("Innovation Zone")

    # ST 检测：只要出现独立的 ST，就算
    # \b 确保是独立词，re.IGNORECASE 忽略大小写
    if re.search(r'\bST\b', text, re.IGNORECASE):
        tags.append("ST")

    return name, tags


def push_tg(msg: str):
    """发送 Telegram 报警（不使用代理）"""
    try:
        print("📤 Sending Telegram alert:", msg)  # 打印即将发送的消息内容
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10,
            proxies={"http": None, "https": None}
        )
        print("✅ Telegram push status:", response.status_code)
        print("📬 Telegram response text:", response.text)
    except Exception as e:
        print("❌ Telegram push failed:", e)


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
