# ─── check_shrap_tags.py ───
"""
SHRAP Tag Monitor  2025‑07‑24 (final)
• 检测 BingX / HTX / Bybit 页面是否出现 “ST” 或 “Innovation Zone”
• 采用 undetected‑chromedriver 绕过 Cloudflare / 防爬
• ST 规则：\bST\b 且同行出现 risk / special / treatment 字根，杜绝 standard 误判
• --test        仅发送测试消息
• --force-alert 无论有没有标签都推送结果
"""

import os, re, time, argparse
from datetime import datetime

import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── Telegram Secrets ──
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID   = os.getenv("TG_CHAT_ID")

# ── 配置 ──
HEADLESS  = True
WAIT_SEC  = 25
LOG_FILE  = "shrap_tag_report.txt"
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

# ──────────────────────
def get_driver():
    opts = uc.ChromeOptions()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0")
    # version_main 指定主版本，120≈当前 LTS，失败可改 122
    return uc.Chrome(options=opts, version_main=120)

def detect(url: str, name: str):
    try:
        drv = get_driver()
        drv.get(url)
        time.sleep(4)                       # 初步等待

        if name == "HTX":
            drv.execute_script("window.scrollBy(0, document.body.scrollHeight)")
        # 显式等待关键词
        WebDriverWait(drv, WAIT_SEC).until(
            EC.any_of(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'innovation')]")
                ),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'ST')]"))
            )
        )

        html = drv.page_source
        drv.quit()
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}: {e}"]

    html_low = html.lower()
    tags = []

    # —— Innovation Zone ——  
    if "innovation" in html_low and "zone" in html_low:
        tags.append("Innovation Zone")

    # —— ST：整词 + risk/special/treatment ——  
    if re.search(r'\bST\b', html) and re.search(r'risk|special|treatment', html_low):
        tags.append("ST")

    return name, tags

def push_tg(msg: str):
    if not (BOT_TOKEN and CHAT_ID):
        print("⚠️  BOT_TOKEN / TG_CHAT_ID 未设置，跳过推送")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    except Exception as e:
        print("Telegram 推送失败:", e)

def main(test=False, force=False):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    if test:
        push_tg(f"[{now}] ✅ Telegram 手动测试成功")
        print("测试消息已发送")
        return

    results = [detect(u, n) for n, u in SITES]
    lines, alert = [], False
    for name, tags in results:
        if tags and not tags[0].startswith("fetch_error"):
            alert = True
        icon = "❗️" if tags else "✅"
        lines.append(f"{name}: {icon} {', '.join(tags) if tags else 'No tag'}")

    msg = f"[{now}] " + " | ".join(lines)
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

    if alert or force:
        push_tg(msg)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--force-alert", action="store_true")
    args = ap.parse_args()
    main(test=args.test, force=args.force_alert)
# ──────────────────────
