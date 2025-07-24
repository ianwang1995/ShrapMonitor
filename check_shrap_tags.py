# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • HTX 网络拦截最终版
· HTX：Playwright 拦截 hotWordList 响应，直接解析 JSON
· BingX/Bybit：requests + Oxylabs 代理 + 原始宽松匹配
"""

import re
import argparse
from datetime import datetime

import requests
from playwright.sync_api import sync_playwright

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbq9sdfkjhCVTrcc"
CHAT_ID   = "1805436662"

# ─── 代理（仅 BingX/Bybit） ───
PROXIES = {
    "http":  "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
    "https": "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
}
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─── 监控目标 URL ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

def detect_htx(url: str):
    """用 Playwright 拦截 hotWordList 接口响应，直接从 JSON 里拿 banner 文本"""
    tags = []
    hotword_data = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = context.new_page()

        # 拦截网络响应，只要 URL 包含 hotWordList，就解析 JSON
        def on_response(response):
            if "hotWordList" in response.url:
                try:
                    j = response.json()
                    data = j.get("data", [])
                    if isinstance(data, list):
                        hotword_data.extend(data)
                except:
                    pass

        page.on("response", on_response)

        # 加载页面并等待所有 XHR 完成
        page.goto(url, wait_until="networkidle", timeout=60000)
        # 给 hotWordList 请求一个机会跑完
        page.wait_for_timeout(2000)

        browser.close()

    # 从抓到的 JSON data 里找包含关键词的条目
    for item in hotword_data:
        txt = str(item.get("text", "")).lower()
        if "innovation zone" in txt or "创新专区" in txt:
            tags.append("Innovation Zone")
            break

    return tags

def detect(name: str, url: str):
    """主检测路由：HTX 用网络拦截，其它两家轻量 requests+代理"""
    if name == "HTX":
        try:
            tags = detect_htx(url)
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]
        return name, tags

    # BingX / Bybit 一行不改，走最初的宽松匹配
    try:
        r = requests.get(url, headers=HEADERS,
                         proxies=PROXIES, verify=False, timeout=20)
        text = r.text.lower()
    except Exception as e:
        return name, [f"fetch_error:{type(e).__name__}"]

    tags = []
    if "innovation" in text and ("zone" in text or "risk" in text):
        tags.append("Innovation Zone")
    # ST 检测（同最初逻辑）
    for m in re.finditer(r'\bst\b', text):
        window = text[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break

    return name, tags

def push_tg(msg: str):
    """Telegram 推送"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}, timeout=10
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
    # 只要有任意 tag，就推送
    if any(tags for _, tags in results):
        push_tg(log)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="仅测试 Telegram 推送")
    args = p.parse_args()
    main(test=args.test)
