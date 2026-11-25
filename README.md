# ガールズホビー.com（girlshobby.com）
女の子に人気のカード・シールの発売日・相場・抽選まとめサイト。ドメインは girlshobby（予定）。

## 中身
- `site/index.html` … サイト本体
- `site/souba.json` … メルカリ相場（ロボットが毎朝自動で作る。最初はない）
- `bot/cards.json` … 相場を調べるカードの一覧
- `tools/carddata.py` … 弾ごとのカード一覧の元データ。直したら `python tools/carddata.py` でサイトとロボットに反映
- `bot/mercari_souba.py` … メルカリ相場ロボット
- `.github/workflows/souba.yml` … ロボットを毎朝5:17に動かす設定

## ロボットがやること
1. `cards.json` のカードを1枚ずつ、メルカリで「売り切れ・新しい順」に検索（ログインしない）
2. タイトルに型番が入っていて、まとめ売り・セット・「3枚」などが入っていないものだけ残す
3. 新しい順に3件取って平均 → `site/souba.json` に保存
4. 取れなかったカードは前回の数字を残す。全部取れなかった日は Actions が赤く失敗表示になる（＝メルカリに弾かれた合図）

## はじめかた
1. GitHubで新しいリポジトリを作る（**Public** にする。Actionsの時間が無料・無制限になる）
2. このフォルダの中身を全部アップロード（`.github` フォルダも忘れずに）
3. Settings → Actions → General → 一番下「Workflow permissions」を **Read and write** にして保存
4. Actions タブ → `mercari-souba` → **Run workflow** で試しに動かす
5. ログに「TNGC03-06 おやじっちスペーススタイル: ○○円 (3件)」と出れば成功

## カードを増やすとき
`bot/cards.json` に1行足す。
- `q` … メルカリで検索する言葉（たまごっちは型番がいちばん正確）
- `must` … タイトルに必ず入っていてほしい言葉（別のカードが混ざるのを防ぐ）
- `set` … サイトのどの商品のカードか

## 商品画像（バンダイ公式）
`bot/bandai_images.py` が毎朝、公式の商品ページから商品画像を集めて弾ページの上に並べます。新しい弾が出たら、このファイルの `PAGES` に「弾のID: 公式ページのURL」を1行足します。

## カード写真（1枚ずつ）
`site/img/弾のID/型番.jpg` に置くと弾ページに表示されます（例：`site/img/tama-gotchi3/TNGC03-06.jpg`）。自分で撮った写真を使ってください。

## シールの写真
`bot/seal_images.py` が毎朝、`bot/seal_items.json` のシールごとに写真を集めます。まず公式・告知ページの代表画像、なければ楽天市場の商品画像を使います。
楽天を使うには、Settings → Secrets に `RAKUTEN_APP_ID` と `RAKUTEN_ACCESS_KEY`（トレカ抽選ナビと同じもの）、Variables に `SITE_URL`（楽天アプリに登録済みのサイトURL）を入れます。

## 検索に出る相場ページ
公開のたびに `tools/build_pages.mjs` が、弾ごと（`/card/弾ID/`）とシールごと（`/seal/ID/`）の相場ページ、`sitemap.xml`、`robots.txt` を作ります。
Settings → Secrets and variables → Actions → Variables に `PUBLIC_URL`（サイトの公開URL。例 `https://kiracolle.com`）を入れると、sitemap と正規URLが入ります。公開したら Google Search Console に sitemap.xml を登録してください。

## 通販カタログ（過去の商品も）
`bot/catalog.py` が毎朝、楽天市場の商品検索APIで `bot/catalog_config.json` のカテゴリごとに商品を集め、`site/catalog.json` に保存します。公開時に `/shop/カテゴリID/` のページも作られます。カテゴリや検索ワードを増やすときは `catalog_config.json` に足します。

## シールの新着ニュース（無料）
`bot/seal_watch.py` が毎朝、Googleニュースと公式ページ（`bot/seal_sources.json` の official_pages）を見て、抽選・再販・新作の新着を `site/seal_news.json` に保存します。XやAIは使わないので無料です。

## 独自ドメイン（girlshobby.com・Cloudflare）
- Cloudflare の DNS：A レコード `@` → 185.199.108.153 / 185.199.109.153 / 185.199.110.153 / 185.199.111.153、CNAME `www` → `supremebuyer1991-svg.github.io`（すべて「DNSのみ」＝灰色の雲）
- GitHub：Settings → Pages → Custom domain に `girlshobby.com` → Save → チェックが通ったら「Enforce HTTPS」にチェック
- Variables：`PUBLIC_URL` = `https://girlshobby.com`
