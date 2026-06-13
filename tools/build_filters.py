#!/usr/bin/env python3
"""EasyList を取り込んで広告ブロック用の rules.json と content.css を生成する。

- ネットワーク遮断 (rules.json):
    EasyList の広告サーバー定義(数万ドメイン)に、主要ネットワークを
    サブドメインごと止めるキュレーション網(国内含む)を統合する。
    DNR の確実な動作上限に収めるため、キュレーション網を優先し、
    残り枠を EasyList で埋めて合計 MAX_RULES 件に制限する。

- 要素非表示 (content.css):
    EasyList の汎用コスメティックフィルタ(##selector)を CSS 化し、
    広告の「枠」自体を消す。AdSense/GPT/Taboola/Outbrain や
    YouTube の表示広告などの高信頼セレクタを先頭に追加する。

EasyList は GPLv3 / CC BY-SA 3.0 のデュアルライセンス。出典表示を行うこと。
  https://easylist.to/

使い方:
    python3 tools/build_filters.py
"""
import json
import os
import re
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
RULES_OUT = os.path.join(ROOT, "rules.json")
CSS_OUT = os.path.join(ROOT, "content.css")

# DNR が「保証する」最大の静的ルール数。これ以内なら端末環境に依存せず必ず有効化される。
MAX_RULES = 30000

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
BASE = "https://raw.githubusercontent.com/easylist/easylist/master"
EASYLIST = {
    "adservers": f"{BASE}/easylist/easylist_adservers.txt",
    "popups": f"{BASE}/easylist/easylist_adservers_popup.txt",
    "hide": f"{BASE}/easylist/easylist_general_hide.txt",
}

# 主要ネットワークはサブドメインごと遮断したいので個別にキュレーション。
# (EasyList は特定サブドメインのみ収録のことが多く、取りこぼしを防ぐ)
CURATED_DOMAINS = [
    # Google 系
    "doubleclick.net", "googlesyndication.com", "googleadservices.com",
    "googletagservices.com", "googletagmanager.com", "google-analytics.com",
    "analytics.google.com", "adservice.google.com", "2mdn.net", "app-measurement.com",
    # 大手アドエクスチェンジ / SSP / DSP
    "amazon-adsystem.com", "adnxs.com", "adnxs-simple.com", "rubiconproject.com",
    "pubmatic.com", "openx.net", "casalemedia.com", "indexww.com", "33across.com",
    "adsrvr.org", "mathtag.com", "bidswitch.net", "smartadserver.com", "adform.net",
    "contextweb.com", "gumgum.com", "districtm.io", "sharethrough.com", "yieldmo.com",
    "spotxchange.com", "spotx.tv", "serving-sys.com", "flashtalking.com", "teads.tv",
    "smartclip.net",
    # ネイティブ広告・レコメンド
    "criteo.com", "criteo.net", "taboola.com", "outbrain.com", "revcontent.com",
    "mgid.com", "adblade.com",
    # 計測 / トラッキング / DMP
    "scorecardresearch.com", "quantserve.com", "quantcount.com", "moatads.com",
    "adsafeprotected.com", "doubleverify.com", "bluekai.com", "demdex.net",
    "everesttech.net", "crwdcntrl.net", "agkn.com", "rlcdn.com", "turn.com",
    "mc.yandex.ru", "hotjar.com", "fullstory.com", "mouseflow.com", "crazyegg.com",
    "mixpanel.com", "segment.com", "segment.io", "amplitude.com", "branch.io",
    "bat.bing.com", "ads.linkedin.com", "ads-twitter.com", "analytics.twitter.com",
    "ads.tiktok.com", "analytics.tiktok.com", "analytics.yahoo.com", "ads.yahoo.com",
    # モバイル広告 SDK
    "applovin.com", "adcolony.com", "inmobi.com", "mopub.com",
    "unityads.unity3d.com", "chartboost.com", "vungle.com",
    # 日本国内
    "i-mobile.co.jp", "microad.jp", "microad.net", "fout.jp", "ad-stir.com",
    "nend.net", "genieesspv.jp", "gsspat.jp", "gssprt.jp", "ad-generation.jp",
    "scaleout.jp", "socdm.com", "popin.cc", "logly.co.jp", "adingo.jp",
    "impact-ad.jp", "advg.jp", "yads.yahoo.co.jp", "ads.yahoo.co.jp",
    "rat.rakuten.co.jp", "a8.net",
]

# ドメイン全体を止めるとログイン等を壊すサービスはパス限定で遮断。
CURATED_URL_FILTERS = [
    "||facebook.com/tr",
    "||facebook.com/plugins/like",
    "||pixel.wp.com",
    "||stats.wp.com",
    "||yjtag.yahoo.co.jp",
]

