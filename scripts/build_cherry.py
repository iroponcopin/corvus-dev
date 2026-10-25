#!/usr/bin/env python3
"""Builds cherry/index.html — the Cherry brand page, for every language.

Owner directive (2026-09-10, IROHA, verbatim):

    次世代のModsを作りに着手を始めます。
    Modsのブランド名称はCherryです。
    ブランドロゴも桜の花を採用すると共にCorvusの様にWebサイトを開くと
    桜の花びらが回転しながら咲くアニメーションが加えられ、Modsの紹介が
    行われます。
    Alphaの上位ブランドという位置付けになるでしょう。
    Alpha Modsと併用して導入することができますが、バージョンは異なります。
    そしてCorvusランチャーにも対応し、自動でアップデート初回はダウンロード
    ボタンが表示されます。

Second directive (2026-09-10, IROHA, verbatim), after the first page was
rejected — this one governs what the page says and how the mark behaves:

    Cherry は Alpha の上位に置くブランドです。Alpha と併せて導入でき、
    バージョンは別に進みます。
    ブランドの強さを説明するだけで良いです。名前の由来など説明しません。
    Appleも同じようにAppleという名前に言及しないのと同じです。
    妥協しないのは当たり前のことわりなのでわざわざ記載しないでください。
    ブランドイメージが軽くなります。
    ランチャー対応とAlphaと併用できること、そして今の状況という記載の仕方
    ではなく、乞うご期待などに変更してください。
    Cherryロゴが一歳動いていません。これは常時動いているロゴです。
    着手したところです。まだ配布できるビルドはありません。こう言った余計な
    文言は排除してください。書くならプレミア感がある文章を添えるだけです。

--------------------------------------------------------------------------
What the page says — and what it must never say
--------------------------------------------------------------------------
Two things, and nothing else:

  1. Where Cherry sits — said once, as a fact, not argued. Until 2026-09-12
     that was "the tier above Alpha"; OUKA now stands above it, so the line
     reads "the tier between OUKA and Alpha" in all 13 languages. The fact
     did not change — Cherry is still above Alpha — but the old wording left
     a reader believing Cherry was the top of the line, and it no longer is.
  2. The release that is on offer. Until V1.0.0 shipped (2026-09-13) this was
     a closing line in the register of 乞うご期待. Now it is the release itself:
     its version and name, ONE line in the same premium register, the download,
     and the facts a player checks before installing (what it needs, how big
     the file is, its SHA-256). Every figure is read from the file in
     downloads/ and from the fabric.mod.json inside it — none is typed here.

NOT on this page, by the owner's word: where the name comes from; that there
is no compromise (self-evident, and saying it cheapens the brand); that it
works with the Corvus launcher; that it installs alongside Alpha or versions
on its own (「ランチャー対応とAlphaと併用できること、そして今の状況という
記載の仕方ではなく、乞うご期待などに変更してください」 — a rewrite on
2026-09-10 read this backwards and kept both as "capability" cards; they are
gone); any status, progress, "not yet", "coming later", build, or schedule.
A feature list is not on it either: 「ブランドの強さを説明するだけで良いです」
and 「書くならプレミア感がある文章を添えるだけです」 — the install and play
guide travels inside the zip (README.txt), not on the brand page.
Every one of the 13 languages carries its own copy; nothing falls back to English.

--------------------------------------------------------------------------
The release block (2026-09-13, Cherry V1.0.0 "The Lunar Genesis Update")
--------------------------------------------------------------------------
  * The line claims only what a proof has shown. "From the launch pad, to the
    Moon" is flown end to end by a real survival player on a dedicated server
    (cherry-src boot proof B2: Earth pad -> Moon -> the same pad). The loading
    screen being skipped at Y1000 is NOT claimed: nobody has watched it in a
    client yet (risk register R-168), and this site has published an unseen
    claim before.
  * The page refuses to build without a Cherry zip of V1.0.0 or later. The
    pre-release line is gone from the code, so a missing file cannot quietly
    turn a released product back into "coming soon" — it stops the build.
  * The line and the codename were written for one version (COPY_FOR). A newer
    zip in downloads/ stops the build until its own line and name are written,
    so an old line can never be printed over a new release.
  * 2026-09-19, V1.0.1 (the move to Minecraft 26.3, by the owner's
    「Cherry Modsの対応バージョンを26.2から26.3へ」): the line and the codename
    carry over unchanged, and COPY_FOR moved to 1.0.1 with the claim re-proven.
    V1.0.1 adds no content. B2 flew Earth pad -> Moon -> the same pad again on
    26.3, twice, before COPY_FOR moved, so "From the launch pad, to the Moon" is
    shown again for this jar, not inherited.
  * 2026-09-20, V1.1.0 "The Aerospace and Naval Update": the line becomes
    "Into the air, and out to sea." and the codename changes with it. Both halves
    are flown and sailed by gates that run in the release suite, not inferred
    from the feature list: the aircraft take off, fly and land in AircraftTests
    and AirportTests, and a vessel sails a channel under her own autopilot in
    HelmTests and AutopilotTests. The brand line ("the tier between OUKA and
    Alpha") does not change: it is about the brand, not the release.
  * 2026-09-21, V1.1.1: a hotfix -- with Improved Transparency on, lighting the
    Aegis-X afterburner crashed the game (notes 14.65). The line and the codename
    carry over unchanged: the release adds no content, and the flights and voyages
    behind "Into the air, and out to sea." are the same gates, run again for this jar.
  * 2026-09-23, V1.1.2: the ships finished -- their real models and interiors, every
    station usable from the game (in 1.1.0/1.1.1 the railgun, the VLS and the chart
    table had no client sender and could not be used, notes 14.69), two triple
    turrets, salvo/VLS/wake effects and the ferry's bow visor and ramps (notes
    14.67-14.75). The line and the codename carry over: the release finishes the
    voyage "Into the air, and out to sea." promised, proven by the client suite
    twice, 21 ship client controls twice and 27 ship server controls twice.
  * 2026-09-23, the controls (owner: 「飛行機と戦闘機の操作方法と船の操作方法を
    教えてください」「Corvus Webに公開してください」): how to fly the aircraft and
    sail the ships is a page of its own, cherry-controls/ (build_cherry_controls.py),
    because this page carries no play guide (above). This page gains exactly one
    quiet link to it, below the release block and outside it, so the release's one
    link is still the download. The codename span now carries lang="en": the V1.0.0
    codename rendered "GENESİS" under text-transform: uppercase on /tr/.
  * 2026-09-23, V1.1.3 (owner: 「操作を非常に簡単にしてください。視点固定を廃止して、
    誰でも簡単に操縦ができることを条件とします」): the aircraft fly where you look
    and the ships answer to W/A/S/D at the wheel (notes 14.79), the four ship
    defects found while writing the controls page are fixed (notes 14.78), and the
    destroyer's main gun damages what it hits (notes 14.77). The line and the
    codename carry over: the release changes how you fly and sail, not where to,
    and "Into the air, and out to sea." rests on the same gates, run again for this
    jar -- the aircraft take off, fly and land in AircraftTests (with the new
    look-to-fly GA27/GA28) and AirportTests, and a vessel sails a channel in
    HelmTests and AutopilotTests.
  * 2026-09-28, V1.2.0 "Celestial Crucible & Tactical Superiority" (the V1.2.0
    specification; owner 2026-09-27: 「仮のままで良いです」): the line becomes
    "Beyond the Moon, to Mars." and the codename changes with it. The line claims
    only what the MARS client test shows: the Apex-1's Stellar Navigation console
    sends the rocket from the Earth pad to Mars, the thin air burns on the way
    down, and it lands on the red ground at 0.38 g (MarsClientTest; MarsTests;
    notes 1.24-1.32).
  * The download button is in the brand's own colours, the way the Aureum page
    carries its own gold one; its label, "File size" and "SHA-256" are the
    Download page's own translations (data/i18n/<lang>.json "download"), with
    no fallback.
  * Versions, the size and the hash carry dir="ltr": on the Arabic page bidi
    mirroring would print "≥" as "≤" and reorder "0.154.2+26.2".
  * scripts/check_cherry_release.py judges the rendered pages against the file
    independently (it imports nothing from here) and is run by check_site.py.

--------------------------------------------------------------------------
The mark — the owner's own logo, and it never stops moving
--------------------------------------------------------------------------
2026-09-12: the owner supplied a real Cherry logo, so this page no longer
inlines the generated blossom SVG. It carries the mark cut out of that
photograph (assets/img/cherry/mark*.webp) — the MARK only: 「ロゴにはテキストが
含まれていますがこれは一切使用せずロゴだけを切り取り使用してください」, so the
word CHERRY under it in the photograph is not on this page.

A photograph cannot be taken apart into five petals the way the generated SVG
could, so what was per-petal is now carried by the whole mark, and the
behaviour the owner asked for is unchanged:

  1. it TURNS, from the first frame and forever — one revolution a minute
     (「Cherryロゴが一歳動いていません。これは常時動いているロゴです。」)
  2. it blooms once on open: folded to nothing and rotated back 90 degrees,
     unfolding as it turns into place
  3. it breathes forever (scale 1 -> 0.985 -> 1 over ~5 s)
  4. a soft halo behind it breathes out of phase, in the petal's own colour

All CSS keyframes with `infinite` iteration; no JavaScript, no SMIL, no library.

`prefers-reduced-motion: reduce` skips ONLY the one-time bloom (the mark starts
open). The turn, the breath and the halo are the identity of the mark —
「常時動いているロゴ」 — and stay on regardless.

Three traps this file has actually shipped:
  ★ CSS `transform` REPLACES the element's other transform, so the turn and
    the bloom/breath CANNOT live on the same element — one silently erases the
    other. The turn is on .ch-spin, the bloom/breath on .ch-breathe inside it.
  ★ The CSS below is NOT run through str.format(). An earlier version was, and
    a mis-doubled brace emitted `{{transform-box:...}}` — broken CSS, the whole
    petal rule discarded, and what the owner saw was a logo that never moved.
    Substitution here is str.replace() of __TOKENS__ that cannot collide with
    a brace, and main() refuses to write a page that still holds one.
  ★ A rotating rectangle sweeps its own DIAGONAL. The mark is only as wide as
    it can be and still stay inside its box at every angle — computed below
    from the file's real pixel size, not eyeballed.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from site_common import (  # noqa: E402
    ROOT, asset_root_prefix, available_langs, esc, load_bundle, page, write_page,
)
from build_cherry_controls import (  # noqa: E402
    SECTION as CONTROLS_SECTION, link_label as controls_link_label,
)

SECTION = "cherry/"

# --- copy -------------------------------------------------------------------
# Every language the site ships has its own entry; there is no fallback. Brand
# names (Cherry, Alpha, Corvus) are never translated. Keys, in every language:
#   title, desc, lede, line.
# `line` belongs to the release named in COPY_FOR (see the docstring).
COPY = {
    "ja": {
        "title": "Cherry",
        "desc": "OUKA のすぐ下に位置するブランド。",
        "lede": "OUKA のすぐ下に位置するブランド。",
        "line": "トーテムが、動き出す。",
    },
    "en": {
        "title": "Cherry",
        "desc": "The tier just below OUKA.",
        "lede": "The tier just below OUKA.",
        "line": "The totem moves.",
    },
    "es": {
        "title": "Cherry",
        "desc": "El nivel justo por debajo de OUKA.",
        "lede": "El nivel justo por debajo de OUKA.",
        "line": "El tótem cobra vida.",
    },
    "fr": {
        "title": "Cherry",
        "desc": "Le niveau juste en dessous d'OUKA.",
        "lede": "Le niveau juste en dessous d'OUKA.",
        "line": "Le totem s'anime.",
    },
    "zh": {
        "title": "Cherry",
        "desc": "位于 OUKA 之下的品牌。",
        "lede": "位于 OUKA 之下的品牌。",
        "line": "图腾，动起来了。",
    },
    "ko": {
        "title": "Cherry",
        "desc": "OUKA 바로 아래에 자리한 브랜드입니다.",
        "lede": "OUKA 바로 아래에 자리한 브랜드입니다.",
        "line": "토템이 움직입니다.",
    },
    "pt-br": {
        "title": "Cherry",
        "desc": "O nível logo abaixo de OUKA.",
        "lede": "O nível logo abaixo de OUKA.",
        "line": "O totem ganha vida.",
    },
    "it": {
        "title": "Cherry",
        "desc": "Il livello appena sotto OUKA.",
        "lede": "Il livello appena sotto OUKA.",
        "line": "Il totem si anima.",
    },
    "ar": {
        "title": "Cherry",
        "desc": "المستوى الذي يلي OUKA مباشرة.",
        "lede": "المستوى الذي يلي OUKA مباشرة.",
        "line": "الطوطم يتحرك.",
    },
    "ru": {
        "title": "Cherry",
        "desc": "Уровень сразу под OUKA.",
        "lede": "Уровень сразу под OUKA.",
        "line": "Тотем оживает.",
    },
    "id": {
        "title": "Cherry",
        "desc": "Tingkat tepat di bawah OUKA.",
        "lede": "Tingkat tepat di bawah OUKA.",
        "line": "Totem pun bergerak.",
    },
    "de": {
        "title": "Cherry",
        "desc": "Die Stufe direkt unter OUKA.",
        "lede": "Die Stufe direkt unter OUKA.",
        "line": "Der Totem kommt in Bewegung.",
    },
    "tr": {
        "title": "Cherry",
        "desc": "OUKA'nın hemen altındaki seviye.",
        "lede": "OUKA'nın hemen altındaki seviye.",
        "line": "Totem hareketleniyor.",
    },
}

KEYS = ("title", "desc", "lede", "line")

# --- the release ---------------------------------------------------------------
# The release COPY's `line` and CODENAME were written for. A newer zip stops the
# build until its own line and name exist (see the docstring).
COPY_FOR = "1.3.1017"
CODENAME = "HoyoBrainrot"
FIRST_RELEASE = (1, 0, 0)
RELEASE_RE = re.compile(r"^Cherry_MODs_v(?P<ver>\d+(?:\.\d+)*)\+mc(?P<mc>\d+(?:\.\d+)*)\.zip$")
# The Download page's own translations (data/i18n/<lang>.json "download").
DOWNLOAD_KEYS = ("primary_cta", "size_label", "sha_label")
# What a player must have, read from the jar's fabric.mod.json "depends", in this order.
REQUIREMENTS = (("minecraft", "Minecraft"), ("fabricloader", "Fabric Loader"),
                ("fabric-api", "Fabric API"))


def _version_key(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _fmt_size(num_bytes: int) -> str:
    """The Download page's rule (build_download._fmt_size), kept identical:
    one decimal in MB, and KB below 1 MB."""
    mb = num_bytes / (1024 * 1024)
    if mb >= 1:
        return f"{mb:.1f} MB"
    return f"{num_bytes / 1024:.1f} KB"


def _requirement(spec: str) -> str:
    """A fabric.mod.json version predicate, as a player reads it."""
    spec = spec.strip()
    if spec.startswith(">="):
        return "≥ " + spec[2:].strip()
    if spec.startswith("~"):
        return spec[1:].strip()
    if re.fullmatch(r"\d+(?:\.\d+)*(?:\+[0-9A-Za-z.]+)?", spec):
        return spec
    raise SystemExit(
        "ERROR: build_cherry: cannot print the requirement %r on one line; "
        "write the rule for that predicate here rather than printing it raw." % spec)


def cherry_release() -> dict:
    """The newest Cherry release in downloads/, every figure read from the file."""
    downloads = ROOT / "downloads"
    found = []
    for path in (sorted(downloads.glob("Cherry*")) if downloads.is_dir() else []):
        m = RELEASE_RE.match(path.name)
        if not m:
            raise SystemExit(
                "ERROR: build_cherry: downloads/%s looks like a Cherry release but "
                "does not parse as Cherry_MODs_v<ver>+mc<mc>.zip. Rename or remove "
                "it -- the page cannot guess which release it is." % path.name)
        found.append((_version_key(m["ver"]), m, path))
    if not found:
        raise SystemExit(
            "ERROR: build_cherry: downloads/ holds no Cherry_MODs_v<ver>+mc<mc>.zip. "
            "Cherry has been released (V1.0.0, 2026-09-13); without the file this "
            "page would lose its download, and it must not quietly go back to "
            "'coming soon'.")
    versions = [key for key, _m, _p in found]
    if len(set(versions)) != len(versions):
        raise SystemExit(
            "ERROR: build_cherry: downloads/ holds two Cherry zips of the same "
            "version (%s); the page cannot tell which one it hands out."
            % ", ".join(p.name for _k, _m, p in found))
    key, m, path = max(found, key=lambda item: item[0])
    ver, mc = m["ver"], m["mc"]
    if key < FIRST_RELEASE:
        raise SystemExit("ERROR: build_cherry: the newest Cherry zip is V%s, older "
                         "than the first release V1.0.0." % ver)
    if ver != COPY_FOR:
        raise SystemExit(
            "ERROR: build_cherry: downloads/ now offers Cherry V%s, but the release "
            "line and codename on this page were written for V%s. Write V%s's own "
            "line (13 languages) and name, then set COPY_FOR." % (ver, COPY_FOR, ver))
    data = path.read_bytes()
    jar_name = "mods/cherry-%s+mc%s.jar" % (ver, mc)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as outer:
            jar = outer.read(jar_name)
        with zipfile.ZipFile(io.BytesIO(jar)) as inner:
            mod = json.loads(inner.read("fabric.mod.json"))
    except (KeyError, zipfile.BadZipFile, ValueError) as e:
        raise SystemExit("ERROR: build_cherry: cannot read %s!/fabric.mod.json inside "
                         "downloads/%s (%s)." % (jar_name, path.name, e))
    if mod.get("id") != "cherry" or mod.get("version") != ver:
        raise SystemExit(
            "ERROR: build_cherry: downloads/%s carries a jar that says id=%r "
            "version=%r; the file name says cherry %s."
            % (path.name, mod.get("id"), mod.get("version"), ver))
    depends = mod.get("depends") or {}
    requires = []
    for dep, label in REQUIREMENTS:
        if not depends.get(dep):
            raise SystemExit("ERROR: build_cherry: the Cherry jar declares no %r "
                             "dependency; the page would print an empty requirement."
                             % dep)
        requires.append((label, _requirement(depends[dep])))
    if requires[0][1] != mc:
        raise SystemExit(
            "ERROR: build_cherry: the jar depends on Minecraft %s but the zip is "
            "named for %s." % (requires[0][1], mc))
    return {
        "version": ver,
        "mc": mc,
        "name": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "requires": requires,
    }


# --- the mark ----------------------------------------------------------------
# The real file on disk, measured (PIL), not guessed. mark-584.webp is the 1x
# source for the hero; mark-320.webp serves narrow screens.
MARK = {"file": "mark-584.webp", "w": 584, "h": 557,
        "small": "mark-320.webp", "small_w": 320}
BOX = "min(22rem,68vw)"          # the square the mark turns inside

# A rotating rectangle needs its own diagonal to fit. 100 * w / hypot(w, h) is
# the widest the mark can be and still stay inside that square at EVERY angle;
# at 100% its corners would swing out over the copy beside it.
FIT_PCT = round(100.0 * MARK["w"] / math.hypot(MARK["w"], MARK["h"]), 1)

# --- timing (ms) --------------------------------------------------------------
BLOOM_MS = 1150          # fold -> open
BLOOM_START_MS = 140     # the bloom starts
BREATHE_MS = 5200        # one breath (1 -> .985 -> 1)
SPIN_S = 60              # one revolution of the whole mark
INTRO_HOLD_MS = BLOOM_START_MS + BLOOM_MS + 600   # then .is-intro comes off
INTRO_SCRIPT = (
    '<script>(function(){var s=document.querySelector(".ch-wrap");'
    'if(!s)return;s.classList.add("is-intro");'
    'setTimeout(function(){s.classList.remove("is-intro")},%d)})();</script>'
    % INTRO_HOLD_MS)
HALO_MS = 7000           # one breath of the halo behind it

# The halo is the petal's own shaded colour, --ch-petal-deep (#e8b4c6) from
# gen_cherry_brand.py's PALETTE, written as rgb so it can carry an alpha inside
# the gradient stop.
HALO_RGB = "232,180,198"


# ★ NOT a format string. See the docstring: a mis-doubled brace once emitted
#   broken CSS and the mark stopped moving. __TOKENS__ cannot collide with a
#   brace, and main() refuses to write a page that still contains one.
HEAD = """<link rel="stylesheet" href="__ROOT__assets/css/cherry-tokens.css">
<style>
.ch-wrap{background:var(--ch-bg);color:var(--ch-text);padding:4rem 1.25rem 5rem;
  margin:0 calc(50% - 50vw);width:100vw}
