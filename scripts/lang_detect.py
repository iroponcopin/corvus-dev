#!/usr/bin/env python3
"""The entry-time language detector: its JavaScript, and the two ways that
JavaScript reaches a page.

It ships as a SHARED file (assets/js/lang.js, written by
scripts/build_lang_assets.py) with a tiny per-page config call inlined in the
<head>. The alternative was inlining the whole thing, which measured +12.6 KB
per page (+4.4 KB gzipped) x 143 pages for code that is byte-identical
everywhere; the shared file costs one same-origin request that the preload
scanner starts in parallel with the two stylesheets already blocking render,
and is cached for the rest of the visit.

Both script tags sit BEFORE the stylesheet links on purpose. A <script> — inline
or external — is not executed until every preceding stylesheet has loaded, and
one of those stylesheets is a third-party Google Fonts request. Putting these
first means a visitor who is about to be redirected is not held behind
fonts.googleapis.com first.
"""
from __future__ import annotations

import json

import lang_regions


# HOW THE RESOLUTION WORKS  (the shipped script below is kept terse on
# purpose: comments here cost nothing, comments in assets/js/lang.js are
# downloaded by every visitor.)
#
#   Order, highest priority first:
#     1  a stored explicit choice ......... wins over everything, forever
#     2  navigator.languages ............... the owner's stated priority
#     3  region, guessed from the IANA timezone then the locale's region
#        subtag ........................... see scripts/lang_regions.py
#     4  nothing -> STAY PUT. On the site root that is Japanese, the
#        documented default. Anywhere else, leaving a visitor on the page
#        they actually asked for beats guessing Japanese at them.
#
# WHERE IT IS ALLOWED TO ACT — this is the whole "never fight the visitor"
# rule, and it is one line: **if document.referrer is same-origin, never
# redirect.** Any in-site navigation (including the switcher itself) is a
# navigation the visitor chose, so it is left alone. That covers the cases the
# main.js click handler cannot: JavaScript off on the previous page, a
# middle-click, "open link in new tab" from the context menu. When such a
# navigation crossed languages within the SAME section — the switcher's exact
# signature, and nothing else on this site links across languages within a
# section — the new language is adopted as the stored choice so it survives to
# the next visit.
#
# WHY IT CANNOT LOOP, two independent legs:
#   (a) `to` is looked up in HREF, which IS the table the switcher's <a href>s
#       are rendered from (lang_hrefs()), so the destination page's own CUR is
#       equal to `to` by construction. On arrival `want === CUR` and the script
#       returns before deciding anything. `stored`, navigator.languages and the
#       timezone are all unchanged by a navigation, so the decision is a fixed
#       point after exactly one step.
#   (b) even if (a) were ever violated by a bad edit, a sessionStorage marker
#       written BEFORE navigating caps a tab at exactly ONE automatic redirect.
#       If sessionStorage is unusable we cannot bound anything, so we do not
#       redirect at all: failing closed beats looping.
#
# FLAG CAPABILITY: a platform that composes regional indicators renders
# U+1F1EF U+1F1F5 as one glyph, so the pair measures about as wide as a single
# indicator; Chrome/Edge on Windows draw two letter-boxes and measure about
# twice as wide. The threshold sits at 1.5x, halfway between the two
# populations. Both raw measurements are published on window.__corvusLang
# so the ratio can be read out of a real browser instead of assumed.
#
# TAG MATCHING is not string equality: en-US / en-GB / en must all reach "en".
#   pt-PT, pt-AO -> pt-br   (Brazilian is the only Portuguese here, and it is a
#                            far smaller gap for a Portuguese reader than
#                            switching them to English)
#   zh-TW, zh-HK, zh-Hant -> zh   (same reasoning; only Simplified exists)
#   in -> id                (the pre-1989 ISO 639 code, still emitted by some
#                            clients)
#
# window.__corvusLang is deliberate, not debris: it is how the resolution
# order is driven with mocked inputs in a test, and it is inert otherwise.
_DETECT_JS = r"""function (C) {
  var LANGS = C.l, HREF = C.h, CUR = C.c, SECTION = C.s;
  /* KEY is a contract with assets/js/main.js — grep "corvus-dev-lang". */
  var KEY = "corvus-dev-lang", ONCE = "corvus-dev-lang-redirected";

  var flagW = null;
  function composesFlags() {
    try {
      var cv = document.createElement("canvas");
      if (!cv.getContext) return false;
      var x = cv.getContext("2d");
      if (!x) return false;
      x.font = "32px sans-serif";
      var pair = x.measureText("\uD83C\uDDEF\uD83C\uDDF5").width;  /* JP flag */
      var one = x.measureText("\uD83C\uDDEF").width;               /* lone RI J */
      flagW = { pair: pair, one: one, ratio: one ? pair / one : null };
      if (!pair || !one) return false;
      return pair < one * 1.5;
    } catch (e) { return false; }
  }
  if (!composesFlags()) document.documentElement.classList.add("no-flag-emoji");

  var maps = {};
  function unpack(name, packed) {
    if (!maps[name]) {
      var m = {}, g = packed.split("|"), i, j, p;
      for (i = 0; i < g.length; i++) {
        p = g[i].split(" ");
        for (j = 1; j < p.length; j++) m[p[j]] = p[0];
      }
      maps[name] = m;
    }
    return maps[name];
  }
  function known(c) { return c && LANGS.indexOf(c) >= 0 ? c : null; }

  function fromTag(t) {
    t = String(t || "").toLowerCase().replace(/_/g, "-");
    if (!t) return null;
    if (known(t)) return t;
    var base = t.split("-")[0];
    if (base === "pt") return known("pt-br");
    if (base === "in") base = "id";
    return known(base);
  }
  function fromDevice(tags) {
    for (var i = 0; i < tags.length; i++) {
      var m = fromTag(tags[i]);
      if (m) return m;
    }
    return null;
  }
  function fromRegion(tz, tags) {
    var i, j, m, parts;
    if (tz) {
      parts = String(tz).split("/");
      m = known(unpack("tz", TZ)[parts[parts.length - 1]]);
      if (m) return m;
      m = known(unpack("ar", AR)[parts[0]]);
      if (m) return m;
    }
    for (i = 0; i < tags.length; i++) {
      parts = String(tags[i] || "").replace(/_/g, "-").split("-");
      for (j = 1; j < parts.length; j++) {
        if (parts[j].length === 2) {
          m = known(unpack("rg", RG)[parts[j].toUpperCase()]);
          if (m) return m;
        }
      }
    }
    return null;
  }

  /* Pure function of `env` so it can be driven with mocked inputs. */
  function resolve(env) {
    var stored = known(env.stored);
    if (stored === CUR) return { act: "stay", why: "stored-is-current" };
    if (env.internal) {
      var adopt = (!env.redirected && env.fromLang && env.fromLang !== CUR &&
                   env.fromSection === SECTION) ? CUR : null;
      return { act: "stay", why: "internal-nav", adopt: adopt };
    }
    var want = stored || fromDevice(env.tags || []) ||
               fromRegion(env.tz, env.tags || []);
    if (!want) return { act: "stay", why: "no-signal" };
    if (want === CUR) return { act: "stay", why: "already-correct" };
    return { act: "go", to: want, why: stored ? "stored" : "detected" };
  }

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { } }

  /* Site root derived, not hardcoded: /corvus-dev/ on Pages, / locally. */
  var here = location.pathname.replace(/index\.html$/, "");
  if (here.charAt(here.length - 1) !== "/") here += "/";
  var tail = (CUR === "ja" ? "" : CUR + "/") + SECTION;
  var base = (tail && here.slice(-tail.length) === tail)
    ? here.slice(0, here.length - tail.length) : here;

  function splitPath(p) {
    p = String(p || "").replace(/index\.html$/, "");
    if (p.charAt(p.length - 1) !== "/") p += "/";
    if (p.indexOf(base) !== 0) return null;
    var rest = p.slice(base.length);
    var i = rest.indexOf("/");
    var head = i < 0 ? "" : rest.slice(0, i);
    if (head && head !== "ja" && LANGS.indexOf(head) >= 0)
      return { lang: head, section: rest.slice(i + 1) };
    return { lang: "ja", section: rest };
  }

  var internal = false, from = null;
  try {
    var ref = document.referrer;
    if (ref && ref.indexOf(location.origin + "/") === 0) {
      internal = true;
      from = splitPath(ref.split("#")[0].split("?")[0].slice(location.origin.length));
    }
  } catch (e) { }

  var nav = window.navigator || {};
  var tags = (nav.languages && nav.languages.length) ? nav.languages
    : (nav.language ? [nav.language] : []);
  var tz = null;
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone; } catch (e) { }

  var redirected = false, ssUsable = true;
  try { redirected = !!window.sessionStorage.getItem(ONCE); }
  catch (e) { ssUsable = false; }

  var env = {
    stored: lsGet(KEY), internal: internal, redirected: redirected,
    fromLang: from && from.lang, fromSection: from && from.section,
    tags: tags, tz: tz
  };
  var decision = resolve(env);
  window.__corvusLang = {
    resolve: resolve, env: env, decision: decision, flagWidths: flagW,
    href: HREF, cur: CUR, section: SECTION, base: base, langs: LANGS
  };

  if (decision.adopt) lsSet(KEY, decision.adopt);
  if (decision.act !== "go") return;
  if (!ssUsable || redirected) return;
  try { window.sessionStorage.setItem(ONCE, "1"); } catch (e) { return; }
  location.replace(HREF[decision.to] + location.search + location.hash);
}"""

