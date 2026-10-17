#!/usr/bin/env python3
"""
Shared registry + page-shell template for the Corvus static site.
Plain Python string templates (no Jinja2 dependency) — every other generator
script imports from here so the header/nav/footer never drifts between pages.

Multi-language: the JA site lives at the repo root (/, /changelog/, ...);
every other language lives one level down (/en/, /en/changelog/, ...). Pull
translated strings via load_bundle(lang) (data/i18n/<lang>.json, produced by
scripts/extract_bundle.py for ja and by translation agents for the rest).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
import html as _html

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lang_detect  # noqa: E402  (entry-time language detection)
from flag_svgs import FLAG_EMOJI  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
I18N_DIR = ROOT / "data" / "i18n"
DOWNLOADS_DIR = ROOT / "downloads"

# Three distinct names, deliberately kept apart:
#   SITE_TITLE          the website              -> "Corvus"
#   PACK_NAME           the mod pack product     -> "Alpha" (was "Glimpse
#                       Alpha" until the V2.5.0 rename; see below)
#   LAUNCHER_APP_NAME   the desktop updater app  -> "Corvus" (was
#                       "Glimpse Launcher" until the 1.3.0 rename)
SITE_TITLE = "Corvus"  # brand name, unchanged across languages
# 2026-09-10、所有者:「Corvus から Corvus に名称を変更」。
# 旧名は Corvus。リポジトリ名(corvus-dev)と公開 URL は
# **変えない** —— 変えると既に配布したランチャーの取得先が 404 になる
# (cross-repo filename coupling と同じ罠)。変わるのは表示名だけである。
LAUNCHER_APP_NAME = "Corvus"

# V2.5.0 renamed the pack "Glimpse Alpha" -> "Alpha" (the owner's instruction
# was to drop "Glimpse"). The BRAND moved; no identifier did — the eleven mod
# ids are still sorakaze_*, so worlds, configs and namespaces are untouched.
#
# This constant and the two helpers below exist because the old name was
# duplicated as an f-string literal in three separate builders
# (build_download.py, build_releases_feed.py, build_glimpse_manifest.py), each
# of which independently reconstructed the ZIP filename. That is the same
# shape of defect as the private find_launcher_jars() copies documented lower
# in this file: three copies of one fact drift, and here they would have
# drifted into *hard build failures* the moment the renamed ZIP landed in
# downloads/ (each _zip_path() raises SystemExit when its guessed name is
# missing). One definition, imported by all three.
PACK_NAME = "Alpha"
PACK_ZIP_STEM = "Alpha_MODs"
LEGACY_PACK_ZIP_STEM = "Glimpse_Alpha_MODs"
# The release the rename shipped in. Below it the pack ZIP legitimately still
# carries the old name on disk (downloads/ keeps every past release), so a
# rebuild of an older release must still find its file.
PACK_RENAME_VERSION = (2, 5, 0)


def _version_tuple(version: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", str(version)))


def pack_zip_name(version: str, mc_version: str = "26.2") -> str:
    """The pack ZIP's filename for `version`, derived from the version itself
    rather than typed. Releases from V2.5.0 on are Alpha_MODs_*; older ones
    keep the pre-rename Glimpse_Alpha_MODs_* name they were actually
    published under."""
    stem = (PACK_ZIP_STEM if _version_tuple(version) >= PACK_RENAME_VERSION
            else LEGACY_PACK_ZIP_STEM)
    return f"{stem}_v{version}+mc{mc_version}.zip"


def pack_zip_path(version: str, mc_version: str = "26.2", *, why: str = "This page"):
    """downloads/<the real ZIP for `version`>, or a loud stop.

    Deliberately does NOT fall back to the other brand's filename when the
    expected one is absent: a fallback would let a forgotten `cp` of the new
    ZIP be papered over by a stale identically-versioned file under the old
    name, which is exactly the silent-stale-artifact failure that
    tools/build_dist_zip.py's detect_version() was written to end.
    """
    name = pack_zip_name(version, mc_version)
    p = DOWNLOADS_DIR / name
    if not p.exists():
        raise SystemExit(
            f"ERROR: {p} does not exist. {why} must not describe a file that isn't actually "
            f"in the wiki's served tree - copy the real assembled ZIP "
            f"(tools/build_dist_zip.py) to downloads/{name} before building."
        )
    return p

# Absolute origin+path this site is published at. Needed because Open Graph
# requires an ABSOLUTE og:image URL — a relative one is silently ignored by
# every scraper, which is how a site ends up with no share preview at all.
# (build_glimpse_manifest.py keeps its own copy for the launcher manifest.)
SITE_BASE_URL = "https://iroponcopin.github.io/corvus-dev"
OG_IMAGE_URL = f"{SITE_BASE_URL}/assets/img/brand/og-image.png"

# (code, native display name, text direction). Order = language-switcher order.
LANGUAGES = [
    ("ja", "日本語", "ltr"),
    ("en", "English", "ltr"),
    ("es", "Español", "ltr"),
    ("fr", "Français", "ltr"),
    ("zh", "简体中文", "ltr"),
    ("ko", "한국어", "ltr"),
    ("pt-br", "Português (Brasil)", "ltr"),
    ("it", "Italiano", "ltr"),
    ("ar", "العربية", "rtl"),
    ("ru", "Русский", "ltr"),
    ("id", "Bahasa Indonesia", "ltr"),
    ("de", "Deutsch", "ltr"),
    ("tr", "Türkçe", "ltr"),
]
LANG_CODES = [c for c, _, _ in LANGUAGES]
LANG_NAME = {c: n for c, n, _ in LANGUAGES}
LANG_DIR = {c: d for c, n, d in LANGUAGES}

# The BCP-47 tag written into hreflang, which is NOT the same string as the
# path segment. Path segments are lowercase because they are directory names;
# hreflang wants a properly cased language-REGION tag, so /pt-br/ is advertised
# as "pt-BR". Google is lenient about the casing but the spec is not, and the
# validators the owner is likely to run flag it.
#
# zh is advertised as plain "zh", not "zh-Hans", ON PURPOSE: the bundle is
# Simplified, but the site WANTS every Chinese reader on that page (there is no
# Traditional version to send anyone to), and "zh-Hans" would tell a search
# engine to withhold it from Traditional-preferring users.
HREFLANG_TAG = dict({c: c for c in LANG_CODES}, **{"pt-br": "pt-BR"})

# The 10 modules of the suite, in the order they were introduced. Colors are
# used as accent hues across nav tags, recipe category tabs, and changelog mod
# badges. Names/taglines are looked up per-language from the bundle's ui.mods;
# "key" here is also the lookup key into that dict.
#
# "cat" is this module's primary recipe-category tab, **by name**, resolved
# against data/recipes.json at build time by recipe_cat_index() below.
# ⚠ It used to be a hard-typed integer, and that broke silently the moment a
#   10th tab appeared: backrooms (0 recipes) carried cat_index 9 as a
#   deliberate "points at a tab that does not exist", and when 二相楽園
#   became tab 9 the backrooms card on the home page started deep-linking
#   into Planarcadia's recipes. Nothing errored; the link just went somewhere
#   wrong. Names are resolved, and an unknown name stops the build.
#   cat=None means "this module has no recipe tab" -> the card links to the
#   recipes page with no hash instead of to a wrong tab.
# deco also has a secondary "ドア" category, not linked here for simplicity.
MOD_ORDER = [
    {"id": "sorakaze_guns", "key": "guns", "color": "#c0533a", "cat": "銃"},
    {"id": "sorakaze_rail", "key": "rail", "color": "#3d7dc4", "cat": "電車"},
    {"id": "sorakaze_deco", "key": "deco", "color": "#4f8f43", "cat": "建材"},
    {"id": "sorakaze_boss", "key": "boss", "color": "#9349b8", "cat": "ボス"},
    {"id": "sorakaze_sky", "key": "sky", "color": "#3badc9", "cat": "天空"},
    {"id": "sorakaze_survival", "key": "survival", "color": "#c19a2e", "cat": "サバイバル"},
    {"id": "sorakaze_vehicles", "key": "vehicles", "color": "#d17a34", "cat": "乗り物"},
    {"id": "sorakaze_power", "key": "power", "color": "#d4b32e", "cat": "電力"},
    {"id": "sorakaze_backrooms", "key": "backrooms", "color": "#7d7d52", "cat": None},
    # V2.0.0 で初出荷。V2.1.0 まで、このサイトのどこにも載っていなかった。
    {"id": "sorakaze_planarcadia", "key": "planarcadia", "color": "#b0559b", "cat": "二相楽園"},
]
MODS_BY_ID = {m["id"]: m for m in MOD_ORDER}
MODS_BY_KEY = {m["key"]: m for m in MOD_ORDER}

_cat_index_cache: dict | None = None


def recipe_cat_index(cat_name):
    """data/recipes.json の "cats" から、ジャンル名 -> タブ番号を引く。

    番号を書き写さない。書き写した瞬間に、ジャンルが 1 つ増えた日に
    どこかのリンクが黙って別のジャンルを指す(実際そうなった)。
    知らない名前は **例外で止める** —— 静かに 0 番へ落とさない。
    """
    global _cat_index_cache
    if cat_name is None:
        return None
    if _cat_index_cache is None:
        p = ROOT / "data" / "recipes.json"
        cats = json.loads(p.read_text(encoding="utf-8"))["cats"]
        _cat_index_cache = {c[0]: i for i, c in enumerate(cats)}
        if not _cat_index_cache:
            raise SystemExit(f"ERROR: {p} lists no recipe categories at all - every deep link "
                             f"below would resolve to nothing")
    if cat_name not in _cat_index_cache:
        raise SystemExit(
            "ERROR: MOD_ORDER names recipe category %r, which is not a tab in data/recipes.json "
            "(tabs: %s). Re-run scripts/extract_recipes.py, or fix the name - a deep link to a "
            "non-existent tab fails silently in the browser."
            % (cat_name, ", ".join(_cat_index_cache)))
    return _cat_index_cache[cat_name]

# slugs are relative to EACH LANGUAGE's own root (no leading slash!). GitHub
# Pages serves this repo at https://<user>.github.io/corvus-dev/, not
# the domain root, so every link in this site is prefix-relative.
NAV_SECTIONS = [
    ("home", ""),
    ("aureum", "aureum/"),
    # V4.3.8. Cherry — above Alpha (owner, 2026-09-10), and since 2026-09-12
    # BELOW OUKA: the line is OUKA → Cherry → Alpha. Sits beside Aureum in the
    # Store group for the same reason: it is its own product, not part of the
    # Alpha pack's get-started flow.
    ("cherry", "cherry/"),
    # 2026-09-12、所有者:「新ブランドOUKAを展開 / ブランド名称:英→OUKA、漢→桜花 /
    # ブランド位置:OUKA→Cherry→Alpha(※左から順に上位ブランド)
    # (Aureum は別ジャンル Mods なので含まれない)」。OUKA は Cherry の上位、
    # すなわちブランド線の最上位に立つ。
    ("ouka", "ouka/"),
    # 2026-10-14: the Store group (NAV_GROUPS) has listed astraea, tsubomi and halia since their releases, but no
    # section entry ever named them, so any build that drew the legacy menu (build_ouka.py for OUKA 1.6.2) died
    # with KeyError. Their pages are the portal's (astraea/, tsubomi/, halia/), served at these addresses.
    ("astraea", "astraea/"),
    ("tsubomi", "tsubomi/"),
    ("halia", "halia/"),
    # 2026-09-10、所有者:「Aureum と Cherry、Alpha のページを作成して、
    # それを Store という新規のタブを作成して、メガメニューに 3 つの Mods を
    # 表示する。」Alpha はこれまで<b>ブランドのページを持っていなかった</b> ——
    # ダウンロード導線(download/)はあっても「Alpha とは何か」の 1 枚が無かった。
    # 2026-09-28 (owner: 「Alphaは公式に配信を終了したことを記載し、抹消」): Alpha's brand page, install
    # guide, gates, features, roadmap and known-issues are gone from the navigation and from the site.
    # alpha/ still exists as ONE page, the official notice that distribution has ended (build_alpha.py);
    # it is reached from the download, changelog and launcher pages, not from the menu.
    ("download", "download/"),
    ("changelog", "changelog/"),
    ("recipes", "recipes/"),
    ("launcher", "launcher/"),
    ("upcoming", "upcoming/"),
    ("discord", "discord/"),
    # V4.3.0. The Sparxie skin, behind its PIN. Filed under "start" with the
    # download/launcher/guide: it is a thing you fetch and install, not a
    # reference page and not a status page.
    ("skin", "skin/"),
]

# English fallback nav labels, used only when a language bundle doesn't
# (yet) carry a translated ui.nav[key] entry. All 13 languages have had
# full nav translations since launch, but a newly-added section (like
# "launcher") lands in en/ja first — see load_bundle()/available_langs()
# for the equivalent "English default" convention used throughout the
# per-page build scripts (e.g. build_download.py's dl.get(key, "...")).
NAV_LABEL_FALLBACK = {
    "launcher": LAUNCHER_APP_NAME,
    # "Aureum" is a proper noun (the mod's own name, not a description of it),
    # same category as LAUNCHER_APP_NAME above -- translating a brand name into
    # 11 more scripts would not produce 11 more correct answers, it would
    # produce 11 wrong ones. ui.nav.aureum is intentionally left unset in every
    # language bundle; this is the ONE string on the new page that is allowed
    # to fall back this way (see build_aureum.py's header for why every other
    # string on that page has a real translation in all 13 languages).
    "aureum": "Aureum",
    # Same reasoning as "aureum": a brand name, not a description. Translating
    # it into 11 more scripts would produce 11 wrong answers, not 11 right ones.
    "cherry": "Cherry",
    # Same reasoning again: "Alpha" is the pack's own name.
    "alpha": "Alpha",
    # And again for "OUKA". The owner gave the brand two names -- 英→OUKA,
    # 漢→桜花 -- and neither is a description that could be translated; the
    # Latin one is the one that goes in the navigation, in every language.
    "ouka": "OUKA",
    # And for "ASTRAEA" (V1.0.0, 2026-09-30): the brand's own name, never translated.
    "astraea": "ASTRAEA",
    # And "Tsubomi" (V1.0.0, 2026-09-30): the Latin name goes in the navigation, as OUKA's
    # does; the portal shows 蕾 itself, so the label never needs it.
    "tsubomi": "Tsubomi",
    # Halia (V1.0.0, 2026-10-11), the top line ("The Max Model").
    "halia": "Halia",
    "upcoming": "Coming next",
    # Same arrangement as "upcoming": the nav label falls back to English
    # until the bundles carry ui.nav.discord, while the page itself is fully
    # translated in all 13 (data/discord_bot.json).
    "discord": "Discord bot",
    # Same arrangement as "upcoming" / "discord": the label falls back to
    # English until the bundles carry ui.nav.skin; the page itself is written
    # in ja/en and falls back to English elsewhere (build_skin_gate.py).
    "skin": "Sparxie skin",
}

# --- Mega menu -------------------------------------------------------------
# The nine sections above are grouped into three hover-revealed panels plus a
# standalone Home link. Every section in NAV_SECTIONS must appear exactly
# once here or in NAV_SOLO — _nav_html() asserts that, so adding a new page
# without filing it can't silently drop it out of the navigation.
# "aureum" sits in NAV_SOLO, not in a mega-menu group, on purpose: Aureum is a
# separate, independently-versioned product (its own repo, its own download,
# reviewed as its own thing on the Download page) that this page exists to
# showcase on its own terms -- exactly the same reasoning that put "home"
# here instead of under a panel. Burying a dedicated premium landing page one
# hover-menu level down would undercut the very thing the owner asked for
# ("非常に洗練された状態" -- see build_aureum.py). It is NOT filed under the
# "start" group's download/launcher/guide (that group is specifically the
# Alpha pack's own get-started flow) nor under "reference" (Aureum has no
# recipes/gates/features of its own) nor "status" (it has no changelog page
# of its own yet) -- it simply does not belong to any of those three stories.
NAV_SOLO = ["home"]
NAV_GROUPS = [
    # Store: the mod brands, side by side. Aureum and Cherry used to sit in
    # NAV_SOLO as one-offs; the owner asked for them under one tab so a reader
    # can see the range at a glance instead of discovering them apart.
    #
    # ★ The ORDER is the owner's, and it is not alphabetical and not historical
    #   (2026-09-12, verbatim): 「ブランド位置:OUKA→Cherry→Alpha
    #   (※左から順に上位ブランド)(Aureum は別ジャンル Mods なので含まれない)」
    #   -- so the brand line reads top-tier first, and AUREUM IS NOT IN THAT
    #   LINE. It is a different genre with its own version line, so it sits
    #   last, after the three that are ranked against each other, rather than
    #   being interleaved with them where its position would read as a rank.
    #   2026-09-30: ASTRAEA V1.0.0 joins the line after Aureum, in the portal's own Store order
    #   (corvus-web/lib/products.ts STORE_ORDER: ouka, cherry, aureum, astraea, ...), so the changelog's
    #   tabs and the Store cannot disagree. ASTRAEA has no compatibility with Alpha (owner, D-1).
    #   2026-09-30: Tsubomi V1.0.0 follows ASTRAEA, in the same order as the portal's STORE_ORDER.
    #   Tsubomi is not compatible with Alpha either (the owner; its jar declares it).
    #   2026-10-11: Halia V1.0.0 is added at the end here; the portal orders its own menus (Halia first).
    ("store", ["ouka", "cherry", "aureum", "astraea", "tsubomi", "halia"]),
    ("start", ["download", "launcher", "skin"]),
    ("reference", ["recipes"]),
    # "upcoming" sits with changelog/roadmap because it answers the same
    # question at a different distance: changelog = what shipped, upcoming =
    # what is next, roadmap = the long view.
    # "discord" sits with them because it answers the same family of question
    # from the other side: changelog/upcoming/roadmap say what happened and
    # what is next, issues says what is broken, and the Discord page is how a
    # server hears those things as they happen -- and how a player tells us
    # about the one that is broken. It is NOT under "start": you do not need
    # Discord to install or play the pack.
    ("status", ["changelog", "upcoming", "discord"]),
]

# English fallbacks for the group heading + one-line blurb shown in each
# panel. Japanese lives in data/i18n/ja.json -> ui.nav_groups; the other 12
# languages fall back to English here,
# exactly the way NAV_LABEL_FALLBACK["launcher"] already does.
NAV_GROUP_FALLBACK = {
    # 2026-09-10、所有者:「Store という新規のタブを作成して、メガメニューに
    # 3 つの Mods を表示する。」
    "store": {
        "label": "Store",
        # The brand line in the owner's own order, and nothing else about it.
        # No feature claim and no status belongs here: OUKA has no published
        # build, and a lede that hinted at one would be a promise the site
        # cannot keep. Aureum is named apart because it is not ranked against
        # the other three.
        "lede": "The brand line, from the top: OUKA, then Cherry. "
                "Aureum stands apart, in a genre of its own.",
    },
    "start": {
        "label": "Get started",
        "lede": "Get %s, and let it keep every mod up to date." % LAUNCHER_APP_NAME,
    },
    "reference": {
        "label": "Reference",
        "lede": "Every crafting recipe for Cherry and OUKA.",
    },
    "status": {
        "label": "Status",
        "lede": "What shipped in each release, what is planned next, and how to hear about it "
                "on Discord.",
    },
}


def esc(s) -> str:
    return _html.escape(str(s), quote=True)


_bundle_cache: dict[str, dict] = {}


def module_counts() -> tuple[int, int]:
    """(このスイートの MOD 数, 導入に要る jar の数)。出典は data/versions.json。

    ⚠ 数を文章に**書かない**ための関数である。V2.0.0 で 10 個目(二相楽園)が
      出荷されたのに、13 言語ぶんの本文・導入手引き・レシピ頁の見出しが
      「9」と書いたまま公開され続けた。人が 13 言語を追いかけて直す作業に
      なっているかぎり、11 個目でも同じことが起きる。
    """
    p = ROOT / "data" / "versions.json"
    mods = json.loads(p.read_text(encoding="utf-8"))["mods"]
    n = len(mods)
    if n < 2:
        raise SystemExit(
            f"ERROR: {p} lists {n} module(s). That is not a small suite - it means "
            f"scripts/extract_versions.py did not see the dist/ jars, and every page would "
            f"publish a wrong module count with no error.")
    return n, n + 1          # +1 = Fabric API


def pack_version() -> str:
    """現在配布中のパックのバージョン(例 "2.4.8")。出典は data/versions.json。

    module_counts() と同じ規律: バージョン番号を 13 言語の文面に**書かない**。
    i18n 文字列側は {pack_version} プレースホルダを使う。ダウンロード頁が
    2.4.8 の ZIP を配りながら本文が「最新版は V2.2.0」と言い続けた実績がある。
    """
    p = ROOT / "data" / "versions.json"
    mods = json.loads(p.read_text(encoding="utf-8"))["mods"]
    versions = set(mods.values())
    if len(versions) != 1:
        raise SystemExit(
            f"ERROR: data/versions.json lists more than one distinct version {sorted(versions)} - "
            f"a single {{pack_version}} placeholder cannot be filled from a mixed release.")
    return versions.pop()


# ---------------------------------------------------------------------------
# Launcher release discovery
#
# ⚠ This lives here, shared, on purpose. build_download.py and
#   build_glimpse_manifest.py each used to carry their own private copy of
#   "find the launcher jar", and both copies had the same two defects:
#
#     1. They globbed "glimpse-launcher-*.jar". The app was renamed to
#        Corvus in 1.3.0 and its files became corvus-1.3.0.*, so the glob
#        matched nothing — and because a missing jar is a *supported* state
#        ("no launcher published yet"), the manifest would have quietly
#        shipped with no "launcher" block at all and every installed
#        launcher's self-update would have gone dark. No error, no warning.
#     2. They took sorted(...)[0] — the lexicographically FIRST match, not
#        the newest. That is correct only while exactly one jar sits in the
#        folder. With two present it advertises the OLDER one, and by string
#        order "1.10.0" < "1.2.1", so the first double-digit minor release
#        would have silently downgraded every user.
#
#   Both names are matched (the pre-rename files are still served), and the
#   winner is chosen by a parsed NUMERIC version tuple.
# ---------------------------------------------------------------------------
LAUNCHER_JAR_PREFIXES = ("corvus", "glimpse-launcher")
_LAUNCHER_JAR_RE = re.compile(
    r"^(?P<prefix>corvus|glimpse-launcher)-(?P<version>\d+(?:\.\d+)*)\.jar$")

# Keep in sync with the platform table in build_download.py /
# build_glimpse_manifest.py: (platform_id, extension, human label).
NATIVE_LAUNCHER_PLATFORMS = [
    ("macos", "dmg", "macOS"),
    ("windows", "msi", "Windows"),
    ("linux", "deb", "Linux"),
]


def launcher_version_key(version: str) -> tuple[int, ...]:
    """"1.10.0" -> (1, 10, 0). Numeric, so 1.10.0 > 1.2.1 — which is exactly
    what plain string sorting got wrong."""
    return tuple(int(p) for p in version.split("."))


def find_launcher_jars(download_dir: Path | None = None) -> list[dict]:
    """Every published launcher jar, newest first."""
    d = DOWNLOADS_DIR if download_dir is None else download_dir
    if not d.is_dir():
        return []
    found = []
    for p in d.iterdir():
        if not p.name.endswith(".jar"):
            continue
        if not p.name.startswith(tuple(f"{x}-" for x in LAUNCHER_JAR_PREFIXES)):
            continue
        m = _LAUNCHER_JAR_RE.match(p.name)
        if not m:
            raise SystemExit(
                f"ERROR: {p} looks like a launcher jar but does not match "
                f"<{'|'.join(LAUNCHER_JAR_PREFIXES)}>-<numeric.version>.jar. Refusing to guess "
                f"its version - rename it or the download page and the manifest would disagree "
                f"about what the current release is.")
        found.append({
            "version": m.group("version"),
            "key": launcher_version_key(m.group("version")),
            "prefix": m.group("prefix"),
            "path": p,
            "file_name": p.name,
        })
    found.sort(key=lambda r: r["key"], reverse=True)
    return found


def newest_launcher_jar(download_dir: Path | None = None) -> dict | None:
    """The launcher release this site currently advertises, or None if the
    downloads folder holds no launcher jar at all.

    Two files parsing to the SAME version (e.g. both a corvus-1.3.0.jar and a
    leftover glimpse-launcher-1.3.0.jar) is refused rather than resolved by
    coin-flip: which one wins would decide the download URL every installed
    launcher polls for.
    """
    found = find_launcher_jars(download_dir)
    if not found:
        return None
    top = [r for r in found if r["key"] == found[0]["key"]]
    if len(top) > 1:
        raise SystemExit(
            "ERROR: downloads/ holds %d launcher jars that all parse to version %s (%s). "
            "Exactly one file must be the current release - delete the stale one."
            % (len(top), top[0]["version"], ", ".join(sorted(r["file_name"] for r in top))))
    return found[0]


def launcher_native_files(version: str, download_dir: Path | None = None) -> list[dict]:
    """Native installers actually present on disk for `version`, in display
    order. Matches whichever of the two name prefixes is really there, so a
    half-migrated downloads/ folder still resolves instead of silently
    reporting "no native builds"."""
    d = DOWNLOADS_DIR if download_dir is None else download_dir
    out = []
    for platform_id, ext, label in NATIVE_LAUNCHER_PLATFORMS:
        for prefix in LAUNCHER_JAR_PREFIXES:
            candidate = d / f"{prefix}-{version}-{platform_id}.{ext}"
            if candidate.exists():
                out.append({
                    "platform_id": platform_id,
                    "label": label,
                    "path": candidate,
                    "file_name": candidate.name,
                    "size_bytes": candidate.stat().st_size,
                })
                break
    return out


def _launcher_placeholders() -> tuple[str, str]:
    """(jar file name, version) for the {launcher_jar}/{launcher_version}
    placeholders. Same rule as {pack_version}: the number is NEVER typed into
    a translated string, it is read off the file actually being served."""
    rel = newest_launcher_jar()
    if rel is None:
        print("WARNING: downloads/ has no launcher jar - {launcher_jar}/{launcher_version} "
              "fall back to a generic name. Publish a launcher build before relying on this copy.")
        return f"{LAUNCHER_APP_NAME.lower()}.jar", "latest"
    return rel["file_name"], rel["version"]


def _fill_counts(node, subs: dict):
    if isinstance(node, dict):
        return {k: _fill_counts(v, subs) for k, v in node.items()}
    if isinstance(node, list):
        return [_fill_counts(v, subs) for v in node]
    if isinstance(node, str):
        for k, v in subs.items():
            node = node.replace(k, v)
        return node
    return node


_placeholder_cache: dict | None = None


def bundle_placeholders() -> dict:
    """The values substituted into every translated string at load time.

    Every entry here exists so a number or a file name is never typed into 13
    language bundles by hand — the class of bug this codebase has already
    been burned by twice (a "9 MODs" count that outlived the 10th module, and
    a "latest is V2.2.0" line shipping next to a V2.4.8 ZIP). {launcher_jar}
    and {launcher_version} joined for the same reason: the install
    instructions used to spell out glimpse-launcher-1.2.1.jar in both the EN
    and JA bundles, so the Corvus 1.3.0 rename would have left two languages
    telling people to run a file that no longer exists.
    """
    global _placeholder_cache
    if _placeholder_cache is None:
        n_mods, n_jars = module_counts()
        jar_name, jar_version = _launcher_placeholders()
        _placeholder_cache = {
            "{mod_count}": str(n_mods),
            "{jar_count}": str(n_jars),
            "{pack_version}": pack_version(),
            "{launcher_app}": LAUNCHER_APP_NAME,
            "{launcher_jar}": jar_name,
            "{launcher_version}": jar_version,
        }
    return _placeholder_cache


def fill_placeholders(node):
    """Run the same {pack_version}/{launcher_jar}/... substitution over
    content that did NOT come from a language bundle — specifically the
    English fallback copy the per-page build scripts carry inline, which
    must not be allowed to state a version the bundles no longer state."""
    return _fill_counts(node, bundle_placeholders())


def load_bundle(lang: str) -> dict:
    if lang not in _bundle_cache:
        p = I18N_DIR / f"{lang}.json"
        _bundle_cache[lang] = _fill_counts(
            json.loads(p.read_text(encoding="utf-8")), bundle_placeholders())
    return _bundle_cache[lang]


def available_langs() -> list[str]:
    """Languages that actually have a bundle on disk yet (lets pages render
    JA-only during development before translations land)."""
    return [c for c in LANG_CODES if (I18N_DIR / f"{c}.json").exists()]


def retirement(product: str) -> dict:
    """data/retirement.json's block for `product`, or {} when that product has no block.

    One reader for every retired product (2026-09-28 Alpha; 2026-10-16 ASTRAEA, a notice rather than an erasure).
    The file is the one place that says what is retired, so no builder keeps its own copy of the dates.
    """
    p = ROOT / "data" / "retirement.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get(product) or {}


def alpha_retirement() -> dict:
    """data/retirement.json's "alpha" block, or {} when Alpha has not been retired.

    2026-09-28 (owner: 「Alphaは廃止されます。Alphaを無効化するアップデートを行なってください」).
    The retirement release is 13 placeholder jars, so it carries no recipes, textures or names: the
    builders and checkers that read "the newest pack zip" must know that, or they stop (extract_recipes.py)
    or compare the recipe sheet against a version it was never meant to be generated from
    (check_recipe_sources.py). One file says it; every reader goes through here.
    """
    block = retirement("alpha")
    if block.get("retired"):
        missing = [k for k in ("retired_version", "last_playable") if not str(block.get(k, "")).strip()]
        if missing:
            raise SystemExit(f"ERROR: data/retirement.json says Alpha is retired but has no {', '.join(missing)}.")
    return block


def alpha_retired_for(version: str) -> bool:
    """True when `version` is the retirement release (the pack the site is distributing now)."""
    block = alpha_retirement()
    return bool(block.get("retired")) and str(version) == str(block.get("retired_version"))


def load_changelog_structural(path=None) -> list:
    """data/changelog.json, with the identity of every entry validated.

    ⚠ `(release, date)` is NOT a unique key here and never was. Two pairs share
      one — v1.3.2/2026-07-22 and v1.8.0/2026-08-04 — and a third label,
      v1.4.0, carries three entries on three different dates. Both readers of
      this file used to build `{(release, date): translation}` as a dict, so
      for those two pairs the SECOND translation silently won and rendered
      against BOTH structural entries. On all 13 published pages, v1.8.0's
      "Renamed to Glimpse Alpha" entry — the one explaining why the jar
      filenames changed — was replaced by a second copy of the config
      auto-repair text, wearing the rename's release badge. Nothing went red:
      the entry count was right, the badges were right, the dates were right,
      and both entries were fluent prose in the reader's own language.

      Every entry therefore carries an explicit `id`, assigned once and never
      recomputed, and that — not (release, date) — is what a translation is
      matched on. Appending a second entry for an existing release never
      forces the first one to be renamed, so ids are stable across the file's
      whole future.

    Both consumers go through this function and index_bundle_changelog()
    below, so there is exactly one place where an entry's identity is decided.
    """
    p = ROOT / "data" / "changelog.json" if path is None else Path(path)
    if not p.exists():
        return []
    structural = json.loads(p.read_text(encoding="utf-8"))
    missing = [f"{e.get('release')}({e.get('date')}) at index {i}"
               for i, e in enumerate(structural) if not e.get("id")]
    if missing:
        raise SystemExit(
            f"ERROR: {p} has {len(missing)} changelog entr(ies) with no 'id': "
            + ", ".join(missing[:6])
            + "\n  Every entry needs a stable unique id — it is what each language's "
              "translation is matched on. (release, date) is NOT unique in this file and "
              "keying on it published one entry twice under two different badges in all 13 "
              "languages. Give the new entry an id: the release label lowercased, or "
              "'<release>-<what-it-is>' if that label is already taken.")
    dupes = sorted({i for i, c in Counter(e["id"] for e in structural).items() if c > 1})
    if dupes:
        raise SystemExit(
            f"ERROR: {p} has duplicate changelog id(s): {', '.join(dupes)}.\n"
            f"  Two entries sharing an id is the exact defect the id was introduced to "
            f"remove: one of them would take the other's translation and both would render "
            f"as the same text under different badges.")
    return structural


def index_bundle_changelog(bundle: dict, lang: str = None) -> dict:
    """{id: translated entry} for one language bundle.

    An entry with no id cannot be matched to anything and is skipped: the
    structural entry it was meant for then falls back to the Japanese source,
    which is VISIBLE on the page, rather than being paired with a neighbour's
    prose, which is not. Duplicate ids stop the build for the same reason
    load_changelog_structural() does.
    """
    entries = bundle.get("changelog") or []
    by_id, keyless = {}, 0
    for t in entries:
        if not t.get("id"):
            keyless += 1
            continue
        by_id.setdefault(t["id"], []).append(t)
    dupes = sorted(i for i, group in by_id.items() if len(group) > 1)
    if dupes:
        raise SystemExit(
            f"ERROR: data/i18n/{lang or bundle.get('lang')}.json has duplicate changelog "
            f"id(s): {', '.join(dupes)}. One translation would silently replace the other.")
    if keyless:
        print(f"  NOTE [{lang or bundle.get('lang')}] {keyless} changelog entr(ies) carry no "
              f"'id' and cannot be matched — they will render in Japanese. Re-run "
              f"scripts/extract_bundle.py (ja) or re-key the translation.")
    return {i: group[0] for i, group in by_id.items()}


def load_latest_changelog_entry(bundle: dict):
    """The newest changelog entry, with translated strings merged in from the
    bundle (falling back to the JA structural file for release/date/type/
    mod_versions, which never need translation).

    Lived in build_home.py until the home page was reduced to the wordmark +
    film and stopped rendering a "latest update" teaser at all. It is here,
    not in build_download.py, because a cross-import between two page
    builders is exactly how a helper ends up deleted out from under its only
    remaining caller.

    ⚠ "Latest" is selected by (date, parsed release version), NOT by file
      position: data/changelog.json once had newer entries hand-prepended at
      the top, and structural[-1] silently promoted V2.4.1 to "latest update"
      while the download page shipped V2.4.8.

    ⚠ The translation is looked up by `id`, not by (release, date). This
      function used to carry the identical dict-collapse build_changelog.py
      did, and was harmless only because the two colliding pairs happen to be
      old: the day a duplicate pair became the newest entry, the download
      page's "what's new" teaser would have shown the wrong one's prose under
      the right one's version number.
    """
    structural = load_changelog_structural()
    if not structural:
        return None
    by_id = index_bundle_changelog(bundle)

    def _key(e):
        return (e.get("date", ""),
                tuple(int(n) for n in re.findall(r"\d+", str(e.get("release", "")))))

    s = max(structural, key=_key)
    t = by_id.get(s["id"], s)
    merged = dict(s)
    merged.update({k: t[k] for k in ("title", "summary", "highlights") if k in t})
    return merged


def mod_badge(bundle: dict, mod_id: str, small: bool = False) -> str:
    m = MODS_BY_ID.get(mod_id)
    if not m:
        return ""
    name = bundle["ui"]["mods"].get(m["key"], {}).get("name", m["key"])
    cls = "mod-badge mod-badge--sm" if small else "mod-badge"
    return f'<span class="{cls}" style="--mod-color:{m["color"]}">{esc(name)}</span>'


def type_badge(bundle: dict, t: str) -> str:
    label = bundle["ui"]["type_badge"].get(t, t)
    # "disclosure" (added for the "previously undocumented mechanics" changelog
    # entry) reuses the neutral info style -- it isn't a new feature (green) or
    # a fix (red), so it shouldn't read as either.
    cls = {
        "release": "type-release",
        "hotfix": "type-hotfix",
        "visual-update": "type-visual",
        "disclosure": "type-visual",
    }.get(t, "type-release")
    return f'<span class="type-badge {cls}">{esc(label)}</span>'


def _levels_to_root(depth: int, lang: str) -> int:
    return depth + (0 if lang == "ja" else 1)


def _prefix(levels: int) -> str:
    return "../" * levels if levels else "./"


def asset_root_prefix(depth: int, lang: str) -> str:
    """Public helper for build scripts that need to reference assets/data
    from inside `extra_head` (e.g. a page-specific <script src>) -- must use
    this rather than a hardcoded "../", since non-ja languages sit one
    directory deeper than ja. Mirrors page()'s own root_prefix computation
    exactly; see the recipes.js/changelog.js 404 this fixed (§ commit
    history) for what goes wrong if a build script hardcodes the prefix
    instead of calling this."""
    return _prefix(_levels_to_root(depth, lang))


def _nav_label(bundle: dict, key: str) -> str:
    return bundle["ui"]["nav"].get(key, NAV_LABEL_FALLBACK.get(key, key))


def _nav_group_strings(bundle: dict, gkey: str) -> dict:
    """Group heading + blurb for one mega-menu panel.

    Same English-default convention as NAV_LABEL_FALLBACK: a language that
    has translated ui.nav_groups gets its own strings, everyone else gets
    the English ones rather than a raw key.
    """
    fallback = NAV_GROUP_FALLBACK[gkey]
    got = (bundle["ui"].get("nav_groups") or {}).get(gkey) or {}
    return {
        "label": got.get("label") or fallback["label"],
        "lede": got.get("lede") or fallback["lede"],
    }


def _mega_link_html(bundle: dict, key: str, slug: str, lang_prefix: str, active: str) -> str:
    """One two-line link inside a mega panel.

    The second line reuses ui.page_titles[key] — the fuller name of the same
    page ("ゲート" in the nav bar, "ゲート・門一覧" as the page title) — so the
    panel reads like Apple's (label + short descriptor) without inventing a
    new string that would need 13 translations. It is dropped when the two
    are identical, which is what happens for the languages whose nav label
    and page title are the same word.
    """
    label = _nav_label(bundle, key)
    sub = (bundle["ui"].get("page_titles") or {}).get(key, "")
    sub_html = f'<span class="mega-link__sub">{esc(sub)}</span>' if sub and sub != label else ""
    is_cur = key == active
    cls = "mega-link is-current" if is_cur else "mega-link"
    cur = ' aria-current="page"' if is_cur else ""
    return (f'<li><a class="{cls}" href="{lang_prefix}{slug}"{cur}>'
            f'<span class="mega-link__label">{esc(label)}</span>{sub_html}</a></li>')


def _nav_html(bundle: dict, active: str, lang_prefix: str) -> str:
    """Top-level nav: standalone links + hover-revealed mega-menu panels.

    Guards against a new NAV_SECTIONS entry going unfiled — an unreachable
    page is exactly the kind of silent breakage this file exists to prevent.
    """
    slug_of = dict(NAV_SECTIONS)
    filed = set(NAV_SOLO)
    for _g, keys in NAV_GROUPS:
        filed.update(keys)
    missing = [k for k, _s in NAV_SECTIONS if k not in filed]
    # And the other way round (2026-10-14): a group that names a key no section defines has no address to link to.
    unaddressed = sorted(k for k in filed if k not in slug_of)
    if unaddressed:
        raise SystemExit("ERROR: site_common.NAV_GROUPS/NAV_SOLO name %s, which NAV_SECTIONS gives no address."
                         % ", ".join(unaddressed))
    if missing:
        raise SystemExit(
            "ERROR: site_common.NAV_SECTIONS lists %s, which no NAV_GROUPS group and no "
            "NAV_SOLO entry claims. Those pages would build but be unreachable from the "
            "navigation on all 13 languages." % ", ".join(repr(m) for m in missing))

    items = []
    for key in NAV_SOLO:
        cls = "nav-link nav-link--solo" + (" is-current" if key == active else "")
        cur = ' aria-current="page"' if key == active else ""
        items.append(
            f'<li class="nav-item">'
            f'<a class="{cls}" href="{lang_prefix}{slug_of[key]}"{cur}>'
            f'{esc(_nav_label(bundle, key))}</a></li>')

    for gkey, keys in NAV_GROUPS:
        g = _nav_group_strings(bundle, gkey)
        panel_id = f"mega-{gkey}"
        open_cls = " is-current" if active in keys else ""
        links = "\n            ".join(
            _mega_link_html(bundle, k, slug_of[k], lang_prefix, active) for k in keys)
        items.append(f"""<li class="nav-item nav-item--mega">
          <button class="nav-link nav-link--mega{open_cls}" type="button"
                  aria-expanded="false" aria-haspopup="true" aria-controls="{panel_id}">
            <span>{esc(g['label'])}</span><span class="nav-link__caret" aria-hidden="true"></span>
          </button>
          <div class="mega-panel" id="{panel_id}" role="group" aria-label="{esc(g['label'])}">
            <div class="mega-panel__inner">
              <div class="mega-panel__blurb">
                <p class="mega-panel__title">{esc(g['label'])}</p>
                <p class="mega-panel__lede">{esc(g['lede'])}</p>
              </div>
              <ul class="mega-links">
            {links}
              </ul>
            </div>
          </div>
        </li>""")
    return "\n        ".join(items)


def lang_hrefs(section: str, root_prefix: str) -> list:
    """[(code, href)] for every language that has a bundle, in switcher order.

    ONE definition, used by three things that must agree: the rendered <a href>
    list, the head detector's redirect map, and the hreflang alternates. When
    the detector sends someone to a URL that is not the URL the switcher would
    have linked, you get a redirect loop; the cheapest way to make that
    impossible is for there to be only one place the URL is built.
    """
    langs = available_langs()
    return [(code, root_prefix + ("" if code == "ja" else f"{code}/") + section)
            for code, _n, _d in LANGUAGES if not langs or code in langs]


def _flag_html(code: str) -> str:
    """The flag for one language: emoji primary, with the hook the fallback
    stylesheet needs (see scripts/build_lang_assets.py). aria-hidden because
    the language NAME sits right next to it — "flag of the United Kingdom
    English" is noise in a screen reader."""
    return (f'<span class="lang-flag lang-flag--{code}" aria-hidden="true">'
            f'<span class="lang-flag__emoji">{FLAG_EMOJI[code]}</span></span>')