.ch-inner{max-width:60rem;margin:0 auto}
.ch-hero{display:grid;gap:2.5rem;align-items:center;
  grid-template-columns:minmax(0,1fr)}
@media (min-width:52rem){.ch-hero{grid-template-columns:22rem minmax(0,1fr)}}
.ch-mark{position:relative;width:__BOX__;aspect-ratio:1;margin-inline:auto;
  display:grid;place-items:center}
.ch-name{font-size:clamp(2.6rem,7vw,4.2rem);line-height:1.02;margin:0 0 .8rem;
  letter-spacing:-.02em;color:var(--ch-petal)}
.ch-lede{font-size:1.12rem;line-height:1.75;color:var(--ch-text);margin:0}

/* --- the release: what is on offer, and the download ---------------------- */
.ch-release{margin:4.5rem auto 0;max-width:36rem;text-align:center}
.ch-edition{margin:0;display:flex;flex-wrap:wrap;align-items:center;
  justify-content:center;gap:.35rem .75rem;font-size:.8rem;letter-spacing:.16em;
  text-transform:uppercase;color:var(--ch-text-muted)}
.ch-ver{color:var(--ch-petal-deep);letter-spacing:.08em}
.ch-dot{width:4px;height:4px;border-radius:50%;background:var(--ch-blush)}
/* balance: at 375 px the English line otherwise leaves "Moon." alone on its own
   line (seen, 2026-09-13); browsers without it simply wrap as before */
