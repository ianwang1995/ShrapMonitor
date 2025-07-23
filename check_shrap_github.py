# ─── check_shrap_tags.py ───
"""
SHRAP Tag Monitor  (2025‑07‑24)
• 检测 BingX / HTX / Bybit 是否出现 “ST” / “Innovation Zone” 英文标签
• 处理 HTX 气泡：滚动并等待元素
• 严格正则 \bST\b 避免 standard / stake 等误判
"""

import os, re, time, argparse
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ── 读取机密 ──
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")   # Telegram Bot Token
CHAT_ID   = os.getenv("TG_CHAT_ID")     # 私聊(正) / 群(负) chat_id

# ── 全局配置 ──
HEADLESS  = True
WAIT_SEC  = 20        # 最长等待秒数
LOG_FILE  = "shrap_tag_report.txt"

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

# ── Selenium 初始化 ──
def get_driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0")
    return webdriver.Chrome(Service(ChromeDriverManager().install()), options=opts)

# ── 单站检测 ──
def detect(url: str, name: str):
    try:
        d = get_driver()
        d.get(url)

        # 给组件更多渲染时间
        time.sleep(5)

        # 滚两次，促使 HTX 风险气泡出现在 DOM
        d.execute_script("window.scrollBy(0, 800)")
        time.sleep(1)
        d.execute_script("window.scrollBy(0, 800)")

        # 显式等待页面出现 innovation / ST 文本
        WebDriverWait(d, WAIT_SEC).until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'innovation') "
                 "or contains(text(),'ST')]")
            )
        )
        page = d.page_source
        d.quit()
    except Exception as e:
        return name, [f"fetch_error:{e}"]

    tags = []
    # —— 精确 ST ——  
    if re.search(r'\bST\b', page, flags=re.I):
        tags.append("ST")
    # —— Innovation Zone ——  
    if "innovation zone" in page.lower():
        tags.append("Innovation Zone")

    return name, tags

# ── Telegram 推送 ──
def push_tg(msg: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️  BOT_TOKEN / CHAT_ID 未设置，跳过推送")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    except Exception as e:
        print(f"❌ Telegram 推送失败: {e}")

# ── 主逻辑 ──
def main(test_mode=False, force_alert=False):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    if test_mode:
        push_tg(f"[{now}] ✅ Telegram 手动测试成功")
        print("测试消息已发送")
        return

    results = [detect(u, n) for n, u in SITES]

    lines, alert = [], False
    for name, tags in results:
        if tags:
            if not tags[0].startswith("fetch_error"):
                alert = True
            lines.append(f"{name}: ❗️{', '.join(tags)}")
        else:
            lines.append(f"{name}: ✅ No tag")

    log_line = f"[{now}] " + " | ".join(lines)
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

    if alert or force_alert:
        push_tg(log_line)

# ── CLI 参数 ──
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="只发测试消息")
    p.add_argument("--force-alert", action="store_true", help="强制推送一次结果")
    args = p.parse_args()

    main(test_mode=args.test, force_alert=args.force_alert)
# ───────────────────────────
