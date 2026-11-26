// 検索に出るための「弾ごと・シールごとの相場ページ」を作る（Google は #dan-○○ のページを別ページとして扱わないため）
// 使い方: node tools/build_pages.mjs   （PUBLIC_URL にサイトの公開URLを入れると sitemap.xml と正規URLも作る）
// 入力: site/index.html の中のデータ（ITEMS・CARDS・SEALS など）と site/souba.json（あれば）
// 出力: site/card/<弾id>/index.html, site/card/index.html, site/seal/<id>/index.html, site/seal/index.html, sitemap.xml, robots.txt
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const SITE = path.join(ROOT, "site");
const PUB = (process.env.PUBLIC_URL || "").replace(/\/+$/, "");
const html = fs.readFileSync(path.join(SITE, "index.html"), "utf8");
const css = html.match(/<style>([\s\S]*?)<\/style>/)[1];
const sprite = (html.match(/<svg class="sprite"[\s\S]*?<\/svg>/) || [""])[0];
const dataSrc = html.slice(html.indexOf("const TITLES="), html.indexOf("\nconst $="));
const D = new vm.Script(dataSrc + ";({TITLES,ITEMS,CARDS,AFF,STITLES,SEALS,SLOTS})").runInNewContext({});
let MC = {};
try { MC = JSON.parse(fs.readFileSync(path.join(SITE, "souba.json"), "utf8")); } catch {}
let CAT = { categories: [] };
try { CAT = JSON.parse(fs.readFileSync(path.join(SITE, "catalog.json"), "utf8")); } catch {}
let IMGS = {}, SIMGS = {};
try { IMGS = JSON.parse(fs.readFileSync(path.join(SITE, "img/index.json"), "utf8")); } catch {}
try { SIMGS = JSON.parse(fs.readFileSync(path.join(SITE, "img/seal/index.json"), "utf8")); } catch {}

const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const yen = n => Number(n).toLocaleString("ja-JP") + "円";
const rkw = u => D.AFF.rakuten ? "https://hb.afl.rakuten.co.jp/hgc/" + D.AFF.rakuten + "/?pc=" + encodeURIComponent(u) + "&m=" + encodeURIComponent(u) : u;
const amz = n => "https://www.amazon.co.jp/s?k=" + encodeURIComponent(n) + (D.AFF.amazon ? "&tag=" + D.AFF.amazon : "");
const rkm = n => rkw("https://search.rakuten.co.jp/search/mall/" + encodeURIComponent(n) + "/");
const rkb = n => rkw("https://books.rakuten.co.jp/search?sitem=" + encodeURIComponent(n));
const merc = n => "https://jp.mercari.com/search?keyword=" + encodeURIComponent(n) + "&status=sold_out&sort=created_time&order=desc";
const tname = id => (D.TITLES.find(x => x.id === id) || {}).n || "";
const sname = id => (D.STITLES.find(x => x.id === id) || {}).n || "";
const ic = n => `<svg class="ic" aria-hidden="true"><use href="#i-${n}"/></svg>`;
const medal = n => `<span class="medal${n < 3 ? " m" + (n + 1) : ""}" aria-label="${n + 1}位">${n + 1}</span>`;
const today = new Date(); const ymd = today.toISOString().slice(0, 10);
const label = it => { if (!it.d) return "調べ中"; const p = it.d.split("-").map(Number); return p.length === 3 ? `${p[0]}年${p[1]}月${p[2]}日` : `${p[0]}年${p[1]}月${it.late ? "下旬" : ""}`; };
const released = it => { if (!it.d) return true; const p = it.d.split("-").map(Number); const dt = new Date(p[0], p[1] - 1, p[2] || (it.late ? 21 : 1)); return dt <= today; };
const mcCard = (sid, c) => (MC.cards || []).find(x => x.id === (/^S?TNGC/.test(c.code) ? c.code : sid + "-" + c.code) && x.avg) || null;
const mcSeal = id => (MC.seals || []).find(x => x.id === id && x.avg) || null;