.ch-line{margin:1rem 0 0;font-size:clamp(1.55rem,4.2vw,2.3rem);line-height:1.3;
  letter-spacing:-.01em;color:var(--ch-petal);text-wrap:balance}
.ch-cta{margin:2.25rem 0 0}
/* the brand's own colours, the way the Aureum page carries its own gold */
.ch-get{display:inline-flex;align-items:center;justify-content:center;
  min-height:var(--tap,44px);padding:12px 30px;border-radius:999px;
  font-weight:600;font-size:.98rem;letter-spacing:.01em;text-decoration:none;
  color:var(--ch-bg) !important;
  background:linear-gradient(100deg,var(--ch-petal) 0%,var(--ch-petal-deep) 100%);
  box-shadow:0 10px 28px rgba(__HALO_RGB__,.26);
  transition:transform .2s cubic-bezier(.16,1,.3,1),box-shadow .2s ease}
.ch-get:hover,.ch-get:focus-visible{transform:translateY(-1px);
  box-shadow:0 14px 34px rgba(__HALO_RGB__,.38)}
.ch-get:focus-visible{outline:2px solid var(--ch-petal);outline-offset:3px}
.ch-spec{margin:2rem 0 0;padding:0;display:flex;flex-wrap:wrap;
  justify-content:center;gap:.5rem 1.75rem}
