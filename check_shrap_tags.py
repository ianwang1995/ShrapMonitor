# ---- check_shrap_tags.py • final ----
import os, re, time, argparse
from datetime import datetime
import requests
from seleniumwire import webdriver          # ← Selenium-Wire
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ----- Telegram -----
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# ----- Web-Unblocker credentials -----
PROXY_USER = "ianwang_w8WVr"
PROXY_PASS = "Snowdor961206~"
PROXY_HOST = "unblock.oxylabs.io:60000"

PROXY_HTTP = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}"
PROXIES    = {"http": PROXY_HTTP, "https": PROXY_HTTP}

# 让 requests 走代理
os.environ["HTTP_PROXY"]  = PROXY_HTTP
os.environ["HTTPS_PROXY"] = PROXY_HTTP

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

HEADERS = {"User-Agent": "Mozilla/5.0"}
WAIT    = 15   # Selenium wait

# ---------- Requests ----------
def get_html_requests(url):
    r = requests.get(url, headers=HEADERS, proxies=PROXIES,
                     verify=False, timeout=30)
    return r.text

# ---------- Selenium-Wire for HTX ----------
def get_html_selenium(url):
    sw_opts = {
        'proxy': {
            'http':  PROXY_HTTP,
            'https': PROXY_HTTP,
            'verify_ssl': False,
        }
    }
    c_opts = Options()
    c_opts.add_argument("--headless=new")
    c_opts.add_argument("--no-sandbox")
    c_opts.add_argument("--disable-gpu")
    c_opts.add_argument("--window-size=1920,1080")
    c_opts.add_argument("user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=c_opts,
        seleniumwire_options=sw_opts
    )
    driver.get(url)
    time.sleep(WAIT)
    html = driver.page_source
    driver.quit()
    return html

# ---------- Detect ----------
def detect(name, url):
    try:
        html = get_html_selenium(url) if name == "HTX" else get_html_requests(url)
    except Exception as e:
        return name, [f"fetch_error:{e.__class__.__name__}"]

    low, tags = html.lower(), []
    if "innovation" in low and ("zone" in low or "risk" in low):
        tags.append("Innovation Zone")
    for m in re.finditer(r'\bst\b', html, flags=re.I):
        win = low[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', win):
            tags.append("ST"); break
    return name, tags

# ---------- Telegram ----------
def push(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            proxies={}, verify=False, timeout=15
        )
    except Exception as e:
        print("TG push fail:", e)

# ---------- Main ----------
def main():
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    res  = [detect(n, u) for n, u in SITES]
    alert = any(t and not t[0].startswith("fetch_error") for _, t in res)
    line  = " | ".join(f"{n}: {'❗️'+', '.join(t) if t else '✅ No tag'}" for n, t in res)
    msg   = f"[{now}] {line}"
    print(msg); open("shrap_tag_report.txt","a",encoding="utf-8").write(msg+"\n")
    if alert: push(msg)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    if args.test:
        push(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] ✅ Telegram 手动测试成功")
    else:
        main()