function page({ title, desc, url, depth, theme, body, ld }) {
  const up = "../".repeat(depth);
  return `<!DOCTYPE html>
<html lang="ja" data-t="${theme}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
${PUB ? `<link rel="canonical" href="${esc(PUB + url)}">` : ""}
<meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(desc)}"><meta property="og:type" content="article">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&family=Zen+Maru+Gothic:wght@500;700&display=swap" rel="stylesheet">
<style>${css}
body{padding-bottom:40px}.crumb{font-size:14px;color:var(--sub);margin:16px 0 0}.crumb a{color:var(--ac-ink);font-weight:700}
.sum{background:var(--card);border:2px solid var(--rule);border-radius:18px;padding:14px 16px;margin:14px 0}.sum p{margin:.3em 0}
.links{display:grid;gap:10px}.links a{display:flex;justify-content:space-between;align-items:center;gap:8px;background:var(--card);border:2px solid var(--rule);border-radius:16px;padding:12px 14px;text-decoration:none;font-weight:700;min-height:52px}
.links small{color:var(--sub);font-weight:500}</style>
${ld ? `<script type="application/ld+json">${JSON.stringify(ld).replace(/</g, "\\u003c")}</script>` : ""}
</head>
<body>
${sprite}
<header class="top"><div class="wrap toprow"><a class="brand" href="${up}"><span><b>ガールズホビー.com</b><small>女の子に人気のカード・シールの発売日・相場・抽選まとめ</small></span></a></div></header>
<main class="wrap">${body}</main>
<footer><div class="wrap">
<p>当サイトは楽天アフィリエイト・Amazonアソシエイトを利用しています。リンク先で購入されると、当サイトに紹介料が入ることがあります。</p>
<p>相場は取引例をもとにした目安です。売買の前に必ずお店・フリマで最新の値段を確認してください。商品画像の著作権は各メーカーに帰属します。商品名・キャラクター名は各権利者の商標または登録商標です。</p>
<p><a href="${up}card/">カードの相場一覧</a>　<a href="${up}seal/">シールの相場一覧</a>　<a href="${up}shop/">通販で買える商品</a>　<a href="${up}calendar/">発売カレンダー</a>　${SERIES.map(x => `<a href="${up}series/${x.slug}/">${esc(x.title)}</a>`).join("　")}　© ガールズホビー.com（girlshobby.com）</p>
</div></footer>
</body></html>`;
}

function write(rel, s) { const f = path.join(SITE, rel); fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, s); }
const urls = ["/"];

// ===== シリーズ（歴代まとめ） =====
const SERIES = [
  { slug: "precure-wafer", key: "プリキュアカードウエハース", t: "pre", title: "プリキュアカードウエハース 歴代一覧" },
  { slug: "sanrio-wafer", key: "サンリオキャラクターズウエハース", t: "sanrio", title: "サンリオキャラクターズ ウエハース 歴代一覧" },
  { slug: "aikatsu-encore", key: "アイカツ！アンコール", t: "aikatsu", title: "アイカツ！アンコール 弾一覧・カードリスト・相場" },
  { slug: "gotchi-card", key: "たまごっちにゅー！ごっちカード", t: "tama", title: "たまごっち にゅー！ごっちカード 歴代一覧" },
];
const skey = it => it.name.replace(/\s/g, "").replace(/（パック）$/, "").replace(/\d+弾?$/, "");
const dkey = it => { if (!it.d) return "0000-00-00"; const p = it.d.split("-"); return p[0] + "-" + p[1] + "-" + (p[2] || (it.late ? "21" : "01")); };
const seriesOf = it => SERIES.find(x => skey(it) === x.key) || null;
const members = sr => D.ITEMS.filter(it => seriesOf(it) === sr).sort((a, b) => dannum(a) - dannum(b));
const dannum = it => { const m = it.name.replace(/（パック）$/, "").match(/(\d+)弾?$/); return m ? Number(m[1]) : 1; };
const faqHtml = qa => `<section class="sec"><h2 class="h"><span class="hi">${ic("info")}</span><span class="tx">よくある質問</span></h2><div class="rules">${qa.map(([q, a]) => `<details class="past" open><summary>${esc(q)}</summary><p>${esc(a)}</p></details>`).join("")}</div></section>`;
const faqLd = qa => ({ "@context": "https://schema.org", "@type": "FAQPage", mainEntity: qa.map(([q, a]) => ({ "@type": "Question", name: q, acceptedAnswer: { "@type": "Answer", text: a } })) });

