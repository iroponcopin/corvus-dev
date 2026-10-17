#!/usr/bin/env python3
"""Independent audit of the BUILT html for the language switcher: flags,
hreflang alternates, detector config, and the relative paths of the two
generated assets.

  python3 scripts/check_lang_switcher.py          # audits the whole site
  node    scripts/check_lang_switcher.js .        # the behavioural half

Deliberately does NOT import site_common: every expectation below is written
out by hand, so this cannot pass by agreeing with the generator about a shared
mistake. It is NOT wired into build.py — it audits output, so running it as
part of producing that output would be circular. Run it after a build.

Each assertion here has been shown to go RED against a deliberate break:
  * en flag switched GB -> US ............ 154 problems
  * pt-BR hreflang casing dropped ........ 429 problems
  * every page advertising the HOME section 1820 problems
  * lang-flags.css path hardcoded to ../ .. 121 problems
  * one language's fallback artwork removed 1 problem
  * SECTIONS pinned to its old hand-written list .. 39 pages never visited

The sections it audits are discovered from disk (see _discover_sections),
not listed here: the hand-written list fell three sections behind the site
and stayed green about it.
"""
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 \
    else Path(__file__).resolve().parent.parent

# Hand-written, not imported. en is GB by owner directive; ar is SA.
FLAG = {
    "ja": "\U0001F1EF\U0001F1F5", "en": "\U0001F1EC\U0001F1E7",
    "es": "\U0001F1EA\U0001F1F8", "fr": "\U0001F1EB\U0001F1F7",
    "zh": "\U0001F1E8\U0001F1F3", "ko": "\U0001F1F0\U0001F1F7",
    "pt-br": "\U0001F1E7\U0001F1F7", "it": "\U0001F1EE\U0001F1F9",
    "ar": "\U0001F1F8\U0001F1E6", "ru": "\U0001F1F7\U0001F1FA",
    "id": "\U0001F1EE\U0001F1E9", "de": "\U0001F1E9\U0001F1EA",
    "tr": "\U0001F1F9\U0001F1F7",
}
ORDER = ["ja", "en", "es", "fr", "zh", "ko", "pt-br", "it", "ar", "ru", "id", "de", "tr"]
HREFLANG = {c: c for c in ORDER}
HREFLANG["pt-br"] = "pt-BR"
BASE = "https://iroponcopin.github.io/corvus-dev"
# Directories that are not language sections. Named rather than pattern-matched
# so a genuinely new section cannot be skipped by accident.
SKIP_DIRS = {"assets", "data", "scripts", "downloads", "scratchpad",
             "changelog_feed", ".git", ".github", "node_modules"}


def _discover_sections():
    """Every section that actually exists, found on disk.

    This list USED to be typed out here, and had silently fallen three
    sections behind the site: /upcoming/, /v4/ and /discord/ were each built
    in all thirteen languages, and this checker had never looked at one of
    them -- while reporting GREEN over "143 pages". A gate that does not know
    a page exists cannot fail for it, and nothing about that reads as broken.

    Discovering them keeps this file's independence (it still shares no list,
    and no expectation, with site_common) while making the coverage impossible
    to fall behind: a section is checked because it is THERE.
    """
    found = {""}
    for path in sorted(REPO.iterdir()):
        if not path.is_dir() or path.name in SKIP_DIRS or path.name in set(ORDER):
            continue
        if (path / "index.html").is_file():
            found.add(path.name + "/")
    return sorted(found)


SECTIONS = _discover_sections()

problems = []
checks = 0


def bad(msg):
    problems.append(msg)


def page_paths():
    for lang in ORDER:
        for section in SECTIONS:
            rel = ("" if lang == "ja" else lang + "/") + section
            yield lang, section, REPO / rel / "index.html"


