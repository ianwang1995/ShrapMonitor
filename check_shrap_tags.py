# ----- check_shrap_tags.py -----
"""
SHRAP Tag Monitor • HTX Proxy + Playwright 集成版
· HTX: Playwright 渲染 + 代理绑定，拦截 hotWordList 响应
· BingX/Bybit: requests + Oxylabs 代理 + 宽松匹配
"""
import re
import argparse
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─── Telegram 配置 ───
BOT_TOKEN = "7725811450:AAF9BQZEsBEfbq9sdfkjhCVTrcc"
CHAT_ID   = "1805436662"

# ─── Oxylabs Web-Unblocker 代理（仅用于 BingX/Bybit 的 requests 部分） ───
PROXIES = {
    "http":  "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
    "https": "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000",
}
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─── Playwright 专用代理（用于 HTX 浏览器环境） ───
PLAYWRIGHT_PROXY = "http://ianwang_w8WVr:Snowdor961206~@unblock.oxylabs.io:60000"

# ─── 监控目标 URL ───
SITES = [
    ("BingX", "https://bingx.com/en/spot/SHRAPUSDT"),
    ("HTX",   "https://www.htx.com/trade/shrap_usdt?type=spot"),
    ("Bybit", "https://www.bybit.com/en/trade/spot/SHRAP/USDT"),
]


def detect_htx(url: str):
    """
    用 Playwright 打开 HTX 并通过代理，
    显式等待 hotWordList 请求并解析其 JSON
    """
    tags = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
            proxy={"server": PLAYWRIGHT_PROXY}
        )
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )
        page = context.new_page()

        # 屏蔽静态资源，加速加载
        page.route("**/*", lambda route, req: route.abort()
                   if req.resource_type in ("image", "stylesheet", "font", "media")
                   else route.continue_())

        # 先加载 DOMContentLoaded
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        try:
            # 等待 hotWordList XHR 完成
            response = page.wait_for_response(
                lambda resp: "hotWordList" in resp.url and resp.status == 200,
                timeout=30000
            )
            data = response.json().get("data", [])
            for item in data:
                text = str(item.get("text", "")).lower()
                if "innovation zone" in text or "创新专区" in text:
                    tags.append("Innovation Zone")
                    break
        except PlaywrightTimeout:
            # 超时静默继续
            pass
        except Exception:
            pass
        finally:
            browser.close()

    return tags


def detect(name: str, url: str):
    """
    统一检测入口：
    - HTX: Playwright + 代理拦截
    - 其他: requests + Oxylabs 代理 + 宽松匹配
    返回 (name, [tags])
    """
    if name == "HTX":
        try:
            tags = detect_htx(url)
            return name, tags
        except Exception as e:
            return name, [f"fetch_error:{type(e).__name__}"]

    # BingX/Bybit 走最轻量逻辑
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            proxies=PROXIES,
            verify=False,
            timeout=20
        )
        text = resp.text.lower()
    except Exception as e:
        return name, [f"fetch_error:{type(e).__name__}"]

    tags = []
    if "innovation" in text and ("zone" in text or "risk" in text):
        tags.append("Innovation Zone")
    # ST 检测
    for m in re.finditer(r'\bst\b', text):
        window = text[max(0, m.start()-15): m.end()+15]
        if re.search(r'risk|special|treatment', window):
            tags.append("ST")
            break
    return name, tags


def push_tg(msg: str):
    """发送 Telegram 报警"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass


def main(test=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if test:
        push_tg(f"[{now}] ✅ Telegram 测试")
        print("测试消息已发")
        return

    results = [detect(n, u) for n, u in SITES]
    line = " | ".join(
        f"{n}: {'❗️'+','.join(tags) if tags else '✅ No tag'}"
        for n, tags in results
    )
    log = f"[{now}] {line}"
    print(log)

    with open("shrap_tag_report.txt", "a", encoding="utf-8") as f:
        f.write(log + "\n")

    if any(tags for _, tags in results):
        push_tg(log)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="仅测试 Telegram 推送")
    args = parser.parse_args()
    main(test=args.test)
