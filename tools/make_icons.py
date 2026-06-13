#!/usr/bin/env python3
"""拡張機能用アイコン(PNG)を純Pythonで生成する。

外部ライブラリ(Pillow等)に依存せず、zlib と struct だけで
RGBA の PNG を書き出す。スーパーサンプリングで簡易アンチエイリアスを行い、
「禁止マーク(丸にスラッシュ)」= 広告ブロックのアイコンを描く。

使い方:
    python3 tools/make_icons.py
"""
import math
import struct
import zlib
import os

# 色 (R, G, B)
BG = (0x22, 0x2B, 0x36)   # ダークスレート(背景)
FG = (0xFF, 0x52, 0x52)   # レッド(禁止マーク)
SS = 4                    # スーパーサンプリング倍率

OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "icons")
SIZES = (16, 32, 48, 128)


def _rounded_square(nx, ny, radius):
    """正規化座標(0..1)が角丸正方形の内側なら True。"""
    dx = abs(nx - 0.5)
    dy = abs(ny - 0.5)
    half = 0.5
    if dx <= half - radius or dy <= half - radius:
        return dx <= half and dy <= half
    cx = half - radius
    return math.hypot(dx - cx, dy - cx) <= radius


def _is_sign(nx, ny):
    """禁止マーク(リング or スラッシュ)の内側なら True。"""
    dx = nx - 0.5
    dy = ny - 0.5
    r = math.hypot(dx, dy)
    # リング
    if 0.26 <= r <= 0.37:
        return True
    # 斜めのスラッシュ(45度方向)。リング内に収める。
    if r <= 0.37:
        perp = (dx + dy) / math.sqrt(2.0)  # 直交方向の距離
        if abs(perp) <= 0.055:
            return True
    return False


def _sample(nx, ny):
    """1サンプル分の (R,G,B,A) を返す。背景外は透明。"""
    if not _rounded_square(nx, ny, 0.22):
        return (0, 0, 0, 0)
    if _is_sign(nx, ny):
        return (FG[0], FG[1], FG[2], 255)
    return (BG[0], BG[1], BG[2], 255)


def _render(size):
    """size x size の RGBA バイト列(スキャンライン)を生成。"""
    rows = []
    inv = 1.0 / (size * SS)
    for y in range(size):
        row = bytearray()
        row.append(0)  # PNG フィルタタイプ: None
        for x in range(size):
            ar = ag = ab = aa = 0
            for sy in range(SS):
                ny = (y * SS + sy + 0.5) * inv
                for sx in range(SS):
                    nx = (x * SS + sx + 0.5) * inv
                    r, g, b, a = _sample(nx, ny)
                    ar += r * a
                    ag += g * a
                    ab += b * a
                    aa += a
            n = SS * SS
            alpha = aa // n
            if aa == 0:
                row += b"\x00\x00\x00\x00"
            else:
                row += bytes((ar // aa, ag // aa, ab // aa, alpha))
        rows.append(bytes(row))
    return b"".join(rows)


def _chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def _write_png(path, size, raw):
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8bit RGBA
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for size in SIZES:
        raw = _render(size)
        path = os.path.join(OUT_DIR, f"icon{size}.png")
        _write_png(path, size, raw)
        print(f"wrote {os.path.normpath(path)} ({size}x{size})")


if __name__ == "__main__":
    main()
