"""メルカリの「売り切れ・新しい順」から、カード1枚売り（シングル）の直近3件を拾って平均を出すロボット。

使い方:  python bot/mercari_souba.py
入力:    bot/cards.json   （調べるカードの一覧。型番や検索ワードを書く）
出力:    site/souba.json  （サイトが読む相場データ）

しくみ:
  1. 本物のブラウザ（Chromium）でメルカリの検索ページを開く（ログインはしない）
  2. ページが裏で受け取る検索結果データ（JSON）を横から読む
  3. タイトルに型番が入っていて、まとめ売り・セット売りではないものだけ残す
  4. 新しい順に3件取って平均する
メルカリに負担をかけないよう、1カードごとに数秒あけて、1日1回だけ動かす前提。
"""
import json
import random
import re
import statistics
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "bot" / "cards.json"
SEALS = ROOT / "bot" / "seal_items.json"   # シールも同じやり方で相場を取る（1シート売りの直近3件）
OUT = ROOT / "site" / "souba.json"
JST = timezone(timedelta(hours=9))
TAKE = 3            # 直近何件で平均するか
MAX_CARDS = 150     # 1回の実行で調べる上限（やりすぎ防止）

# この言葉がタイトルにあれば「1枚売り」ではないとみなして捨てる
NG_WORDS = [
    "まとめ", "セット", "BOX", "ボックス", "box", "コンプ", "大量", "引退",
    "以上", "種", "パック", "未開封品多数", "おまけ", "ファイル", "セミコンプ", "+", "＋", "&", "＆",
]
CODE_RE = re.compile(r"TNGC\d{2}-\d{2}", re.I)
MULTI_RE = re.compile(r"([2-9２-９]|\d{2,})\s*枚")   # 「3枚」「10枚」は複数（「1枚」はOK）


def search_url(q: str) -> str:
    return ("https://jp.mercari.com/search?keyword=" + quote(q)
            + "&status=sold_out&sort=created_time&order=desc")


def is_single(title: str, must: list[str]) -> bool:
    """カード1枚だけの出品かどうか"""
    t = title.replace("　", " ")
    if not all(m.lower() in t.lower() for m in must):
        return False
    if any(w.lower() in t.lower() for w in NG_WORDS):
        return False
    if MULTI_RE.search(t):
        return False
    if len(set(c.upper() for c in CODE_RE.findall(t))) > 1:   # 型番が2つ以上 = 複数枚
        return False
    return True


def pick(items: list[dict], must: list[str]) -> list[dict]:
    """検索結果（新しい順）からシングル売りの直近TAKE件を返す"""
    out = []
    for it in items:
        title = str(it.get("name", ""))
        try:
            price = int(str(it.get("price", "")).replace(",", ""))
        except ValueError:
            continue
        if price < 50:          # 送料にもならない値段は、ほぼ別物 or いたずら
            continue
        if not is_single(title, must):
            continue
        out.append({"title": title, "price": price,
                    "url": "https://jp.mercari.com/item/" + str(it.get("id", ""))})
        if len(out) >= TAKE:
            break
    return out


def summarize(card: dict, picked: list[dict]) -> dict:
    row = {"id": card["id"], "set": card["set"], "name": card["name"],
           "search": search_url(card["q"]), "n": len(picked), "items": picked}
    if picked:
        row["avg"] = round(statistics.mean(p["price"] for p in picked))
    return row


def fetch_items(page, q: str) -> list[dict]:
    """検索ページを開き、ページが受け取る検索結果JSONを横取りする"""
    got: list[dict] = []

    def on_response(res):
        if "entities:search" in res.url and res.request.method == "POST":
            try:
                got.extend(res.json().get("items", []))
            except Exception:
                pass

    page.on("response", on_response)
    try:
        page.goto(search_url(q), wait_until="networkidle", timeout=45000)
        for _ in range(30):          # 結果が届くまで最大15秒待つ
            if got:
                break
            page.wait_for_timeout(500)
    finally:
        page.remove_listener("response", on_response)
    return got


def main() -> int:
    from playwright.sync_api import sync_playwright

    cards = json.loads(CARDS.read_text(encoding="utf-8"))[:MAX_CARDS]
    seals = []
    if SEALS.exists():
        for x in json.loads(SEALS.read_text(encoding="utf-8")):
            seals.append({"id": x["id"], "set": "seal", "name": x.get("rk", x["id"]), "q": x.get("mq") or x["rk"], "must": x.get("must", []), "seal": True})
    old = {}
    if OUT.exists():
        try:
            j = json.loads(OUT.read_text(encoding="utf-8"))
            old = {r["id"]: r for r in j.get("cards", []) + j.get("seals", [])}
        except Exception:
            old = {}

    rows, srows, ok, fail = [], [], 0, 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(locale="ja-JP", viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        for c in cards + seals:
            try:
                items = fetch_items(page, c["q"])
                if not items:                       # 取れなかったら少し待って1回だけやり直す
                    page.wait_for_timeout(5000)
                    items = fetch_items(page, c["q"])
                if not items:
                    raise RuntimeError("検索結果が取れなかった")
                row = summarize(c, pick(items, c["must"]))
                row["checked"] = datetime.now(JST).strftime("%Y-%m-%d")
                ok += 1
            except Exception as e:  # 取れなかったら前回の数字を残す
                print(f"[skip] {c['id']}: {e}", file=sys.stderr)
                row = old.get(c["id"]) or summarize(c, [])
                fail += 1
            (srows if c.get("seal") else rows).append(row)
            print(f"{c['id']} {c['name']}: {row.get('avg', '-')}円 ({row['n']}件)")
            time.sleep(random.uniform(4, 8))
        browser.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "rule": f"メルカリの売り切れ・新しい順から、1枚売りの直近{TAKE}件の平均",
        "cards": rows,
        "seals": srows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"done: 成功{ok} / 失敗{fail}")
    # 全部失敗したらエラーで知らせる（メルカリに弾かれた合図）
    return 1 if (cards or seals) and ok == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
