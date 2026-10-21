#!/usr/bin/env python3
"""Builds ouka/index.html — the OUKA brand page, for every language.

Owner directive (2026-09-12, IROHA, verbatim):

    新ブランドOUKAを展開
    ブランド名称:英→OUKA、漢→桜花
    ブランド位置:OUKA→Cherry→Alpha(※左から順に上位ブランド)
    (Aureumは別ジャンルModsなので含まれない)
    ブランドロゴをデザインフォルダーに追加しています。ウェブサイトに表示して
    今までにない圧倒的な品質とアニメーションでその名を轟かせ披露してください。

--------------------------------------------------------------------------
What the page says — and what it must never say
--------------------------------------------------------------------------
This page is built to the shape the owner arrived at for Cherry, after he
rejected two earlier drafts of that page (his words are quoted in full in
build_cherry.py's header). Two things, and nothing else:

  1. Where OUKA sits — said once, as a fact, not argued. He put it at the top
     of the line: OUKA → Cherry → Alpha, 左から順に上位ブランド.
  2. The release that is on offer. Until V1.0.0 this was a closing line in the
     register of 乞うご期待. Now it is the release itself, in the shape Cherry's
     page gave its own: the version and name, ONE line in the same register,
     the download, and the facts a player checks before installing (what it
     needs, how big the file is, its SHA-256). Every figure is read from the
     file in downloads/ and from the fabric.mod.json inside it — none is typed
     here.

NOT on this page, by his word on Cherry, which governs here because this is the
same kind of page: where the name comes from; that there is no compromise
(self-evident, and saying it cheapens the brand); what it contains — there is
no feature list, and the install and play guide travels inside the zip
(README.txt); any status, progress, "not yet", "coming later", build, or
schedule. Before V1.0.0 OUKA had no published build, and that is why none of
this could be written down, in either direction; the release block now states
only what the file itself proves. Every one of the 13 languages carries its own
copy; nothing falls back to English.

「桜花」はこのページには出さない。所有者が挙げたのはブランド名称としての表記
(「ブランド名称:英→OUKA、漢→桜花」)であって、ページに載せる文言としてではない。
承認を得た Cherry のページの形は「ブランドの位置」と「結びの一行」だけで、漢字
表記は無い。所有者が日本語版に置きたいと言えば KANJI = {"ja": "桜花"} と書けば
戻る(一行)。それまでは出さない——見せていないものを勝手に足さない。

--------------------------------------------------------------------------
The release block (OUKA V1.0.0 "The Apex Artifact", released 2026-09-20)
--------------------------------------------------------------------------
  * The line claims only what the zip's own README.txt states: the box
    addressed to the player arrives at dawn ("HOW IT BEGINS"). It names no
    feature and makes no promise.
  * The page refuses to build without an OUKA zip of V1.0.0 or later. The
    pre-release line is gone from the code, so a missing file cannot quietly
    turn a released product back into "coming soon" — it stops the build.
  * The line and the codename were written for one version (COPY_FOR). A newer
    zip in downloads/ stops the build until its own line and name are written,
    so an old line can never be printed over a new release.
  * The download button is in the mark's own two colours; its label, "File
    size" and "SHA-256" are the Download page's own translations
    (data/i18n/<lang>.json "download"), with no fallback.
  * Versions, the size, the hash and the codename carry dir="ltr": on the
    Arabic page bidi mirroring would print "≥" as "≤" and reorder
    "0.154.2+26.2". The codename also carries lang="en", because the edition
    line is set in capitals and a Turkish page would capitalise its i as İ.
  * The block enters where the closing line did (.ou-fade at RELEASE_START_MS,
    the same moment), so the entrance keeps its order and its timing.
  * scripts/check_ouka_release.py judges the rendered pages against the file
    independently (it imports nothing from here) and is run by check_site.py.

--------------------------------------------------------------------------
The mark, and the animation the owner asked for
--------------------------------------------------------------------------
The mark is cut out of the logo photograph the owner supplied, and it is the
MARK ONLY — his standing instruction for every one of these logos is
「ロゴにはテキストが含まれていますがこれは一切使用せずロゴだけを切り取り
使用してください」, so the word OUKA under it in the photograph is not used;
the <h1> below the mark is the name.

「今までにない圧倒的な品質とアニメーション」 is the brief, so the blossom is not
animated as one flat picture. It was TAKEN APART, by measurement, into its five
petals and the α at its centre (scripts written for this page, kept in the
scratchpad; the parts they produced are committed as assets/img/ouka/petal-N-*
and core-*):

  * The centre of the mark's five-fold symmetry is at (51.04%, 53.70%) of the
    image — found by minimising |A − A rotated 72°| over candidate centres.
    Controls: the error rises monotonically as the centre is moved off it
    (59.9 → 61.6 → 68.6 → 82.8 at +6/+12/+24 px), and a half-step rotation of
    36° scores 112.8 against 59.9 for 72°.
  * The petals are seated at 53.57° + 72k (image space, 0 = +x, y down). Found
    as the phase of the 5th angular harmonic, which carries 0.246 of the mark's
    angular mass against ≤ 0.043 for every other harmonic except its own 10th
    (0.118 — each petal has one facet seam down its middle, which is why there
    are ten half-petals below and not five).
    ★ The first phase fit came out 36° wrong, i.e. pointing at the clefts. The
      control that caught it: mean radial mass at the claimed tips must exceed
      that at the claimed clefts, and it was 0.24× instead. A tip is where the
      mark HAS mass. An animation built on the unchecked fit would have hinged
      every petal about the gap between two petals.
  * The split itself is by connected components at alpha ≥ 180 (ten half-petals
    in five pairs, one per measured tip, plus the α glyph), after which every
    remaining pixel with alpha > 0 — the anti-aliased edges and the whole outer
    glow — is grown outward to the nearest part. So the six layers PARTITION
    the mark: their composite is the mark itself, alpha max |Δ| = 0 at 584 px
    (1 at 320 px, where 6 pixels of glow are lost), colour mean |Δ| 2.06 from
    webp quantisation alone. There is no seam, no double-darkened edge, and no
    lost glow, because no pixel is in two layers or in none.
  * A circular clip for the α was measured and REJECTED: the glyph reaches
    r = 123 px while the petals begin at r = 45 px — they interleave radially,
    and a disc that held the whole glyph would have held four petals with it.
    That is why the α is a cut layer and not a CSS circle().

What the page then does with those parts, all in CSS, no JavaScript, no
library, no video, no SMIL:

  1. the five petals unfold into their seats — each hinged on the measured
     centre, from folded (rotate −26°, scale .62) to seated, 1250 ms each,
     staggered 130 ms apart, starting at the top petal and going clockwise
  2. the α settles into the middle of them, 1120 ms, landing at 2100 ms
  3. the wordmark's four glyphs rise, 90 ms apart
  4. and then it LIVES: one revolution every 90 s, a slow breath, two haloes
     breathing out of phase in the mark's own two colours, and a highlight
     that travels across the metal every 11 s. The alpha counter-turns inside
     that revolution so the letter never goes upside down -- see .ou-core-anchor.

Both halo colours and the wordmark's gradient are MEASURED off the mark's own
opaque pixels (alpha ≥ 235, 35,166 samples): the left half of the blossom is
#fed1dd, the right half #e6dbe1. Nothing on this page is coloured by a palette
someone invented next to the logo.

--------------------------------------------------------------------------
Traps, every one of which this repo has actually shipped
--------------------------------------------------------------------------
  ★ CSS `transform` REPLACES the element's other transform, so the turn, the
    breath and each petal's unfold cannot share an element — one silently
    erases the other. They are on .ou-turn, .ou-breathe and .ou-p.
  ★ The CSS below is NOT a format string. A mis-doubled brace once emitted
    broken CSS and a Cherry logo that never moved, for a day. Substitution is
    str.replace() of __TOKENS__, and main() refuses to write a page that still
    holds one.
  ★ A rotating rectangle sweeps its own diagonal — and this one turns about
    the FLOWER's centre, not the image's, so the sweep radius is the distance
    from that centre to the farthest corner of the artwork (420 of 584 px),
    not half the diagonal. FIT below is computed from the real pixels; at any
    larger size the glow would swing out over the name on every revolution.
  ★ Every animated element's BASE style is its FINISHED state, and the intro
    animations reach it via `backwards` fill. That is what makes
    prefers-reduced-motion correct: switching the animations off shows the
    finished mark, assembled and still — never a frozen frame 0.
  ★ --t0 (below) exists so the animation can be INSPECTED: a test copy of the
    page sets .ou-stage{--t0:-2400ms} and animation-play-state:paused to freeze
    every animation at a chosen moment with its stagger intact. Chrome's
    --virtual-time-budget does NOT advance CSS animations (measured: a
    10s/1000px box moved 5 px between budgets of 100 ms and 5000 ms), so
    without this hook the page could only ever be screenshotted at whatever
    instant the renderer happened to stop.
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
    ROOT, SITE_BASE_URL, asset_root_prefix, available_langs, esc, load_bundle,
    page, write_page,
)

SECTION = "ouka/"

# The share card, so a link to the flagship brand page shows the brand's own
# mark instead of the generic Corvus card. It is the cut mark on the site's
# ground and nothing else -- no wordmark, by the owner's standing instruction.
# Built by scripts/make_ouka_og.py; 1200x630, which is what page() declares.
OG_CARD = f"{SITE_BASE_URL}/assets/img/ouka/og-ouka.png"

# --- copy -------------------------------------------------------------------
# Every language the site ships has its own entry; there is no fallback. Brand
# names (OUKA, Cherry, Alpha, Corvus, Aureum) are never translated.
# The lede says one thing: OUKA is the top of the line, above Cherry. Both
# halves of that come from the owner's own sentence and neither is inferred.
# `line` belongs to the release named in COPY_FOR (see the docstring). It took
# the place of `soon`, the closing line the owner accepted on the Cherry page,
# when V1.0.0 was staged; the English and Japanese lines were put to the owner
# as a proposal on 2026-09-15, and the other eleven follow them.
COPY = {
    "ja": {"title": "OUKA",
           "desc": "Cherry の上に立つ、最上位のブランド。",
           "lede": "Cherry の上に立つ、最上位のブランド。",
           "line": "静かな和室と、自分の手で灯す太陽。",
           "soon": "ご期待ください。"},
    "en": {"title": "OUKA",
           "desc": "The highest tier, above Cherry.",
           "lede": "The highest tier, above Cherry.",
           "line": "A quiet room, and a sun of your own.",
           "soon": "Coming soon."},
    "de": {"title": "OUKA",
           "desc": "Die höchste Stufe, über Cherry.",
           "lede": "Die höchste Stufe, über Cherry.",
           "line": "Ein stiller Raum und eine eigene Sonne.",
           "soon": "Bald verfügbar."},
    "fr": {"title": "OUKA",
           "desc": "Le niveau le plus élevé, au-dessus de Cherry.",
           "lede": "Le niveau le plus élevé, au-dessus de Cherry.",
           "line": "Une pièce paisible, et un soleil bien à vous.",
           "soon": "Bientôt disponible."},
    "es": {"title": "OUKA",
           "desc": "El nivel más alto, por encima de Cherry.",
           "lede": "El nivel más alto, por encima de Cherry.",
           "line": "Una sala en calma y un sol propio.",
           "soon": "Muy pronto."},
    "it": {"title": "OUKA",
           "desc": "Il livello più alto, sopra Cherry.",
           "lede": "Il livello più alto, sopra Cherry.",
           "line": "Una stanza quieta e un sole tutto tuo.",
           "soon": "In arrivo."},
    "pt-br": {"title": "OUKA",
              "desc": "O nível mais alto, acima do Cherry.",
              "lede": "O nível mais alto, acima do Cherry.",
              "line": "Uma sala serena e um sol só seu.",
           "soon": "Em breve."},
    "ru": {"title": "OUKA",
           "desc": "Высший уровень — выше Cherry.",
           "lede": "Высший уровень — выше Cherry.",
           "line": "Тихая комната и собственное солнце.",
           "soon": "Уже скоро."},
    "tr": {"title": "OUKA",
           "desc": "En üst seviye; Cherry'nin üzerinde.",
           "lede": "En üst seviye; Cherry'nin üzerinde.",
           "line": "Sessiz bir oda ve size ait bir güneş.",
           "soon": "Çok yakında."},
    "ar": {"title": "OUKA",
           "desc": "المستوى الأعلى، فوق Cherry.",
           "lede": "المستوى الأعلى، فوق Cherry.",
           "line": "غرفة هادئة، وشمس من صنعك.",
           "soon": "ترقّبوا قريباً."},
    "id": {"title": "OUKA",
           "desc": "Tingkat tertinggi, di atas Cherry.",
           "lede": "Tingkat tertinggi, di atas Cherry.",
           "line": "Ruang yang tenang, dan matahari milik Anda sendiri.",
           "soon": "Segera hadir."},
    "ko": {"title": "OUKA",
           "desc": "Cherry 위에 서는 최상위 브랜드입니다.",
           "lede": "Cherry 위에 서는 최상위 브랜드입니다.",
           "line": "고요한 방, 그리고 내 손으로 밝히는 태양.",
           "soon": "기대해 주세요."},
    "zh": {"title": "OUKA",
           "desc": "位于 Cherry 之上,最高级别的品牌。",
           "lede": "位于 Cherry 之上,最高级别的品牌。",
           "line": "一间静室，与一轮属于你的太阳。",
           "soon": "敬请期待。"},
}

# 2026-09-12 — the owner had the theme and the field made (Gemini; Grok was out of
# its weekly quota) and asked for them on the page. A browser will not play audio
# by itself, so the theme sits behind a control the visitor presses; these are that
# control's two states. Not in COPY/KEYS because those four are the page's prose and
# this is furniture.
TRACK = "Silver and Petals"                 # the piece's own title, a name in every language
PLAY = {
    "ja": "テーマ曲を再生", "en": "Play the theme", "de": "Thema abspielen",
    "fr": "Écouter le thème", "es": "Reproducir el tema", "it": "Riproduci il tema",
    "pt-br": "Tocar o tema", "ru": "Включить тему", "tr": "Temayı çal",
    "ar": "تشغيل اللحن", "id": "Putar tema", "ko": "테마 재생", "zh": "播放主题曲",
}
PAUSE = {
    "ja": "一時停止", "en": "Pause", "de": "Pause", "fr": "Pause", "es": "Pausa",
    "it": "Pausa", "pt-br": "Pausar", "ru": "Пауза", "tr": "Duraklat",
    "ar": "إيقاف مؤقت", "id": "Jeda", "ko": "일시정지", "zh": "暂停",
}

# The field behind the mark. Measured on the delivered image: its pools peak at
# luminance 216.7 against this site's ground (#07090f) at 9.0 - twenty-four times
# the ground, where the brief asked for a pool at 8% opacity. The centre of the
# frame is already clean (mean 12.1), so only the strength needed holding back.
FIELD_OPACITY = 0.16
FIELD_W, FIELD_SMALL = 1365, 900

KEYS = ("title", "desc", "lede", "line")

# --- the release ---------------------------------------------------------------
# The release COPY's `line` and CODENAME were written for. A newer zip stops the
# build until its own line and name exist (see the docstring).
# V1.4.0 (2026-10-05): the line and codename are V1.4's own. The codename is the working title from the spec
# (Update/OUKA_V1.4_IMPLEMENTATION_NOTES.md); the owner has not confirmed a public one, so confirm before the release.
COPY_FOR = "1.7.2.2"
CODENAME = "The Grand Synthesis"
FIRST_RELEASE = (1, 0, 0)
RELEASE_RE = re.compile(r"^OUKA_MODs_v(?P<ver>\d+(?:\.\d+)*)\+mc(?P<mc>\d+(?:\.\d+)*)\.zip$")
# The Download page's own translations (data/i18n/<lang>.json "download").
DOWNLOAD_KEYS = ("primary_cta", "size_label", "sha_label")
# What a player must have, read from the jar's fabric.mod.json "depends", in this
# order -- the same three the Cherry page prints. GeckoLib is not among them: it
# travels inside the zip.
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
        "ERROR: build_ouka: cannot print the requirement %r on one line; "
        "write the rule for that predicate here rather than printing it raw." % spec)


def ouka_release() -> dict:
    """The newest OUKA release in downloads/, every figure read from the file."""
    downloads = ROOT / "downloads"
    found = []
    for path in (sorted(downloads.glob("OUKA*")) if downloads.is_dir() else []):
        m = RELEASE_RE.match(path.name)
        if not m:
            raise SystemExit(
                "ERROR: build_ouka: downloads/%s looks like an OUKA release but "
                "does not parse as OUKA_MODs_v<ver>+mc<mc>.zip. Rename or remove "
                "it -- the page cannot guess which release it is." % path.name)
        found.append((_version_key(m["ver"]), m, path))
    if not found:
        raise SystemExit(
            "ERROR: build_ouka: downloads/ holds no OUKA_MODs_v<ver>+mc<mc>.zip. "
            "OUKA has been released (V1.0.0); without the file this page would "
            "lose its download, and it must not quietly go back to 'coming soon'.")
    versions = [key for key, _m, _p in found]
    if len(set(versions)) != len(versions):
        raise SystemExit(
            "ERROR: build_ouka: downloads/ holds two OUKA zips of the same "
            "version (%s); the page cannot tell which one it hands out."
            % ", ".join(p.name for _k, _m, p in found))
    key, m, path = max(found, key=lambda item: item[0])
    ver, mc = m["ver"], m["mc"]
    if key < FIRST_RELEASE:
        raise SystemExit("ERROR: build_ouka: the newest OUKA zip is V%s, older "
                         "than the first release V1.0.0." % ver)
    if ver != COPY_FOR:
        raise SystemExit(
            "ERROR: build_ouka: downloads/ now offers OUKA V%s, but the release "
            "line and codename on this page were written for V%s. Write V%s's own "
            "line (13 languages) and name, then set COPY_FOR." % (ver, COPY_FOR, ver))
    data = path.read_bytes()
    jar_name = "mods/ouka-%s+mc%s.jar" % (ver, mc)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as outer:
            jar = outer.read(jar_name)
        with zipfile.ZipFile(io.BytesIO(jar)) as inner:
            mod = json.loads(inner.read("fabric.mod.json"))
    except (KeyError, zipfile.BadZipFile, ValueError) as e:
        raise SystemExit("ERROR: build_ouka: cannot read %s!/fabric.mod.json inside "
                         "downloads/%s (%s)." % (jar_name, path.name, e))
    if mod.get("id") != "ouka" or mod.get("version") != ver:
        raise SystemExit(
            "ERROR: build_ouka: downloads/%s carries a jar that says id=%r "
            "version=%r; the file name says ouka %s."
            % (path.name, mod.get("id"), mod.get("version"), ver))
    depends = mod.get("depends") or {}
    requires = []
    for dep, label in REQUIREMENTS:
        if not depends.get(dep):
            raise SystemExit("ERROR: build_ouka: the OUKA jar declares no %r "
                             "dependency; the page would print an empty requirement."
                             % dep)
        requires.append((label, _requirement(depends[dep])))
    if requires[0][1] != mc:
        raise SystemExit(
            "ERROR: build_ouka: the jar depends on Minecraft %s but the zip is "
            "named for %s." % (requires[0][1], mc))
    return {
        "version": ver,
        "mc": mc,
        "name": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "requires": requires,
    }


# The name in kanji — see the docstring. EMPTY on purpose: the owner gave 桜花
# as the brand's name, not as copy for this page, and the shape he approved on
# Cherry carries no such line. Putting it back is one entry: {"ja": "桜花"}.
KANJI: dict[str, str] = {}

# --- the mark's parts -------------------------------------------------------
# Real files on disk, measured with PIL, not guessed. Each layer is the FULL
# canvas with only its own part opaque, so all six share one coordinate system
# and one transform-origin.
LAYER_W, LAYER_H = 584, 552
SMALL_W, SMALL_H = 320, 303
# The five petals in the order they open: the top petal first, then clockwise.
# The numbers are the seats measured off the mark (petal N is the one whose
# tip sits at 53.57 + 72*(N-1) degrees), so this list is a viewing order, not
# a renaming of the files.
PETAL_ORDER = [4, 5, 1, 2, 3]
PETAL_TIP_DEG = {n: (53.57 + 72 * (n - 1)) % 360 for n in range(1, 6)}

# The centre of the mark's five-fold symmetry, as a fraction of the layer box.
# Every rotation and every scale on this page pivots here.
CX_PCT, CY_PCT = 51.04, 53.70

# The farthest the artwork reaches from that centre, in layer pixels: the
# corner distances are 420.1 / 411.6 / 393.0 / 384.3, so 420.1 governs.
REACH_PX = 420.1
# The mark turns about that centre inside a square box. To keep every corner of
# the artwork inside the box at every angle, the layer may be no wider than:
FIT_PCT = round(100.0 * LAYER_W / (2.0 * REACH_PX), 1)   # 69.5
BOX = "min(30rem,80vw)"

# Measured off the mark's own opaque pixels (alpha >= 235, sampled at the
# centre split): left half 17,659 px, right half 17,507 px.
PINK = "254,209,221"      # #fed1dd
SILVER = "230,219,225"    # #e6dbe1

# --- timing (ms) ------------------------------------------------------------
PETAL_MS = 1250
PETAL_START_MS = 180
PETAL_STEP_MS = 130
CORE_MS = 1120
CORE_START_MS = 980
GLYPH_MS = 700
GLYPH_START_MS = 1500
GLYPH_STEP_MS = 90
LEDE_MS = 800
LEDE_START_MS = 1800
KANJI_START_MS = 1950
# The release block (V1.0.0) enters at the moment the closing line used to, and
# the theme control with it.
RELEASE_START_MS = 2000
# the mark is fully assembled here; everything that lives forever starts after
ASSEMBLED_MS = CORE_START_MS + CORE_MS          # 2100
SPIN_S = 90               # one revolution. Cherry turns in 60; the tier above
                          # it moves more deliberately, and still visibly.
BREATHE_MS = 6000
HALO_IN_MS = 7000
HALO_OUT_MS = 9000        # out of phase with the inner halo, on purpose
SHEEN_MS = 11000
SHEEN_START_MS = ASSEMBLED_MS + 500

# The entrance is OPT-IN. Every intro animation is scoped to .is-intro, which
# the script below the stage adds and then removes once the entrance is over.
# The reason is measured, not reasoned: a renderer that runs script but never
# advances animation time holds a `backwards` fill at frame 0 for ever, and
# frame 0 of this mark is a blossom with no petals and a page with no text.
# With the preview pane hidden, document.timeline.currentTime read 0 twice
# across 2,355 ms of wall clock while all five petals sat at opacity 0 and
# rotate(-26deg) scale(.62), and both lines at opacity 0. setTimeout does not
# need a frame, so the class comes off even there and the base style -- which
# IS the finished mark -- is what such a renderer captures.
INTRO_END_MS = RELEASE_START_MS + LEDE_MS     # 2800: the release block has landed
INTRO_HOLD_MS = INTRO_END_MS + 600            # a margin, then the class goes
assert INTRO_HOLD_MS > INTRO_END_MS, "the class would come off mid-entrance"
INTRO_SCRIPT = (
    '<script>(function(){var s=document.querySelector(".ou-stage");'
    'if(!s)return;s.classList.add("is-intro");'
    'setTimeout(function(){s.classList.remove("is-intro")},%d)})();</script>'
    % INTRO_HOLD_MS)

# ★ NOT a format string. See the docstring's second trap.
HEAD = """<style>
.ou-stage{--t0:0ms;padding:3.5rem 0 1rem;display:grid;justify-items:center;
  text-align:center}
