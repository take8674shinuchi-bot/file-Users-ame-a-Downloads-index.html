# かんたん広告ブロッカー（Chrome 拡張機能）

Chrome で Web を見るときに、広告やトラッキングをブロックするシンプルな拡張機能です。
Manifest V3 の [`declarativeNetRequest`](https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest) を使い、広告配信ドメインへの通信を遮断します。

- 余計な権限を要求せず、外部サーバーへも一切送信しません（すべてローカルで完結）
- ツールバーのアイコンから ワンクリックで ON / OFF
- バッジに「そのタブでブロックした数」、ポップアップに「累計ブロック数」を表示
- グローバル＋日本国内の主要な広告／計測ネットワーク 100 件以上をカバー

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
| `rules.json` | ブロック対象のルール（`declarativeNetRequest` 形式・自動生成） |
| `background.js` | ON/OFF 切り替え・バッジ表示・累計集計を行う Service Worker |
| `popup.html` / `popup.css` / `popup.js` | アイコンクリックで開く操作パネル |
| `icons/` | アイコン画像（16/32/48/128px） |
| `tools/make_rules.py` | `rules.json` を生成するスクリプト |
| `tools/make_icons.py` | アイコン PNG を生成するスクリプト |

ページの最上位の表示（`main_frame`）はブロック対象から外しているため、
広告ドメインが原因でページ全体が真っ白になることはありません。

---

## ブロック対象を追加・編集する

ブロックしたいドメインは `tools/make_rules.py` の `AD_DOMAINS` リストに 1 行追記して、
スクリプトを実行すると `rules.json` が再生成されます。

```bash
python3 tools/make_rules.py
```

その後、`chrome://extensions` で拡張機能の「更新（再読み込み）」ボタンを押すと反映されます。

アイコンを作り直したい場合:

```bash
python3 tools/make_icons.py
```

---

## うまく動かないとき

- **サイトの一部が表示されない / 動かない**
  まれにブロックが原因のことがあります。アイコンから一時的に OFF にして再読み込みし、
  改善するなら原因ドメインを `rules.json` から外してください。
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

## 注意

- 本拡張機能はドメイン単位のブロックリスト方式です。uBlock Origin のような
  高度な要素非表示（コスメティックフィルタ）は行いません。
- ブロックリストは主要なネットワークを対象にした軽量版です。網羅性を求める場合は
  `tools/make_rules.py` にドメインを追加してご利用ください。
