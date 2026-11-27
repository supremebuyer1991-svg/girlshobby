"""トレカ抽選ナビ側のロボットが作った「楽天・Amazonの写真一覧」を取り込む。

楽天とAmazonの鍵はトレカ抽選ナビ（card-lottery-bot）のGitHubにだけ入っているので、
あっちのロボットが毎朝この一覧を作って https://girlshobby-img.pages.dev/ に置いてくれる。
ここでは、公式（バンダイ）の写真が無いものにだけ、その写真を入れる。
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://girlshobby-img.pages.dev/"
SHOP = ("楽天ブックス", "楽天市場", "Amazon")


def get(name):
    req = urllib.request.Request(BASE + name, headers={"User-Agent": "girlshobby relay"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def merge(local_path, remote, shop_of, has_official):
    idx = json.loads(local_path.read_text(encoding="utf-8")) if local_path.exists() else {}
    n = 0
    for k, v in remote.items():
        if shop_of(v) not in SHOP:
            continue
        if has_official(idx.get(k) or {}):
            continue
        idx[k] = v
        n += 1
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    return n


def main():
    try:
        cards, seals = get("img.json"), get("seal.json")
    except Exception as e:
        print(f"[skip] 写真一覧が取れなかった: {e}", file=sys.stderr)
        return 0
    a = merge(ROOT / "site/img/index.json", cards, lambda v: v.get("credit"),
              lambda c: bool(c.get("images")) and c.get("credit") not in SHOP)
    b = merge(ROOT / "site/img/seal/index.json", seals, lambda v: v.get("kind"),
              lambda c: bool(c.get("file")) and c.get("kind") not in SHOP)
    print(f"楽天・Amazonの写真を取り込み: カード{a}弾・シール{b}個")
    try:
        rc = get("cards.json")
        lp = ROOT / "site/img/cards.json"
        mine = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {}
        for k, v in rc.items():
            if v.get("credit") in SHOP and (mine.get(k) or {}).get("credit") != "公式":
                mine[k] = v
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text(json.dumps(mine, ensure_ascii=False, indent=1), encoding="utf-8")
        print("シングルカードの写真を取り込み:", sum(1 for v in mine.values() if v.get("credit") in SHOP), "枚")
    except Exception as e:
        print(f"[skip] カード写真一覧が取れなかった: {e}", file=sys.stderr)
    try:
        cat = get("catalog.json")
        if sum(len(c.get("items", [])) for c in cat.get("categories", [])) > 0:
            (ROOT / "site/catalog.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
            print("通販カタログを取り込み:", {c["id"]: len(c["items"]) for c in cat["categories"]})
    except Exception as e:
        print(f"[skip] 通販カタログが取れなかった: {e}", file=sys.stderr)
    try:
        hb = get("hobby.json")
        if hb.get("lotteries") or hb.get("kaitori"):
            (ROOT / "site/hobby.json").write_text(json.dumps(hb, ensure_ascii=False, indent=1), encoding="utf-8")
            print("抽選・買取情報を取り込み:", len(hb.get("lotteries", [])), "件・", len(hb.get("kaitori", [])), "件")
    except Exception as e:
        print(f"[skip] 抽選・買取情報が取れなかった: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