# 高信頼の要素非表示セレクタ(誤検知が少ないもの)。EasyList より前に置く。
CURATED_SELECTORS = [
    # Google AdSense / GPT
    "ins.adsbygoogle", ".adsbygoogle",
    'iframe[id^="google_ads_iframe"]', 'iframe[id^="aswift_"]',
    '[id^="div-gpt-ad"]', '[id^="google_ads_"]',
    # Taboola / Outbrain / Amazon
    '[id^="taboola-"]', ".trc_related_container", ".trc_rbox_div",
    ".OUTBRAIN", '[id^="outbrain_widget"]', ".ob-widget",
    '[id^="amzn_assoc_ad"]',
    # YouTube の「表示広告」(※プレロール動画広告は CSS では消せない)
    "#masthead-ad", "ytd-ad-slot-renderer", "ytd-in-feed-ad-layout-renderer",
    "ytd-promoted-sparkles-web-renderer", "ytd-banner-promo-renderer",
    "ytd-statement-banner-renderer", "#player-ads", ".ytp-ad-overlay-slot",
]

# ABP 拡張セレクタ(標準 CSS で表現できない)を含む行は除外する。
UNSUPPORTED = (
    ":-abp-", ":has-text(", ":contains(", ":matches-css", ":style(", ":remove(",
    ":upward(", ":xpath(", ":nth-ancestor(", ":watch-attr(", "[-ext-",
    ":min-text-length", ":if(", ":if-not(", "+js(", "##^",
)

DOMAIN_RE = re.compile(r"^([A-Za-z0-9.\-_]+)\^")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "ignore").splitlines()


def parse_domains(lines):
    """ABP のネットワーク行から純粋なドメイン(||domain^)を抽出する。"""
    out = []
    for line in lines:
        line = line.strip()
        if not line or line[0] in "!#[":
            continue
        if line.startswith("@@"):  # 例外(許可)ルールは扱わない
            continue
        if "##" in line or "#?#" in line or "#@#" in line or "#$#" in line:
            continue  # コスメティック
        if not line.startswith("||"):
            continue
        m = DOMAIN_RE.match(line[2:])
        if not m:
            continue
        d = m.group(1).lower().strip(".")
        if "." in d and "*" not in d:
            out.append(d)
    return out


def parse_selectors(lines):
    """EasyList 汎用コスメティック(##selector)を抽出する。"""
    out = []
    for line in lines:
        line = line.rstrip("\n").rstrip()
        if not line or line.startswith("!"):
            continue
        if not line.startswith("##"):
            continue  # ドメイン限定や例外は対象外
        sel = line[2:].strip()
        if not sel or any(bad in sel for bad in UNSUPPORTED):
            continue
        out.append(sel)
    return out


def build_rules():
    ads = parse_domains(fetch(EASYLIST["adservers"]))
    pop = parse_domains(fetch(EASYLIST["popups"]))

    ordered = []
    seen = set()
    # キュレーション網を最優先(必ず収録される)
    for d in CURATED_DOMAINS:
        if d not in seen:
            seen.add(d)
            ordered.append(d)
    # 残り枠を EasyList で補完
    budget = MAX_RULES - len(CURATED_URL_FILTERS)
    for d in ads + pop:
        if len(ordered) >= budget:
            break
        if d not in seen:
            seen.add(d)
            ordered.append(d)

    rules = []
    rid = 1
    for d in ordered:
        rules.append({
            "id": rid,
            "action": {"type": "block"},
            "condition": {
                "urlFilter": f"||{d}^",
                "excludedResourceTypes": ["main_frame"],
            },
        })
        rid += 1
    for uf in CURATED_URL_FILTERS:
        rules.append({
            "id": rid,
            "action": {"type": "block"},
            "condition": {
                "urlFilter": uf,
                "excludedResourceTypes": ["main_frame"],
            },
        })
        rid += 1
    return rules


def build_css():
    selectors = []
    seen = set()
    for sel in CURATED_SELECTORS + parse_selectors(fetch(EASYLIST["hide"])):
        if sel not in seen:
            seen.add(sel)
            selectors.append(sel)
    header = (
        "/* かんたん広告ブロッカー - 要素非表示スタイル\n"
        " * 広告の枠そのものを隠す。EasyList の汎用コスメティックフィルタを基に生成。\n"
        " * Source: EasyList (https://easylist.to/) - GPLv3 / CC BY-SA 3.0\n"
        " * セレクタ単位で1ルールにし、1つが無効でも他へ波及しないようにしている。\n"
        " */\n"
    )
    body = "\n".join(f"{sel}{{display:none!important}}" for sel in selectors)
    return header + body + "\n", len(selectors)


def main():
    rules = build_rules()
    with open(RULES_OUT, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    css, n_sel = build_css()
    with open(CSS_OUT, "w", encoding="utf-8") as f:
        f.write(css)
    print(f"wrote {os.path.relpath(RULES_OUT, ROOT)} ({len(rules)} rules)")
    print(f"wrote {os.path.relpath(CSS_OUT, ROOT)} ({n_sel} selectors)")


if __name__ == "__main__":
    main()
