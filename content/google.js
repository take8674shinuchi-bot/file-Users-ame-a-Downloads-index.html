// かんたん広告ブロッカー - Google 検索ページの広告非表示(コスメティックフィルタ)
//
// 役割:
//   ネットワーク遮断(rules.json)だけでは消せない、Google 検索結果ページに
//   サーバー側で埋め込まれる「スポンサー / 広告 / Sponsored」枠を、CSS と
//   DOM 走査で隠す。これらは google.com 自身(検索結果と同一オリジン)から
//   配信されるため、通信ブロックでは消せない。
//
//   拡張機能の ON/OFF(chrome.storage.local の "enabled")と連動し、
//   OFF のときは何も隠さない。

const STATE_KEY = "enabled";
const ON_CLASS = "eab-on"; // CSS 側はこのクラスが付いている間だけ広告を隠す
const HIDDEN_CLASS = "eab-hidden-ad"; // JS が広告と判定した結果ブロックに付ける目印

// 「スポンサー枠」を示すラベル文言。葉ノードのテキストと完全一致で判定する。
const AD_LABELS = ["sponsored", "スポンサー", "広告"];

// 走査でさかのぼる先(検索結果の各領域)の id。ここを親に持つ要素を結果ブロックと見なす。
const RESULT_CONTAINER_IDS = new Set([
  "rso",
  "center_col",
  "rhs",
  "search",
  "main",
]);

// document_start で実行される。既定が「有効」なので、まず楽観的にクラスを付け、
// 広告枠が描画される前に隠れるようにして表示のチラつきを防ぐ。
document.documentElement.classList.add(ON_CLASS);

let enabled = true;
let observer = null;
let scanQueued = false;

// 保存済みの ON/OFF を読み込んで反映
chrome.storage.local
  .get(STATE_KEY)
  .then(({ [STATE_KEY]: value = true }) => {
    enabled = value;
    apply();
  })
  .catch(() => {
    // 拡張機能のコンテキスト失効時などは既定(有効)のまま動かす
    apply();
  });

// ポップアップで ON/OFF が切り替わったら即座に追従する
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local" || !changes[STATE_KEY]) return;
  enabled = changes[STATE_KEY].newValue ?? true;
  apply();
});

document.addEventListener("DOMContentLoaded", scheduleScan);
window.addEventListener("load", scheduleScan);

// 現在の ON/OFF を画面へ反映する
function apply() {
  document.documentElement.classList.toggle(ON_CLASS, enabled);
  if (enabled) {
    startObserver();
    scheduleScan();
  } else {
    stopObserver();
    // JS で付けた目印を外す(これだけで再表示される)
    document
      .querySelectorAll("." + HIDDEN_CLASS)
      .forEach((el) => el.classList.remove(HIDDEN_CLASS));
  }
}

// 走査対象は検索結果の領域に限定して、負荷と誤検出を抑える
function scanRoots() {
  return [
    document.getElementById("center_col"),
    document.getElementById("rso"),
    document.getElementById("rhs"),
  ].filter(Boolean);
}

// ラベル要素から、結果コンテナの直下にある「結果ブロック」までさかのぼる
function findAdBlock(labelEl) {
  let node = labelEl;
  for (let i = 0; i < 14 && node && node.parentElement; i++) {
    const parent = node.parentElement;
    if (RESULT_CONTAINER_IDS.has(parent.id) || parent === document.body) {
      return node; // node は結果コンテナの直下 = 広告ブロック全体
    }
    node = parent;
  }
  return null;
}

// 結果一覧そのものを誤って掴んでいないかの安全チェック。
// (1 件の広告には見出し h3 はほぼ 1 つ。多数あれば一覧全体なので隠さない)
function looksTooBig(block) {
  if (RESULT_CONTAINER_IDS.has(block.id)) return true;
  if (block.querySelector("#rso, #search, #center_col")) return true;
  return block.querySelectorAll("h3").length > 2;
}

function isAdLabel(text) {
  const normalized = text.trim().toLowerCase().replace(/[:：・]/g, "");
  return AD_LABELS.includes(normalized);
}

// 「スポンサー」ラベル付きの結果ブロックを探して目印を付ける
function scan() {
  scanQueued = false;
  if (!enabled) return;
  for (const root of scanRoots()) {
    for (const el of root.querySelectorAll("span")) {
      // 子要素を持たない葉ノードで、文言が完全一致するものだけを対象にする
      if (el.childElementCount !== 0 || !isAdLabel(el.textContent)) continue;
      const block = findAdBlock(el);
      if (
        block &&
        !block.classList.contains(HIDDEN_CLASS) &&
        !looksTooBig(block)
      ) {
        block.classList.add(HIDDEN_CLASS);
      }
    }
  }
}

// 走査はまとめて実行(MutationObserver の大量発火に備えてデバウンス)
function scheduleScan() {
  if (scanQueued || !enabled) return;
  scanQueued = true;
  if (window.requestIdleCallback) {
    requestIdleCallback(scan, { timeout: 500 });
  } else {
    setTimeout(scan, 200);
  }
}

function startObserver() {
  if (observer) return;
  observer = new MutationObserver(scheduleScan);
  const target =
    document.getElementById("search") ||
    document.body ||
    document.documentElement;
  observer.observe(target, { childList: true, subtree: true });
}

function stopObserver() {
  if (observer) {
    observer.disconnect();
    observer = null;
  }
}
