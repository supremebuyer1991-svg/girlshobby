"""公式の写真が無いカードの弾に、楽天市場の商品画像を入れるロボット。

使い方:  python bot/rakuten_card_images.py
- サイトの弾一覧（site/index.html の ITEMS）を読み、site/img/index.json に写真が無い弾だけ楽天で探す
- 楽天の画像は保存せず、楽天のURLのまま表示する（出典「楽天市場」と商品ページへのリンクつき）
- 公式（バンダイ）の写真が後で見つかったら、そっちが優先で上書きされる
楽天APIの鍵は GitHub の Secrets：RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY。鍵が無いときは何もしない。
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
HTML = ROOT / "site" / "index.html"
IDX = ROOT / "site" / "img" / "index.json"
ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
UA = "Mozilla/5.0 (girlshobby card image bot)"
NG = ("中古", "バラ売り", "空箱", "偽物", "類似", "互換", "スリーブ", "ローダー", "ファイル", "ホルダー")
ITEM_RE = re.compile(r'\{id:"([^"]+)"[^\n]*?\bname:"([^"]+)"')


def norm(s):
    return unicodedata.normalize("NFKC", s or "").lower()


def compact(s):
    # 空白・記号・カッコの中身を消して比べやすくする
    s = re.sub(r"[（(][^）)]*[）)]", "", norm(s))
    return re.sub(r"[\s・!！?？~〜ー\-_/／&＆:：、。【】\[\]「」]", "", s)


def matches(want, title):
    """商品名（want）が楽天の商品名（title）に入っていて、弾の数字がズレていないか"""
    t = compact(title)
    pos = t.find(want)
    while pos != -1:
        after = t[pos + len(want): pos + len(want) + 1]
        if not after.isdigit():          # 「ウエハース1」が「ウエハース13」に当たらないように
            return True
        pos = t.find(want, pos + 1)
    return False


def search(name):
    app, key = os.environ.get("RAKUTEN_APP_ID", "").strip(), os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
    site = (os.environ.get("SITE_URL") or "https://tcg-chusen.com").rstrip("/")
    keyword = re.sub(r"[（(][^）)]*[）)]", " ", name).strip()
    q = {"applicationId": app, "keyword": keyword, "format": "json", "formatVersion": 2,
         "hits": 30, "imageFlag": 1}
    aff = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
    if aff:
        q["affiliateId"] = aff
    req = urllib.request.Request(ENDPOINT + "?" + urllib.parse.urlencode(q),
                                 headers={"User-Agent": UA, "accessKey": key,
                                          "Referer": site + "/", "Origin": site})
    with urllib.request.urlopen(req, timeout=30) as r:
        items = json.loads(r.read()).get("Items") or []
    want = compact(name)
    for x in items:
        title = x.get("itemName", "")
        if any(norm(w) in norm(title) for w in NG) or not matches(want, title):
            continue
        imgs = x.get("mediumImageUrls") or []
        urls = []
        for u in imgs[:4]:
            if isinstance(u, dict):
                u = u.get("imageUrl", "")
            if u:
                urls.append(re.sub(r"\?_ex=\d+x\d+", "", u) + "?_ex=500x500")
        if urls:
            return urls, x.get("affiliateUrl") or x.get("itemUrl") or ""
    return None


def main():
    if not (os.environ.get("RAKUTEN_APP_ID") and os.environ.get("RAKUTEN_ACCESS_KEY")):
        print("楽天の鍵が無いのでスキップ")
        return 0
    idx = json.loads(IDX.read_text(encoding="utf-8")) if IDX.exists() else {}
    html = HTML.read_text(encoding="utf-8")
    start = html.index("const ITEMS=")
    items = dict(ITEM_RE.findall(html[start: html.index("];", start)]))   # カードの弾だけ（シールは別ロボット）
    for sid, name in items.items():
        if idx.get(sid, {}).get("images") and idx[sid].get("credit") != "楽天市場":
            continue                     # 公式の写真があるものは触らない
        try:
            got = search(name)
        except Exception as e:
            print(f"[skip] {sid}: {e}", file=sys.stderr)
            got = None
        time.sleep(1.2)
        if not got:
            print(f"{sid}: 楽天でも見つからず")
            continue
        urls, link = got
        idx[sid] = {"source": link, "images": urls, "credit": "楽天市場"}
        print(f"{sid}: 楽天から{len(urls)}枚")
    IDX.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