.ch-spec div{display:flex;align-items:baseline;gap:.5rem}
.ch-spec dt{font-size:.8rem;color:var(--ch-text-muted)}
.ch-spec dd{margin:0;font-size:.9rem;color:var(--ch-text);
  font-variant-numeric:tabular-nums}
.ch-sha{margin:1.1rem auto 0;max-width:32rem;font-size:.72rem;line-height:1.6;
  color:var(--ch-text-muted)}
.ch-sha-label{display:block;letter-spacing:.08em}
.ch-sha code{display:block;word-break:break-all;background:none;border:0;
  padding:0;font-size:.72rem;color:var(--ch-text-muted)}
/* the one way on to the controls page: quiet, below the release, never a button */
.ch-more{margin:2.75rem 0 0;text-align:center}
.ch-more-link{display:inline-flex;align-items:center;min-height:var(--tap,44px);
  padding:0 .5rem;font-size:.95rem;color:var(--ch-petal-deep);text-decoration:underline;
  text-decoration-color:rgba(__HALO_RGB__,.45);text-underline-offset:.35em}
.ch-more-link:hover,.ch-more-link:focus-visible{color:var(--ch-petal);
  text-decoration-color:var(--ch-petal)}
.ch-more-link:focus-visible{outline:2px solid var(--ch-petal);outline-offset:3px}