/* The field behind the mark. position:fixed so it is full-bleed whatever the
   container's padding is; z-index:-1 puts it under every painted thing on the
   page and over the body's own ground. .ou-stage makes no stacking context
   (no transform, no opacity, no isolation), so the -1 is not trapped. */
.ou-field{position:fixed;inset:0;z-index:-1;pointer-events:none;
  opacity:__FIELD_OP__}
.ou-field img{width:100%;height:100%;object-fit:cover;display:block}
.ou-audio{display:flex;align-items:center;gap:.7rem;margin:2.2rem 0 0}
.ou-play{width:2.6rem;height:2.6rem;flex:none;display:grid;place-items:center;
  border-radius:50%;border:1px solid rgba(__SILVER__,.28);
  background:rgba(__SILVER__,.05);color:rgba(__SILVER__,.9);cursor:pointer;
  padding:0;transition:background .25s ease,border-color .25s ease}
.ou-play:hover{background:rgba(__PINK__,.10);border-color:rgba(__PINK__,.45)}
.ou-play svg{width:.85rem;height:.85rem;fill:currentColor}
.ou-play .ou-pause-icon{display:none}
.ou-play[aria-pressed="true"] .ou-play-icon{display:none}
.ou-play[aria-pressed="true"] .ou-pause-icon{display:block}
.ou-track{font-size:.94rem;letter-spacing:.10em;color:var(--text-muted)}
.ou-mark{position:relative;width:__BOX__;aspect-ratio:1;margin-bottom:2.2rem}
.ou-halo{position:absolute;border-radius:50%;pointer-events:none}
.ou-halo--in{inset:6%;
  background:radial-gradient(circle,rgba(__PINK__,.22),rgba(__PINK__,0) 66%);
  animation:ou-halo-in __HALO_IN_MS__ms ease-in-out infinite;
  animation-delay:var(--t0)}
