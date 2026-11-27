"""トレカ抽選ナビ側（card-lottery-bot）が集めた情報から、ガールズホビー向けのものだけを取り出す。

使い方: python bot/export_hobby.py <card-lottery-botのstate/gameフォルダ> <出力するjson>
・抽選／先着／再販（ボンボンドロップシール・たまごっち・ちいかわ・サンリオ など）
・たまごっち本体の買取価格（家電市場・ケータイゴッドなどの買取表）
"""
import json
import re
import sys
from pathlib import Path

KW = re.compile(r"ボンボンドロップ|ボンドロ|たまごっち|Tamagotchi|ちいかわ|サンリオ|プリキュア|アイカツ|アイプリ|にじさんじ|にじなな|シール")
NG = re.compile(r"ポケモンカード|ポケカ|ワンピース|ガンダム|ガンプラ")


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def main(src, out):
    src = Path(src)
    lots = []
    for k, v in (load(src / "lotteries.json") or {}).items():
        t = f"{v.get('product','')} {v.get('series','')}"
        if KW.search(t) and not NG.search(t):
            lots.append({k2: v.get(k2) for k2 in ("product", "series", "store", "kind", "start", "end", "announce", "method", "conditions", "price", "url", "channel")})
    for k, v in (load(src / "lottery_pages.json") or {}).items():
        s = v.get("snap") or {}
        t = f"{s.get('product','')} {s.get('series','')}"
        if KW.search(t) and not NG.search(t):
            row = {k2: s.get(k2) for k2 in ("product", "series", "store", "kind", "start", "end", "announce", "method", "conditions", "price", "url", "channel")}
            row["facts"] = s.get("facts") or []
            if not any(x["product"] == row["product"] and x["store"] == row["store"] for x in lots):
                lots.append(row)
    kai = []
    for shop, v in (load(src / "kaitori_multi.json") or {}).items():
        for it in v.get("items", []):
            if re.search(r"たまごっち|Tamagotchi", it[0]) and it[2]:
                kai.append({"shop": shop, "name": it[0], "jan": it[1], "price": it[2], "at": (v.get("at") or "")[:10]})
    Path(out).write_text(json.dumps({"lotteries": lots, "kaitori": kai}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"抽選・発売情報 {len(lots)}件、たまごっち本体の買取 {len(kai)}件")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
