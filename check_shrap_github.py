import os, re, time, argparse
from datetime import datetime

import requests, undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID   = os.getenv("TG_CHAT_ID")

HEADLESS  = True
BASE_WAIT = 35          # 最长 35 s
LOG_FILE  = "shrap_tag_report.txt"
DEBUG_CHARS = 300       # 输出源码前 N 字到日志

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX"  , "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

def driver():
    opt = uc.ChromeOptions()
    if HEADLESS:
        opt.add_argument("--headless=new")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--window-size=1920,1080")
    opt.add_argument("user-agent=Mozilla/5.0")
    return uc.Chrome(options=opt)          # auto‑match v138 driver

def detect(url, name):
    try:
        d = driver()
        d.get(url)

        # 多轮滚动 + 分段等待
        end_time = time.time() + BASE_WAIT
        seen = False
        while time.time() < end_time and not seen:
            try:
                WebDriverWait(d, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Innovation') or contains(text(),'innovation')]")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'ST')]"))
                    )
                )
                seen = True
            except Exception:
                # 触发懒加载再等
                d.execute_script("window.scrollBy(0, 300);")
                time.sleep(2)

        html = d.page_source
        d.quit()
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]

    # 调试：打印页面段首
    print(f"{name} html head: {html[:DEBUG_CHARS].replace(chr(10),' ')[:200]}...")

    low = html.lower()
    tags = []

    # Innovation（BingX/HTX）
    if "innovation" in low and ("risk" in low or "zone" in low):
        tags.append("Innovation Zone")

    # ST：整词 + risk/special/treatment 出现在 30 字节窗口内
    for m in re.finditer(r'\bST\b', html, flags=re.I):
        window = low[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break

    return name, tags

def push(msg):
    if not (BOT_TOKEN and CHAT_ID):
        print("TG creds missing, skip push")
        return
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg},
        timeout=20,
    )

def main(test=False, force=False):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    if test:
        push(f"[{now}] ✅ Telegram 手动测试成功")
        print("测试消息已发送"); return

    results = [detect(u, n) for n, u in SITES]
    lines, alert = [], False
    for name, tags in results:
        if tags and not tags[0].startswith("fetch_error"):
            alert = True
        icon = "❗️" if tags else "✅"
        lines.append(f"{name}: {icon} {', '.join(tags) if tags else 'No tag'}")

    msg = f"[{now}] " + " | ".join(lines)
    print(msg); open(LOG_FILE,"a",encoding="utf-8").write(msg+"\n")
    if alert or force: push(msg)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--force-alert", action="store_true")
    args = ap.parse_args(); main(args.test, args.force_alert)