/* --- the mark: the owner's logo, always turning -------------------------- */
.ch-halo{position:absolute;inset:-4%;border-radius:50%;pointer-events:none;
  background:radial-gradient(circle,rgba(__HALO_RGB__,.30),rgba(__HALO_RGB__,0) 70%);
  animation:ch-halo __HALO_MS__ms ease-in-out infinite}
/* the turn lives alone on this wrapper -- see the docstring's first trap */
.ch-spin{display:block;width:__FIT__%;
  animation:ch-spin __SPIN_S__s linear infinite}
.ch-breathe{display:block;
  animation:ch-breathe __BREATHE_MS__ms ease-in-out __BREATHE_DELAY__ms infinite}
/* The bloom is OPT-IN, for the reason written against .is-intro in
   build_ouka.py: a renderer that runs script but never advances animation
   time holds this `backwards` fill at frame 0 for ever, and frame 0 of
   ch-open is rotate(-90deg) scale(.04) at opacity 0 -- an invisible mark on
   a page whose whole subject is the mark. The class comes off on a timer,
   which needs no frame, so such a renderer settles on the base style: the
   mark, open and turning. */
.is-intro .ch-breathe{
  animation:ch-open __BLOOM_MS__ms cubic-bezier(.16,.84,.28,1) __BLOOM_DELAY__ms backwards,
            ch-breathe __BREATHE_MS__ms ease-in-out __BREATHE_DELAY__ms infinite}
