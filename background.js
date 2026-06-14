// かんたん広告ブロッカー - バックグラウンド(Service Worker)
//
// 役割:
//   1) 広告ブロックの ON/OFF を保存し、ネットワーク遮断(DNR ルールセット)と
//      要素非表示(コスメティック CSS)の両方を連動して切り替える
//   2) ツールバーアイコンのバッジに「このタブでブロックした数」を表示する
//   3) ブロックの累計件数を集計してポップアップに見せる(開発モードのみ)

const RULESET_ID = "ruleset_ads"; // rules.json (ネットワーク遮断)
const COSMETIC_ID = "cosmetic"; // content.css (広告枠の非表示)
const STATE_KEY = "enabled";
const TOTAL_KEY = "blockedTotal";

const COLOR_ON = "#e53935";
const COLOR_OFF = "#9e9e9e";

chrome.runtime.onInstalled.addListener(initialize);
chrome.runtime.onStartup.addListener(initialize);

async function initialize() {
  const { [STATE_KEY]: enabled = true } = await chrome.storage.local.get(STATE_KEY);
  await applyEnabled(enabled);
}

// 有効/無効を「ネットワーク遮断」「要素非表示」「バッジ」へ反映する。
async function applyEnabled(enabled) {
  // 1) ネットワーク遮断のルールセット
  await chrome.declarativeNetRequest.updateEnabledRulesets(
    enabled
      ? { enableRulesetIds: [RULESET_ID] }
      : { disableRulesetIds: [RULESET_ID] }
  );

  // 2) 要素非表示の CSS(全サイトへ document_start で注入)
  if (enabled) {
    await registerCosmetic();
  } else {
    await unregisterCosmetic();
  }

  // 3) バッジ表示
  if (enabled) {
    await chrome.action.setBadgeText({ text: "" });
    await chrome.declarativeNetRequest.setExtensionActionOptions({
      displayActionCountAsBadgeText: true,
    });
    await chrome.action.setBadgeBackgroundColor({ color: COLOR_ON });
    await chrome.action.setTitle({ title: "かんたん広告ブロッカー: 有効" });
  } else {
    await chrome.declarativeNetRequest.setExtensionActionOptions({
      displayActionCountAsBadgeText: false,
    });
    await chrome.action.setBadgeBackgroundColor({ color: COLOR_OFF });
    await chrome.action.setBadgeText({ text: "off" });
    await chrome.action.setTitle({ title: "かんたん広告ブロッカー: 無効" });
  }
}

// content.css を全フレームに注入するコンテンツスクリプトを登録する。
// 二重登録エラーを避けるため、いったん解除してから登録する。
async function registerCosmetic() {
  await unregisterCosmetic();
  try {
    await chrome.scripting.registerContentScripts([
      {
        id: COSMETIC_ID,
        matches: ["<all_urls>"],
        css: ["content.css"],
        runAt: "document_start",
        allFrames: true,
        persistAcrossSessions: false,
      },
    ]);
  } catch (e) {
    // 失敗してもネットワーク遮断は機能するため、握りつぶしてログのみ。
    console.warn("コスメティックCSSの登録に失敗:", e);
  }
}

async function unregisterCosmetic() {
  try {
    await chrome.scripting.unregisterContentScripts({ ids: [COSMETIC_ID] });
  } catch (e) {
    // 未登録なら何もしない。
  }
}

// --- 累計ブロック数の集計 ---
// onRuleMatchedDebug は開発モード(パッケージ化されていない拡張機能)でのみ発火する。
// タブ単位のバッジ表示は本番でも動くため、累計はあくまで補助的な指標。
let pendingCount = 0;
let flushTimer = null;
let writeChain = Promise.resolve();

if (chrome.declarativeNetRequest.onRuleMatchedDebug) {
  chrome.declarativeNetRequest.onRuleMatchedDebug.addListener(() => {
    pendingCount += 1;
    if (flushTimer === null) {
      flushTimer = setTimeout(flushPendingCount, 500);
    }
  });
}

function flushPendingCount() {
  flushTimer = null;
  const add = pendingCount;
  pendingCount = 0;
  if (add === 0) return;
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
  return true;
});
