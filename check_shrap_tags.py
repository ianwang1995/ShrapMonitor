# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor · 2025-07-24
· BingX / Bybit  →  requests  (快)
· HTX           →  selenium-wire (执行 JS，代理认证 100 % 成功)
"""

import os, re, time, argparse
from datetime import datetime
import requests
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ───────── Telegram ─────────
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ───────── Oxylabs Web-Unblocker ─────────
PROXY_USER = "ianwang_w8WVr"
PROXY_PASS = "Snowdor961206~"
PROXY_HOST = "unblock.oxylabs.io:60000"

PROXY_HTTP = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}"
PROXIES    = {"http": PROXY_HTTP, "https": PROXY_HTTP}

# 让 requests 默认走代理
os.environ["HTTP_PROXY"]  = PROXY_HTTP
os.environ["HTTPS_PROXY"] = PROXY_HTTP

# ───────── 目标站 ─────────
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

HEADERS = {"User-Agent": "Mozilla/5.0"}
SELEN_WAIT = 15          # 等待 HTX 前端脚本执行

# ───────── Requests 抓取 ─────────
def get_html_requests(url: str) -> str:
    r = requests.get(url, headers=HEADERS, proxies=PROXIES,
                     verify=False, timeout=30)
    r.raise_for_status()
    return r.text

# ───────── Selenium-wire 抓取 (HTX) ─────────
def get_html_selenium(url: str) -> str:
    sw_opts = {
        "proxy": {
            "http":  PROXY_HTTP,
            "https": PROXY_HTTP,
            "verify_ssl": False,
        }
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
    html = driver.page_source
    driver.quit()
    return html

# ───────── 标签检测 ─────────
def detect(name: str, url: str):
    try:
        html = get_html_selenium(url) if name == "HTX" else get_html_requests(url)
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]

    low, tags = html.lower(), []

    # Innovation Zone
    if "innovation" in low and ("zone" in low or "risk" in low):
        tags.append("Innovation Zone")

    # ST：匹配整词且附近含 risk/special/treatment
    for m in re.finditer(r'\bst\b', html, flags=re.I):
        win = low[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', win):
            tags.append("ST"); break

    return name, tags

# ───────── Telegram 推送 ─────────
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
        print("TG push fail:", e)

# ───────── 主流程 ─────────
def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if test:
        push(f"[{now}] ✅ Telegram 手动测试成功")
        print("测试消息已发"); return

    results = [detect(n, u) for n, u in SITES]
    alert = any(t and not t[0].startswith("fetch_error") for _, t in results)
    line  = " | ".join(f"{n}: {'❗️'+', '.join(t) if t else '✅ No tag'}" for n, t in results)
    log   = f"[{now}] {line}"
    print(log); open("shrap_tag_report.txt","a",encoding="utf-8").write(log+"\n")
    if alert: push(log)

# ───────── CLI ─────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    main(test=args.test)
