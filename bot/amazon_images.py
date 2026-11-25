"""写真が無いカードの弾・シールに、Amazon（Creators API）の商品画像を入れるロボット。

使い方:  python bot/amazon_images.py
- 公式の写真も楽天の写真も無いものだけ Amazon で探す（公式＞楽天＞Amazon の順で優先）
- Amazon の規約に合わせて、画像は保存せず Amazon のURLのまま表示し、商品ページ（アフィリンク）を出典にする
- 毎朝取り直すので、Amazon の「24時間以内に更新」ルールも守れる
鍵は GitHub の Secrets：AMAZON_CREDENTIAL_ID / AMAZON_CREDENTIAL_SECRET / AMAZON_CREDENTIAL_VERSION（例 3.3）
トラッキングID：AMAZON_PARTNER_TAG（無ければ tcgchusen-22）。鍵が無いときは何もしない。
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rakuten_card_images import compact, matches, ITEM_RE, norm  # 同じ「商品名の一致チェック」を使う

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "site" / "index.html"
CARD_IDX = ROOT / "site" / "img" / "index.json"
SEAL_IDX = ROOT / "site" / "img" / "seal" / "index.json"
SEAL_ITEMS = ROOT / "bot" / "seal_items.json"
API = "https://creatorsapi.amazon/catalog/v1/searchItems"
TOKEN_URL = {  # 鍵のバージョン → トークンをもらう場所
    "3.1": "https://api.amazon.com/auth/o2/token",
    "3.2": "https://api.amazon.co.uk/auth/o2/token",
    "3.3": "https://api.amazon.co.jp/auth/o2/token",
}
NG = ("中古", "スリーブ", "ローダー", "ファイル", "ホルダー", "互換")
MARKET = "www.amazon.co.jp"


def post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def token():
    cid, sec = os.environ["AMAZON_CREDENTIAL_ID"].strip(), os.environ["AMAZON_CREDENTIAL_SECRET"].strip()
    ver = (os.environ.get("AMAZON_CREDENTIAL_VERSION") or "3.3").strip()
    url = TOKEN_URL.get(ver, TOKEN_URL["3.3"])
    j = post(url, {"grant_type": "client_credentials", "client_id": cid,
                   "client_secret": sec, "scope": "creatorsapi::default"}, {})
    return j["access_token"], ver


def search(tok, ver, keyword, ok):
    tag = (os.environ.get("AMAZON_PARTNER_TAG") or "tcgchusen-22").strip()
    auth = f"Bearer {tok}" if ver.startswith("3") else f"Bearer {tok}, Version {ver}"
    j = post(API, {"keywords": keyword, "searchIndex": "All", "itemCount": 10,
                   "partnerTag": tag, "marketplace": MARKET,
                   "resources": ["images.primary.large", "images.variants.large", "itemInfo.title"]},
             {"Authorization": auth, "x-marketplace": MARKET})
    res = j.get("searchResult") or j.get("itemsResult") or {}
    for it in res.get("items") or []:
        title = (((it.get("itemInfo") or {}).get("title") or {}).get("displayValue")) or ""
        if any(w in norm(title) for w in map(norm, NG)) or not ok(title):
            continue
        imgs = it.get("images") or {}
        urls = []
        p = ((imgs.get("primary") or {}).get("large") or {}).get("url")
        if p:
            urls.append(p)
        for v in (imgs.get("variants") or [])[:3]:
            u = ((v or {}).get("large") or {}).get("url")
            if u:
                urls.append(u)
        if urls:
            return urls, it.get("detailPageURL") or ""
    return None


def load(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main():
    if not (os.environ.get("AMAZON_CREDENTIAL_ID") and os.environ.get("AMAZON_CREDENTIAL_SECRET")):
        print("Amazonの鍵が無いのでスキップ")
        return 0
    try:
        tok, ver = token()
    except Exception as e:
        print(f"[skip] Amazonのログインに失敗: {e}", file=sys.stderr)
        return 0

    # カードの弾
    cidx = load(CARD_IDX)
    html = HTML.read_text(encoding="utf-8")
    st = html.index("const ITEMS=")
    for sid, name in ITEM_RE.findall(html[st: html.index("];", st)]):
        cur = cidx.get(sid) or {}
        if cur.get("images") and cur.get("credit") != "Amazon":
            continue
        want = compact(name)
        try:
            got = search(tok, ver, re.sub(r"[（(][^）)]*[）)]", " ", name).strip(), lambda t: matches(want, t))
        except Exception as e:
            print(f"[skip] {sid}: {e}", file=sys.stderr)
            got = None
        time.sleep(1.5)
        if got:
            cidx[sid] = {"source": got[1], "images": got[0], "credit": "Amazon"}
            print(f"{sid}: Amazonから{len(got[0])}枚")
        else:
            print(f"{sid}: Amazonでも見つからず")
    CARD_IDX.write_text(json.dumps(cidx, ensure_ascii=False, indent=1), encoding="utf-8")

    # シール
    sidx = load(SEAL_IDX)
    for it in load(SEAL_ITEMS) if SEAL_ITEMS.exists() else []:
        sid = it["id"]
        cur = sidx.get(sid) or {}
        if cur.get("file") and cur.get("kind") != "Amazon":
            continue
        must = [norm(m) for m in it.get("must", [])]
        try:
            got = search(tok, ver, it.get("rk") or sid, lambda t: all(m in norm(t) for m in must))
        except Exception as e:
            print(f"[skip] {sid}: {e}", file=sys.stderr)
            got = None
        time.sleep(1.5)
        if got:
            sidx[sid] = {"file": got[0][0], "source": got[1], "kind": "Amazon"}
            print(f"{sid}: Amazonから保存")
        else:
            print(f"{sid}: Amazonでも見つからず")
    SEAL_IDX.parent.mkdir(parents=True, exist_ok=True)
    SEAL_IDX.write_text(json.dumps(sidx, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
