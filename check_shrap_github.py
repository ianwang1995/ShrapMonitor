# ─── check_shrap_tags.py ───
"""
SHRAP Tag Monitor
-----------------
• 检测 BingX / HTX / Bybit 是否出现 “ST” 或 “Innovation Zone” 英文标签
• 显式等待元素，避免 GitHub Runner 抓到降级 / 未渲染页面
• 默认仅当发现标签时推送；--force-alert 可强制推送
• 用法示例：
      python check_shrap_tags.py                  # 常规检测
      python check_shrap_tags.py --force-alert    # 总推送
      python check_shrap_tags.py --test           # 仅发测试消息
"""

import os
import re
import time
import argparse
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ── 环境变量：从 GitHub Secrets / 本地 shell 读取 ──
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")   # Telegram Bot Token
CHAT_ID   = os.getenv("TG_CHAT_ID")     # 私聊(正) / 群(负) chat_id

# ── 全局配置 ──
HEADLESS  = True      # False 可打开浏览器窗口调试
WAIT_SEC  = 15        # 最长等待渲染秒数
LOG_FILE  = "shrap_tag_report.txt"

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

# ────────────────────────────────────────────────
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

def detect(url: str, name: str):
    """返回 (平台名, 标签列表|fetch_error)"""
    try:
        d = get_driver()
        d.get(url)

        # 等待到页面文本出现目标关键词
        WebDriverWait(d, WAIT_SEC).until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'innovation zone') or "
                 "contains(text(),'ST')]")
            )
        )
        page = d.page_source.lower()
        d.quit()
    except Exception as e:
        return name, [f"fetch_error:{e}"]

    # 调试输出：抓到的源码长度
    print(f"{name} page length: {len(page)}")

    tags = []
    if re.search(r'\bst\b', page):              # \b 单词边界，精确匹配 “ST”
        tags.append("ST")
    if "innovation zone" in page:
        tags.append("Innovation Zone")
    return name, tags

def push_tg(msg: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️  BOT_TOKEN 或 CHAT_ID 未设置，跳过推送。")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    except Exception as e:
        print(f"❌ Telegram 推送失败: {e}")

def main(test_mode=False, force_alert=False):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    if test_mode:
        push_tg(f"[{now}] ✅ Telegram 手动测试成功")
        print("已发送测试消息到 Telegram")
        return

    results = [detect(u, n) for n, u in SITES]

    lines, alert_needed = [], False
    for name, tags in results:
        if tags:
            if not tags[0].startswith("fetch_error"):
                alert_needed = True
            lines.append(f"{name}: ❗️{', '.join(tags)}")
        else:
            lines.append(f"{name}: ✅ No tag")

    report   = " | ".join(lines)
    log_line = f"[{now}] {report}"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")
    print(log_line)

    if alert_needed or force_alert:
        push_tg(log_line)

# ── CLI ──
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SHRAP tag monitor")
    parser.add_argument("--test", action="store_true",
                        help="发送一条 Telegram 测试消息后退出")
    parser.add_argument("--force-alert", action="store_true",
                        help="无论有没有标签都推送一次检测结果")
    args = parser.parse_args()

    main(test_mode=args.test, force_alert=args.force_alert)
# ────────────────────────────────────────────────
