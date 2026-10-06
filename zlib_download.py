#!/usr/bin/env python3
"""
Z-Library 自动搜索下载工具

前置条件:
  1. 在 z-library.sk 注册免费账号
  2. 在 .env 里填写账号：
       ZLIBRARY_EMAIL=你的邮箱
       ZLIBRARY_PASSWORD=你的密码
  3. 安装依赖（首次）：pip3 install playwright && python3 -m playwright install firefox

用法:
  python3 zlib_download.py "The Mom Test"
  python3 zlib_download.py "疯传" --lang chinese --ext epub
  python3 zlib_download.py "机器学习" -n 20 -o ~/books
  python3 zlib_download.py --batch booklist.txt        # 批量

注意：必须用 Firefox（不能用 Chromium）——z-library.sk 有 DiamWall 反爬，
      Chromium headless 会被识别拦截，Firefox headless 可通过。
"""

import argparse
import asyncio
import json
import os
import sys
import urllib.parse
from pathlib import Path

try:
    from playwright.async_api import async_playwright, BrowserContext, Page
except ImportError:
    print("缺少 Playwright：pip3 install playwright && python3 -m playwright install chromium")
    sys.exit(1)

# ─── 配置 ─────────────────────────────────────────────────────────────────────

DOMAIN      = "https://z-library.sk"
COOKIE_FILE = Path(__file__).parent / ".zlib_cookies.json"
DOWNLOAD_DIR = Path("downloads")

HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def load_env() -> tuple[str, str]:
    """从 tools/books/.env 或项目根目录 .env 读取凭据"""
    email = password = ""
    for env_path in [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent.parent / ".env",  # 项目根目录
    ]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ZLIBRARY_EMAIL="):
                    email = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("ZLIBRARY_PASSWORD="):
                    password = line.split("=", 1)[1].strip().strip('"')
            if email and password:
                break
    email = email or os.environ.get("ZLIBRARY_EMAIL", "")
    password = password or os.environ.get("ZLIBRARY_PASSWORD", "")
    if not email or not password:
        print("缺少凭据！请在 tools/books/.env 里添加：")
        print("  ZLIBRARY_EMAIL=你的邮箱")
        print("  ZLIBRARY_PASSWORD=你的密码")
        sys.exit(1)
    return email, password


# ─── 登录 ─────────────────────────────────────────────────────────────────────

def _is_logged_in(content: str) -> bool:
    return ("My Library" in content or "my-library" in content.lower()) and "Log In" not in content


async def login(ctx: BrowserContext, email: str, password: str) -> bool:
    """登录并保存 Cookie；若已有有效 Cookie 则跳过"""
    # 尝试加载已有 Cookie
    if COOKIE_FILE.exists():
        cookies = json.loads(COOKIE_FILE.read_text())
        await ctx.add_cookies(cookies)
        # 验证 Cookie 是否仍有效
        page = await ctx.new_page()
        await page.goto(f"{DOMAIN}/", timeout=25000)
        await page.wait_for_timeout(5000)
        content = await page.content()
        await page.close()
        if _is_logged_in(content):
            print("  已用缓存 Cookie 登录")
            return True
        # Cookie 失效，重新登录
        await ctx.clear_cookies()

    print("  登录中…", end=" ", flush=True)
    page = await ctx.new_page()
    await page.goto(f"{DOMAIN}/login", timeout=25000)
    await page.wait_for_timeout(8000)

    await page.fill('input[name="email"]', email)
    await page.fill('input[name="password"]', password)
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(3000)

    content = await page.content()
    if _is_logged_in(content):
        cookies = await ctx.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies))
        print("成功")
        await page.close()
        return True
    else:
        body = await page.inner_text("body")
        print("失败")
        print(f"  页面内容: {body[:200]}")
        await page.close()
        return False


# ─── 搜索 ─────────────────────────────────────────────────────────────────────

