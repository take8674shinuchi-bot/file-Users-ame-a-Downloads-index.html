#!/usr/bin/env python3
"""配布用の拡張機能 ZIP を生成する。

ランディングページ(public/index.html)の「ダウンロード」ボタンから
配布するため、拡張機能の実体ファイルだけを public/downloads/ 配下に
まとめる。`tools/` や `public/` などの開発用ファイルは含めない。

使い方:
    python3 tools/make_zip.py
"""
import os
import zipfile

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
OUT = os.path.join(ROOT, "public", "downloads", "kantan-ad-blocker.zip")

# 拡張機能として読み込むのに必要なファイル一式。
FILES = [
    "manifest.json",
    "rules.json",
    "background.js",
    "popup.html",
    "popup.css",
    "popup.js",
    "icons/icon16.png",
    "icons/icon32.png",
    "icons/icon48.png",
    "icons/icon128.png",
    "README.md",
]

TOP = "kantan-ad-blocker"  # 展開時のトップフォルダ名


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in FILES:
            src = os.path.join(ROOT, rel)
            z.write(src, arcname=os.path.join(TOP, rel))
    print(f"wrote {os.path.normpath(OUT)} ({len(FILES)} files)")


if __name__ == "__main__":
    main()
