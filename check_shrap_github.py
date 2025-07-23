# ─── check_shrap_tags.py ───
"""
SHRAP Tag Monitor  (2025‑07‑24)
• 检测 BingX / HTX / Bybit 是否出现 “ST” / “Innovation Zone” 英文标签
• 精确 \bST\b 避免 standard / stake 等误判
• 处理 HTX 风险披露栏：滚动并等待元素
• --test        仅发测试消息
• --force-alert 总推送一次检测结果
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

# ── 环境变量（GitHub Secrets 或本地 shell） ──
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID   = os.getenv("TG_CHAT_ID")

# ── 配置 ──
HEADLESS  = True
WAIT_SEC  = 20
LOG_FILE  = "shrap_tag_report.txt"

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

# ────────────────────────────────
def get_driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0")
    service = Service(ChromeDriverManager().install())
    # 关键：用关键词 service=service，避免 Selenium 旧签名冲突
    return webdriver.Chrome(service=service, options=opts)

def detect(url: str, name: str):
    try:
        d = get_driver()
        d.get(url)
        time.sleep(5)

        # HTX 页面需要滚动 + 等待 banner
        if name == "HTX":
            d.execute_script("window.scrollBy(0, 800)")
            time.sleep(1)
            d.execute_script("window.scrollBy(0, 800)")
            WebDriverWait(d, WAIT_SEC).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'innovation zone')]")
                )
            )
        else:
            WebDriverWait(d, WAIT_SEC).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     "//*[contains(text(),'ST') or "
                     "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'innovation')]")
                )
            )

        page = d.page_source
        d.quit()
    except Exception as e:
        return name, [f"fetch_error:{e}"]

    tags = []
    # —— ST：整词匹配 ——  
    if re.search(r'\bST\b', page, flags=re.I):
        tags.append("ST")
    # —— Innovation Zone ——  
    if "innovation" in page.lower() and "zone" in page.lower():
        tags.append("Innovation Zone")

    return name, tags

def push_tg(msg: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️  BOT_TOKEN / CHAT_ID 未设置，跳过推送")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    except Exception as e:
        print(f"❌ Telegram 推送失败: {e}")

def main(test=False, force=False):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    if test:
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

    if alert or force:
        push_tg(log_line)

# ── CLI ──
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--force-alert", action="store_true")
    args = ap.parse_args()

    main(test=args.test, force=args.force_alert)
# ────────────────────────────────
