"""シールの抽選・再販・新作を無料で見張るロボット（X と AI は使わない）。

1. Googleニュース（RSS・無料）で「ボンボンドロップシール 抽選」などを検索して新しい記事を拾う
2. 公式ページ（クーリア公式ストア・ロフトの抽選ページなど）を見に行き、中身が変わったら「更新あり」として拾う
3. タイトルから「抽選／再販／新作」の種類と、「○月○日」の日付をルールで読み取る（AIは使わない）
出力: site/seal_news.json（サイトのシール画面に「新着ニュース」として出す。くわしくはリンク先へ）
一般の人の店舗目撃情報は拾わない（ニュースと公式ページだけ）。
"""
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "bot" / "seal_sources.json"
OUT = ROOT / "site" / "seal_news.json"
JST = timezone(timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (girlshobby seal watcher)"}
KEEP_DAYS = 45
QUERIES = ["ボンボンドロップシール 抽選", "ボンボンドロップシール 再販", "ボンボンドロップシール 発売", "ボンドロ 抽選販売",
           "たまごっち シール 発売", "サンリオ シール 発売 ぷっくり"]
NG = ["転売", "逮捕", "事件", "トラブル", "ケガ", "開店アタック", "偽物", "詐欺"]   # 事件系の記事はシール情報として出さない


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def kind(title):
    if re.search(r"抽選|応募|当選", title):
        return "抽選"
    if re.search(r"再販|再入荷|再生産", title):
        return "再販"
    if re.search(r"発売|新作|登場|予約", title):
        return "新作"
    return "ニュース"


def dates(title):
    return [f"{int(m)}月{int(d)}日" for m, d in re.findall(r"(\d{1,2})月(\d{1,2})日", title)][:3]


def news():
    out = []
    for q in QUERIES:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q + " when:14d", "hl": "ja", "gl": "JP", "ceid": "JP:ja"})
        try:
            root = ET.fromstring(get(url))
        except Exception as e:
            print(f"[skip] ニュース「{q}」: {e}", file=sys.stderr)
            continue
        for it in root.iter("item"):
            title = html.unescape(it.findtext("title") or "")
            link = it.findtext("link") or ""
            src = it.findtext("source") or ""
            try:
                pub = parsedate_to_datetime(it.findtext("pubDate")).astimezone(JST)
            except Exception:
                pub = datetime.now(JST)
            if not title or any(w in title for w in NG):
                continue
            # 末尾の「 - 媒体名」をはずす
            if src and title.endswith(" - " + src):
                title = title[: -len(" - " + src)]
            out.append({"id": hashlib.md5(title.encode()).hexdigest()[:12], "title": title, "url": link, "source": src or "ニュース",
                        "kind": kind(title), "dates": dates(title), "at": pub.strftime("%Y-%m-%d %H:%M"), "from": "news"})
        time.sleep(1)
    return out


def page_text(raw):
    s = raw.decode("utf-8", "replace")
    s = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def pages(state):
    out = []
    try:
        conf = json.loads(SRC.read_text(encoding="utf-8"))
    except Exception:
        return out
    for p in conf.get("official_pages", []):
        url = p.get("url")
        if not url:
            continue
        try:
            text = page_text(get(url))
        except Exception as e:
            print(f"[skip] {p['name']}: {e}", file=sys.stderr)
            continue
        h = hashlib.md5(text.encode()).hexdigest()
        before = state.get(url)
        state[url] = h
        if before and before != h:          # 前回と中身が変わった
            now = datetime.now(JST)
            out.append({"id": "pg-" + h[:10], "title": f"{p['name']}のページが更新されました", "url": url, "source": p["name"],
                        "kind": "公式の更新", "dates": [], "at": now.strftime("%Y-%m-%d %H:%M"), "from": "official"})
        time.sleep(1)
    return out


def main():
    old = {"items": [], "pages": {}}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            pass
    state = old.get("pages", {})
    items = {x["id"]: x for x in old.get("items", [])}
    for x in news() + pages(state):
        items.setdefault(x["id"], x)
    limit = (datetime.now(JST) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    rows = sorted([x for x in items.values() if x["at"][:10] >= limit], key=lambda x: x["at"], reverse=True)[:80]
    OUT.write_text(json.dumps({"updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"), "items": rows, "pages": state},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"シールの新着: {len(rows)}件（抽選 {sum(1 for r in rows if r['kind'] == '抽選')}件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
