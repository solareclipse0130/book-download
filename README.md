# book-download

**中文** | [English](#english)

---

## 中文

Claude Code skill + Python 脚本，从 Z-Library 批量下载电子书。  
使用 Firefox headless 绕过 DiamWall 反爬机制 —— **国内无需 VPN 可直接使用**。

### 原理

- Z-Library（`z-library.sk`）国内可访问，但 DiamWall 会拦截所有基于 Chromium 的无头浏览器
- Firefox headless 因指纹不同可通过 DiamWall
- 搜索结果里的 `<z-bookcard download="/dl/...">` 属性直接包含下载链接，无需进入详情页

### 安装

```bash
# 1. 安装依赖
pip install playwright
python -m playwright install firefox

# 2. 创建 .env 填写 Z-Library 账号
#    （免费注册：https://z-library.sk/registration）
echo "ZLIBRARY_EMAIL=你的邮箱" >> .env
echo "ZLIBRARY_PASSWORD=你的密码" >> .env
```

### 使用

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

### 作为 Claude Code skill 使用

```bash
cp .claude/agents/book-download.md ~/.claude/agents/
```

放入后，跟 Claude 说"帮我下载《XX》"即可自动触发。

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

Claude Code skill + Python script for batch ebook downloads from Z-Library.  
Uses Firefox headless to bypass DiamWall bot protection — **works from mainland China without a VPN**.

### How it works

- Z-Library (`z-library.sk`) is accessible from China, but DiamWall blocks all Chromium-based headless browsers
- Firefox headless passes DiamWall because of a different browser fingerprint
- Search results expose `<z-bookcard download="/dl/...">` attributes with direct download links — no detail-page visits needed

### Setup

```bash
# 1. Install dependencies
pip install playwright
python -m playwright install firefox

# 2. Create .env with your Z-Library credentials
#    (register free at https://z-library.sk/registration)
echo "ZLIBRARY_EMAIL=your@email.com" >> .env
echo "ZLIBRARY_PASSWORD=yourpassword" >> .env
```

### Usage

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

### As a Claude Code skill

```bash
cp .claude/agents/book-download.md ~/.claude/agents/
```

Claude will automatically invoke it when you ask to download books.

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
