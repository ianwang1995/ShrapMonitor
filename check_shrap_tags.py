# ----- check_shrap_tags.py (hybrid) -----
import os, re, time, argparse
from datetime import datetime
import requests
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Telegram
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbp9y80GlqTGBsM1qhVCTrcc"
CHAT_ID   = "1805436662"

# Web-Unblocker proxy
PROXY_FULL = "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000"
PROXY_HOST = "unblock.oxylabs.io:60000"        # no creds
os.environ["HTTP_PROXY"]  = PROXY_FULL
os.environ["HTTPS_PROXY"] = PROXY_FULL

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

HEADERS = {"User-Agent": "Mozilla/5.0"}
WAIT    = 15

def get_html_requests(url):
    r = requests.get(url, headers=HEADERS, proxies={"http":PROXY_FULL,"https":PROXY_FULL},
                     verify=False, timeout=30)
    return r.text

def get_html_selenium(url):
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument(f"--proxy-server=http://{PROXY_HOST}")
    opt.add_argument("--ignore-certificate-errors")
    opt.add_argument("--no-sandbox"); opt.add_argument("--disable-gpu")
    opt.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(options=opt,
                       service=Service(ChromeDriverManager().install()))
    driver.get(url)
    time.sleep(WAIT)
    html = driver.page_source
    driver.quit()
    return html

def detect(site_name, url):
    try:
        html = (get_html_selenium if site_name=="HTX" else get_html_requests)(url)
    except Exception as e:
        return site_name, [f"fetch_error:{e.__class__.__name__}"]

    low, tags = html.lower(), []
    if "innovation" in low and ("zone" in low or "risk" in low):
        tags.append("Innovation Zone")
    for m in re.finditer(r'\bst\b', html, flags=re.I):
        win = low[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', win):
            tags.append("ST"); break
    return site_name, tags

def push(msg):                                   # Telegram
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id":CHAT_ID,"text":msg},timeout=15)
    except Exception as e:
        print("TG push fail:", e)

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    res = [detect(n,u) for n,u in SITES]
    alert = any(t and not t[0].startswith("fetch_error") for _,t in res)
    line  = " | ".join(f"{n}: {'❗️'+', '.join(t) if t else '✅ No tag'}" for n,t in res)
    msg   = f"[{now}] {line}"
    print(msg); open("shrap_tag_report.txt","a",encoding="utf-8").write(msg+"\n")
    if alert: push(msg)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        push(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] ✅ Telegram 手动测试成功")
    else:
        main()