# The shared file. `init` is the ONLY name it puts on window besides the
# diagnostic object the detector itself publishes; the per-page call below
# guards on it, so a missing or blocked lang.js degrades to "no detection and
# emoji flags" rather than to a ReferenceError in the head of every page.
JS_GLOBAL = "__corvusLangInit"


def js_file_source() -> str:
    """The whole of assets/js/lang.js."""
    q = json.dumps  # the tables are plain ASCII strings; let json quote them
    return (
        "/* GENERATED by scripts/build_lang_assets.py from scripts/lang_detect.py\n"
        "   and scripts/lang_regions.py - do not edit by hand.\n"
        "\n"
        "   Entry-time language detection + the flag-emoji capability probe.\n"
        "   Loaded from the <head> of every page and called immediately with that\n"
        "   page's own language / section / link table. See scripts/lang_detect.py\n"
        "   for the resolution order, the anti-loop argument and the SEO note.\n"
        "\n"
        "   The three tables below are region guesses, not location data: see\n"
        "   scripts/lang_regions.py for why a static site on GitHub Pages has\n"
        "   nothing better than the device timezone to go on. */\n"
        "window." + JS_GLOBAL + "=(function(){\n"
        "var TZ=" + q(lang_regions.tz_table()) + ";\n"
        "var RG=" + q(lang_regions.region_table()) + ";\n"
        "var AR=" + q(lang_regions.area_table()) + ";\n"
        "return " + _DETECT_JS + ";\n})();\n")


def page_config(lang: str, section: str, links: list) -> str:
    """The per-page config object, as compact JSON."""
    href = {code: target for code, target in links}
    if lang not in href:
        raise SystemExit(
            f"ERROR: page() is rendering language {lang!r} but lang_hrefs() did not "
            f"produce a link for it. The detector would have no URL for the current "
            f"language and could send a visitor to a page that sends them straight "
            f"back.")
    return json.dumps(
        {"l": [c for c, _t in links], "h": href, "c": lang, "s": section},
        ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def head_html(lang: str, section: str, links: list, root_prefix: str) -> str:
    return (f'<script src="{root_prefix}assets/js/lang.js"></script>\n'
            f"<script>window.{JS_GLOBAL}&&{JS_GLOBAL}("
            f"{page_config(lang, section, links)});</script>\n")
