"""楽天市場の商品検索APIで、カテゴリごとに商品（過去の商品も含む）を集めてカタログにするロボット。

入力:  bot/catalog_config.json（カテゴリ・検索ワード・NGワード）
出力:  site/catalog.json（サイトと相場ページ作成が読む）
・商品名・価格・画像・お店・アフィリエイトリンクは楽天APIが返したものだけを使う（こちらで作らない）
・同じ商品が何店舗にもあるときは1つにまとめ、いちばん安いお店を代表にする
・楽天APIのカギ: RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY（Secrets）、RAKUTEN_AFFILIATE_ID（なければ設定ファイルのIDを使う）
・楽天の新APIは Referer が必要なので、楽天に登録済みのサイトURLを SITE_URL に入れる
・1秒に1回より速く呼ばない
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / "bot" / "catalog_config.json"
OUT = ROOT / "site" / "catalog.json"
ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
DEFAULT_AFF = "0f60e3a0.0ec21e9a.0f60e3a1.23a40abb"   # トレカ抽選ナビと同じ楽天アフィリエイトID（公開されるIDなのでここに書いてOK）
JST = timezone(timedelta(hours=9))
PAGES = int(os.environ.get("CATALOG_PAGES", "3"))   # 1つの検索ワードで何ページ（30件ずつ）見るか


def norm(s):
    return unicodedata.normalize("NFKC", s or "").lower()


def core(name):
    """お店ごとの飾り文字（送料無料・ポイント・【】の中など）を消して、同じ商品をまとめるためのキーを作る"""
    s = norm(name)
    s = re.sub(r"【[^】]*】|\[[^\]]*\]|［[^］]*］|＼[^／]*／|★[^★]*★|☆[^☆]*☆", " ", s)
    s = re.sub(r"送料無料|ポイント\d*倍|あす楽|在庫あり|即納|新品|正規品|公式|メール便|ネコポス|予約|再販|\d{1,2}月\d{1,2}日|発売|入荷", " ", s)
    s = re.sub(r"[\s・/／\-ー〜~!！?？。、,，.:：()（）「」『』]+", "", s)
    return s[:40]


def ok(name, cat, ng_common):
    n = norm(name)
    if any(norm(w) in n for w in ng_common + cat.get("ng", [])):
        return False
    if cat.get("must_any") and not any(norm(w) in n for w in cat["must_any"]):
        return False
    if cat.get("also_any") and not any(norm(w) in n for w in cat["also_any"]):
        return False
    return True


def api(keyword, page, aff):
    app, key = os.environ.get("RAKUTEN_APP_ID", "").strip(), os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
    site = (os.environ.get("SITE_URL") or "https://tcg-chusen.com").rstrip("/")
    q = {"applicationId": app, "keyword": keyword, "format": "json", "formatVersion": 2, "hits": 30, "page": page,
         "imageFlag": 1, "sort": "standard", "affiliateId": aff}
    req = urllib.request.Request(ENDPOINT + "?" + urllib.parse.urlencode(q),
                                 headers={"accessKey": key, "Referer": site + "/", "Origin": site, "User-Agent": "girlshobby/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("Items") or []


def image(x):
    imgs = x.get("mediumImageUrls") or []
    u = imgs[0] if imgs else ""
    if isinstance(u, dict):
        u = u.get("imageUrl", "")
    return re.sub(r"\?_ex=\d+x\d+", "", u) + "?_ex=300x300" if u else ""


def collect(cat, ng_common, aff, fetch=api):
    groups = {}
    for kw in cat["keywords"]:
        for page in range(1, PAGES + 1):
            try:
                items = fetch(kw, page, aff)
            except Exception as e:
                print(f"[skip] {cat['id']} 「{kw}」p{page}: {e}", file=sys.stderr)
                if "401" in str(e) or "403" in str(e):
                    raise
                break
            time.sleep(1.1)
            for x in items:
                name = x.get("itemName", "")
                if not name or not ok(name, cat, ng_common):
                    continue
                k = core(name)
                price = int(x.get("itemPrice") or 0)
                row = {"name": name[:120], "price": price, "image": image(x), "shop": x.get("shopName", ""),
                       "url": x.get("affiliateUrl") or x.get("itemUrl", ""), "reviews": int(x.get("reviewCount") or 0),
                       "rate": float(x.get("reviewAverage") or 0), "available": int(x.get("availability", 1) or 0)}
                g = groups.get(k)
                if not g:
                    groups[k] = {**row, "shops": 1}
                else:
                    g["shops"] += 1
                    g["reviews"] += row["reviews"]
                    if row["available"] and (not g["available"] or (price and price < g["price"])):
                        keep = g["shops"], g["reviews"]
                        g.update(row)
                        g["shops"], g["reviews"] = keep
            if len(items) < 30:
                break
    rows = sorted(groups.values(), key=lambda r: (-r["available"], -r["shops"], -r["reviews"]))
    return rows[: cat.get("max", 40)]


def main():
    conf = json.loads(CONF.read_text(encoding="utf-8"))
    if not (os.environ.get("RAKUTEN_APP_ID") and os.environ.get("RAKUTEN_ACCESS_KEY")):
        print("楽天APIのカギがないので、カタログは更新しません")
        return 0
    aff = os.environ.get("RAKUTEN_AFFILIATE_ID", "").strip() or DEFAULT_AFF
    old = {}
    if OUT.exists():
        try:
            old = {c["id"]: c for c in json.loads(OUT.read_text(encoding="utf-8")).get("categories", [])}
        except Exception:
            old = {}
    out = []
    for cat in conf["categories"]:
        try:
            items = collect(cat, conf.get("ng_common", []), aff)
        except Exception as e:
            print(f"[stop] 楽天APIのカギか許可サイトの設定を確認してください: {e}", file=sys.stderr)
            items = []
        if not items and cat["id"] in old:          # 取れなかったら前回のまま
            out.append(old[cat["id"]])
            print(f"{cat['id']}: 取得できず、前回のまま")
            continue
        out.append({"id": cat["id"], "mode": cat["mode"], "group": cat["group"], "name": cat["name"], "items": items})
        print(f"{cat['id']} {cat['name']}: {len(items)}商品")
    OUT.write_text(json.dumps({"updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"), "source": "楽天市場", "categories": out},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
