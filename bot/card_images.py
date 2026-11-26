"""シングルカード1枚ごとの写真を集めるロボット。

・アイカツ！アンコール：公式カードリストの画像を保存（--official で動かす。ガールズホビー側）
・それ以外（たまごっち・プリキュアなど）：楽天市場のカードショップのシングル出品の写真（--rakuten。鍵があるトレカ抽選ナビ側）
  楽天の画像は保存せず楽天のURLのまま表示し、その商品ページ（アフィリンク）を出典にする
出力: site/img/cards.json  {カードのID: {"img": 画像, "link": 出典ページ, "credit": "公式" / "楽天市場"}}
カードのIDは相場（souba.json）と同じ：たまごっちは型番、ほかは「弾のID-カード番号」
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rakuten_card_images import ENDPOINT, NG, SHIP_NG, norm, UA  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "bot" / "cards.json"
OUT = ROOT / "site" / "img" / "cards.json"
AK = "https://dcd.aikatsu.com/encore/images/cardlist/card/"
AK_DIR = ROOT / "site" / "img" / "cards" / "aikatsu"
RAR = {"PR": "PR", "ER": "ER", "R": "R", "N": "N"}


def load():
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}


def save(d):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (girlshobby card bot)", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def official():
    """アイカツ：相場を取っているカードの公式画像を保存"""
    d = load()
    rows = [r for r in json.loads(CARDS.read_text(encoding="utf-8")) if r["set"].startswith("aikatsu")]
    AK_DIR.mkdir(parents=True, exist_ok=True)
    for r in rows:
        code = r["id"].split("-", 2)[-1]            # 例 E1-01★
        no = code.rstrip("★")
        rar = r["name"].split(" ")[-1].replace("★（パラレル）", "")
        rar = re.sub(r"[^A-Z]", "", rar) or "N"
        par = code.endswith("★")
        name = f"{no}_{rar}{'_p1' if par else ''}.webp"
        path = AK_DIR / name
        if not path.exists():
            for cand in ([f"{no}_{rar}_p1.webp", f"{no}_{rar}.webp"] if par else [f"{no}_{rar}.webp"]):
                try:
                    path.write_bytes(fetch(AK + cand))
                    break
                except Exception:
                    continue
            time.sleep(0.8)
        if path.exists():
            d[r["id"]] = {"img": f"img/cards/aikatsu/{name}", "link": "https://dcd.aikatsu.com/encore/cardlist/", "credit": "公式"}
    save(d)
    print("公式カード画像:", sum(1 for v in d.values() if v.get("credit") == "公式"), "枚")


def rakuten():
    app, key = os.environ.get("RAKUTEN_APP_ID", "").strip(), os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
    if not (app and key):
        print("楽天の鍵が無いのでスキップ")
        return
    site = (os.environ.get("SITE_URL") or "https://tcg-chusen.com").rstrip("/")
    aff = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip()
    d = load()
    rows = [r for r in json.loads(CARDS.read_text(encoding="utf-8")) if not r["set"].startswith("aikatsu")]
    n = 0
    for r in rows:
        if (d.get(r["id"]) or {}).get("credit") == "公式":
            continue
        q = {"applicationId": app, "keyword": r["q"], "format": "json", "formatVersion": 2, "hits": 30, "imageFlag": 1}
        if aff:
            q["affiliateId"] = aff
        try:
            items = json.loads(fetch(ENDPOINT + "?" + urllib.parse.urlencode(q),
                                     {"accessKey": key, "Referer": site + "/", "Origin": site})).get("Items") or []
        except Exception as e:
            print(f"[skip] {r['id']}: {e}", file=sys.stderr)
            time.sleep(5)
            continue
        time.sleep(3.5)              # 速すぎると楽天に断られる（429）
        hit = None
        for x in items:
            t = norm(x.get("itemName", ""))
            if any(norm(w) in t for w in NG + SHIP_NG + ("まとめ", "セット", "BOX", "ボックス", "コンプ")):
                continue
            if not all(any(norm(a) in t for a in m.split("|")) for m in r["must"]):
                continue
            if any(norm(w) in t for w in r.get("ng", [])):
                continue
            imgs = x.get("mediumImageUrls") or []
            u = imgs[0] if imgs else ""
            if isinstance(u, dict):
                u = u.get("imageUrl", "")
            if u:
                hit = {"img": re.sub(r"\?_ex=\d+x\d+", "", u) + "?_ex=300x300",
                       "link": x.get("affiliateUrl") or x.get("itemUrl") or "", "credit": "楽天市場",
                       "title": x.get("itemName", "")[:80]}
                break
        if hit:
            d[r["id"]] = hit
            n += 1
    save(d)
    print("楽天のカード写真:", n, "枚 /", len(rows), "枚中")


if __name__ == "__main__":
    official() if "--official" in sys.argv else rakuten()
