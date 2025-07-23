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

# --- Secrets -------------------------------------------------
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID   = os.getenv("TG_CHAT_ID")

# --- Config --------------------------------------------------
HEADLESS  = True
WAIT_SEC  = 20
LOG_FILE  = "shrap_tag_report.txt"
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

# -------------------------------------------------------------
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

# -------------------------------------------------------------
def detect(url: str, name: str):
    try:
        drv = get_driver()
        drv.get(url)
        time.sleep(5)

        # 让 HTX 风险条进入 DOM
        if name == "HTX":
            drv.execute_script("window.scrollBy(0, 1500)")

        WebDriverWait(drv, WAIT_SEC).until(
            EC.any_of(
                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'innovation')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'ST')]"))
            )
        )
        html = drv.page_source
        drv.quit()
    except Exception as e:
        return name, [f"fetch_error:{e}"]

    html_low = html.lower()
    tags = []

    # ---- Innovation Zone ----
    if "innovation" in html_low and "zone" in html_low:
        tags.append("Innovation Zone")

    # ---- ST 严格匹配：需出现“ST” 且伴随 risk / special treatment 词根 ----
    if re.search(r'\bst\b', html, flags=re.I) and (
        ("risk" in html_low) or ("special" in html_low) or ("treatment" in html_low)
    ):
        tags.append("ST")

    return name, tags

# -------------------------------------------------------------
def push(msg: str):
    if not (BOT_TOKEN and CHAT_ID):
        print("缺少 TG_BOT_TOKEN / TG_CHAT_ID，跳过推送")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)

# -------------------------------------------------------------
def main(test=False, force=False):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    if test:
        push(f"[{now}] ✅ Telegram 手动测试成功")
        print("测试消息已发")
        return

    results = [detect(u, n) for n, u in SITES]
    lines, alert = [], False
    for name, tags in results:
        if tags and not tags[0].startswith("fetch_error"):
            alert = True
        tag_txt = ", ".join(tags) if tags else "No tag"
        icon = "❗️" if tags else "✅"
        lines.append(f"{name}: {icon} {tag_txt}")

    msg = f"[{now}] " + " | ".join(lines)
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

    if alert or force:
        push(msg)

# -------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--force-alert", action="store_true")
    args = ap.parse_args()
    main(test=args.test, force=args.force_alert)