async def search(page: Page, query: str, lang: str = "", ext: str = "", count: int = 10) -> list[dict]:
    url = f"{DOMAIN}/s?q={urllib.parse.quote(query)}"
    if lang:
        url += f"&languages%5B%5D={lang}"
    if ext:
        url += f"&extensions%5B%5D={ext}"

    await page.goto(url, timeout=30000)
    await page.wait_for_timeout(6000)

    results = []
    items = await page.query_selector_all(".book-item")
    for item in items[:count]:
        card = await item.query_selector("z-bookcard")
        if not card:
            continue
        href     = (await card.get_attribute("href") or "").strip()
        dl_path  = (await card.get_attribute("download") or "").strip()
        ext_val  = (await card.get_attribute("extension") or "").strip()
        lang_val = (await card.get_attribute("language") or "").strip()
        size_val = (await card.get_attribute("filesize") or "").strip()
        year_val = (await card.get_attribute("year") or "").strip()

        # 书名来自 slot=title 子元素，或直接 inner_text
        title_el = await card.query_selector("[slot=title], .book-title, h3")
        if title_el:
            title = (await title_el.inner_text()).strip()
        else:
            title = (await card.inner_text()).strip()[:80]

        if not href:
            continue
        book_url  = DOMAIN + href if not href.startswith("http") else href
        dl_url    = (DOMAIN + dl_path) if dl_path else ""
        info      = f"{ext_val} {size_val} {lang_val} {year_val}".strip()

        results.append({"title": title, "url": book_url, "dl_url": dl_url, "info": info})

    return results


# ─── 详情页：获取下载链接 ──────────────────────────────────────────────────────

async def get_download_url(page: Page, book_url: str) -> str | None:
    await page.goto(book_url, wait_until="domcontentloaded", timeout=20000)
    await page.wait_for_timeout(1000)

    # 主下载按钮（z-lib.id 2024+ 格式）
    for sel in [
        'a[href*="/dl/"]',
        'a.btn[href*="/dl/"]',
        '.dlButton a',
        'a.addDownloadedBook',
        'a[href*="/book/archive/"][href*="/download"]',
        'a[data-url*="/dl/"]',
        'a:has-text("Download")',
        'a:has-text("下载")',
    ]:
        try:
            el = await page.query_selector(sel)
            if el:
                href = await el.get_attribute("href") or await el.get_attribute("data-url") or ""
                if href:
                    return DOMAIN + href if not href.startswith("http") else href
        except Exception:
            pass

    # 从页面源码找 /dl/ 路径
    import re
    content = await page.content()
    dl_matches = re.findall(r'["\'](/dl/[^"\']+)["\']', content)
    if dl_matches:
        return DOMAIN + dl_matches[0]

    # 如果是"需登录"提示
    body = await page.inner_text("body")
    if "sign in" in body.lower() or ("login" in body.lower() and "download" not in body.lower()):
        return None
    return None


# ─── 下载文件 ─────────────────────────────────────────────────────────────────

async def download_file(page: Page, dl_url: str, title: str, out_dir: Path):
    """通过 Playwright 的下载拦截器下载文件"""
    out_dir.mkdir(parents=True, exist_ok=True)

    async with page.expect_download(timeout=120000) as dl_info:
        try:
            await page.goto(dl_url, wait_until="commit", timeout=20000)
        except Exception:
            pass  # "Download is starting" 错误是正常的

    download = await dl_info.value
    filename = download.suggested_filename or (title[:60] + ".epub")
    save_path = out_dir / filename
    await download.save_as(save_path)
    print(f"  已保存: {save_path.resolve()}")
    return save_path


# ─── 主流程 ──────────────────────────────────────────────────────────────────