def _lang_switcher_html(lang: str, section: str, root_prefix: str) -> str:
    items = []
    for code, target in lang_hrefs(section, root_prefix):
        cls = ' class="active" aria-current="true"' if code == lang else ""
        # data-lang is what main.js persists on click; hreflang is a correct
        # (and free) hint to crawlers and assistive tech about what is on the
        # other end of the link.
        items.append(
            f'<li><a href="{target}" data-lang="{code}" '
            f'hreflang="{HREFLANG_TAG[code]}"{cls}>'
            f'{_flag_html(code)}{esc(LANG_NAME[code])}</a></li>')
    return "\n        ".join(items)


def _hreflang_html(section: str) -> str:
    """rel=alternate hreflang for all 13 languages plus x-default.

    Required here, not optional: the head detector can send a visitor from one
    language to another, and a search engine that sees that without a declared
    relationship between the URLs reads it as an ordinary redirect. The
    alternates tell it these are the same page in different languages.

    hreflang wants ABSOLUTE URLs — a relative href is silently ignored, which
    is the failure mode where you ship an hreflang cluster that does nothing at
    all. Every page emits the set for ITS OWN section, so /de/changelog/
    advertises the other twelve changelogs, not the home pages.
    """
    out = []
    for code, _n, _d in LANGUAGES:
        if code not in available_langs():
            continue
        href = f"{SITE_BASE_URL}/" + ("" if code == "ja" else f"{code}/") + section
        out.append(f'<link rel="alternate" hreflang="{HREFLANG_TAG[code]}" '
                   f'href="{esc(href)}">')
    # x-default is the URL for a visitor whose language we do not target. That
    # is the Japanese root: the site's own default, and the only tree the bare
    # domain resolves to.
    out.append(f'<link rel="alternate" hreflang="x-default" '
               f'href="{esc(SITE_BASE_URL)}/{esc(section)}">')
    return "\n".join(out) + "\n"


