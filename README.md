# book-download

Claude Code skill + Python script for batch ebook downloads from Z-Library.  
Uses Firefox headless to bypass DiamWall bot protection — **works from mainland China without a VPN**.

## How it works

- Z-Library (`z-library.sk`) is accessible from China, but its DiamWall protection blocks all Chromium-based headless browsers
- Firefox headless passes DiamWall because of different browser fingerprints
- Search results return `<z-bookcard download="/dl/...">` elements with direct download links — no detail-page navigation needed

## Setup

```bash
# 1. Install dependencies
pip install playwright
python -m playwright install firefox

# 2. Create .env with your Z-Library credentials
#    (register free at https://z-library.sk/registration)
echo "ZLIBRARY_EMAIL=your@email.com" >> .env
echo "ZLIBRARY_PASSWORD=yourpassword" >> .env
```

## Usage

**Single book (interactive):**
```bash
python zlib_download.py "The Mom Test"
```

**Single book (auto-select first result):**
```bash
python zlib_download.py "疯传" -d 1 --ext epub
```

**Batch download from a list:**
```bash
python zlib_download.py --batch booklist.txt -o ~/books
```

`booklist.txt` format: one book title per line (Chinese or English), lines starting with `#` are skipped.

## As a Claude Code skill

Place `.claude/agents/book-download.md` in your project's `.claude/agents/` directory (or symlink it).  
Claude will automatically invoke it when you ask to download books.

```bash
cp .claude/agents/book-download.md ~/.claude/agents/
```

## Limits & notes

- Free Z-Library accounts: **10 downloads/day**
- Large files (30+ MB) can take 10–15 minutes
- Credentials are read from `.env` in the script directory or the project root — never commit `.env`
- Cookie cache is stored in `.zlib_cookies.json` (also git-ignored) and reused across runs

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Search returns 0 results | Z-Library redesigned; update `.book-item` selector in `search()` |
| Login fails | Delete `.zlib_cookies.json` and retry; verify credentials at z-library.sk/login |
| Download timeout on large files | Increase `timeout=120000` → `300000` in `download_file()` |
| DiamWall blocks again | Switch from `pw.firefox` to try webkit; or wait — DiamWall sometimes updates |