.ou-halo--out{inset:-8%;
  background:radial-gradient(circle,rgba(__SILVER__,.13),rgba(__SILVER__,0) 70%);
  animation:ou-halo-out __HALO_OUT_MS__ms ease-in-out infinite;
  animation-delay:var(--t0)}
/* the turn lives alone on this element -- a transform replaces a transform */
.ou-turn{position:absolute;inset:0;
  animation:ou-turn __SPIN_S__s linear infinite;animation-delay:var(--t0)}
.ou-breathe{position:absolute;inset:0;
  animation:ou-breathe __BREATHE_MS__ms ease-in-out infinite;
  animation-delay:calc(var(--t0) + __ASSEMBLED_MS__ms)}
/* the six layers share one box, so one transform-origin is the flower's
   centre for all of them. The box is placed so that centre sits exactly on
   the square's centre -- otherwise the blossom would orbit as it turned. */
.ou-parts{position:absolute;left:50%;top:50%;width:__FIT__%;
  aspect-ratio:__LW__/__LH__;transform:translate(-__CX__%,-__CY__%)}
.ou-l{position:absolute;inset:0;width:100%;height:100%;
  transform-origin:__CX__% __CY__%}
/* The alpha is the one part of this mark that is a LETTER, and a mark that
   turns through 360 degrees would carry it upside down for a third of every
   revolution -- which is exactly what the first build did. Its own wrapper
   turns BACKWARDS at the rate .ou-turn turns forwards, about the same
   measured centre, so the petals revolve and the alpha stays upright. This is
   only possible because the alpha was cut out as a layer of its own. */
