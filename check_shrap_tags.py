# ----- check_shrap_tags.py -----
import re
import urllib.parse
import argparse
from datetime import datetime
import requests

BOT_TOKEN = "7725811450:AAF9BQZEsBEfbq9sdfkjhCVTrcc"
CHAT_ID   = "1805436662"

PROXIES = {
    "http":  "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
    "https": "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
}
HEADERS = {
    "User-Agent":      "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With":"XMLHttpRequest",
}

SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]

def detect_htx(url):
    session = requests.Session()
    session.headers.update(HEADERS)
    # 1) 先 GET 页面，拿到 HTML + Cookie
    resp = session.get(url, timeout=20, verify=False)
    html = resp.text

    # 2) 正则提取完整的 hotWordList 接口路径（包括所有 query 参数）
    m = re.search(r"""['"](?P<api>/[^'"]*hotWordList\?[^'"]+)['"]""", html)
    if not m:
        return []  # 真正的接口没找到，回空

    api_path = m.group("api")
    api_url  = urllib.parse.urljoin(url, api_path)
    # 3) 直接调用这个接口
    jresp = session.get(api_url, timeout=10, verify=False)
    if jresp.status_code != 200:
        return []

    try:
        data = jresp.json().get("data", [])
    except ValueError:
        return []

    # 4) 在返回数组里找 banner 文本
    for item in data:
        text = item.get("text","").lower()
        if "innovation zone" in text or "创新专区" in text:
            return ["Innovation Zone"]
    return []

def detect(name, url):
    if name == "HTX":
        try:
            tags = detect_htx(url)
            return name, tags
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]
    else:
        # BingX/Bybit：原始轻量逻辑
        try:
            r = requests.get(url, headers=HEADERS,
                             proxies=PROXIES, verify=False, timeout=20)
            txt = r.text.lower()
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]
        tags = []
        if "innovation" in txt and ("zone" in txt or "risk" in txt):
            tags.append("Innovation Zone")
        # ST 检测
        for m in re.finditer(r'\bst\b', txt):
            w = txt[max(0, m.start()-15):m.end()+15]
            if re.search(r'risk|special|treatment', w):
                tags.append("ST")
                break
        return name, tags

def push_tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}, timeout=10
        )
    except:
        pass

def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if test:
        push_tg(f"[{now}] ✅ Telegram 测试")
        print("测试消息已发")
        return

    results = [detect(n,u) for n,u in SITES]
    line = " | ".join(
        f"{n}: {'❗️'+','.join(tags) if tags else '✅ No tag'}"
        for n,tags in results
    )
    print(f"[{now}] {line}")
    with open("shrap_tag_report.txt","a",encoding="utf-8") as f:
        f.write(f"[{now}] {line}\n")
    if any(tags for _,tags in results):
        push_tg(f"[{now}] {line}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test",action="store_true",help="测试 Telegram")
    args = p.parse_args()
    main(test=args.test)