def audit(lang, section, path):
    global checks
    if not path.exists():
        bad(f"{path} missing")
        return
    html = path.read_text(encoding="utf-8")
    rel = path.parent.relative_to(REPO).as_posix()
    where = "/" + (rel + "/" if rel != "." else "")

    # --- 1. switcher: 13 rows, right order, right flag, right code ---------
    menu = re.search(r'<ul class="lang-switch__menu"[^>]*>(.*?)</ul>', html, re.S)
    if not menu:
        bad(f"{where}: no language menu at all")
        return
    rows = re.findall(
        r'<a href="([^"]+)" data-lang="([^"]+)" hreflang="([^"]+)"[^>]*>'
        r'<span class="lang-flag lang-flag--([^"]+)"[^>]*>'
        r'<span class="lang-flag__emoji">([^<]+)</span></span>',
        menu.group(1))
    checks += 1
    if [r[1] for r in rows] != ORDER:
        bad(f"{where}: switcher codes {[r[1] for r in rows]} != {ORDER}")
        return
    for href, code, hl, cls, emoji in rows:
        checks += 3
        if emoji != FLAG[code]:
            bad(f"{where}: {code} shows {emoji!r}, expected {FLAG[code]!r}")
        if cls != code:
            bad(f"{where}: {code} row carries class lang-flag--{cls}")
        if hl != HREFLANG[code]:
            bad(f"{where}: {code} anchor hreflang={hl!r}, expected {HREFLANG[code]!r}")
        # the relative href must resolve to a real file on disk
        target = (path.parent / href).resolve() / "index.html"
        checks += 1
        if not target.exists():
            bad(f"{where}: switcher link {href!r} -> {target} does not exist")

    # --- 2. toggle button carries THIS page's flag -------------------------
    tog = re.search(r'<button class="lang-switch__toggle".*?</button>', html, re.S)
    checks += 1
    if not tog or f'lang-flag--{lang}"' not in tog.group(0) or FLAG[lang] not in tog.group(0):
        bad(f"{where}: toggle button does not show the {lang} flag")
    checks += 1
    if tog and "\U0001F310" in tog.group(0):
        bad(f"{where}: toggle button still shows the globe")

    # --- 3. hreflang alternates -------------------------------------------
    alts = re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', html)
    got = dict(alts)
    checks += 1
    if len(alts) != len(got):
        bad(f"{where}: duplicate hreflang entries")
    want = {HREFLANG[c]: f"{BASE}/" + ("" if c == "ja" else c + "/") + section
            for c in ORDER}
    want["x-default"] = f"{BASE}/{section}"
    checks += len(want)
    if got != want:
        for k in sorted(set(want) | set(got)):
            if got.get(k) != want.get(k):
                bad(f"{where}: hreflang {k}: {got.get(k)!r} != {want.get(k)!r}")
    checks += 1
    if any(not v.startswith("http") for v in got.values()):
        bad(f"{where}: a relative hreflang href (silently ignored by crawlers)")

    # --- 4. the two generated assets resolve at this depth ------------------
    for pat, must in ((r'<script src="([^"]*assets/js/lang\.js)"></script>', "assets/js/lang.js"),
                      (r'<link rel="stylesheet" href="([^"]*assets/css/lang-flags\.css)">',
                       "assets/css/lang-flags.css")):
        m = re.search(pat, html)
        checks += 2
        if not m:
            bad(f"{where}: no link to {must}")
            continue
        if not (path.parent / m.group(1)).resolve().exists():
            bad(f"{where}: {m.group(1)!r} does not resolve to a file")

    # --- 5. detector config matches the page it is on ----------------------
    m = re.search(r'__corvusLangInit\((\{.*?\})\);</script>', html, re.S)
    checks += 3
    if not m:
        bad(f"{where}: no detector config")
    else:
        import json
        cfg = json.loads(m.group(1))
        if cfg["c"] != lang:
            bad(f"{where}: detector says lang {cfg['c']!r}")
        if cfg["s"] != section:
            bad(f"{where}: detector says section {cfg['s']!r}, page is {section!r}")
        if sorted(cfg["h"]) != sorted(ORDER):
            bad(f"{where}: detector href table is not the 13 languages")
        # every redirect target the detector can pick must be a real page,
        # and must be the SAME url the switcher links to
        for code, href in cfg["h"].items():
            if not (path.parent / href).resolve().joinpath("index.html").exists():
                bad(f"{where}: detector target {href!r} for {code} is not a page")
            if href != dict((c, h) for h, c, _hl, _cl, _e in
                            [(r[0], r[1], r[2], r[3], r[4]) for r in rows])[code]:
                bad(f"{where}: detector target for {code} differs from the switcher link")

    # --- 6. the script must precede the stylesheets (see lang_detect.py) ----
    checks += 1
    i_js = html.find("assets/js/lang.js")
    i_css = html.find("fonts.googleapis.com/css2")
    if i_js < 0 or i_css < 0 or i_js > i_css:
        bad(f"{where}: lang.js is not ahead of the blocking stylesheets")

    # --- 7. <html lang> agrees with the directory it is in -----------------
    checks += 1
    if not re.search(r'<html lang="%s"' % re.escape(lang), html):
        bad(f'{where}: <html lang> is not "{lang}"')


for lang, section, path in page_paths():
    audit(lang, section, path)

# --- 8. 404 carries neither alternates nor the detector --------------------
h404 = (REPO / "404.html").read_text(encoding="utf-8")
checks += 2
if 'rel="alternate"' in h404:
    bad("404.html emits hreflang alternates for a section it does not have")
if "__corvusLangInit" in h404:
    bad("404.html runs the language detector")

# --- 9. every flag has real artwork in the fallback stylesheet -------------
css = (REPO / "assets/css/lang-flags.css").read_text(encoding="utf-8")
for code in ORDER:
    checks += 2
    m = re.search(r'html\.no-flag-emoji \.lang-flag--%s \{ background-image: url\("(data:[^"]+)"\); \}'
                  % re.escape(code), css)
    if not m:
        bad(f"lang-flags.css has no artwork for {code}")
        continue
    uri = m.group(1)
    if "%3Csvg" not in uri or "viewBox=%270%200%2060%2040%27" not in uri:
        bad(f"lang-flags.css: {code} artwork is not a 60x40 svg")

print(f"{checks} assertions over "
      f"{len(ORDER) * len(SECTIONS)} pages + 404 + the flag stylesheet")
if problems:
    print(f"\nRED — {len(problems)} problem(s):")
    for p in problems[:40]:
        print("  - " + p)
    if len(problems) > 40:
        print(f"  ... and {len(problems) - 40} more")
    sys.exit(1)
print("GREEN")
