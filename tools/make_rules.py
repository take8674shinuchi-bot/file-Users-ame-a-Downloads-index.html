#!/usr/bin/env python3
"""declarativeNetRequest 用のブロックルール(rules.json)を生成する。

ドメインベースのブロックを中心にすることで、サイトを壊しにくくしつつ
主要な広告/トラッカー配信網を遮断する。広告主のドメインを足したく
なったら、下のリストに 1 行追記して `python3 tools/make_rules.py` を
実行するだけで rules.json が更新される。

トップレベル遷移(main_frame)は対象外にしているため、ページ自体の
表示を巻き込んでブロックすることはない。
"""
import json
import os

# 各ルールが対象とするリソース種別。ページ遷移(main_frame)は含めない。
RESOURCE_TYPES = [
    "sub_frame",
    "script",
    "image",
    "stylesheet",
    "object",
    "xmlhttprequest",
    "ping",
    "media",
    "font",
    "websocket",
    "other",
]

# ポップアップ/リダイレクト型の広告は別タブやページ遷移として開くため、
# トップレベル遷移(main_frame)も含めて止める必要がある。
ALL_RESOURCE_TYPES = ["main_frame", *RESOURCE_TYPES]

# ||domain は当該ドメインとそのサブドメインに一致する(Adblock 構文の部分集合)。
AD_DOMAINS = [
    # --- Google 系の広告/計測 ---
    "doubleclick.net",
    "googlesyndication.com",
    "googleadservices.com",
    "googletagservices.com",
    "googletagmanager.com",
    "google-analytics.com",
    "analytics.google.com",
    "adservice.google.com",
    "2mdn.net",
    "app-measurement.com",
    # --- 大手アドエクスチェンジ / SSP / DSP ---
    "amazon-adsystem.com",
    "adnxs.com",
    "adnxs-simple.com",
    "rubiconproject.com",
    "pubmatic.com",
    "openx.net",
    "casalemedia.com",
    "indexww.com",
    "33across.com",
    "adsrvr.org",
    "mathtag.com",
    "bidswitch.net",
    "smartadserver.com",
    "adform.net",
    "contextweb.com",
    "gumgum.com",
    "districtm.io",
    "sharethrough.com",
    "yieldmo.com",
    "spotxchange.com",
    "spotx.tv",
    "serving-sys.com",
    "flashtalking.com",
    "teads.tv",
    "smartclip.net",
    # --- コンテンツ/ネイティブ広告・レコメンド ---
    "criteo.com",
    "criteo.net",
    "taboola.com",
    "outbrain.com",
    "revcontent.com",
    "mgid.com",
    "adblade.com",
    # --- 計測 / トラッキング / DMP ---
    "scorecardresearch.com",
    "quantserve.com",
    "quantcount.com",
    "moatads.com",
    "adsafeprotected.com",
    "doubleverify.com",
    "bluekai.com",
    "demdex.net",
    "everesttech.net",
    "crwdcntrl.net",
    "agkn.com",
    "rlcdn.com",
    "turn.com",
    "mc.yandex.ru",
    "hotjar.com",
    "fullstory.com",
    "mouseflow.com",
    "crazyegg.com",
    "mixpanel.com",
    "segment.com",
    "segment.io",
    "amplitude.com",
    "branch.io",
    "bat.bing.com",
    "ads.linkedin.com",
    "ads-twitter.com",
    "analytics.twitter.com",
    "ads.tiktok.com",
    "analytics.tiktok.com",
    "analytics.yahoo.com",
    "ads.yahoo.com",
    # --- モバイル広告 SDK ---
    "applovin.com",
    "adcolony.com",
    "inmobi.com",
    "mopub.com",
    "unityads.unity3d.com",
    "chartboost.com",
    "vungle.com",
    # --- 日本国内の広告/計測ネットワーク ---
    "i-mobile.co.jp",
    "microad.jp",
    "microad.net",
    "fout.jp",
    "ad-stir.com",
    "nend.net",
    "genieesspv.jp",
    "gsspat.jp",
    "gssprt.jp",
    "ad-generation.jp",
    "scaleout.jp",
    "socdm.com",
    "popin.cc",
    "logly.co.jp",
    "adingo.jp",
    "impact-ad.jp",
    "advg.jp",
    "yads.yahoo.co.jp",
    "ads.yahoo.co.jp",
    "rat.rakuten.co.jp",
    "a8.net",
    "yimg.jp",  # Yahoo! JAPAN の広告配信に使われるサブドメインのみ後段で限定
]