.ou-core-anchor{position:absolute;inset:0;transform-origin:__CX__% __CY__%;
  animation:ou-unturn __SPIN_S__s linear infinite;animation-delay:var(--t0)}
.is-intro .ou-p{animation:ou-petal __PETAL_MS__ms cubic-bezier(.2,.82,.25,1)
  backwards;animation-delay:calc(var(--t0) + var(--d))}
.is-intro .ou-core{animation:ou-core __CORE_MS__ms cubic-bezier(.18,.9,.28,1)
  backwards;animation-delay:calc(var(--t0) + __CORE_START_MS__ms)}

/* Light travelling across the metal. The bar is masked by the mark's own
   alpha, so it lights the artwork and never the empty box around it; where
   the mask is not supported there is simply no sheen, rather than a white
   rectangle sweeping a blossom. The mask is the mark's body with its glow cut
   away (alpha 60 -> 0, 200 -> 255), so the light travels across the metal and
   not across the halo -- and it costs 4 KB instead of the 19 KB the full
   soft-edged alpha channel cost. */
.ou-sheen{display:none}
@supports ((-webkit-mask-image:url(#a)) or (mask-image:url(#a))){
  .ou-sheen{display:block;position:absolute;inset:0;overflow:hidden;
    pointer-events:none;mix-blend-mode:screen;
    -webkit-mask-image:url(__ROOT__assets/img/ouka/sheen-mask-192.webp);
    mask-image:url(__ROOT__assets/img/ouka/sheen-mask-192.webp);
    -webkit-mask-size:100% 100%;mask-size:100% 100%;
    -webkit-mask-repeat:no-repeat;mask-repeat:no-repeat}
}
.ou-sheen::before{content:"";position:absolute;top:-40%;bottom:-40%;left:0;
  width:34%;filter:blur(7px);
  background:linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,.62),
    rgba(255,255,255,0));
  transform:translateX(-180%) rotate(14deg);
  animation:ou-sheen __SHEEN_MS__ms cubic-bezier(.42,0,.4,1) infinite;
  animation-delay:calc(var(--t0) + __SHEEN_START_MS__ms)}