// ===== カード（弾ごと） =====
const cardList = [];
for (const it of D.ITEMS) {
  const S = D.CARDS[it.id] || { total: it.kinds || 0, cards: [] };
  const rows = S.cards.map(c => { const m = mcCard(it.id, c); return { ...c, m, val: m ? m.avg : 0 }; }).filter(c => c.m).sort((a, b) => b.val - a.val);  // メルカリで売れた記録があるカードだけ
  const topR = rows[0];
  const total = S.total || it.kinds || 0;
  const hasRank = rows.length > 0;
  const title = hasRank ? `${it.name} 相場ランキング【全${total || "？"}種・買取/メルカリ価格】` : `${it.name} 発売日・予約・相場【${label(it)}】`;
  const desc = hasRank
    ? `${it.name}のシングルカード相場を高い順にランキング。いちばん高いのは${topR.code} ${topR.name}の${yen(topR.val)}。メルカリで実際に売れた直近の値段を${ymd}時点でまとめています。`
    : `${it.name}（${label(it)}発売${released(it) ? "" : "予定"}）の発売日・価格・予約できるお店・相場をまとめています。`;
  const pre = !released(it);
  // よくある質問（データにあることだけで答える）
  const qa = [[`${it.name}の発売日はいつ？`, `${label(it)}${pre ? "に発売予定です" : "に発売されました"}。${it.maker ? "メーカーは" + it.maker + "です。" : ""}`]];
  if (total) qa.push([`${it.name}は全何種？`, `全${total}種です。`]);
  if (it.price) qa.push([`${it.name}の値段は？`, `${it.price}です（定価・参考価格）。`]);
  qa.push([`${it.name}はどこで売ってる？`, `${it.where || "おもちゃ売り場・お菓子売り場など"}で販売されています。通販ではAmazon・楽天ブックス・楽天市場で${pre ? "予約" : "さがす"}ことができます。`]);
  if (hasRank) qa.push([`${it.name}でいちばん高いカードは？`, `${topR.code} ${topR.name}で、${yen(topR.val)}です（${topR.m ? "メルカリで最近売れた" + topR.m.n + "件の平均" : topR.shop.src + "の" + topR.shop.k + "価格"}・${ymd}時点）。`]);
  // 同じシリーズの前後の弾
  const sr = seriesOf(it); let nav = "";
  if (sr) { const ms = members(sr), i = ms.indexOf(it), pv = ms[i - 1], nx = ms[i + 1];
    nav = `<section class="sec"><h2 class="h"><span class="hi">${ic("cards")}</span><span class="tx">${esc(sr.title.replace(" 歴代一覧", ""))}のほかの弾</span></h2><div class="links">
${pv ? `<a href="../${esc(pv.id)}/"><span>前の弾：${esc(pv.name)}<br><small>${esc(label(pv))}</small></span>${ic("go")}</a>` : ""}
${nx ? `<a href="../${esc(nx.id)}/"><span>次の弾：${esc(nx.name)}<br><small>${esc(label(nx))}</small></span>${ic("go")}</a>` : ""}
<a href="../../series/${sr.slug}/"><span>${esc(sr.title)}（全${ms.length}弾）を見る</span>${ic("go")}</a></div></section>`; }
  const im = IMGS[it.id] && IMGS[it.id].images && IMGS[it.id].images.length ? IMGS[it.id] : null;
  const body = `<p class="crumb"><a href="../../">トップ</a> › <a href="../">カードの相場一覧</a> › ${esc(tname(it.t))}</p>
<div class="dan-h"><div class="tags"><span class="tag">${ic("star")}${esc(tname(it.t))}</span></div><h1>${esc(title)}</h1>
<p>${esc(label(it))}発売${pre ? "予定" : ""}・全${esc(total || "？")}種${it.maker ? "・" + esc(it.maker) : ""}${it.price ? "・" + esc(it.price) : ""}</p><p class="legend">最終更新：${ymd}</p></div>
${im ? `<div class="gal">${im.images.map((u, k) => `<img src="../../${esc(u)}" alt="${esc(it.name)} 商品画像${k + 1}" loading="lazy">`).join("")}</div><p class="gal-cap">画像出典：<a href="${esc(im.source)}" rel="nofollow">バンダイ公式</a>　©BANDAI</p>` : ""}
<div class="sum">${hasRank ? `<p><b>いちばん高いカード：</b>${esc(topR.code)} ${esc(topR.name)}（${yen(topR.val)}）</p><p>相場がわかっているカード：${rows.length}枚／全${esc(total || "？")}種</p>` : ""}<p>${esc(it.note || "")}</p></div>
<div class="shopbox" id="shops"><h2>${ic("bag")}${pre ? "この商品を予約できるお店" : "この商品を買えるお店"}</h2>
<div class="main"><a class="btn az" href="${amz(it.jan || it.name)}" rel="nofollow sponsored">${ic("bag")}Amazonで${pre ? "予約" : "買う"}</a><a class="btn rk" href="${rkb(it.name)}" rel="nofollow sponsored">${ic("bag")}楽天ブックスで${pre ? "予約" : "買う"}</a></div>
<div class="sub-btns"><a class="btn rk" href="${rkm(it.name)}" rel="nofollow sponsored">楽天市場でさがす</a><a class="btn mc" href="${merc(it.name)}" rel="nofollow">メルカリで売れた値段</a></div></div>
${hasRank ? `<section class="sec"><h2 class="h"><span class="hi">${ic("crown")}</span><span class="tx">${esc(it.name)} シングル相場ランキング</span></h2>
<p class="legend">メルカリで最近売れた1枚売りの平均（直近3件）があればそれを、なければお店の値段を使っています。値段の種類と出典はカードごとに書いています。</p>
<div class="rank">${rows.map((c, n) => {
    const q = /^S?TNGC/.test(c.code) ? c.code : it.name + " " + c.code + " " + c.name.split(" ")[0];
    const main = c.m ? `<b>${yen(c.m.avg)}</b><small><span class="kk メルカリ">メルカリ</span>直近${Number(c.m.n)}件平均</small>` : (c.shop ? `<b>${yen(c.shop.p)}</b><small><span class="kk ${esc(c.shop.k)}">${esc(c.shop.k)}</span>${esc(c.shop.src)}</small>` : "<b>－</b>");
    return `<div class="crow${n < 3 ? " top3" : ""}">${medal(n)}<div class="ph">${ic("star")}<img src="../../img/${encodeURIComponent(it.id)}/${encodeURIComponent(c.code)}.jpg" alt="${esc(c.code)} ${esc(c.name)}" loading="lazy" onerror="this.remove()"></div><div class="cb"><span class="code">${esc(c.code)}</span><p>${esc(c.name)}</p></div><div class="pr">${main}</div><a class="ml" href="${merc(q)}" rel="nofollow">メルカリで売れた値段を見る${ic("go")}</a></div>`;
  }).join("")}</div></section>` : ""}
${faqHtml(qa)}
${nav}
<p style="margin-top:22px"><a class="btn line" href="../../#dan-${esc(it.id)}">サイトで見る（持ってる記録・ほかの弾）${ic("go")}</a></p>`;
  const ld = [faqLd(qa), { "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: [
      { "@type": "ListItem", position: 1, name: "トップ", item: PUB ? PUB + "/" : undefined },
      { "@type": "ListItem", position: 2, name: "カードの相場一覧", item: PUB ? PUB + "/card/" : undefined },
      { "@type": "ListItem", position: 3, name: it.name }] }];
  if (hasRank) ld.push({ "@context": "https://schema.org", "@type": "ItemList", name: `${it.name} 相場ランキング`, itemListElement: rows.slice(0, 20).map((c, n) => ({ "@type": "ListItem", position: n + 1, name: `${c.code} ${c.name}` })) });
  const url = `/card/${it.id}/`;
  write(`card/${it.id}/index.html`, page({ title: title + "｜ガールズホビー.com", desc, url, depth: 2, theme: it.t, body, ld }));
  urls.push(url); cardList.push({ it, rows, total, topR });
}
write("card/index.html", page({ title: "女の子に人気のカード 相場一覧（たまごっち・プリキュア・サンリオ）｜ガールズホビー.com",
  desc: "たまごっちカード・プリキュアカードウエハース・サンリオウエハースなどの弾ごとの相場ランキングと発売日の一覧。", url: "/card/", depth: 1, theme: "all",
  body: `<p class="crumb"><a href="../">トップ</a> › カードの相場一覧</p><div class="dan-h"><h1>カードの相場一覧</h1><p class="legend">最終更新：${ymd}</p></div>
${D.TITLES.filter(t => t.id !== "all").map(t => `<section class="sec"><h2 class="h"><span class="tx">${esc(t.n)}</span></h2><div class="links">${cardList.filter(x => x.it.t === t.id).map(x => `<a href="${esc(x.it.id)}/"><span>${esc(x.it.name)}<br><small>${esc(label(x.it))}・全${esc(x.total || "？")}種${x.topR ? "・最高 " + yen(x.topR.val) : ""}</small></span>${ic("go")}</a>`).join("")}</div></section>`).join("")}` }));
urls.push("/card/");

