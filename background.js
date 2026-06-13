// かんたん広告ブロッカー - バックグラウンド(Service Worker)
//
// 役割:
//   1) 広告ブロックの ON/OFF を chrome.storage に保存し、ルールセットを切り替える
//   2) ツールバーアイコンのバッジに「このタブでブロックした数」を自動表示する
//   3) ブロックの累計件数を集計してポップアップに見せる(開発モードのみ)

const RULESET_ID = "ruleset_ads";
const STATE_KEY = "enabled";
const TOTAL_KEY = "blockedTotal";

const COLOR_ON = "#e53935"; // 有効時のバッジ色(赤)
const COLOR_OFF = "#9e9e9e"; // 無効時のバッジ色(グレー)

// --- 起動時 / インストール時に現在の状態を反映 ---
chrome.runtime.onInstalled.addListener(initialize);
chrome.runtime.onStartup.addListener(initialize);

async function initialize() {
  const { [STATE_KEY]: enabled = true } = await chrome.storage.local.get(STATE_KEY);
  await applyEnabled(enabled);
}

// 有効/無効をルールセットとバッジ表示に反映する。
async function applyEnabled(enabled) {
  await chrome.declarativeNetRequest.updateEnabledRulesets(
    enabled
      ? { enableRulesetIds: [RULESET_ID] }
      : { disableRulesetIds: [RULESET_ID] }
  );

  if (enabled) {
    // 手動バッジを消してから、Chrome にタブ単位のブロック数を表示させる
    await chrome.action.setBadgeText({ text: "" });
    await chrome.declarativeNetRequest.setExtensionActionOptions({
      displayActionCountAsBadgeText: true,
    });
    await chrome.action.setBadgeBackgroundColor({ color: COLOR_ON });
    await chrome.action.setTitle({ title: "かんたん広告ブロッカー: 有効" });
  } else {
    // 自動カウント表示をやめ、「off」バッジに切り替える
    await chrome.declarativeNetRequest.setExtensionActionOptions({
      displayActionCountAsBadgeText: false,
    });
    await chrome.action.setBadgeBackgroundColor({ color: COLOR_OFF });
    await chrome.action.setBadgeText({ text: "off" });
    await chrome.action.setTitle({ title: "かんたん広告ブロッカー: 無効" });
  }
}

// --- 累計ブロック数の集計 ---
// onRuleMatchedDebug は「パッケージ化されていない拡張機能(開発モード)」でのみ
// 発火する。本番パッケージでは使えないため、存在チェックして安全に劣化させる。
// タブ単位のバッジ表示は本番でも動くので、累計はあくまで補助的な指標。
let pendingCount = 0;
let flushTimer = null;
let writeChain = Promise.resolve();

if (chrome.declarativeNetRequest.onRuleMatchedDebug) {
  chrome.declarativeNetRequest.onRuleMatchedDebug.addListener(() => {
    pendingCount += 1;
    if (flushTimer === null) {
      // 大量発火時の書き込みを抑えるため 500ms ごとにまとめて保存
      flushTimer = setTimeout(flushPendingCount, 500);
    }
  });
}

function flushPendingCount() {
  flushTimer = null;
  const add = pendingCount;
  pendingCount = 0;
  if (add === 0) return;
  // 読み出し→加算→保存を直列化して、取りこぼし(競合)を防ぐ
  writeChain = writeChain.then(async () => {
    const { [TOTAL_KEY]: total = 0 } = await chrome.storage.local.get(TOTAL_KEY);
    await chrome.storage.local.set({ [TOTAL_KEY]: total + add });
  });
}

// --- ポップアップからのメッセージ処理 ---
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  (async () => {
    switch (message?.type) {
      case "getState": {
        const data = await chrome.storage.local.get([STATE_KEY, TOTAL_KEY]);
        sendResponse({
          enabled: data[STATE_KEY] ?? true,
          blockedTotal: data[TOTAL_KEY] ?? 0,
        });
        break;
      }
      case "setEnabled": {
        const enabled = Boolean(message.enabled);
        await chrome.storage.local.set({ [STATE_KEY]: enabled });
        await applyEnabled(enabled);
        sendResponse({ ok: true, enabled });
        break;
      }
      case "resetCount": {
        await chrome.storage.local.set({ [TOTAL_KEY]: 0 });
        sendResponse({ ok: true });
        break;
      }
      default:
        sendResponse({ ok: false, error: "unknown message" });
    }
  })();
  return true; // 非同期で sendResponse を呼ぶため true を返す
});
