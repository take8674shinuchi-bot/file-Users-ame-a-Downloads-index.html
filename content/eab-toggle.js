// かんたん広告ブロッカー - コスメティックフィルタ共通の ON/OFF 連動スクリプト
//
// <html> に "eab-on" クラスを付け外しするだけの小さなスクリプト。
// サイト別の CSS(例: content/kemono.css)は「html.eab-on のときだけ広告要素を
// 隠す」ように書かれており、このクラス 1 つで有効/無効をまとめて切り替える。
// 拡張機能の ON/OFF(chrome.storage.local の "enabled")と連動する。
//
// CSS だけで広告枠を隠せるサイト向けの汎用トグル。動的に広告を探す必要がある
// サイト(例: Google 検索の content/google.js)は、専用スクリプト側でクラス管理も
// 行うため、このファイルは読み込まない(同一ページで二重に読み込まないこと)。

const STATE_KEY = "enabled";
const ON_CLASS = "eab-on";

// 既定が有効なので、まず楽観的に付けて表示のチラつきを防ぐ(document_start)
document.documentElement.classList.add(ON_CLASS);

chrome.storage.local
  .get(STATE_KEY)
  .then(({ [STATE_KEY]: value = true }) => {
    document.documentElement.classList.toggle(ON_CLASS, value);
  })
  .catch(() => {
    // コンテキスト失効時などは既定(有効)のまま
  });

// ポップアップで ON/OFF が切り替わったら即座に追従する
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local" || !changes[STATE_KEY]) return;
  document.documentElement.classList.toggle(
    ON_CLASS,
    changes[STATE_KEY].newValue ?? true
  );
});
