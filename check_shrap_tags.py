# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor  • 2025-07-24
· 依次检测 BingX / HTX / Bybit 是否出现 “ST” 或 “Innovation Zone”
· 使用 Oxylabs Web-Unblocker 代理，自动绕过 Cloudflare
· 本地 & GitHub Actions 通用，无需额外环境变量
"""

import re, time, argparse
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ================== 配置区 ==================
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"   # Telegram Bot Token
CHAT_ID   = "1805436662"                                       # chat_id

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

# — Oxylabs Web-Unblocker 代理（已写死） —
PROXY = "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000"

HEADLESS  = True     # 调试可设 False
WAIT_SEC  = 20       # 页面加载最长等待秒
LOG_FILE  = "shrap_tag_report.txt"
# ===========================================

# ---------- Selenium 启动 ----------
def get_driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0")
    opts.add_argument(f"--proxy-server={PROXY}")         # 指定代理
    # 忽略代理自签证书
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--ignore-ssl-errors")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

# ---------- 单站检测 ----------
def detect(url: str, name: str):
    try:
        d = get_driver()
        d.get(url)
        time.sleep(WAIT_SEC)
        page = d.page_source
        d.quit()
    except Exception as e:
        return (name, [f"fetch_error:{e.__class__.__name__}"])

    low = page.lower()
    tags = []

    # Innovation Zone：innovation + (zone|risk)
    if "innovation" in low and ("zone" in low or "risk" in low):
        tags.append("Innovation Zone")

    # ST：整词 ST 且附近 30 字节含 risk/special/treatment
    for m in re.finditer(r'\bst\b', page, flags=re.I):
        window = low[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break

    return (name, tags)

# ---------- Telegram 推送 ----------
def push_tg(msg: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    except Exception as e:
        print(f"❌ Telegram 推送失败: {e}")

# ---------- 主流程 ----------
def main(test_mode=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if test_mode:
        push_tg(f"[{now}] ✅ Telegram 手动测试成功")
        print("已发送测试消息到 Telegram")
        return

    results = [detect(u, n) for n, u in SITES]

    lines, alert_needed = [], False
    for name, tags in results:
        if tags and not tags[0].startswith("fetch_error"):
            alert_needed = True
        lines.append(f"{name}: {'❗️' if tags else '✅'} {', '.join(tags) if tags else 'No tag'}")

    log_line = f"[{now}] " + " | ".join(lines)
    print(log_line)

    # 写日志
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

    # 推送（有标签时）
    if alert_needed:
        push_tg(log_line)

# ---------- CLI ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SHRAP tag monitor")
    parser.add_argument("--test", action="store_true",
                        help="发送一条 Telegram 测试消息后退出")
    args = parser.parse_args()
    main(test_mode=args.test)