# パス指定でピンポイント遮断する高信頼パターン。
# (ドメイン全体を止めるとログイン等を壊すサービス向け)
AD_URL_FILTERS = [
    "||facebook.com/tr",            # Facebook ピクセル(ビーコンのみ)
    "||facebook.com/plugins/like",  # いいねトラッキング
    "||pixel.wp.com",               # WordPress.com 計測ピクセル
    "||stats.wp.com",
]

# yimg.jp は CDN も兼ねるためサブドメインを広告系に限定する。
# (誤って画像 CDN を止めないよう、上のリストからは除外して個別指定)
AD_DOMAINS.remove("yimg.jp")
AD_URL_FILTERS.append("||yjtag.yahoo.co.jp")  # Yahoo! JAPAN タグ計測

# --- ポップアップ/リダイレクト型の広告ネットワーク ---
# アダルト/海賊版系サイト(例: hitomi.la)で多用される、ポップアンダー(クリック
# 時に別タブで開く広告)や強制リダイレクトを出すネットワーク。これらのドメインは
# 広告配信専用で一般ユーザーが直接アクセスすることはないため、トップレベル遷移
# (main_frame)も含めて遮断する。これにより、リンククリック時に勝手に開く別タブ
# 広告や、ページが広告サイトへ飛ばされるリダイレクトも止められる。
POPUP_AD_DOMAINS = [
    # ExoClick 系(hitomi.la のポップアンダー/リダイレクトの主因)
    "exoclick.com",
    "exosrv.com",
    "exdynsrv.com",
    "realsrv.com",
    "magsrv.com",
    # その他の主要なポップアンダー/アダルト系広告ネットワーク
    "juicyads.com",
    "trafficstars.com",
    "tsyndicate.com",
    "popads.net",
    "popadscdn.net",
    "popcash.net",
    "propellerads.com",
    "onclkds.com",
    "clickadu.com",
    "hilltopads.net",
    "ad-maven.com",
    "plugrush.com",
    "eroadvertising.com",
    "trafficjunky.net",
    "trafficforce.com",
    "adnium.com",
    "adspyglass.com",
    "highperformanceformat.com",
    "profitabledisplaynetwork.com",
]

OUT_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "rules.json")


def build_rules():
    rules = []
    rule_id = 1
    for domain in AD_DOMAINS:
        rules.append(
            {
                "id": rule_id,
                "priority": 1,
                "action": {"type": "block"},
                "condition": {
                    "urlFilter": f"||{domain}^",
                    "resourceTypes": RESOURCE_TYPES,
                },
            }
        )
        rule_id += 1
    for url_filter in AD_URL_FILTERS:
        rules.append(
            {
                "id": rule_id,
                "priority": 1,
                "action": {"type": "block"},
                "condition": {
                    "urlFilter": url_filter,
                    "resourceTypes": RESOURCE_TYPES,
                },
            }
        )
        rule_id += 1
    # ポップアップ/リダイレクト広告は main_frame も含めて遮断する
    for domain in POPUP_AD_DOMAINS:
        rules.append(
            {
                "id": rule_id,
                "priority": 1,
                "action": {"type": "block"},
                "condition": {
                    "urlFilter": f"||{domain}^",
                    "resourceTypes": ALL_RESOURCE_TYPES,
                },
            }
        )
        rule_id += 1
    return rules


def main():
    rules = build_rules()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"wrote {os.path.normpath(OUT_PATH)} ({len(rules)} rules)")


if __name__ == "__main__":
    main()