.ch-img{display:block;width:100%;height:auto}

@keyframes ch-spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
@keyframes ch-open{from{transform:rotate(-90deg) scale(.04);opacity:0}
  60%{opacity:1}
  to{transform:rotate(0deg) scale(1);opacity:1}}
@keyframes ch-breathe{0%,100%{transform:scale(1)}50%{transform:scale(.985)}}
@keyframes ch-halo{0%,100%{opacity:.55;transform:scale(1)}
  50%{opacity:.95;transform:scale(1.045)}}

/* Reduced motion skips ONLY the one-time bloom: the mark starts open. The
   turn, the breath and the halo are the mark itself and stay on. */
@media (prefers-reduced-motion:reduce){
  .ch-breathe,.is-intro .ch-breathe{
    animation:ch-breathe __BREATHE_MS__ms ease-in-out infinite}
  .ch-get{transition:none}
}
</style>"""

TOKENS = ("__ROOT__", "__BOX__", "__FIT__", "__SPIN_S__", "__BLOOM_MS__",
          "__BLOOM_DELAY__", "__BREATHE_MS__", "__BREATHE_DELAY__",
          "__HALO_MS__", "__HALO_RGB__")


def head_css(root: str) -> str:
    out = HEAD
    for token, value in (
        ("__ROOT__", root),
        ("__BOX__", BOX),
        ("__FIT__", "%g" % FIT_PCT),
        ("__SPIN_S__", str(SPIN_S)),
        ("__BLOOM_MS__", str(BLOOM_MS)),
        ("__BLOOM_DELAY__", str(BLOOM_START_MS)),
        ("__BREATHE_MS__", str(BREATHE_MS)),
        ("__BREATHE_DELAY__", str(BLOOM_START_MS + BLOOM_MS)),
        ("__HALO_MS__", str(HALO_MS)),
        ("__HALO_RGB__", HALO_RGB),
    ):
        out = out.replace(token, value)
    return out


def _mark_html(root: str) -> str:
    """The cut-out mark, wrapped so the turn and the bloom cannot erase each
    other. alt="" on purpose: the <h1> beside it already says Cherry, so a
    screen reader that announced the image too would say the name twice."""
    base = root + "assets/img/cherry/"
    return (
        '<div class="ch-mark"><span class="ch-halo" aria-hidden="true"></span>'
        '<span class="ch-spin"><span class="ch-breathe">'
        '<img class="ch-img" src="%s%s" srcset="%s%s %dw, %s%s %dw" '
        'sizes="calc(%s * %g / 100)" width="%d" height="%d" alt="" '
        'decoding="async" fetchpriority="high" loading="eager">'
        '</span></span></div>'
        % (base, MARK["file"], base, MARK["small"], MARK["small_w"],
           base, MARK["file"], MARK["w"], BOX, FIT_PCT, MARK["w"], MARK["h"])
    )


def zip_href(root: str, release: dict) -> str:
    # downloads/ sits at the wiki root, outside every language directory, so it
    # takes the language-aware root prefix -- never a hardcoded "../".
    return root + "downloads/" + release["name"]


def _release_html(c: dict, dl: dict, release: dict, root: str) -> str:
    spec = "".join(
        '<div><dt>%s</dt><dd dir="ltr">%s</dd></div>' % (esc(label), esc(value))
        for label, value in release["requires"])
    spec += ('<div><dt>%s</dt><dd dir="ltr" data-bytes="%d">%s</dd></div>'
             % (esc(dl["size_label"]), release["bytes"],
                esc(_fmt_size(release["bytes"]))))
    return (
        '<section class="ch-release" aria-labelledby="ch-edition">'
        '<p class="ch-edition" id="ch-edition">'
        '<span class="ch-ver" dir="ltr">V%s</span>'
        '<span class="ch-dot" aria-hidden="true"></span>'
        '<span class="ch-codename" lang="en" dir="ltr">%s</span></p>'
        '<p class="ch-line">%s</p>'
        '<p class="ch-cta"><a class="ch-get" href="%s" download>%s</a></p>'
        '<dl class="ch-spec">%s</dl>'
        '<p class="ch-sha"><span class="ch-sha-label">%s</span>'
        '<code dir="ltr">%s</code></p>'
        '</section>'
        % (esc(release["version"]), esc(CODENAME), esc(c["line"]),
           esc(zip_href(root, release)), esc(dl["primary_cta"]), spec,
           esc(dl["sha_label"]), esc(release["sha256"]))
    )


def _controls_link_html(lang: str) -> str:
    """One quiet link to the controls page, outside the release block (whose one
    link check_cherry_release.py counts). Its words are that page's own heading."""
    return ('<p class="ch-more"><a class="ch-more-link" href="../%s">%s</a></p>'
            % (CONTROLS_SECTION, esc(controls_link_label(lang))))


