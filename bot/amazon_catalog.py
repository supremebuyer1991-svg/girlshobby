"""Amazon（Creators API）でシールの商品を集めて、楽天のカタログ（site/catalog.json）に足すロボット。

・catalog_config.json の「mode: seal」のカテゴリを、同じ検索ワードでAmazonでも探す
・Amazonの規約に合わせ、画像は保存せずAmazonのURLのまま・商品ページ（アフィリンク）へ飛ばす。毎日取り直す
・楽天と同じ商品っぽいもの（名前がほぼ同じ）は二重に出さない
鍵：AMAZON_CREDENTIAL_ID / AMAZON_CREDENTIAL_SECRET / AMAZON_CREDENTIAL_VERSION、トラッキングID：AMAZON_PARTNER_TAG
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amazon_images import token, post, API, MARKET       # noqa: E402
from catalog import ok, core, CONF, OUT                    # noqa: E402

PAGES = int(os.environ.get("AMAZON_PAGES", "3"))          # 1ワードで何ページ（10件ずつ）


def search(tok, ver, kw, page):
    tag = (os.environ.get("AMAZON_PARTNER_TAG") or "tcgchusen-22").strip()
    auth = f"Bearer {tok}" if ver.startswith("3") else f"Bearer {tok}, Version {ver}"
    j = post(API, {"keywords": kw, "searchIndex": "All", "itemCount": 10, "itemPage": page,
                   "partnerTag": tag, "marketplace": MARKET,
                   "resources": ["images.primary.medium", "itemInfo.title", "offersV2.listings.price"]},
             {"Authorization": auth, "x-marketplace": MARKET})
    res = j.get("searchResult") or j.get("itemsResult") or {}
    return res.get("items") or []


def price_of(it):
    try:
        l = ((it.get("offersV2") or {}).get("listings") or [])[0]
        p = (l.get("price") or {}).get("money") or l.get("price") or {}
        return int(float(p.get("amount") or 0))
    except Exception:
        return 0


def main():
    if not (os.environ.get("AMAZON_CREDENTIAL_ID") and os.environ.get("AMAZON_CREDENTIAL_SECRET")):
        print("Amazonの鍵が無いのでスキップ")
        return 0
    if not OUT.exists():
        print("楽天のカタログがまだ無いのでスキップ")
        return 0
    conf = json.loads(CONF.read_text(encoding="utf-8"))
    data = json.loads(OUT.read_text(encoding="utf-8"))
    tok, ver = token()
    bycat = {c["id"]: c for c in data.get("categories", [])}
    for cat in conf["categories"]:
        if cat["mode"] != "seal":
            continue
        c = bycat.setdefault(cat["id"], {"id": cat["id"], "mode": cat["mode"], "group": cat["group"], "name": cat["name"], "items": []})
        c["items"] = [x for x in c["items"] if x.get("mall") != "amazon"]   # 前回のAmazon分は捨てて取り直す
        seen = {core(x["name"]) for x in c["items"]}
        added = 0
        for kw in cat["keywords"]:
            for page in range(1, PAGES + 1):
                try:
                    items = search(tok, ver, kw, page)
                except Exception as e:
                    print(f"[skip] {cat['id']} 「{kw}」p{page}: {e}", file=sys.stderr)
                    break
                time.sleep(1.2)
                for it in items:
                    name = (((it.get("itemInfo") or {}).get("title") or {}).get("displayValue")) or ""
                    if not name or not ok(name, cat, conf.get("ng_common", [])):
                        continue
                    k = core(name)
                    if k in seen:
                        continue
                    seen.add(k)
                    img = (((it.get("images") or {}).get("primary") or {}).get("medium") or {}).get("url", "")
                    c["items"].append({"name": name[:120], "price": price_of(it), "image": img, "shop": "Amazon",
                                       "url": it.get("detailPageURL", ""), "reviews": 0, "rate": 0, "available": 1,
                                       "shops": 1, "mall": "amazon"})
                    added += 1
                if len(items) < 10:
                    break
        c["items"] = c["items"][: cat.get("max", 100) + 100]
        print(f"{cat['id']}: Amazonから{added}商品（合計{len(c['items'])}）")
    data["categories"] = list(bycat.values())
    data["source"] = "楽天市場・Amazon"
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
