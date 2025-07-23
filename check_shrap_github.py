# ─── check_shrap_tags.py ───
"""
每天检测 SHRAP 代币是否被标注 ST / Innovation Zone。
● BingX / HTX / Bybit 三个平台
● 发现标签才推送 Telegram
● --test        只发一条“Telegram 手动测试成功”
● --force-alert 无论有没有标签都推送一次检测结果
"""

import os
import time
from datetime import datetime
import argparse
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ===== 环境变量 =====
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")   # GitHub Secrets / 本地终端导出
CHAT_ID   = os.getenv("TG_CHAT_ID")     # 私聊或群/频道 chat_id
# ====================

HEADLESS = True        # 调试可改 False
WAIT_SEC = 5           # 页面加载等待秒数
LOG_FILE = "shrap_tag_report.txt"

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

# ---------- Selenium 驱动 ----------
def get_driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

# ---------- 单站检测 ----------
def detect(url: str, name: str):
    """返回 (平台名, 标签列表)；若抓取失败返回 fetch_error"""
    try:
        d = get_driver()
        d.get(url)
        time.sleep(WAIT_SEC)
        page = d.page_source.lower()
        d.quit()
    except Exception as e:
        return name, [f"fetch_error:{e}"]

    tags = []
    if " st " in page:                         # 避免 best/first 等误判
        tags.append("ST")
    if "innovation zone" in page or "创新区" in page:
        tags.append("Innovation Zone")
    return name, tags

# ---------- Telegram 推送 ----------
def push_tg(msg: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️  BOT_TOKEN / CHAT_ID 未设置，无法推送。")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"❌ Telegram 推送失败: {e}")

# ---------- 主逻辑 ----------
def main(test_mode=False, force_alert=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 手动测试
    if test_mode:
        push_tg(f"[{now}] ✅ Telegram 手动测试成功")
        print("已发送测试消息到 Telegram")
        return

    # 正常检测
    results = [detect(u, n) for n, u in SITES]

    lines, alert_needed = [], False
    for name, tags in results:
        if tags:
            if not tags[0].startswith("fetch_error"):
                alert_needed = True
            lines.append(f"{name}: ❗️{', '.join(tags)}")
        else:
            lines.append(f"{name}: ✅ No tag")

    report  = " | ".join(lines)
    log_line = f"[{now}] {report}"

    # 写日志
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")
    print(log_line)

    # 推送
    if alert_needed or force_alert:
        push_tg(log_line)

# ---------- CLI ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SHRAP tag monitor")
    parser.add_argument("--test", action="store_true",
                        help="发送一条 Telegram 测试消息后退出")
    parser.add_argument("--force-alert", action="store_true",
                        help="无论有没有标签都推送一次检测结果")
    args = parser.parse_args()

    main(test_mode=args.test, force_alert=args.force_alert)
# ───────────────────────────