def build_body(c: dict, dl: dict, release: dict, root: str, lang: str) -> str:
    return (
        '<div class="ch-wrap"><div class="ch-inner">'
        '<div class="ch-hero">'
        '%s'
        '<div><h1 class="ch-name">%s</h1>'
        '<p class="ch-lede">%s</p></div>'
        '</div>'
        '%s%s'
        '</div></div>%s'
        % (_mark_html(root), esc(c["title"]), esc(c["lede"]),
           _release_html(c, dl, release, root), _controls_link_html(lang), INTRO_SCRIPT)
    )


def main() -> int:
    langs = available_langs()
    missing = [lang for lang in langs if lang not in COPY]
    if missing:
        print("build_cherry: no copy for %s (no fallback by design)" % ", ".join(missing))
        return 1
    for lang, c in COPY.items():
        gaps = [k for k in KEYS if not c.get(k)]
        if gaps:
            print("build_cherry: %s is missing %s" % (lang, ", ".join(gaps)))
            return 1
    release = cherry_release()
    for lang in langs:
        c = COPY[lang]
        dl = load_bundle(lang).get("download") or {}
        gaps = [k for k in DOWNLOAD_KEYS if not dl.get(k)]
        if gaps:
            raise SystemExit(
                "ERROR: build_cherry: data/i18n/%s.json has no download.%s; the "
                "release block takes the Download page's own words and has no "
                "fallback." % (lang, ", download.".join(gaps)))
        # NOT "../" for every language: /de/cherry/ is two levels below the
        # site root but one below its language root.
        root = asset_root_prefix(1, lang)
        html = page(
            lang=lang,
            section=SECTION,
            title=c["title"],
            description=c["desc"],
            active="cherry",
            body=build_body(c, dl, release, root, lang),
            depth=1,
            extra_head=head_css(root),
        )
        target = ROOT / ("" if lang == "ja" else lang) / SECTION / "index.html"
        # --- the ways this page has failed, or could fail, silently; all refused here.
        # 1. a substitution token surviving into the CSS (the broken-brace
        #    defect's successor): the rule would be discarded and the mark
        #    would sit still, with nothing red anywhere.
        left = [tok for tok in TOKENS if tok in html]
        if left or "{{" in html:
            raise SystemExit(
                "ERROR: build_cherry: %s still holds %s -- the CSS would be "
                "discarded and the mark would not move."
                % (lang, left or ["{{"]))
        # 2. the mark missing, or its animations gone: a text-only hero still
        #    renders perfectly well and looks intentional.
        for needed in ("ch-img", "@keyframes ch-spin", "@keyframes ch-open",
                       "@keyframes ch-breathe", "prefers-reduced-motion"):
            if needed not in html:
                raise SystemExit(
                    "ERROR: build_cherry: %s is missing %r." % (lang, needed))
        # 2b. the bloom must be opt-in and must switch itself off. Frame 0 of
        #    ch-open is an invisible mark, and a renderer that never advances
        #    animation time holds it for ever behind the `backwards` fill.
        if ".is-intro .ch-breathe{\n  animation:ch-open" not in html:
            raise SystemExit(
                "ERROR: build_cherry: %s does not scope the bloom to "
                ".is-intro. A renderer that never advances animation time "
                "would hold frame 0 -- rotate(-90deg) scale(.04) at opacity "
                "0, an invisible mark." % lang)
        if ".ch-breathe{display:block;\n  animation:ch-open" in html:
            raise SystemExit(
                "ERROR: build_cherry: %s still blooms outside .is-intro." % lang)
        for needed in ('classList.add("is-intro")',
                       'classList.remove("is-intro")', str(INTRO_HOLD_MS)):
            if needed not in html:
                raise SystemExit(
                    "ERROR: build_cherry: %s is missing %r -- without it the "
                    "bloom either never runs or never ends." % (lang, needed))
        # 3. the image path resolving to nothing from THIS page's depth.
        want = root + "assets/img/cherry/" + MARK["file"]
        probe = (target.parent / want).resolve()
        if not probe.is_file():
            raise SystemExit(
                "ERROR: build_cherry: %s references %s, which resolves to %s "
                "-- no such file. The mark would 404." % (lang, want, probe))
        # 4. the download resolving to nothing from THIS page's depth, or the
        #    page describing a file other than the one it links.
        href = zip_href(root, release)
        if ('href="%s"' % esc(href)) not in html:
            raise SystemExit("ERROR: build_cherry: %s does not link %s." % (lang, href))
        zprobe = (target.parent / href).resolve()
        if zprobe != (ROOT / "downloads" / release["name"]).resolve() or not zprobe.is_file():
            raise SystemExit(
                "ERROR: build_cherry: %s links %s, which resolves to %s -- not "
                "downloads/%s. The download would 404."
                % (lang, href, zprobe, release["name"]))
        for needed in (release["sha256"], 'data-bytes="%d"' % release["bytes"],
                       '<span class="ch-ver" dir="ltr">V%s</span>' % release["version"]):
            if needed not in html:
                raise SystemExit("ERROR: build_cherry: %s is missing %r." % (lang, needed))
        # 5. the pre-release line surviving beside the release.
        if "ch-soon" in html:
            raise SystemExit(
                "ERROR: build_cherry: %s still carries the pre-release line." % lang)
        write_page(lang, SECTION, html)
    print("build_cherry: %d language(s), mark %s at %g%% of %s, release V%s "
          "(%s, %d bytes, sha256 %s)"
          % (len(langs), MARK["file"], FIT_PCT, BOX, release["version"],
             release["name"], release["bytes"], release["sha256"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
