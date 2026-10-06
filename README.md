# book-download

**中文** | [English](#english)

---

## 中文

从 Z-Library 批量下载电子书。使用 Firefox headless 绕过 DiamWall 反爬机制 —— **国内无需 VPN 可直接使用**。

有两种使用方式：

| 方式 | 适合场景 |
|------|----------|
| **方式一：Claude Code skill**（推荐） | 已有 Claude Code，直接用自然语言下载 |
| **方式二：直接运行脚本** | 不用 Claude Code，命令行独立使用 |

### 方式一：作为 Claude Code skill

```bash
# 复制 skill 文件到 Claude 全局 agents 目录
cp .claude/agents/book-download.md ~/.claude/agents/
```

之后在任意项目里对 Claude 说"帮我下载《疯传》"，Claude 会自动调用 `zlib_download.py` 完成搜索和下载。

### 方式二：直接运行脚本

**安装依赖（首次）：**
```bash
pip install playwright
python -m playwright install firefox
```

**创建 `.env` 填写账号（免费注册：https://z-library.sk/registration）：**
```bash
echo "ZLIBRARY_EMAIL=你的邮箱" >> .env
echo "ZLIBRARY_PASSWORD=你的密码" >> .env
```

**单本（交互选择）：**
```bash
python zlib_download.py "The Mom Test"
```

**单本（自动下载第 1 条）：**
```bash
python zlib_download.py "疯传" -d 1 --ext epub
```

**批量下载书单：**
```bash
python zlib_download.py --batch booklist.txt -o ~/books
```

`booklist.txt` 格式：每行一本书名（中英文均可），`#` 开头为注释行。

### 原理

- Z-Library（`z-library.sk`）国内可访问，但 DiamWall 会拦截所有基于 Chromium 的无头浏览器
- Firefox headless 因指纹不同可通过 DiamWall
- 搜索结果里的 `<z-bookcard download="/dl/...">` 属性直接包含下载链接，无需进入详情页

### 注意事项

- 免费账号每天限下载 **10 本**
- 大文件（30 MB+）可能需要 10–15 分钟
- 凭据从脚本目录或项目根目录的 `.env` 读取，**不要提交 `.env`**
- Cookie 缓存在 `.zlib_cookies.json`（已 git-ignore），下次运行自动复用

### 常见问题

| 问题 | 解决方法 |
|------|----------|
| 搜索返回 0 结果 | Z-Library 改版了，更新 `search()` 里的 `.book-item` 选择器 |
| 登录失败 | 删除 `.zlib_cookies.json` 重试；在 z-library.sk/login 验证账号 |
| 大文件下载超时 | 把 `download_file()` 里的 `timeout=120000` 改为 `300000` |
| DiamWall 又开始拦截 | 换用 `pw.webkit` 试试；或等待（DiamWall 会不定期更新规则） |

---

<a name="english"></a>

## English

Batch ebook downloader for Z-Library.  
Uses Firefox headless to bypass DiamWall bot protection — **works from mainland China without a VPN**.

Two ways to use it:

| Mode | Best for |
|------|----------|
| **Mode 1: Claude Code skill** (recommended) | Already using Claude Code — download books in plain language |
| **Mode 2: Run the script directly** | No Claude Code — use it as a standalone CLI tool |

### Mode 1: As a Claude Code skill

```bash
cp .claude/agents/book-download.md ~/.claude/agents/
```

Then tell Claude "download *The Mom Test* for me" from any project — it will call `zlib_download.py` automatically.

### Mode 2: Run the script directly

**Install dependencies (first time):**
```bash
pip install playwright
python -m playwright install firefox
```

**Create `.env` with your credentials (free registration: https://z-library.sk/registration):**
```bash
echo "ZLIBRARY_EMAIL=your@email.com" >> .env
echo "ZLIBRARY_PASSWORD=yourpassword" >> .env
```

**Single book (interactive):**
```bash
python zlib_download.py "The Mom Test"
```

**Single book (auto-select first result):**
```bash
python zlib_download.py "Contagious" -d 1 --ext epub
```

**Batch download from a list:**
```bash
python zlib_download.py --batch booklist.txt -o ~/books
```

`booklist.txt` format: one title per line (Chinese or English), lines starting with `#` are skipped.

### How it works

- Z-Library (`z-library.sk`) is accessible from China, but DiamWall blocks all Chromium-based headless browsers
- Firefox headless passes DiamWall because of a different browser fingerprint
- Search results expose `<z-bookcard download="/dl/...">` attributes with direct download links — no detail-page visits needed

### Limits & notes

- Free Z-Library accounts: **10 downloads/day**
- Large files (30+ MB) can take 10–15 minutes
- Credentials are read from `.env` in the script directory or the project root — never commit `.env`
- Cookie cache stored in `.zlib_cookies.json` (git-ignored) and reused across runs

### Troubleshooting

| Problem | Fix |
|---------|-----|
| Search returns 0 results | Z-Library redesigned; update `.book-item` selector in `search()` |
| Login fails | Delete `.zlib_cookies.json` and retry; verify credentials at z-library.sk/login |
| Download timeout on large files | Increase `timeout=120000` → `300000` in `download_file()` |
| DiamWall blocks again | Try `pw.webkit` instead; or wait — DiamWall updates periodically |