.ou-name{font-size:clamp(2.9rem,8.4vw,5.2rem);line-height:1;margin:0;
  letter-spacing:.1em;font-weight:700;color:rgb(__PINK__)}
@supports ((-webkit-background-clip:text) or (background-clip:text)){
  .ou-name{background:linear-gradient(100deg,rgb(__PINK__) 10%,#fff 47%,
    rgb(__SILVER__) 86%);-webkit-background-clip:text;background-clip:text;
    color:transparent}
}
/* The glyphs rise out of a clipping wrapper -- deliberately NOT with
   transform or opacity. Measured, not reasoned: a descendant of a
   background-clip:text element that runs a COMPOSITED animation is not
   painted by the parent's clipped background, so it renders as
   color:transparent -- nothing at all. Both halves were isolated separately
   on this exact gradient: transform-only measured 0 bright pixels and
   opacity-only also measured 0, against 2,924 with the animation switched
   off. This page shipped that bug: the name was blank for the whole of its
   entrance (0 px at t=1500/1700/1900/2100) and then snapped in one letter at
   a time. `top` is not a compositable property, creates no stacking context,
   and so the <h1> keeps painting the letter while it moves; the wrapper's
   overflow does the hiding that opacity used to do. Guarded in main(). */
.ou-gw{display:inline-block;overflow:hidden;vertical-align:bottom;
  padding-top:.28em;margin-top:-.28em}
.ou-g{display:inline-block;position:relative}
.is-intro .ou-g{animation:ou-glyph __GLYPH_MS__ms
  cubic-bezier(.16,.84,.28,1) backwards;
  animation-delay:calc(var(--t0) + __GLYPH_START_MS__ms + var(--i) * __GLYPH_STEP_MS__ms)}
.ou-kanji{margin:1.1rem 0 0;font-size:1.02rem;letter-spacing:.42em;
  text-indent:.42em;color:var(--text-muted);font-weight:500}
.ou-lede{font-size:1.16rem;line-height:1.8;color:var(--text);
  margin:1.9rem 0 0;max-width:34rem}
/* The release (V1.0.0): what is on offer, and the download. The section is an
   .ou-fade, so it enters where the closing line did; the button is in the
   mark's own two colours, the way the Cherry page's is in its petals'. */
.ou-release{margin:4.5rem 0 0;width:100%;max-width:36rem}
.ou-edition{margin:0;display:flex;flex-wrap:wrap;align-items:center;
  justify-content:center;gap:.35rem .75rem;font-size:.8rem;letter-spacing:.16em;
  text-transform:uppercase;color:var(--text-muted)}
.ou-ver{color:rgb(__PINK__);letter-spacing:.08em}
.ou-dot{width:4px;height:4px;border-radius:50%;background:rgba(__SILVER__,.55)}
.ou-line{margin:1rem 0 0;font-size:clamp(1.55rem,4.2vw,2.3rem);line-height:1.3;
  letter-spacing:.02em;color:rgb(__PINK__);text-wrap:balance}
