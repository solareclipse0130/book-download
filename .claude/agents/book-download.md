---
name: book-download
description: 从 Z-Library 搜索并下载电子书。支持单本交互和批量书单。国内可用（Firefox headless 绕 DiamWall），需 Z-Library 账号，免费版每日 10 本。
---

# book-download skill

## 触发场景

- 用户说"帮我下载《书名》"
- 用户说"把书单里的书都下了"
- 用户说"批量下载"
- 用户粘贴书名列表，要求批量搜索

## 关键事实（实测 2026-10-06）

- **可用域名**：`z-library.sk`（国内可达；z-lib.id 已被 GFW 封）
- **必须用 Firefox**：z-library.sk 有 DiamWall 反爬，Chromium headless 被识别并拒绝；Firefox headless 可通过
- **直接下载**：搜索结果的 `<z-bookcard download="/dl/...">` 属性已含直链，无需进详情页
- **账号**：凭据存在 `~/earnM/.env`（`ZLIBRARY_EMAIL` / `ZLIBRARY_PASSWORD`）
- **Cookie 缓存**：登录成功后存 `tools/books/.zlib_cookies.json`，下次复用
- **免费限额**：10 本/天；批量超过时后续请求会提示登录失败或下载受限
- **大文件慢**：32MB epub 约 12 分钟；英文书 100–900KB 约 30 秒

## 脚本位置

```
~/earnM/tools/books/zlib_download.py
~/earnM/tools/books/booklist.txt      # 当前书单（39 本）
~/earnM/tools/books/downloads/        # 下载目标目录
```

## 前置检查

```bash
# 确认 Firefox Playwright 已安装
python3 -c "from playwright.async_api import async_playwright; print('ok')"
python3 -m playwright install firefox   # 如未安装
```

凭据检查：

```bash
grep ZLIB ~/earnM/.env
```

应有 `ZLIBRARY_EMAIL` 和 `ZLIBRARY_PASSWORD`。

## 单本下载

```bash
cd ~/earnM/tools/books
python3 zlib_download.py "The Mom Test"          # 交互选择
python3 zlib_download.py "疯传" -d 1             # 直接下第 1 条
python3 zlib_download.py "Contagious" --ext epub  # 指定格式
python3 zlib_download.py "机器学习" -o ~/books   # 指定输出目录
```

## 批量下载

```bash
cd ~/earnM/tools/books
python3 zlib_download.py --batch booklist.txt -o downloads > /tmp/zlib_batch.log 2>&1 &
tail -f /tmp/zlib_batch.log
```

书单格式：每行一本书名（中英文均可），`#` 开头行跳过。

## 常见问题排查

### 搜索返回 0 条

Z-Library 页面改版，选择器失效。调试步骤：

```bash
cd ~/earnM/tools/books && python3 - <<'EOF'
import asyncio, urllib.parse
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)
        page = await (await browser.new_context()).new_page()
        await page.goto("https://z-library.sk/s?q=" + urllib.parse.quote("The Mom Test"), timeout=30000)
        await page.wait_for_timeout(6000)
        # 检查当前有效选择器
        for sel in [".book-item", ".resItemBox", ".bookRow", "article[class*=book]"]:
            els = await page.query_selector_all(sel)
            print(f"{sel}: {len(els)} 条")
        await browser.close()

asyncio.run(debug())
EOF
```

找到有效选择器后，更新 `zlib_download.py` 的 `search()` 函数里的 `".book-item"`。

同时检查 `z-bookcard` 属性名是否变化：

```bash
# 在 debug 脚本中加入：
item = await page.query_selector(".book-item")
card = await item.query_selector("z-bookcard")
attrs = ["href", "download", "extension", "language", "filesize"]
for a in attrs:
    print(a, "=", await card.get_attribute(a))
```

### 登录失败

1. 确认账号密码正确：手动访问 `https://z-library.sk/login` 测试
2. 删除缓存 Cookie 重新登录：`rm ~/earnM/tools/books/.zlib_cookies.json`
3. 检查登录成功判断：`zlib_download.py` 的 `_is_logged_in()` 函数查找 `"My Library"` 字符串，若 Z-Library 改版则更新

### 下载超时（大文件）

`download_file()` 默认超时 120 秒。大文件（>20MB）可能不够：

```python
# zlib_download.py 第 207 行附近
async with page.expect_download(timeout=300000) as dl_info:  # 改为 5 分钟
```

### 达到每日 10 本限额

Z-Library 免费账号每日 10 本。批量任务中第 11 本起会下载失败（跳过并继续）。第二天重新运行，脚本会跳过已存在的文件（尚未实现；目前会重复下载同名文件，需手动去重）。

## 批量任务跳过已下载（手动）

```bash
cd ~/earnM/tools/books/downloads
ls *.epub *.pdf 2>/dev/null | wc -l  # 已下载数量

# 从 booklist.txt 中去掉已下载书目，生成剩余清单
# （根据文件名模糊匹配，不完全精准，需人工核对）
```

## 其他书源（备用）

| 来源 | 国内可达 | 自动化 | 说明 |
|------|---------|--------|------|
| Z-Library (z-library.sk) | ✅ | ✅ | 需账号，免费 10/天 |
| 微信读书 | ✅ | ❌ | 需 App，中文书覆盖好 |
| TheFuture (bks.thefuture.top) | ✅ | ❌ | nc-captcha，需人工 |
| 鸠摩搜书 (jiumodiary.com) | ✅ | ❌ | 需人工输入验证码 |
| Anna's Archive | ❌ GFW | — | 需 VPN |
| LibGen | ❌ GFW | — | 需 VPN |
| SaltyLeo (tstrs.me) | ✅ | ❌ | /obtain2 Slack 文件已全部 404 |

## 注意事项

- 下载仅供个人学习，注意版权
- 每次间隔 4 秒（脚本已内置），避免触发频率限制
- 凭据不要提交到 git（`.env` 已在 `.gitignore`）
