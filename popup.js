// かんたん広告ブロッカー - ポップアップ UI のロジック

const toggle = document.getElementById("toggle");
const statusText = document.getElementById("statusText");
const statusDot = document.getElementById("statusDot");
const tabCountEl = document.getElementById("tabCount");
const totalCountEl = document.getElementById("totalCount");
const resetBtn = document.getElementById("reset");

// background へメッセージを送る小さなヘルパ
function send(message) {
  return chrome.runtime.sendMessage(message);
}

// ON/OFF の見た目を反映
function renderState(enabled) {
  toggle.checked = enabled;
  statusText.textContent = enabled ? "有効" : "無効";
  statusDot.classList.toggle("on", enabled);
  statusDot.classList.toggle("off", !enabled);
}

// 現在のタブのバッジ(=このタブでブロックした数)を読む
async function loadTabCount() {
  try {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });
    if (!tab) return;
    const text = await chrome.action.getBadgeText({ tabId: tab.id });
    const n = parseInt(text, 10);
    tabCountEl.textContent = Number.isNaN(n) ? "0" : String(n);
  } catch {
    tabCountEl.textContent = "0";
  }
}

// 状態と累計を読み込んで描画
async function refresh() {
  const state = await send({ type: "getState" });
  renderState(state.enabled);
  totalCountEl.textContent = (state.blockedTotal ?? 0).toLocaleString("ja-JP");
  await loadTabCount();
}

// トグル操作
toggle.addEventListener("change", async () => {
  const enabled = toggle.checked;
  renderState(enabled);
  await send({ type: "setEnabled", enabled });
});

// 累計リセット
resetBtn.addEventListener("click", async () => {
  await send({ type: "resetCount" });
  totalCountEl.textContent = "0";
});

refresh();