.ou-cta{margin:2.25rem 0 0}
.ou-get{display:inline-flex;align-items:center;justify-content:center;
  min-height:var(--tap,44px);padding:12px 30px;border-radius:999px;
  font-weight:600;font-size:.98rem;letter-spacing:.01em;text-decoration:none;
  color:var(--bg,#07090f) !important;
  background:linear-gradient(100deg,rgb(__PINK__) 0%,rgb(__SILVER__) 100%);
  box-shadow:0 10px 28px rgba(__PINK__,.22);
  transition:transform .2s cubic-bezier(.16,1,.3,1),box-shadow .2s ease}
.ou-get:hover,.ou-get:focus-visible{transform:translateY(-1px);
  box-shadow:0 14px 34px rgba(__PINK__,.34)}
.ou-get:focus-visible{outline:2px solid rgb(__PINK__);outline-offset:3px}
.ou-spec{margin:2rem 0 0;padding:0;display:flex;flex-wrap:wrap;
  justify-content:center;gap:.5rem 1.75rem}
.ou-spec div{display:flex;align-items:baseline;gap:.5rem}
.ou-spec dt{font-size:.8rem;color:var(--text-muted)}
.ou-spec dd{margin:0;font-size:.9rem;color:var(--text);
  font-variant-numeric:tabular-nums}
.ou-sha{margin:1.1rem auto 0;max-width:32rem;font-size:.72rem;line-height:1.6;
  color:var(--text-muted)}
.ou-sha-label{display:block;letter-spacing:.08em}
.ou-sha code{display:block;word-break:break-all;background:none;border:0;
  padding:0;font-size:.72rem;color:var(--text-muted)}
.is-intro .ou-fade{animation:ou-fade __LEDE_MS__ms
  cubic-bezier(.16,.84,.28,1) backwards;
  animation-delay:calc(var(--t0) + var(--d))}

@keyframes ou-turn{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
@keyframes ou-unturn{from{transform:rotate(0deg)}to{transform:rotate(-360deg)}}
@keyframes ou-breathe{0%,100%{transform:scale(1)}50%{transform:scale(.984)}}
@keyframes ou-petal{from{transform:rotate(-26deg) scale(.62);opacity:0}
  40%{opacity:1}
  to{transform:none;opacity:1}}
@keyframes ou-core{from{transform:rotate(-16deg) scale(.66);opacity:0}
  45%{opacity:1}
  to{transform:none;opacity:1}}
@keyframes ou-glyph{from{top:1.15em}to{top:0}}
@keyframes ou-fade{from{opacity:0;transform:translateY(12px)}
  to{opacity:1;transform:none}}
@keyframes ou-halo-in{0%,100%{opacity:.52;transform:scale(1)}
  50%{opacity:1;transform:scale(1.055)}}
@keyframes ou-halo-out{0%,100%{opacity:.95;transform:scale(1.05)}
  50%{opacity:.45;transform:scale(1)}}
@keyframes ou-sheen{0%{transform:translateX(-180%) rotate(14deg)}
  20%,100%{transform:translateX(340%) rotate(14deg)}}

/* Reduced motion: the finished mark, assembled and still -- NOT frame 0.
   Every element's base style already IS its finished state (the intro
   animations only reach it, via `backwards` fill), so switching them off
   leaves the blossom complete. */
@media (prefers-reduced-motion:reduce){
  .ou-turn,.ou-core-anchor,.ou-breathe,.ou-sheen::before,
  .is-intro .ou-p,.is-intro .ou-core,.is-intro .ou-g,.is-intro .ou-fade{
    animation:none}
  .ou-halo--in{animation:none;opacity:.76}
  .ou-halo--out{animation:none;opacity:.7}
  .ou-sheen{display:none}
  .ou-get{transition:none}
}
</style>"""

TOKENS = ("__ROOT__", "__BOX__", "__FIT__", "__LW__", "__LH__", "__CX__",
          "__CY__", "__PINK__", "__SILVER__", "__SPIN_S__", "__BREATHE_MS__",
          "__ASSEMBLED_MS__", "__PETAL_MS__", "__CORE_MS__", "__CORE_START_MS__",
          "__GLYPH_MS__", "__GLYPH_START_MS__", "__GLYPH_STEP_MS__",
          "__LEDE_MS__", "__HALO_IN_MS__", "__HALO_OUT_MS__", "__SHEEN_MS__",
          "__SHEEN_START_MS__", "__FIELD_OP__")


def head_css(root: str) -> str:
    out = HEAD
    for token, value in (
        ("__ROOT__", root),
        ("__BOX__", BOX),
        ("__FIT__", "%g" % FIT_PCT),
        ("__LW__", str(LAYER_W)),
        ("__LH__", str(LAYER_H)),
        ("__CX__", "%g" % CX_PCT),
        ("__CY__", "%g" % CY_PCT),
        ("__PINK__", PINK),
        ("__SILVER__", SILVER),
        ("__FIELD_OP__", "%g" % FIELD_OPACITY),
        ("__SPIN_S__", str(SPIN_S)),
        ("__BREATHE_MS__", str(BREATHE_MS)),
        ("__ASSEMBLED_MS__", str(ASSEMBLED_MS)),
        ("__PETAL_MS__", str(PETAL_MS)),
        ("__CORE_MS__", str(CORE_MS)),
        ("__CORE_START_MS__", str(CORE_START_MS)),
        ("__GLYPH_MS__", str(GLYPH_MS)),
        ("__GLYPH_START_MS__", str(GLYPH_START_MS)),
        ("__GLYPH_STEP_MS__", str(GLYPH_STEP_MS)),
        ("__LEDE_MS__", str(LEDE_MS)),
        ("__HALO_IN_MS__", str(HALO_IN_MS)),
        ("__HALO_OUT_MS__", str(HALO_OUT_MS)),
        ("__SHEEN_MS__", str(SHEEN_MS)),
        ("__SHEEN_START_MS__", str(SHEEN_START_MS)),
    ):
        out = out.replace(token, value)
    return out


def _layer(root: str, stem: str, cls: str, delay_ms: int | None) -> str:
    """One cut part of the mark. alt="" on all six: the <h1> below already says
    OUKA, and six images that each announced themselves would say it seven
    times. sizes matches the CSS exactly -- the layer is FIT% of the box."""
    base = root + "assets/img/ouka/"
    style = ' style="--d:%dms"' % delay_ms if delay_ms is not None else ""
    return (
        '<img class="ou-l %s" src="%s%s-%d.webp" '
        'srcset="%s%s-%d.webp %dw, %s%s-%d.webp %dw" '
        'sizes="calc(%s * %g / 100)" width="%d" height="%d" alt=""%s '
        'decoding="async" loading="eager">'
        % (cls, base, stem, LAYER_W,
           base, stem, SMALL_W, SMALL_W, base, stem, LAYER_W, LAYER_W,
           BOX, FIT_PCT, LAYER_W, LAYER_H, style)
    )


def _mark_html(root: str) -> str:
    petals = "".join(
        _layer(root, "petal-%d" % n, "ou-p",
               PETAL_START_MS + i * PETAL_STEP_MS)
        for i, n in enumerate(PETAL_ORDER)
    )
    return (
        '<div class="ou-mark" aria-hidden="true">'
        '<span class="ou-halo ou-halo--out"></span>'
        '<span class="ou-halo ou-halo--in"></span>'
        '<span class="ou-turn"><span class="ou-breathe">'
        '<span class="ou-parts">%s<span class="ou-core-anchor">%s</span>'
        '<span class="ou-sheen"></span></span>'
        '</span></span></div>'
        % (petals, _layer(root, "core", "ou-core", None))
    )


def _field_html(root: str) -> str:
    """The field behind the mark (Gemini, 2026-09-12; watermark removed by solving
    Laplace's equation inside the 48x48 glyph with the surrounding pixels as the
    boundary, then matching the ring's own grain - the patch reads 0.00 of 255 away
    from a smooth reading of its surroundings). aria-hidden: it says nothing."""
    base = root + "assets/img/ouka/"
    return (
        '<div class="ou-field" aria-hidden="true">'
        '<img src="%sfield-%d.webp" srcset="%sfield-%d.webp %dw, %sfield-%d.webp %dw" '
        'sizes="100vw" width="%d" height="%d" alt="" decoding="async" '
        'fetchpriority="low"></div>'
        % (base, FIELD_W, base, FIELD_SMALL, FIELD_SMALL, base, FIELD_W, FIELD_W,
           FIELD_W, round(FIELD_W * 768 / 1365)))


def _audio_html(root: str, lang: str) -> str:
    """The theme, behind a control. NEVER autoplay: every browser refuses sound a
    visitor did not ask for, and a page that tries it either fails silently or is
    punished (Chrome's media engagement index). preload="none" so a visitor who
    never presses it pays nothing. Two sources because Firefox on some platforms
    has no AAC decoder; the .mp3 is the same 56.8 s at the same level."""
    base = root + "assets/audio/ouka/"
    play, pause = PLAY[lang], PAUSE[lang]
    return (
        '<div class="ou-audio ou-fade" style="--d:%dms">'
        '<button class="ou-play" type="button" aria-pressed="false" '
        'aria-label="%s" data-play="%s" data-pause="%s">'
        '<svg class="ou-play-icon" viewBox="0 0 12 14" aria-hidden="true">'
        '<path d="M1 0.6 11 7 1 13.4Z"/></svg>'
        '<svg class="ou-pause-icon" viewBox="0 0 12 14" aria-hidden="true">'
        '<path d="M1 1h3.3v12H1Zm6.7 0H11v12H7.7Z"/></svg>'
        '</button><span class="ou-track">%s</span>'
        '<audio class="ou-track-audio" preload="none">'
        '<source src="%ssilver-and-petals.m4a" type="audio/mp4">'
        '<source src="%ssilver-and-petals.mp3" type="audio/mpeg">'
        '</audio></div>'
        % (RELEASE_START_MS, esc(play), esc(play), esc(pause), esc(TRACK), base, base))


AUDIO_SCRIPT = (
    '<script>(function(){var b=document.querySelector(".ou-play");'
    'if(!b)return;var a=document.querySelector(".ou-track-audio");'
    'function set(p){b.setAttribute("aria-pressed",p?"true":"false");'
    'b.setAttribute("aria-label",b.getAttribute(p?"data-pause":"data-play"))}'
    'b.addEventListener("click",function(){'
    'if(a.paused){var q=a.play();if(q&&q.catch)q.catch(function(){set(false)})}'
    'else{a.pause()}});'
    'a.addEventListener("play",function(){set(true)});'
    'a.addEventListener("pause",function(){set(false)});'
    'a.addEventListener("ended",function(){set(false)})})();</script>')


def wordmark(text: str) -> str:
    """One span per glyph so the reveal can stagger, each inside the wrapper
    it rises out of. Emitted at BUILD time: the split is in the served HTML,
    so nothing depends on a script running for the name to be readable. The
    wrapper's overflow is what hides a letter before its turn -- see .ou-gw
    for why this cannot be done with opacity.

    Each wrapper is an inline block, and a right-to-left page lays inline
    blocks out from the right, so the <h1> holding them carries dir="ltr"
    (build_body). Without it the Arabic page printed the name as "AKUO":
    plain text keeps its letter order under bidi, split glyphs do not. Seen on
    the rendered page on 2026-09-15; check_ouka_release.py now refuses it."""
    return "".join('<span class="ou-gw"><span class="ou-g" style="--i:%d">%s'
                   '</span></span>' % (i, esc(ch))
                   for i, ch in enumerate(text))


def zip_href(root: str, release: dict) -> str:
    # downloads/ sits at the wiki root, outside every language directory, so it
    # takes the language-aware root prefix -- never a hardcoded "../".
    return root + "downloads/" + release["name"]


def _release_html(c: dict, dl: dict, release: dict, root: str) -> str:
    """The release, in the Cherry page's markup under this page's own prefix.
    The section is an .ou-fade at RELEASE_START_MS: it takes the closing line's
    place in the entrance."""
    spec = "".join(
        '<div><dt>%s</dt><dd dir="ltr">%s</dd></div>' % (esc(label), esc(value))
        for label, value in release["requires"])
    spec += ('<div><dt>%s</dt><dd dir="ltr" data-bytes="%d">%s</dd></div>'
             % (esc(dl["size_label"]), release["bytes"],
                esc(_fmt_size(release["bytes"]))))
    return (
        '<section class="ou-release ou-fade" style="--d:%dms" '
        'aria-labelledby="ou-edition">'
        '<p class="ou-edition" id="ou-edition">'
        '<span class="ou-ver" dir="ltr">V%s</span>'
        '<span class="ou-dot" aria-hidden="true"></span>'
        '<span class="ou-codename" dir="ltr" lang="en">%s</span></p>'
        '<p class="ou-line">%s</p>'
        '<p class="ou-cta"><a class="ou-get" href="%s" download>%s</a></p>'
        '<dl class="ou-spec">%s</dl>'
        '<p class="ou-sha"><span class="ou-sha-label">%s</span>'
        '<code dir="ltr">%s</code></p>'
        '</section>'
        % (RELEASE_START_MS, esc(release["version"]), esc(CODENAME),
           esc(c["line"]), esc(zip_href(root, release)), esc(dl["primary_cta"]),
           spec, esc(dl["sha_label"]), esc(release["sha256"]))
    )


def build_body(lang: str, c: dict, dl: dict, release: dict, root: str) -> str:
    kanji = KANJI.get(lang, "")
    kanji_html = ('<p class="ou-kanji ou-fade" style="--d:%dms">%s</p>'
                  % (KANJI_START_MS, esc(kanji))) if kanji else ""
    return (
        '<div class="ou-stage">'
        '%s%s'
        '<h1 class="ou-name" dir="ltr" aria-label="%s">%s</h1>'
        '%s'
        '<p class="ou-lede ou-fade" style="--d:%dms">%s</p>'
        '%s'
        '%s'
        '</div>%s%s'
        % (_field_html(root), _mark_html(root), esc(c["title"]),
           wordmark(c["title"]), kanji_html,
           LEDE_START_MS, esc(c["lede"]), _release_html(c, dl, release, root),
           _audio_html(root, lang), INTRO_SCRIPT, AUDIO_SCRIPT)
    )


def main() -> int:
    langs = available_langs()
    missing = [lang for lang in langs if lang not in COPY]
    if missing:
        print("build_ouka: no copy for %s (no fallback by design)"
              % ", ".join(missing))
        return 1
    for lang, c in COPY.items():
        gaps = [k for k in KEYS if not c.get(k)]
        if gaps:
            print("build_ouka: %s is missing %s" % (lang, ", ".join(gaps)))
            return 1
    if sorted(PETAL_ORDER) != [1, 2, 3, 4, 5]:
        raise SystemExit("ERROR: build_ouka: PETAL_ORDER is not the five seats.")
    for lang in langs:
        for table, what in ((PLAY, "play"), (PAUSE, "pause")):
            if not table.get(lang):
                raise SystemExit("ERROR: build_ouka: no %s label for %s (no fallback "
                                 "by design)." % (what, lang))
    for rel in ("assets/img/ouka/field-%d.webp" % FIELD_W,
                "assets/img/ouka/field-%d.webp" % FIELD_SMALL,
                "assets/audio/ouka/silver-and-petals.m4a",
                "assets/audio/ouka/silver-and-petals.mp3"):
        if not (ROOT / rel).is_file():
            raise SystemExit("ERROR: build_ouka: %s is not on disk. The page would "
                             "point at nothing and still look fine." % rel)
    release = ouka_release()

    for lang in langs:
        c = COPY[lang]
        dl = load_bundle(lang).get("download") or {}
        gaps = [k for k in DOWNLOAD_KEYS if not dl.get(k)]
        if gaps:
            raise SystemExit(
                "ERROR: build_ouka: data/i18n/%s.json has no download.%s; the "
                "release block takes the Download page's own words and has no "
                "fallback." % (lang, ", download.".join(gaps)))
        # NOT "../" for every language: /de/ouka/ is two levels below the site
        # root but one below its language root.
        root = asset_root_prefix(1, lang)
        html = page(
            lang=lang,
            section=SECTION,
            title=c["title"],
            description=c["desc"],
            active="ouka",
            body=build_body(lang, c, dl, release, root),
            depth=1,
            extra_head=head_css(root),
            og_image=OG_CARD,
            og_image_alt="OUKA",
        )
        # Every failure below looks FINE in a browser, which is why each one is
        # refused here instead of being left to the eye.
        # 1. a surviving token: the rule holding it is discarded, and the mark
        #    silently stops moving (this repo has shipped exactly that).
        left = [tok for tok in TOKENS if tok in html]
        if left or "{{" in html:
            raise SystemExit(
                "ERROR: build_ouka: %s still holds %s -- the CSS would be "
                "discarded and the mark would not move." % (lang, left or ["{{"]))
        # 2. a missing animation: a still blossom still looks like a logo.
        for needed in ("@keyframes ou-petal", "@keyframes ou-core",
                       "@keyframes ou-turn", "@keyframes ou-breathe",
                       "@keyframes ou-sheen", "@keyframes ou-glyph", "@keyframes ou-unturn",
                       "prefers-reduced-motion", "--t0:0ms"):
            if needed not in html:
                raise SystemExit("ERROR: build_ouka: %s is missing %r."
                                 % (lang, needed))
        # 2c. the entrance must be opt-in, and must switch itself off. Every
        #    check above passes on a page whose mark never assembles, because
        #    in a browser with a running clock it always does. Where the clock
        #    never runs -- a card scraper, a print path, the hidden preview
        #    pane this repo captures with -- `backwards` fill holds frame 0,
        #    and frame 0 is five invisible petals and two invisible lines.
        #    Measured with the pane hidden: timeline.currentTime 0 over
        #    2,355 ms, every petal opacity 0 at rotate(-26deg) scale(.62).
        for scoped in (".is-intro .ou-p{animation:", ".is-intro .ou-core{animation:",
                       ".is-intro .ou-g{animation:", ".is-intro .ou-fade{animation:"):
            if scoped not in html:
                raise SystemExit(
                    "ERROR: build_ouka: %s does not scope %r to .is-intro. A "
                    "renderer that never advances animation time would hold "
                    "frame 0 -- a blossom with no petals." % (lang, scoped))
        for unscoped in ("\n.ou-p{animation:", "\n.ou-core{animation:",
                         "\n.ou-fade{animation:",
                         ".ou-g{display:inline-block;position:relative;animation"):
            if unscoped in html:
                raise SystemExit(
                    "ERROR: build_ouka: %s still applies %r outside .is-intro."
                    % (lang, unscoped.strip()))
        # 2d. the field and the theme. Both are files: a page that points at one
        #    that is not there looks FINE (a missing backdrop is black, and a
        #    control that 404s just never sounds), so the files are checked on
        #    disk, not only in the HTML.
        for needed in ('class="ou-field"', "field-%d.webp" % FIELD_W,
                       'class="ou-play"', "silver-and-petals.m4a",
                       "silver-and-petals.mp3", esc(PLAY[lang]), esc(PAUSE[lang]),
                       'preload="none"', 'aria-pressed="false"'):
            if needed not in html:
                raise SystemExit("ERROR: build_ouka: %s is missing %r." % (lang, needed))
        if "autoplay" in html:
            raise SystemExit(
                "ERROR: build_ouka: %s would try to autoplay. Every browser refuses "
                "sound the visitor did not ask for." % lang)

        for needed in ('classList.add("is-intro")',
                       'classList.remove("is-intro")', str(INTRO_HOLD_MS)):
            if needed not in html:
                raise SystemExit(
                    "ERROR: build_ouka: %s is missing %r -- without it the "
                    "entrance either never runs or never ends."
                    % (lang, needed))
        # 2b. the glyph reveal must animate NEITHER transform NOR opacity. A
        #    descendant of the gradient-clipped <h1> that runs either one is
        #    not painted at all while it animates -- the name goes blank for
        #    its whole entrance and then snaps in. That shipped. Each half was
        #    measured alone (transform-only 0 px, opacity-only 0 px, animation
        #    off 2,924 px), so this refuses the regression instead of leaving
        #    an invisible brand name to be noticed by eye.
        kf = ""
        if "@keyframes ou-glyph{" in html:
            kf = html.split("@keyframes ou-glyph{", 1)[1].split("}}", 1)[0]
        bad = [p for p in ("transform", "opacity") if p in kf]
        if bad:
            raise SystemExit(
                "ERROR: build_ouka: %s animates %s on .ou-g. The gradient-"
                "clipped <h1> cannot paint a composited descendant, so the "
                "name would be invisible for its entire entrance."
                % (lang, "/".join(bad)))
        if html.count('class="ou-gw"') != html.count('class="ou-g" style='):
            raise SystemExit(
                "ERROR: build_ouka: %s has %d glyph wrappers for %d glyphs -- "
                "an unwrapped glyph is visible before its turn."
                % (lang, html.count('class="ou-gw"'),
                   html.count('class="ou-g" style=')))
        # 3. a part that is not there: five petals and one core, no more and no
        #    fewer. A four-petal blossom would still render, and would be wrong.
        if html.count('class="ou-l ou-p"') != 5:
            raise SystemExit("ERROR: build_ouka: %s has %d petal layers, not 5."
                             % (lang, html.count('class="ou-l ou-p"')))
        if html.count('class="ou-l ou-core"') != 1:
            raise SystemExit("ERROR: build_ouka: %s has no single core layer."
                             % lang)
        # the alpha must sit inside the counter-turning anchor. Without it the
        # letter rides the 360 degree turn and spends a third of every
        # revolution upside down -- which renders perfectly and looks cheap.
        if html.count('class="ou-core-anchor"') != 1 or (
                '<span class="ou-core-anchor"><img class="ou-l ou-core"' not in html):
            raise SystemExit("ERROR: build_ouka: %s does not seat the alpha in "
                             "the counter-turning anchor." % lang)
        # 4. an image path that resolves to nothing FROM THIS PAGE'S DEPTH:
        #    a 404 the build cannot see, on a page whose whole subject is the
        #    picture. The sheen mask is checked too -- without it the sheen
        #    silently becomes a white bar over the blossom.
        target = ROOT / ("" if lang == "ja" else lang) / SECTION / "index.html"
        wanted = ["sheen-mask-192.webp"]
        for stem in ["core"] + ["petal-%d" % n for n in range(1, 6)]:
            wanted += ["%s-%d.webp" % (stem, LAYER_W),
                       "%s-%d.webp" % (stem, SMALL_W)]
        for name in wanted:
            want = root + "assets/img/ouka/" + name
            if want not in html:
                raise SystemExit("ERROR: build_ouka: %s never references %s."
                                 % (lang, name))
            probe = (target.parent / want).resolve()
            if not probe.is_file():
                raise SystemExit(
                    "ERROR: build_ouka: %s references %s, which resolves to %s "
                    "-- no such file." % (lang, want, probe))
        # 5. the download resolving to nothing from THIS page's depth, or the
        #    page describing a file other than the one it links.
        href = zip_href(root, release)
        if ('href="%s"' % esc(href)) not in html:
            raise SystemExit("ERROR: build_ouka: %s does not link %s." % (lang, href))
        zprobe = (target.parent / href).resolve()
        if zprobe != (ROOT / "downloads" / release["name"]).resolve() or not zprobe.is_file():
            raise SystemExit(
                "ERROR: build_ouka: %s links %s, which resolves to %s -- not "
                "downloads/%s. The download would 404."
                % (lang, href, zprobe, release["name"]))
        for needed in (release["sha256"], 'data-bytes="%d"' % release["bytes"],
                       '<span class="ou-ver" dir="ltr">V%s</span>' % release["version"]):
            if needed not in html:
                raise SystemExit("ERROR: build_ouka: %s is missing %r." % (lang, needed))
        # 6. one release block, and it is part of the entrance: an .ou-fade at
        #    the closing line's old moment. Outside the entrance it would sit on
        #    the page before the mark had assembled.
        if html.count('<section class="ou-release') != 1:
            raise SystemExit("ERROR: build_ouka: %s has %d release sections, not 1."
                             % (lang, html.count('<section class="ou-release')))
        if ('<section class="ou-release ou-fade" style="--d:%dms"'
                % RELEASE_START_MS) not in html:
            raise SystemExit(
                "ERROR: build_ouka: %s: the release block is not an .ou-fade at "
                "%dms, so it is outside the entrance." % (lang, RELEASE_START_MS))
        # 7. the pre-release line surviving beside the release.
        if "ou-soon" in html:
            raise SystemExit(
                "ERROR: build_ouka: %s still carries the pre-release line." % lang)
        write_page(lang, SECTION, html)

    print("build_ouka: %d language(s); 6 cut layers at %g%% of %s, pivot "
          "(%g%%, %g%%); petals open %s over %dms, assembled at %dms; "
          "one turn per %ds; release V%s (%s, %d bytes, sha256 %s)"
          % (len(langs), FIT_PCT, BOX, CX_PCT, CY_PCT,
             "->".join(str(n) for n in PETAL_ORDER),
             PETAL_START_MS + 4 * PETAL_STEP_MS + PETAL_MS, ASSEMBLED_MS, SPIN_S,
             release["version"], release["name"], release["bytes"], release["sha256"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