async def run_single(query: str, lang: str, ext: str, count: int, out_dir: Path,
                     auto_download: int | None):
    email, password = load_env()

    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 800},
        )

        print(f'\n搜索 "{query}" …\n')

        # 先搜索（不需要登录）
        page = await ctx.new_page()
        results = await search(page, query, lang=lang, ext=ext, count=count)

        if not results:
            print("未找到结果")
            await browser.close()
            return

        for i, r in enumerate(results, 1):
            info = f"  [{r.get('info','')}]" if r.get("info") else ""
            print(f"  {i:>3}.  {r['title']}{info}")

        # 选择
        if auto_download is not None:
            idx = auto_download
        else:
            print()
            try:
                raw = input("输入序号下载（0 退出）: ").strip()
                idx = int(raw)
            except (ValueError, EOFError):
                await browser.close()
                return

        if idx == 0 or idx < 1 or idx > len(results):
            await browser.close()
            return

        book = results[idx - 1]
        print(f'\n获取下载链接: {book["title"]}')

        # 登录
        logged_in = await login(ctx, email, password)
        if not logged_in:
            print("登录失败，无法下载")
            await browser.close()
            return

        page2 = await ctx.new_page()
        dl_url = book.get("dl_url") or await get_download_url(page2, book["url"])

        if not dl_url:
            print(f"未找到下载链接，请手动访问: {book['url']}")
            await browser.close()
            return

        print(f"  下载 URL: {dl_url}")
        await download_file(page2, dl_url, book["title"], out_dir)
        await browser.close()


async def run_batch(book_file: Path, lang: str, ext: str, out_dir: Path):
    email, password = load_env()
    titles = [l.strip() for l in book_file.read_text().splitlines() if l.strip()]

    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 800},
        )

        logged_in = await login(ctx, email, password)
        if not logged_in:
            print("登录失败")
            await browser.close()
            return

        # 已下载文件名集合（用于跳过）
        done_stems = {p.stem.split(" (")[0].strip() for p in out_dir.glob("*") if p.is_file()}

        for title in titles:
            # 跳过已下载（文件名开头包含书名关键词）
            if any(title.lower() in s.lower() or s.lower() in title.lower() for s in done_stems):
                print(f'\n─── {title} ─── 已下载，跳过')
                continue

            print(f'\n─── {title} ───')
            page = await ctx.new_page()
            try:
                results = await search(page, title, lang=lang, ext=ext, count=3)
                if not results:
                    print("  未找到结果，跳过")
                    await page.close()
                    continue

                # 取第一条，优先用搜索结果里的直链
                book = results[0]
                print(f"  命中: {book['title']} [{book.get('info','')}]")
                dl_url = book.get("dl_url") or await get_download_url(page, book["url"])
                if dl_url:
                    await download_file(page, dl_url, book["title"], out_dir)
                else:
                    print(f"  无下载链接: {book['url']}")
            except Exception as e:
                print(f"  下载失败，跳过: {e}")
            finally:
                await page.close()
            await asyncio.sleep(4)

        await browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Z-Library 搜索下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("query", nargs="?", help="搜索关键词（书名/作者）")
    parser.add_argument("--batch", metavar="FILE", help="批量模式：从文本文件读取书单（每行一本）")
    parser.add_argument("--lang",  default="", help="语言过滤，如 chinese / english")
    parser.add_argument("--ext",   default="", help="格式过滤，如 epub / pdf / mobi")
    parser.add_argument("-n", "--num", type=int, default=10, help="结果数量（默认 10）")
    parser.add_argument("-d", "--download", type=int, metavar="IDX",
                        help="直接下载第 IDX 条（省略则交互选择）")
    parser.add_argument("-o", "--output", default="downloads", help="下载目录（默认 downloads/）")
    args = parser.parse_args()

    out_dir = Path(args.output)

    if args.batch:
        asyncio.run(run_batch(Path(args.batch), lang=args.lang, ext=args.ext, out_dir=out_dir))
    elif args.query:
        asyncio.run(run_single(
            args.query, lang=args.lang, ext=args.ext,
            count=args.num, out_dir=out_dir, auto_download=args.download,
        ))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