// ===== シール =====
const sealList = [];
for (const it of D.SEALS) {
  const m = mcSeal(it.id);
  const fixed = Number(String(it.price || "").replace(/[^0-9]/g, "")) || 0;
  const ratio = m && fixed ? (m.avg / fixed) : 0;
  const title = `${it.name} 相場・定価・発売日`;
  const desc = `${it.name}の発売日（${label(it)}）・定価（${it.price || "調べ中"}）${m ? `と、メルカリで最近売れた値段の平均（${yen(m.avg)}）` : ""}をまとめています。`;
  const im = SIMGS[it.id] && SIMGS[it.id].file ? SIMGS[it.id] : null;
  const pre = !released(it);
  const body = `<p class="crumb"><a href="../../">トップ</a> › <a href="../">シールの相場一覧</a> › ${esc(sname(it.t))}</p>
<div class="dan-h"><div class="tags"><span class="tag">${ic("sparkle")}${esc(sname(it.t))}</span></div><h1>${esc(title)}</h1><p>${esc(label(it))}発売${pre ? "予定" : ""}${it.maker ? "・" + esc(it.maker) : ""}</p><p class="legend">最終更新：${ymd}</p></div>
${im ? `<div class="gal"><img src="../../${esc(im.file)}" alt="${esc(it.name)}" loading="lazy"></div><p class="gal-cap">画像出典：<a href="${esc(im.source)}" rel="nofollow">${esc(im.kind || "公式")}</a></p>` : ""}
<div class="sum"><p><b>定価：</b>${esc(it.price || "調べ中")}</p>${m ? `<p><b>メルカリ相場：</b>${yen(m.avg)}（最近売れた${Number(m.n)}件の平均${ratio ? `・定価の約${ratio.toFixed(1)}倍` : ""}）</p><p class="legend">${(m.items || []).map(x => yen(x.price)).join(" / ")}</p>` : `<p><b>メルカリ相場：</b>まだ集計前です</p>`}<p><b>売り場：</b>${esc(it.where)}</p><p>${esc(it.note)}</p><p class="src">情報のもと：<a href="${esc(it.src.u)}" rel="nofollow">${esc(it.src.n)}</a></p></div>
<div class="shopbox t-seal"><h2>${ic("bag")}${it.book && pre ? "この商品を予約できるお店" : "この商品を買えるお店"}</h2>
<div class="main"><a class="btn az" href="${amz(it.name)}" rel="nofollow sponsored">${ic("bag")}Amazon${it.book ? (pre ? "で予約" : "で買う") : "でさがす"}</a><a class="btn rk" href="${it.book ? rkb(it.name) : rkm(it.name)}" rel="nofollow sponsored">${ic("bag")}${it.book ? "楽天ブックス" : "楽天市場"}${it.book ? (pre ? "で予約" : "で買う") : "でさがす"}</a></div>
<div class="sub-btns"><a class="btn line" href="${esc(it.src.u)}" rel="nofollow">公式の案内を見る</a><a class="btn mc" href="${merc(it.name)}" rel="nofollow">メルカリで売れた値段</a></div></div>
<p style="margin-top:22px"><a class="btn line" href="../../#seal-${esc(it.id)}">サイトで見る（抽選・新作）${ic("go")}</a></p>`;
  const url = `/seal/${it.id}/`;
  write(`seal/${it.id}/index.html`, page({ title: title + "｜ガールズホビー.com", desc, url, depth: 2, theme: "seal", body,
    ld: { "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: "トップ" }, { "@type": "ListItem", position: 2, name: "シールの相場一覧" }, { "@type": "ListItem", position: 3, name: it.name }] } }));
  urls.push(url); sealList.push({ it, m });
}
write("seal/index.html", page({ title: "ボンボンドロップなど人気シールの相場・発売日一覧｜ガールズホビー.com",
  desc: "ボンボンドロップシールやたまごっちのシールなど、女の子に人気のシールの定価・メルカリ相場・発売日の一覧。", url: "/seal/", depth: 1, theme: "seal",
  body: `<p class="crumb"><a href="../">トップ</a> › シールの相場一覧</p><div class="dan-h"><h1>シールの相場・発売日一覧</h1><p class="legend">最終更新：${ymd}</p></div>
<div class="links">${sealList.map(x => `<a href="${esc(x.it.id)}/"><span>${esc(x.it.name)}<br><small>${esc(label(x.it))}・定価 ${esc(x.it.price || "調べ中")}${x.m ? "・相場 " + yen(x.m.avg) : ""}</small></span>${ic("go")}</a>`).join("")}</div>` }));
urls.push("/seal/");

// ===== シリーズのまとめページ =====
for (const sr of SERIES) {
  const ms = members(sr); if (!ms.length) continue;
  const rel = ms.filter(released), up = ms.filter(x => !released(x));
  const first = ms[0], lastR = rel[rel.length - 1];
  const rng = ms.length > 1 ? `第${dannum(first)}弾〜第${dannum(ms[ms.length - 1])}弾` : `第${dannum(first)}弾`;
  const title = `${sr.title}【${rng}】発売日・種類数・相場まとめ`;
  const row = it => { const c = cardList.find(x => x.it === it); return `<a href="../../card/${esc(it.id)}/"><span>${esc(it.name)}<br><small>${esc(label(it))}${released(it) ? "発売" : "発売予定"}・全${esc(c && c.total || it.kinds || "？")}種${it.price ? "・" + esc(it.price) : ""}${c && c.topR ? "・最高 " + yen(c.topR.val) : ""}</small></span>${ic("go")}</a>`; };
  const qa = [[`${sr.key.replace("サンリオキャラクターズ", "サンリオキャラクターズ ")}は今まで何弾出ている？`, `${ymd}時点で、当サイトでは${rel.length}弾の発売を確認しています${up.length ? `（ほかに${up.length}弾が発売予定）` : ""}。最初の弾は${label(first)}発売です。`]];
  if (lastR) qa.push(["最新の弾は？", `発売済みでいちばん新しいのは${lastR.name}（${label(lastR)}発売）です。${up[0] ? `次は${up[0].name}が${label(up[0])}に発売予定です。` : ""}`]);
  write(`series/${sr.slug}/index.html`, page({ title: title + "｜ガールズホビー.com",
    desc: `${sr.title.replace(" 歴代一覧", "")}の第${dannum(first)}弾から最新弾までの発売日・価格・種類数・相場を一覧にまとめました。${up[0] ? `次は${up[0].name}（${label(up[0])}発売予定）。` : ""}`,
    url: `/series/${sr.slug}/`, depth: 2, theme: sr.t,
    body: `<p class="crumb"><a href="../../">トップ</a> › <a href="../../card/">カードの相場一覧</a> › ${esc(sr.title)}</p><div class="dan-h"><h1>${esc(title)}</h1><p class="legend">最終更新：${ymd}</p></div>
${up.length ? `<section class="sec"><h2 class="h"><span class="tx">これから発売</span></h2><div class="links">${up.map(row).join("")}</div></section>` : ""}
<section class="sec"><h2 class="h"><span class="tx">発売済みの弾（新しい順）</span></h2><div class="links">${rel.slice().reverse().map(row).join("")}</div></section>${faqHtml(qa)}`,
    ld: [faqLd(qa), { "@context": "https://schema.org", "@type": "ItemList", name: sr.title, itemListElement: ms.map((it, n) => ({ "@type": "ListItem", position: n + 1, name: it.name, url: PUB ? PUB + "/card/" + it.id + "/" : undefined })) }] }));
  urls.push(`/series/${sr.slug}/`);
}

// ===== 月別の発売カレンダーページ =====
const allRel = [...D.ITEMS.map(it => ({ it, kind: "card" })), ...D.SEALS.map(it => ({ it, kind: "seal" }))].filter(x => x.it.d);
const months = [...new Set(allRel.map(x => x.it.d.slice(0, 7)))].sort();
const recentMonths = months.filter(m => m >= "2025-01");
for (const m of recentMonths) {
  const [y, mo] = m.split("-").map(Number);
  const xs = allRel.filter(x => x.it.d.startsWith(m)).sort((a, b) => dkey(a.it).localeCompare(dkey(b.it)));
  const i = months.indexOf(m), pv = months[i - 1], nx = months[i + 1];
  const li = x => `<a href="../../${x.kind}/${esc(x.it.id)}/"><span>${esc(x.it.name)}<br><small>${x.it.d.length > 7 ? Number(x.it.d.slice(8)) + "日" : "日にち未定"}・${x.kind === "seal" ? "シール" : "カード"}${x.it.price ? "・" + esc(x.it.price) : ""}</small></span>${ic("go")}</a>`;
  write(`calendar/${m}/index.html`, page({ title: `${y}年${mo}月発売の女の子向けカード・シール一覧（${xs.length}件）｜ガールズホビー.com`,
    desc: `${y}年${mo}月に発売される・発売されたたまごっち・プリキュア・サンリオのカードや、ボンボンドロップなどのシールを日付順にまとめました。`,
    url: `/calendar/${m}/`, depth: 2, theme: "all",
    body: `<p class="crumb"><a href="../../">トップ</a> › <a href="../">発売カレンダー</a> › ${y}年${mo}月</p><div class="dan-h"><h1>${y}年${mo}月発売のカード・シール</h1><p class="legend">最終更新：${ymd}</p></div>
<div class="links">${xs.map(li).join("")}</div>
<section class="sec"><div class="links">${pv && pv >= "2025-01" ? `<a href="../${pv}/"><span>前の月（${Number(pv.slice(5))}月）</span>${ic("go")}</a>` : ""}${nx ? `<a href="../${nx}/"><span>次の月（${Number(nx.slice(5))}月）</span>${ic("go")}</a>` : ""}</div></section>` }));
  urls.push(`/calendar/${m}/`);
}
write("calendar/index.html", page({ title: "女の子向けカード・シール 発売カレンダー｜ガールズホビー.com", desc: "たまごっち・プリキュア・サンリオのカードと人気シールの発売日を月ごとにまとめた発売カレンダー。",
  url: "/calendar/", depth: 1, theme: "all",
  body: `<p class="crumb"><a href="../">トップ</a> › 発売カレンダー</p><div class="dan-h"><h1>発売カレンダー</h1></div><div class="links">${recentMonths.slice().reverse().map(m => `<a href="${m}/"><span>${m.slice(0, 4)}年${Number(m.slice(5))}月発売</span>${ic("go")}</a>`).join("")}</div>` }));
urls.push("/calendar/");

// ===== 通販カタログ（楽天市場の商品をカテゴリ別に） =====
const shopCats = (CAT.categories || []).filter(c => c.items && c.items.length);
const pcard = x => `<a class="dcard pcard" href="${esc(x.url)}" rel="nofollow sponsored"><div class="dimg">${x.image ? `<img src="${esc(x.image)}" alt="${esc(x.name)}" loading="lazy">` : ""}${x.available ? "" : '<span class="tag st done">売り切れ</span>'}</div>
<div class="dbody"><b class="pn">${esc(x.name)}</b><small>${esc(x.shop)}${x.shops > 1 ? `（ほか${x.shops - 1}店）` : ""}</small><span class="top">${x.price ? yen(x.price) : "価格はお店で"}</span><span class="more">${x.mall === "amazon" ? "Amazonで" : "楽天で"}見る${ic("go")}</span></div></a>`;
const pcss = `.pcard .dimg img{object-fit:contain;background:#fff}.pn{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}`;
for (const c of shopCats) {
  const url = `/shop/${c.id}/`;
  const title = `${c.name}の通販・一覧（${c.items.length}商品）`;
  const lowest = c.items.filter(x => x.price).sort((a, b) => a.price - b.price)[0];
  write(`shop/${c.id}/index.html`, page({ title: title + "｜ガールズホビー.com",
    desc: `${c.name}を楽天市場からまとめて${c.items.length}商品掲載。${lowest ? `いちばん安いのは${yen(lowest.price)}から。` : ""}発売済みの商品も新作も、価格と売っているお店をチェックできます。`,
    url, depth: 2, theme: c.mode === "seal" ? "seal" : (c.group === "all" ? "all" : c.group),
    body: `<style>${pcss}</style><p class="crumb"><a href="../../">トップ</a> › <a href="../">通販で買える商品</a> › ${esc(c.name)}</p>
<div class="dan-h"><h1>${esc(title)}</h1><p class="legend">楽天市場・Amazonの商品を${esc(CAT.updated || ymd)}時点でまとめています。同じ商品を売っているお店が複数あるときは、いちばん安いお店を表示しています。価格・在庫はリンク先で確認してください。</p></div>
<div class="dgrid">${c.items.map(pcard).join("")}</div>
<p class="legend" style="margin-top:18px">商品情報・画像の出典：楽天市場</p>` }));
  urls.push(url);
}
if (shopCats.length) {
  const grp = m => shopCats.filter(c => c.mode === m).map(c => `<a href="${esc(c.id)}/"><span>${esc(c.name)}<br><small>${c.items.length}商品</small></span>${ic("go")}</a>`).join("");
  write("shop/index.html", page({ title: "女の子に人気のカード・シール 通販で買える商品一覧｜ガールズホビー.com",
    desc: "たまごっちカード・プリキュアカード・ボンボンドロップシール・シール帳などを、カテゴリ別に楽天市場からまとめています。", url: "/shop/", depth: 1, theme: "all",
    body: `<p class="crumb"><a href="../">トップ</a> › 通販で買える商品</p><div class="dan-h"><h1>通販で買える商品</h1></div>
<section class="sec"><h2 class="h"><span class="tx">カード</span></h2><div class="links">${grp("card")}</div></section>
<section class="sec"><h2 class="h"><span class="tx">シール</span></h2><div class="links">${grp("seal")}</div></section>` }));
  urls.push("/shop/");
}

// ===== トップページ（index.html）に、検索エンジンがたどれるリンク一覧を入れる =====
{
  const idxF = path.join(SITE, "index.html");
  let idx = fs.readFileSync(idxF, "utf8");
  const links = `<nav class="seo-links" aria-label="ページ一覧"><p><b>シリーズ：</b>${SERIES.map(x => `<a href="series/${x.slug}/">${esc(x.title)}</a>`).join("　")}</p>
<p><b>弾ごとの相場：</b>${cardList.map(x => `<a href="card/${esc(x.it.id)}/">${esc(x.it.name)}</a>`).join("　")}</p>
<p><b>シール：</b>${sealList.map(x => `<a href="seal/${esc(x.it.id)}/">${esc(x.it.name)}</a>`).join("　")}</p>
<p><b>発売カレンダー：</b>${recentMonths.slice().reverse().map(m => `<a href="calendar/${m}/">${m.slice(0, 4)}年${Number(m.slice(5))}月</a>`).join("　")}</p></nav>`;
  idx = idx.replace(/<!--SEO-LINKS-->[\s\S]*?<!--\/SEO-LINKS-->/, `<!--SEO-LINKS-->${links}<!--/SEO-LINKS-->`);
  if (PUB) idx = idx.replace(/<link rel="canonical"[^>]*>\n?/, "").replace("</title>", `</title>\n<link rel="canonical" href="${esc(PUB)}/">`);
  fs.writeFileSync(idxF, idx);
}

// ===== sitemap / robots =====
if (PUB) {
  write("sitemap.xml", `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map(u => `<url><loc>${esc(PUB + u)}</loc><lastmod>${ymd}</lastmod></url>`).join("\n")}\n</urlset>\n`);
  write("robots.txt", `User-agent: *\nAllow: /\nSitemap: ${PUB}/sitemap.xml\n`);
}
console.log(`pages: ${urls.length}（カード${cardList.length}・シール${sealList.length}・通販カテゴリ${shopCats.length}）${PUB ? "・sitemapあり" : "・PUBLIC_URL未設定のためsitemapなし"}`);
