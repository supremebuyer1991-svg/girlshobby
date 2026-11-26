"""メルカリの出品タイトルから、新しい弾のカード一覧（型番・名前・レア）を集める道具。
使い方: python tools/discover_cards.py STNGC01   → bot/discovered_STNGC01.json と画面に一覧
"""
import collections, json, re, sys, time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
prefix = sys.argv[1] if len(sys.argv) > 1 else "STNGC01"
RE = re.compile(prefix + r"[-‐ー－]?(\d{2})\s*[\]】]?\s*[:：]?\s*([^\s(（\[【】\]]+)\s*[\(（\[]?\s*(SGR|GR|R|N)?", re.I)
RAR = re.compile(r"\b(SGR|GR|R|N)\b")

def main():
    from playwright.sync_api import sync_playwright
    names = collections.defaultdict(collections.Counter)
    rars = collections.defaultdict(collections.Counter)
    queries = [prefix, prefix + " SGR", prefix + " GR", prefix + " R レア", prefix + " N ノーマル", "スクラッチ ごっちカード SGR", "スクラッチ ごっちカード GR"]
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_context(locale="ja-JP").new_page()
        for q in queries:
            for status in ("", "&status=sold_out"):
                got = []
                def on(res):
                    if "entities:search" in res.url and res.request.method == "POST":
                        try: got.extend(res.json().get("items", []))
                        except Exception: pass
                page.on("response", on)
                page.goto("https://jp.mercari.com/search?keyword=" + quote(q) + status, wait_until="networkidle", timeout=45000)
                for _ in range(30):
                    if got: break
                    page.wait_for_timeout(500)
                page.remove_listener("response", on)
                for it in got:
                    t = str(it.get("name", ""))
                    for m in RE.finditer(t):
                        no, nm, r = m.group(1), m.group(2), m.group(3)
                        nm = nm.strip("・:：")
                        if len(nm) >= 2:
                            names[no][nm] += 1
                        if r:
                            rars[no][r.upper()] += 1
                print(q, status or "on_sale", len(got), "件")
                time.sleep(4)
        b.close()
    out = []
    for no in sorted(names, key=int):
        out.append({"code": f"{prefix}-{no}", "name": names[no].most_common(1)[0][0],
                    "rarity": rars[no].most_common(1)[0][0] if rars[no] else "", "seen": sum(names[no].values()),
                    "alt": [n for n, _ in names[no].most_common(4)[1:]]})
    (ROOT / "bot" / f"discovered_{prefix}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for o in out:
        print(o["code"], o["name"], o["rarity"], o["seen"], o["alt"])
    print("合計", len(out), "種")

if __name__ == "__main__":
    main()
