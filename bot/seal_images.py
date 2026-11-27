"""シールの商品写真を集めるロボット。

順番:
  1. 公式・告知ページの代表画像（og:image）を使う
  2. なければ（または X のページなど開けないときは）楽天市場の商品検索APIの商品画像を使う
出力: site/img/seal/<id>.jpg と site/img/seal/index.json（サイトが読む一覧。出典も入れる）
入力: bot/seal_items.json（id・公式ページ・楽天で探す言葉・タイトルに必ず入る言葉）

楽天APIの鍵は GitHub の Secrets：RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY（トレカ抽選ナビと同じもの）。
楽天の新APIは「許可するWebサイト」と同じURLを Referer で送る必要があるので、SITE_URL に登録済みのサイトURLを入れる。
すでに写真がある商品は取り直さない（REFRESH=1 で全部取り直し）。
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "bot" / "seal_items.json"
OUT = ROOT / "site" / "img" / "seal"
ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
UA = "Mozilla/5.0 (girlshobby seal image bot)"
OG_RE = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I)
OG_RE2 = re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I)
NG = ("中古", "まとめ売り", "バラ売り", "空箱", "偽物", "類似", "互換", "ノーブランド")
SKIP_HOSTS = ("x.com", "twitter.com", "instagram.com")


def get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(), r.headers.get("content-type", "")


def norm(s):
    return unicodedata.normalize("NFKC", s or "").lower()


def from_page(page):
    if not page or any(h in page for h in SKIP_HOSTS):
        return None
    html = get(page)[0].decode("utf-8", "replace")
    m = OG_RE.search(html) or OG_RE2.search(html)
    if not m:
        return None
    return urllib.parse.urljoin(page, m.group(1)), page


import sys as _s; from pathlib import Path as _P; _s.path.insert(0, str(_P(__file__).resolve().parent))
from rakuten_card_images import SHIP_NG, rk_kw  # noqa: E402  前日発送・ポイントなどの文字入り出品を外す


def from_rakuten(it):
    """楽天ブックス → 楽天市場 の順に探す"""
    for shop in ("book", ""):
        got = _rakuten(it, shop)
        if got:
            return got
        time.sleep(2)
    return None


def _rakuten(it, shop):
    app, key = os.environ.get("RAKUTEN_APP_ID", "").strip(), os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
    if not (app and key):
        return None
    site = (os.environ.get("SITE_URL") or "https://tcg-chusen.com").rstrip("/")
    q = {"applicationId": app, "keyword": rk_kw(it["rk"]), "format": "json", "formatVersion": 2,
         "hits": 20, "imageFlag": 1}
    if shop:
        q["shopCode"] = shop          # 楽天ブックスは在庫切れでも商品ページと写真はある
    # 写真がほしいだけなので、売り切れの出品も対象にする（シールはほとんど売り切れのため）
    aff = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
    if aff:
        q["affiliateId"] = aff
    body, _ = get(ENDPOINT + "?" + urllib.parse.urlencode(q),
                  {"accessKey": key, "Referer": site + "/", "Origin": site})
    for x in json.loads(body).get("Items") or []:
        name = norm(x.get("itemName"))
        if any(w in name for w in map(norm, NG + SHIP_NG)) or not all(any(norm(x) in name for x in m.split("|")) for m in it.get("must", [])):
            continue
        imgs = x.get("mediumImageUrls") or []
        u = imgs[0] if imgs else ""
        if isinstance(u, dict):
            u = u.get("imageUrl", "")
        if u:
            return re.sub(r"\?_ex=\d+x\d+", "", u) + "?_ex=500x500", x.get("itemUrl") or ""
    return None


def main():
    items = json.loads(ITEMS.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    idx_f = OUT / "index.json"
    idx = json.loads(idx_f.read_text(encoding="utf-8")) if idx_f.exists() else {}
    refresh = os.environ.get("REFRESH") == "1"
    for it in items:
        sid = it["id"]
        cur = idx.get(sid) or {}
        if cur.get("file") and not cur["file"].startswith("http") and (ROOT / "site" / cur["file"]).exists() and not refresh:
            continue                     # 公式の写真を保存済み
        got, kind = None, ""
        for kind, fn in (("公式・告知ページ", lambda: from_page(it.get("page"))), ("楽天市場", lambda: from_rakuten(it))):
            try:
                got = fn()
            except Exception as e:
                print(f"[skip] {sid} {kind}: {e}", file=sys.stderr)
                got = None
            if got:
                break
        if not got:
            print(f"{sid}: 写真なし")
            continue
        url, source = got
        if kind == "楽天市場":           # 楽天の画像は保存せず、楽天のURLのまま表示する
            idx[sid] = {"file": url, "source": source, "kind": kind}
            print(f"{sid}: 楽天市場の画像を表示")
            continue
        try:
            data, ctype = get(url)
        except Exception as e:
            print(f"[skip] {sid} 画像DL: {e}", file=sys.stderr)
            continue
        ext = ".png" if "png" in ctype or url.lower().split("?")[0].endswith(".png") else ".jpg"
        name = f"{sid}{ext}"
        (OUT / name).write_bytes(data)
        idx[sid] = {"file": f"img/seal/{name}", "source": source, "kind": kind}
        print(f"{sid}: {kind}から保存")
        time.sleep(1.2)
    idx_f.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
