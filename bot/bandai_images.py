"""バンダイ公式の商品ページから商品画像を集めて、弾ページに表示するロボット。

使い方:  python bot/bandai_images.py
入力:    下の PAGES（弾のID → バンダイ公式の商品ページURL）
出力:    site/img/<弾のID>/product_1.jpg ...  と  site/img/index.json（サイトが読む一覧）
すでに保存済みの画像はダウンロードし直さない。
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "site" / "img"

# 公式の商品ページ。新しい弾が出たらここに1行足す
PAGES = {
    "tama-gotchi3": "https://toy.bandai.co.jp/ja/item/01_6323/",
    "tama-gotchi1": "https://toy.bandai.co.jp/item/detail/15081/",          # たまごっち公式サイトが案内しているURL
    "tama-scratch": "https://toy.bandai.co.jp/ja/series/carddass/tamagotchi_scratch/",
    "pre-wafer2": "https://www.bandai.co.jp/candy/products/2021/4549660550983000.html",   # バンダイキャンディ公式
    "pre-wafer3": "https://www.bandai.co.jp/candy/products/2021/4549660583882000.html",
    # まだURLが確認できていない弾（見つけたら上と同じ形で足す）:
    # "tama-gotchi2": "",  "tama-omisecchi": "",  "pre-wafer11": "",  "pre-wafer12": "",  "pre-wafer13": "",
}
IMG_RE = re.compile(r"https://bandai-a\.akamaihd\.net/bc/img/model/xl/[0-9A-Za-z_]+\.(?:jpg|png)")
# 商品画像が見つからないページでは、ページの代表画像（og:image）を1枚だけ使う
OG_RE = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I)
UA = {"User-Agent": "Mozilla/5.0 (girlshobby image bot)"}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main() -> int:
    index = {}
    idx_file = IMG / "index.json"
    if idx_file.exists():
        index = json.loads(idx_file.read_text(encoding="utf-8"))
    for sid, page in PAGES.items():
        try:
            html = get(page).decode("utf-8", "replace")
        except Exception as e:
            print(f"[skip] {sid}: ページが開けない {e}", file=sys.stderr)
            continue
        urls = list(dict.fromkeys(IMG_RE.findall(html)))   # 重複を消して順番そのまま
        if not urls:
            urls = OG_RE.findall(html)[:1]
        folder = IMG / sid
        folder.mkdir(parents=True, exist_ok=True)
        files = []
        for n, u in enumerate(urls, 1):
            ext = ".png" if u.lower().endswith(".png") else ".jpg"
            name = f"product_{n}{ext}"
            path = folder / name
            if not path.exists():
                try:
                    path.write_bytes(get(u))
                    time.sleep(1)
                except Exception as e:
                    print(f"[skip] {u}: {e}", file=sys.stderr)
                    continue
            files.append(f"img/{sid}/{name}")
        index[sid] = {"source": page, "images": files}
        print(f"{sid}: {len(files)}枚")
    IMG.mkdir(parents=True, exist_ok=True)
    idx_file.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
