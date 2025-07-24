# ----- check_shrap_tags.py -----
import time
import ssl
import argparse
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ================== 配置区 ==================
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"  # 你的 Bot Token
CHAT_ID   = "1805436662"                                      # 私聊 / 群 / 频道 ID

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]
HEADLESS = True        # 如需调试可改为 False
WAIT_SEC = 5           # 页面加载等待秒数
LOG_FILE = "shrap_tag_report.txt"
# ===========================================

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
    """返回 (site_name, tag_list)"""
    try:
        d = get_driver()
        d.get(url)
        time.sleep(WAIT_SEC)
        page = d.page_source.lower()
        d.quit()
    except Exception as e:
        return (name, [f"fetch_error:{e}"])

    tags = []
    if " st " in page:
        tags.append("ST")
    if "innovation zone" in page or "创新区" in page:
        tags.append("Innovation Zone")
    return (name, tags)

def push_tg(msg: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10
        )
    except Exception as e:
        print(f"❌ Telegram 推送失败: {e}")

def main(test_mode=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if test_mode:
        # 仅发送一条测试消息
        push_tg(f"[{now}] ✅ Telegram 手动测试成功")
        print("已发送测试消息到 Telegram")
        return

    # -------- 执行检测 --------
    results = [detect(u, n) for n, u in SITES]

    lines = []
    alert_needed = False
    for name, tags in results:
        if tags:
            # fetch_error 不算真正标签，但显示出来方便排错
            if not tags[0].startswith("fetch_error"):
                alert_needed = True
            lines.append(f"{name}: ❗️{', '.join(tags)}")
        else:
            lines.append(f"{name}: ✅ No tag")

    report = " | ".join(lines)
    log_line = f"[{now}] {report}"

    # 写日志
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")
    print(log_line)

    # 推送
    if alert_needed:
        push_tg(log_line)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SHRAP tag monitor")
    parser.add_argument(
        "--test", action="store_true", help="发送一条 Telegram 测试消息后退出"
    )
    args = parser.parse_args()
    main(test_mode=args.test)
