# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor · 2025-07-24
• BingX / Bybit → requests (HTML 直接含标签)
• HTX          → selenium-wire (执行首屏 JS 注入标签)
• 代理：Oxylabs Web-Unblocker
"""

import re, time, argparse, os
from datetime import datetime
import requests
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ───── Telegram ─────
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ───── Oxylabs Web-Unblocker ─────
PROXY_USER = "ianwang_w8WVr"
PROXY_PASS = "Snowdor961206~"
PROXY_HOST = "unblock.oxylabs.io:60000"
PROXY_HTTP = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}"
PROXIES    = {"http": PROXY_HTTP, "https": PROXY_HTTP}

# 让 requests 默认走代理
os.environ["HTTP_PROXY"]  = PROXY_HTTP
os.environ["HTTPS_PROXY"] = PROXY_HTTP

# ───── 目标站 ─────
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

HEADERS    = {"User-Agent": "Mozilla/5.0"}
SELEN_WAIT = 15          # JS 渲染等待秒数

# ───── Requests 抓取 ─────
def html_via_requests(url: str) -> str:
    r = requests.get(url, headers=HEADERS, proxies=PROXIES,
                     verify=False, timeout=30)
    r.raise_for_status()
    return r.text.lower()

# ───── Selenium-wire 抓取 (仅 HTX) ─────
def html_via_selenium(url: str) -> str:
    sw_opts = {
        "proxy": {
            "http":  PROXY_HTTP,
            "https": PROXY_HTTP,
            "verify_ssl": False,
        },
        "port": 9090   # 固定本地端口，GitHub runner 稳定
    }
    c_opts = Options()
    c_opts.add_argument("--headless=new")
    c_opts.add_argument("--no-sandbox")
    c_opts.add_argument("--disable-gpu")
    c_opts.add_argument("--window-size=1920,1080")
    c_opts.add_argument("user-agent=Mozilla/5.0")
    c_opts.add_argument("--ignore-certificate-errors")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=c_opts,
        seleniumwire_options=sw_opts,
    )
    driver.get(url)
    time.sleep(SELEN_WAIT)
    html = driver.page_source.lower()
    driver.quit()
    return html

# ───── 标签检测 ─────
def detect(name: str, url: str):
    try:
        html = html_via_selenium(url) if name == "HTX" else html_via_requests(url)
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]

    tags = []

    # Innovation Zone：两词距离 ≤ 30 字符
    if re.search(r'innovation.{0,30}zone|zone.{0,30}innovation', html):
        tags.append("Innovation Zone")

    # ST：整词 ST 且 30 字节窗口出现 risk|special|treatment
    for m in re.finditer(r'\bst\b', html):
        window = html[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break

    return name, tags

# ───── Telegram 推送 ─────
def push(msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            proxies={},          # 不走代理
            verify=False,        # 跳过证书
            timeout=15,
        )
    except Exception as e:
        print("Telegram push fail:", e)

# ───── 主流程 ─────
def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if test:
        push(f"[{now}] ✅ Telegram 手动测试成功")
        print("测试消息已发"); return

    results = [detect(n, u) for n, u in SITES]
    alert = any(t and not t[0].startswith("fetch_error") for _, t in results)
    line  = " | ".join(f"{n}: {'❗️'+', '.join(t) if t else '✅ No tag'}" for n, t in results)
    log   = f"[{now}] {line}"
    print(log)
    with open("shrap_tag_report.txt", "a", encoding="utf-8") as f:
        f.write(log + "\n")
    if alert: push(log)

# ───── CLI ─────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true",
                    help="发送一条 Telegram 测试消息后退出")
    args = ap.parse_args()
    main(test=args.test)