# The entry-time language detector lives in scripts/lang_detect.py (its
# JavaScript, its resolution order, the argument for why it cannot loop, and
# the SEO caveat about automatic redirection). page() only wires it in.


def page(
    *,
    lang: str,
    section: str,
    title: str,
    description: str,
    active: str,
    body: str,
    depth: int = 0,
    extra_head: str = "",
    og_image: str | None = None,
    og_image_alt: str | None = None,
    absolute_base: str | None = None,
) -> str:
    """Wrap body HTML in the full site shell (head, nav, footer).

    lang: language code (e.g. "ja", "en").
    section: this page's slug relative to its language root ("" for home,
        "changelog/" etc.) — used to build the language-switcher links.
    depth: 0 for the language-root page (home), 1 for a one-level section.
    absolute_base: for the one page that isn't reachable via a predictable
        relative depth (the site-wide 404.html — GitHub Pages serves its
        *content* at whatever broken URL the visitor hit, at any depth, so
        relative asset/nav paths would resolve against the wrong base). Pass
        e.g. "/corvus-dev/" to force every link/asset in the shell to
        an absolute path instead of a depth-relative one.
    """
    bundle = load_bundle(lang)
    ui = bundle["ui"]
    if absolute_base is not None:
        root_prefix = absolute_base
        lang_prefix = absolute_base if lang == "ja" else f"{absolute_base}{lang}/"
    else:
        root_prefix = _prefix(_levels_to_root(depth, lang))
        lang_prefix = _prefix(depth)
    text_dir = LANG_DIR.get(lang, "ltr")

    full_title = f"{title} | {SITE_TITLE}" if title else SITE_TITLE
    # Every page gets a share card. og_image may override it per page, but it
    # must be absolute either way (see OG_IMAGE_URL).
    og_src = og_image or OG_IMAGE_URL
    og_alt = og_image_alt or SITE_TITLE
    og = (f'<meta property="og:image" content="{esc(og_src)}">\n'
          f'<meta property="og:image:width" content="1200">\n'
          f'<meta property="og:image:height" content="630">\n'
          f'<meta property="og:image:alt" content="{esc(og_alt)}">\n'
          f'<meta name="twitter:card" content="summary_large_image">\n    ')
    lang_switch = _lang_switcher_html(lang, section, root_prefix)

    # 404.html gets neither alternates nor the detector. Its content is served
    # by GitHub Pages at whatever broken URL the visitor hit, so its "section"
    # is a fiction: hreflang would advertise twelve URLs that are not
    # translations of what the visitor is looking at, and the detector would
    # bounce someone off an error page to a language home instead of showing
    # them the error. absolute_base is set for exactly that one page.
    if absolute_base is None:
        alternates = _hreflang_html(section)
        detect = lang_detect.head_html(lang, section,
                                       lang_hrefs(section, root_prefix),
                                       root_prefix)
    else:
        alternates = ""
        detect = ""

    return f"""<!doctype html>
<html lang="{lang}" dir="{text_dir}">
<head>
<meta charset="utf-8">
<!-- viewport-fit=cover so env(safe-area-inset-*) is non-zero on notched
     iPhones; every edge-anchored surface (header, drawer, main, footer,
     modal) pads itself with max(gutter, inset) in style.css. -->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE_TITLE)}">
<meta name="theme-color" content="#07090f">
{og}{alternates}<link rel="icon" href="{root_prefix}assets/img/brand/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="{root_prefix}assets/img/brand/favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="{root_prefix}assets/img/brand/favicon-16.png">
<link rel="apple-touch-icon" sizes="180x180" href="{root_prefix}assets/img/brand/apple-touch-icon.png">
<!-- Entry-time language detection + the flag-emoji capability probe. Placed
     AHEAD of the stylesheet links deliberately: a <script> does not execute
     until every preceding stylesheet has loaded, and one of those is a
     third-party fonts.googleapis.com request — a visitor who is about to be
     redirected should not be held behind it. See scripts/lang_detect.py. -->
{detect}<!-- Typography is the Apple system stack (SF Pro on macOS/iOS, Hiragino Sans
     for Japanese) — see style.css. Cormorant Garamond and Zen Kaku Gothic New
     were dropped on owner directive (hard to read), and their font request
     went with them rather than being left behind as a dead download. Inter is
     the cross-platform stand-in for SF and sits after the native names in the
     stack, so on Apple hardware the face files are never fetched at all. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="{root_prefix}assets/css/style.css">
<!-- Flag artwork for the language switcher, used only where the platform
     cannot compose regional-indicator emoji. Generated by
     scripts/build_lang_assets.py; kept out of style.css so a generated file
     and a hand-maintained one never share a build step. -->
<link rel="stylesheet" href="{root_prefix}assets/css/lang-flags.css">
<script>
/* Boot: tag JS availability for the motion layer.

   2026-09-10、所有者:「白と黒のテーマ変更を廃止に。」テーマの切り替えは
   無くなったので、保存も読み出しもしない。データ属性は<b>常に dark</b>で、
   これが唯一の見た目である。以前ここに在った localStorage の移行処理は
   切り替え自体が消えたので不要になった。 */
(function () {{
  var d = document.documentElement;
  d.classList.add("js");
  d.setAttribute("data-theme", "dark");
}})();
</script>
{extra_head}</head>
<body>
<div class="sky" aria-hidden="true"><div class="sky__glow"></div></div>
<a class="skip-link" href="#main">{esc(ui['skip_link'])}</a>
<div class="nav-scrim" id="navScrim" aria-hidden="true"></div>
<header class="site-header">
  <div class="site-header__inner">
    <a class="brand" href="{lang_prefix}">
      <span class="brand__mark" aria-hidden="true"></span>
      <span class="brand__text">{esc(SITE_TITLE)}</span>
    </a>
    <button class="nav-toggle" id="navToggle" aria-expanded="false" aria-controls="siteNav" aria-label="{esc(ui['menu_toggle'])}">
      <span></span><span></span><span></span>
    </button>
    <nav class="site-nav" id="siteNav">
      <ul class="nav-list">
        {_nav_html(bundle, active, lang_prefix)}
      </ul>
      <div class="lang-switch">
        <button class="lang-switch__toggle" id="langToggle" type="button" aria-expanded="false" aria-controls="langMenu" title="{esc(ui['lang_switch_label'])}">
          {_flag_html(lang)}<span>{esc(LANG_NAME.get(lang, lang))}</span>
        </button>
        <ul class="lang-switch__menu" id="langMenu">
          {lang_switch}
        </ul>
      </div>
    </nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="site-footer__inner">
    <p class="site-footer__brand"><span class="brand__mark" aria-hidden="true"></span> {esc(SITE_TITLE)}</p>
    <p>{esc(ui['site_tagline'])}</p>
    <p class="site-footer__note">{esc(ui['footer_note'])}</p>
  </div>
</footer>
<script src="{root_prefix}assets/js/main.js"></script>
</body>
</html>
"""


def out_dir_for(lang: str, section: str) -> Path:
    base = ROOT if lang == "ja" else ROOT / lang
    return (base / section) if section else base


def write_page(lang: str, section: str, html: str):
    out_path = out_dir_for(lang, section) / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path.relative_to(ROOT)} ({len(html):,} bytes)")
