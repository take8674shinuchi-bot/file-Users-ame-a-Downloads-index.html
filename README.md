# かんたん広告ブロッカー（Chrome 拡張機能）

Chrome で Web を見るときに、広告やトラッキングをブロックする拡張機能です。
Manifest V3 の [`declarativeNetRequest`](https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest) で広告配信ドメインへの通信を遮断し、さらに広告の「枠」自体を CSS で非表示にします。

- **ネットワーク遮断**: [EasyList](https://easylist.to/) を採用し、約 **30,000 件**の広告／計測ドメインをブロック（国内ネットワークも統合）
- **要素非表示**: EasyList の汎用コスメティックフィルタ約 **13,000 セレクタ**で、残った広告枠・空きスペースを非表示
- ツールバーのアイコンから ワンクリックで ON / OFF（両方を連動して切替）
- バッジに「そのタブでブロックした数」、ポップアップに「累計ブロック数」を表示
- 収集や外部送信は一切なし。処理はすべて端末内で完結します

---

## インストール手順

この拡張機能は Chrome ウェブストア未配布です。以下の手順で「パッケージ化されていない拡張機能」として読み込みます。

1. このリポジトリをダウンロード（または `git clone`）して、フォルダをローカルに置きます。
2. Chrome のアドレスバーに `chrome://extensions` と入力して開きます。
3. 右上の **「デベロッパー モード」** を ON にします。
4. **「パッケージ化されていない拡張機能を読み込む」** をクリックします。
5. この **フォルダ（`manifest.json` がある階層）** を選択します。
6. ツールバーに 🚫 アイコンが追加されれば完了です。

> Microsoft Edge / Brave など Chromium 系ブラウザでも同じ手順で使えます。

---

## 使い方

- **ON / OFF**: ツールバーのアイコンをクリックし、ポップアップのスイッチで切り替えます。
- **バッジの数字**: そのタブでブロックした件数です。OFF のときは `off` と表示されます。
- **累計ブロック**: これまでにブロックした合計数。リンクからリセットできます。
- 設定を変えたあとは、開いているページを **再読み込み（F5）** すると確実に反映されます。

---

## 仕組み

| ファイル | 役割 |
| --- | --- |
| `manifest.json` | 拡張機能の定義（MV3） |
| `rules.json` | ネットワーク遮断ルール（`declarativeNetRequest` 形式・自動生成） |
| `content.css` | 広告枠を消す要素非表示スタイル（自動生成） |
| `background.js` | ON/OFF 切り替え・CSS 注入・バッジ表示・累計集計を行う Service Worker |
| `popup.html` / `popup.css` / `popup.js` | アイコンクリックで開く操作パネル |
| `icons/` | アイコン画像（16/32/48/128px） |
| `tools/build_filters.py` | EasyList を取り込み `rules.json` と `content.css` を生成 |
| `tools/make_icons.py` | アイコン PNG を生成するスクリプト |

ページの最上位の表示（`main_frame`）はブロック対象から外しているため、
広告ドメインが原因でページ全体が真っ白になることはありません。
要素非表示の CSS は ON のときだけ全サイトに注入され、OFF にすると解除されます。

> **権限について**: 要素非表示（コスメティックフィルタ）を全サイトで行うため、
> `scripting` と「すべてのサイトへのアクセス」(`<all_urls>`) を使用します。
> これは広告枠を消すための CSS 注入にのみ利用し、データの収集・送信は行いません。

---

## ブロックリストを更新・編集する

最新の EasyList を取り込んで `rules.json`（ネットワーク遮断）と `content.css`（要素非表示）を
再生成します。独自に止めたいドメインは `tools/build_filters.py` の `CURATED_DOMAINS` に追記できます。

```bash
python3 tools/build_filters.py
```

その後、`chrome://extensions` で拡張機能の「更新（再読み込み）」ボタンを押すと反映されます。

> DNR が確実に有効化できる上限（3 万件）に収めるため、キュレーション網を優先し、
> 残り枠を EasyList で補完しています（`MAX_RULES` で調整可能）。

アイコンを作り直したい場合:

```bash
python3 tools/make_icons.py
```

---

## うまく動かないとき

- **サイトの一部が表示されない / 崩れる**
  まれにネットワーク遮断や要素非表示が原因のことがあります。アイコンから一時的に
  OFF にして再読み込みし、改善するなら原因ドメインを `rules.json` から、または
  該当セレクタを `content.css` から外してください。
- **YouTube などの動画の前後に出る広告（プレロール）**
  これらはサイトと同一ドメインから配信されるため、本拡張機能では止められません。
  バナーやおすすめ枠などの「表示広告」は非表示にします。動画広告まで対策したい場合は
  uBlock Origin などの専用拡張機能をご利用ください。
- **「累計ブロック」が増えない**
  累計カウントは Chrome の仕様上「デベロッパー モードで読み込んだ拡張機能」でのみ集計されます
  （`onRuleMatchedDebug` を利用）。タブごとのバッジ表示は常に動作します。

---

## Cloudflare Workers での公開（ランディングページ）

拡張機能の紹介とダウンロードができる静的サイトを `public/` に同梱しており、
Cloudflare Workers の静的アセット配信としてそのまま公開できます。

| ファイル | 役割 |
| --- | --- |
| `public/index.html` | 紹介＆ダウンロード用ランディングページ |
| `public/downloads/kantan-ad-blocker.zip` | 配布用の拡張機能 ZIP（`tools/make_zip.py` で生成） |
| `wrangler.toml` | Cloudflare Workers 設定（`public/` をアセット配信） |
| `package.json` | `wrangler deploy` 用の最小構成 |

GitHub 連携（Workers Builds）が設定済みの場合、`main` への push で自動デプロイされます。
手元から手動でデプロイする場合:

```bash
npm install
npx wrangler deploy
```

配布 ZIP を更新したいときは、拡張機能ファイルを変更したあとに再生成します。

```bash
python3 tools/make_zip.py
```

> Cloudflare 側の Worker サービス名は `wrangler.toml` の `name` と一致させてください
> （既定は `file-users-ame-a-downloads-index`）。別サービス名の連携が残っている場合は、
> Cloudflare ダッシュボードの Workers → 該当サービス → Settings → Build から
> Git 連携を解除できます。

---

## クレジット / ライセンス

ブロックリストは [EasyList](https://easylist.to/) を基に生成しています。
EasyList は GPLv3 / CC BY-SA 3.0 のデュアルライセンスで提供されています。

- ネットワーク遮断: EasyList（adservers / popups）
- 要素非表示: EasyList（general hide）の汎用コスメティックフィルタ

## 注意

- uBlock Origin のようなスクリプトレット注入や高度な回避対策は行いません。
  プレロール動画広告（YouTube 等）や、サイトと同一ドメインから配信される広告は
  仕組み上ブロックできない場合があります。
- 誤検知でサイトが崩れた場合は、アイコンから OFF にするか、該当ルールを
  `rules.json` / `content.css` から削除してください。
