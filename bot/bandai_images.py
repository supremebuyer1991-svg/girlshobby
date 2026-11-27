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
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "site" / "img"

# 公式の商品ページ。新しい弾が出たらここに1行足す
PAGES = {
    "tama-gotchi3": "https://toy.bandai.co.jp/ja/item/01_6323/",
    # ↓バンダイキャンディ公式（お菓子売り場のウエハース）
    "pre-wafer1": "https://www.bandai.co.jp/candy/products/2020/4549660504313000.html",
    "pre-wafer2": "https://www.bandai.co.jp/candy/products/2021/4549660550983000.html",
    "pre-wafer3": "https://www.bandai.co.jp/candy/products/2021/4549660583882000.html",
    "pre-wafer5": "https://www.bandai.co.jp/candy/products/2022/4549660701583000.html",
    "pre-wafer7": "https://www.bandai.co.jp/candy/products/2023/4549660876588000.html",
    "pre-wafer9": "https://www.bandai.co.jp/candy/products/2024/4570117913846000.html",
    "pre-wafer10": "https://www.bandai.co.jp/candy/products/2024/4570117917080000.html",
    "pre-wafer11": "https://www.bandai.co.jp/candy/products/2025/4570117920288000.html",
    "pre-wafer12": "https://www.bandai.co.jp/candy/products/2025/4570117924965000.html",
    "pre-wafer13": "https://www.bandai.co.jp/candy/products/2026/4570117930768000.html",
    "pre-wafer14": "https://www.bandai.co.jp/candy/products/2027/4570117934612000.html",
    "sanrio-wafer1": "https://www.bandai.co.jp/candy/products/2022/4549660738206000.html",
    "sanrio-wafer2": "https://www.bandai.co.jp/candy/products/2022/4549660820536000.html",
    "sanrio-wafer3": "https://www.bandai.co.jp/candy/products/2023/4549660876625000.html",
    "sanrio-wafer4": "https://www.bandai.co.jp/candy/products/2023/4570117911385000.html",
    "sanrio-wafer6": "https://www.bandai.co.jp/candy/products/2024/4570117915727000.html",
    "sanrio-wafer7": "https://www.bandai.co.jp/candy/products/2024/4570117917493000.html",
    "sanrio-wafer9": "https://www.bandai.co.jp/candy/products/2025/4570117921797000.html",
    "sanrio-wafer11": "https://www.bandai.co.jp/candy/products/2025/4570117927096000.html",
    "sanrio-wafer12": "https://www.bandai.co.jp/candy/products/2026/4570117930065000.html",
    "sanrio-wafer13": "https://www.bandai.co.jp/candy/products/2027/4570117934155000.html",
    # ↓アイカツ
    "aikatsu-encore1": "https://dcd.aikatsu.com/encore/",
    "aikatsu-phone": "https://toy.bandai.co.jp/ja/item/01_21043/",
    "aikatsu-kuji": "https://1kuji.com/products/aikatsu8",
    "aikatsu-file": "https://www.bandai.co.jp/catalog/item.php?jan_cd=4582770134674000",
    "chiikawa-wafer2": "https://www.bandai.co.jp/candy/products/2025/4570117926594000.html",
    # ↓メーカーのプレスリリース（その商品の発表ページなので代表画像を使ってよい）
    "aipri-verse4": "https://prtimes.jp/main/html/rd/p/000000363.000009185.html",
    # まだURLが確認できていない弾: tama-gotchi1, tama-scratch, tama-gotchi2, tama-omisecchi, pre-wafer4/6/8, sanrio-wafer5/8
}
IMG_RE = re.compile(r"https://bandai-a\.akamaihd\.net/bc/img/model/(?:xl|b)/[0-9A-Za-z_]+\.(?:jpg|png)")
# 代表画像（og:image）を使ってよいページ（そのページ＝その商品だけの公式ページ）
OG_OK = {"aikatsu-kuji", "aipri-verse4"}
# ページを開かず、メーカー発表の商品画像をそのまま使う商品（出典ページ, 画像URL）
KN = "https://cdn.kyodonewsprwire.jp/prwfile/release/M000076/202610057308/"
DIRECT = {"niji-sleeve": ("https://kyodonewsprwire.jp/release/202610057308", [KN + f for f in (
    "_prw_PI17lg_hocv9dz3.jpg", "_prw_PI16lg_zVMwERc7.jpg", "_prw_PI18lg_j8H01S07.jpg", "_prw_PI19lg_D27l7O1M.jpg")])}
# 公式のカード画像をそのまま使う弾（アイカツ！アンコール公式カードリストの当たりカード）
AK = "https://dcd.aikatsu.com/encore/images/cardlist/card/"
EXTRA = {"aikatsu-encore1": [AK + c + ".webp" for c in (
    "E1-30_ER", "E1-50_ER", "E1-31_ER", "E1-32_ER", "E1-01_PR", "E1-02_PR", "E1-33_PR", "E1-51_PR")]}
# バンダイキャンディ公式の商品写真（"-product-main" は別商品のおすすめ欄なので除外）
CANDY_RE = re.compile(r'(?:https://www\.bandai\.co\.jp)?/candy/published/bnc_files/product/\w+/\w+\.(?:jpg|png)(?=["\'\s)])')
MAX_IMAGES = 12
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
    for old in [k for k in index if k not in PAGES and k not in DIRECT]:   # 一覧から外した弾は写真も外す
        index.pop(old)
    for sid, page in list(PAGES.items()) + [(k, v[0]) for k, v in DIRECT.items()]:
        try:
            html = "" if sid in DIRECT else get(page).decode("utf-8", "replace")
        except Exception as e:
            print(f"[skip] {sid}: ページが開けない {e}", file=sys.stderr)
            continue
        title = re.search(r"<title>(.*?)</title>", html, re.S)
        title = title.group(1) if title else ""
        want = "ウエハース" if "wafer" in sid else ("たまごっち" if sid.startswith("tama") else ("アイカツ" if sid.startswith("aikatsu") else ""))
        if want and want not in title and sid not in DIRECT:
            print(f"[skip] {sid}: ページの商品名が違う（{title[:40]}）", file=sys.stderr)
            continue
        found = IMG_RE.findall(html) + [
            u if u.startswith("http") else "https://www.bandai.co.jp" + u for u in CANDY_RE.findall(html)]
        urls = (DIRECT.get(sid, ("", []))[1] or EXTRA.get(sid) or list(dict.fromkeys(found)))[:MAX_IMAGES]   # 重複を消して順番そのまま
        if not urls and sid in OG_OK:
            m = OG_RE.search(html)
            if m:
                urls = [urllib.parse.urljoin(page, m.group(1))]
        if not urls:   # 代表画像（og:image）は別商品やロゴのことがあるので使わない
            print(f"[skip] {sid}: 商品写真が見つからない", file=sys.stderr)
            continue
        folder = IMG / sid
        folder.mkdir(parents=True, exist_ok=True)
        files = []
        for n, u in enumerate(urls, 1):
            ext = ".png" if u.lower().endswith(".png") else (".webp" if u.lower().endswith(".webp") else ".jpg")
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
