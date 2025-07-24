# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor  • 2025-07-24
· Oxylabs Web-Unblocker 代理分离端点与凭据
· 环境变量负责认证，Chrome 仅用 host:port，云端、本地一致
"""

import os, re, time, argparse
from datetime import datetime
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ============ Telegram ============
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ========= Proxy & Sites =========
# Oxylabs Web-Unblocker
PROXY_USER = "ianwang_w8WVr"
PROXY_PASS = "Snowdor961206~"
PROXY_HOST = "unblock.oxylabs.io:60000"      # 仅 host:port
PROXY_FULL = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}"

# 注入到环境变量，让 Chrome 自动带凭据
os.environ["HTTP_PROXY"]  = PROXY_FULL
os.environ["HTTPS_PROXY"] = PROXY_FULL

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

HEADLESS, WAIT = True, 25
LOG_FILE = "shrap_tag_report.txt"

# ---------- Selenium ----------
def get_driver():
    opt = Options()
    if HEADLESS:
        opt.add_argument("--headless=new")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--window-size=1920,1080")
    opt.add_argument("user-agent=Mozilla/5.0")
    # 只给 host:port，不带用户名密码
    opt.add_argument(f"--proxy-server=http://{PROXY_HOST}")
    opt.add_argument("--ignore-certificate-errors")
    opt.add_argument("--ignore-ssl-errors")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opt
    )

# ---------- Detection ----------
def detect(url, name):
    try:
        d = get_driver()
        d.get(url)
        time.sleep(WAIT)
        html = d.page_source
        d.quit()
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]

    low, tags = html.lower(), []
    if "innovation" in low and ("zone" in low or "risk" in low):
        tags.append("Innovation Zone")
    for m in re.finditer(r'\bst\b', html, flags=re.I):
        win = low[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', win):
            tags.append("ST")
            break
    return name, tags

# ---------- Telegram ----------
def push(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=15
        )
    except Exception as e:
        print("Telegram 推送失败:", e)

# ---------- Main ----------
def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if test:
        push(f"[{now}] ✅ Telegram 手动测试成功")
        print("测试消息已发"); return

    results = [detect(u, n) for n, u in SITES]
    alert = any(t and not t[0].startswith("fetch_error") for _, t in results)
    line = " | ".join(
        f"{n}: {'❗️'+', '.join(t) if t else '✅ No tag'}" for n, t in results
    )
    log = f"[{now}] {line}"
    print(log); open(LOG_FILE,"a",encoding="utf-8").write(log+"\n")
    if alert: push(log)

# ---------- CLI ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    main(test=args.test)
