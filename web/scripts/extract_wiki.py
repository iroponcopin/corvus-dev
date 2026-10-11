#!/usr/bin/env python3
"""Aurora Corvus portal — the one reader of the wiki's data.

Everything the portal shows comes through here, at build time, from this repository:

  data/i18n/<lang>.json, data/*.json, glimpse_manifest.json, releases.json, upcoming.json
  scripts/build_*.py copy tables (imported — the owner's routine edits them, so they must stay importable)
  downloads/<brand zips and jars>  (requirements from fabric.mod.json; the Store catalogue from the Corvus jar)
  web/src/i18n/legacy.json         (copy that only ever lived in the pre-4.0 portal; see capture_legacy_strings.py)

and is written to web/.data/wiki.json, which the Next.js build reads. Nothing in the repository is written,
and no contract file is touched. Run with bytecode off so the checkout stays clean:

    PYTHONDONTWRITEBYTECODE=1 python3 -B web/scripts/extract_wiki.py

A data problem (a missing translation the page would render empty, a release the manifest and the jar
disagree about) stops the build with the reason, exactly as the old generators did.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WEB = HERE.parent
WIKI = Path(os.environ.get("WIKI_DIR", WEB.parent)).resolve()
OUT = WEB / ".data" / "wiki.json"
sys.path.insert(0, str(WIKI / "scripts"))

# The builders print notes while they compute; the portal build keeps its own output readable.
_quiet = io.StringIO()
with contextlib.redirect_stdout(_quiet):
    import site_common as SC  # noqa: E402
    import build_ouka as BO  # noqa: E402
    import build_cherry as BC  # noqa: E402
    import build_cherry_controls as CC  # noqa: E402
    import build_aureum as BA  # noqa: E402
    import build_download as BD  # noqa: E402
    import build_alpha as BAL  # noqa: E402
    import build_404 as B404  # noqa: E402
    import build_discord as BDC  # noqa: E402
    import build_changelog as BCL  # noqa: E402
    import build_skin_gate as BSG  # noqa: E402

SCHEMA = "aurora-corvus.wiki/4"
BASE_URL = SC.SITE_BASE_URL
BASE_PATH = "/aurora-corvus"
LANGS = SC.available_langs()
# The models with a page of their own (src/app/[lang]/<id>/).
MODEL_PAGES = ("ouka", "cherry", "aureum", "alpha", "astraea", "tsubomi", "noctua", "halia")
SECTIONS = ["", "launcher/", "download/", "recipes/", "changelog/", "announcement/", "teasers/", "skin/", "discord/",
            "ouka/", "cherry/", "cherry-controls/", "aureum/", "alpha/", "astraea/", "tsubomi/", "noctua/", "halia/"]


def die(msg: str) -> None:
    raise SystemExit(f"extract_wiki: {msg}")


def read_json(rel: str):
    return json.loads((WIKI / rel).read_text(encoding="utf-8"))


def lang_prefix(lang: str) -> str:
    return "" if lang == "ja" else f"{lang}/"


def href(lang: str, section: str) -> str:
    """App-relative href (the renderer prefixes the basePath)."""
    return f"/{lang_prefix(lang)}{section}"


def fmt_size(n: int) -> str:
    return BD._fmt_size(n)


def file_facts(name: str, url: str, size: int, sha: str) -> dict:
    return {"name": name, "url": url, "bytes": size, "bytesDisplay": f"{size:,}", "sizeDisplay": fmt_size(size),
            "sha256": sha}


def major_minor(v: str) -> str:
    m = re.match(r"^(\d+)\.(\d+)", v)
    return f"{m.group(1)}.{m.group(2)}" if m else v


# ------------------------------------------------------------------ Java .properties (the Store catalogue)

def parse_properties(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    logical: list[str] = []
    buf = ""
    for raw in text.splitlines():
        line = raw.lstrip() if not buf else raw.lstrip()
        if not buf and (not line or line[0] in "#!"):
            continue
        # Line continuation: an odd number of trailing backslashes.
        trailing = len(line) - len(line.rstrip("\\"))
        if trailing % 2 == 1:
            buf += line[:-1]
            continue
        logical.append(buf + line)
        buf = ""
    if buf:
        logical.append(buf)
    for line in logical:
        m = re.match(r"((?:\\.|[^=:\s\\])+)\s*[=:\s]\s*(.*)$", line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)

        def unescape(s: str) -> str:
            res, i = [], 0
            while i < len(s):
                c = s[i]
                if c == "\\" and i + 1 < len(s):
                    n = s[i + 1]
                    if n == "u" and i + 5 < len(s):
                        res.append(chr(int(s[i + 2:i + 6], 16)))
                        i += 6
                        continue
                    res.append({"n": "\n", "t": "\t", "r": "\r", "f": "\f"}.get(n, n))
                    i += 2
                    continue
                res.append(c)
                i += 1
            return "".join(res)
        out[unescape(key)] = unescape(value)
    return out


def store_catalogue(manifest: dict) -> dict:
    """The Corvus Store's own strings (13 languages) from the jar the manifest publishes."""
    jar = WIKI / "downloads" / manifest["launcher"]["file_name"]
    if not jar.exists():
        die(f"the manifest's launcher jar {jar.name} is not in downloads/")
    z = zipfile.ZipFile(jar)
    out = {}
    for lang in LANGS:
        name = f"net/sorakaze/glimpse/ui/i18n/messages_{lang}.properties"
        try:
            props = parse_properties(z.read(name).decode("utf-8"))
        except KeyError:
            die(f"{jar.name} has no {name}")
        out[lang] = {k: v for k, v in props.items()
                     if k.startswith(("store.", "perch.", "account.perch.", "account.title", "nav."))}
    return {"jar": jar.name, "version": manifest["launcher"]["latest"], "messages": out}


# ------------------------------------------------------------------ shared facts

def git_facts() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=WIKI, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""
    status = run("status", "--porcelain", "--", "data", "scripts", "glimpse_manifest.json", "releases.json",
                 "upcoming.json", "downloads")
    return {"commit": run("rev-parse", "HEAD"), "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
            "dataDirty": bool(status)}


def product_ids() -> list[str]:
    """The Store order (the portal's STORE_ORDER): the brand line, then the coming and the archived."""
    # Halia first (2026-10-11): the owner's order is HALIA, ASTRAEA, OUKA, CHERRY, TSUBOMI, and the Store lists it first.
    return ["halia", "ouka", "cherry", "aureum", "astraea", "tsubomi", "noctua", "alpha"]


def availability(pid: str, manifest: dict, retirement: dict) -> str:
    if pid == "alpha":
        return "archived" if retirement.get("retired") else "available"
    return "available" if pid in manifest and manifest[pid].get("latest") else "soon"


def requirements_of(brand: str) -> list[dict]:
    fn = {"ouka": BO.ouka_release, "cherry": BC.cherry_release}.get(brand)
    if fn is None:
        return []
    with contextlib.redirect_stdout(_quiet):
        try:
            rel = fn()
        except SystemExit as e:  # the builders refuse a zip newer than their COPY_FOR, by design
            die(f"{brand}: {e}")
    return [{"label": label, "value": value} for label, value in rel["requires"]], rel


# ------------------------------------------------------------------ recipes

_KATA = re.compile(r"[ァ-ヶ]")


def normalise(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    return _KATA.sub(lambda m: chr(ord(m.group(0)) - 0x60), s)


# The words the machine recipes need (inputs a tag or alternatives stand for, chances, times, the bore's veins).
MACHINE_LABELS = {
    "ja": {"any": "または同じ種類の物", "outputs": "取れる物", "chance": "{0}% の確率", "time": "{0} 秒",
           "water": "水 {0} mB", "xp": "経験値 {0}", "vein": "{0}で掘れる鉱脈の {1}%", "drill": "素材は要らない",
           "overworld": "オーバーワールド", "nether": "ネザー", "end": "エンド"},
    "en": {"any": "or another of its kind", "outputs": "What comes out", "chance": "{0}% chance", "time": "{0} s",
           "water": "{0} mB of water", "xp": "{0} XP", "vein": "{1}% of the veins in the {0}",
           "drill": "No ingredients", "overworld": "Overworld", "nether": "Nether", "end": "End"},
    "es": {"any": "u otro de su tipo", "outputs": "Lo que sale", "chance": "{0} % de probabilidad", "time": "{0} s",
           "water": "{0} mB de agua", "xp": "{0} PX", "vein": "{1} % de las vetas en el {0}",
           "drill": "Sin ingredientes", "overworld": "Mundo Normal", "nether": "Nether", "end": "End"},
    "fr": {"any": "ou un autre du même type", "outputs": "Ce qui en sort", "chance": "{0} % de chances",
           "time": "{0} s", "water": "{0} mB d’eau", "xp": "{0} XP", "vein": "{1} % des filons dans {0}",
           "drill": "Aucun ingrédient", "overworld": "la Surface", "nether": "le Nether", "end": "l’End"},
    "zh": {"any": "或同类物品", "outputs": "产出", "chance": "{0}% 概率", "time": "{0} 秒", "water": "{0} mB 水",
           "xp": "{0} 经验", "vein": "{0}中 {1}% 的矿脉", "drill": "无需材料",
           "overworld": "主世界", "nether": "下界", "end": "末地"},
    "ko": {"any": "또는 같은 종류", "outputs": "나오는 것", "chance": "{0}% 확률", "time": "{0}초",
           "water": "물 {0} mB", "xp": "경험치 {0}", "vein": "{0} 광맥의 {1}%", "drill": "재료 없음",
           "overworld": "오버월드", "nether": "네더", "end": "엔드"},
    "pt-br": {"any": "ou outro do mesmo tipo", "outputs": "O que sai", "chance": "{0}% de chance", "time": "{0} s",
              "water": "{0} mB de água", "xp": "{0} XP", "vein": "{1}% dos veios no {0}",
              "drill": "Sem ingredientes", "overworld": "Mundo Superior", "nether": "Nether", "end": "End"},
    "it": {"any": "o un altro dello stesso tipo", "outputs": "Cosa si ottiene", "chance": "{0}% di probabilità",
           "time": "{0} s", "water": "{0} mB d’acqua", "xp": "{0} PE", "vein": "{1}% dei filoni nel {0}",
           "drill": "Nessun ingrediente", "overworld": "Sopramondo", "nether": "Nether", "end": "End"},
    "ar": {"any": "أو غيره من النوع نفسه", "outputs": "الناتج", "chance": "احتمال {0}%", "time": "{0} ث",
           "water": "{0} mB من الماء", "xp": "{0} خبرة", "vein": "{1}% من العروق في {0}",
           "drill": "بلا مكوّنات", "overworld": "العالم العلوي", "nether": "النذر", "end": "النهاية"},
    "ru": {"any": "или другой того же вида", "outputs": "Что получается", "chance": "шанс {0}%", "time": "{0} с",
           "water": "{0} mB воды", "xp": "{0} опыта", "vein": "{1}% жил в мире «{0}»",
           "drill": "Без ингредиентов", "overworld": "Верхний мир", "nether": "Незер", "end": "Энд"},
    "id": {"any": "atau yang sejenis", "outputs": "Hasilnya", "chance": "peluang {0}%", "time": "{0} dtk",
           "water": "{0} mB air", "xp": "{0} XP", "vein": "{1}% urat di {0}", "drill": "Tanpa bahan",
           "overworld": "Overworld", "nether": "Nether", "end": "End"},
    "de": {"any": "oder ein anderes der Art", "outputs": "Was herauskommt", "chance": "{0} % Chance",
           "time": "{0} s", "water": "{0} mB Wasser", "xp": "{0} EP", "vein": "{1} % der Adern ({0})",
           "drill": "Keine Zutaten", "overworld": "Oberwelt", "nether": "Nether", "end": "End"},
    "tr": {"any": "ya da aynı türden biri", "outputs": "Çıkanlar", "chance": "%{0} şans", "time": "{0} sn",
           "water": "{0} mB su", "xp": "{0} TP", "vein": "{0} damarlarının %{1}'i", "drill": "Malzeme gerekmez",
           "overworld": "Üst Dünya", "nether": "Nether", "end": "End"},
}


def recipes_shared(legacy: dict) -> dict:
    r = read_json("data/recipes.json")
    items = r["items"]
    kinds = legacy["langs"]["ja"]["recipes"].get("kinds", {})
    stations_ja = {"crucible": items.get("cherry:resonance_crucible", [""])[0],
                   "fabricator": items.get("cherry:advanced_cherry_fabricator", [""])[0]}
    names_by_len = sorted(((v[0], k) for k, v in items.items() if v[0]), key=lambda t: -len(t[0]))
    recipes = []
    for i, card in enumerate(r["cards"]):
        cat, result, grid, count, how, search = card
        rec = {"key": f"{result}#{i}", "cat": cat, "result": result, "count": count, "grid": grid,
               "station": "workbench", "search": search}
        if how:
            rec["how"] = how
            # A machine recipe yields one item unless the text says otherwise (the card stores 0).
            rec["count"] = count or 1
            station = next((sid for sid, nm in stations_ja.items() if nm and nm in how), None)
            if station:
                rec["station"] = station
            fusion = []
            rest = how
            for name, iid in names_by_len:
                for m in re.finditer(re.escape(name) + r"\s*(\d+)\s*個", rest):
                    fusion.append((m.start(), {"id": iid, "n": int(m.group(1))}))
                rest = rest.replace(name, "\0" * len(name))
            if fusion:
                rec["fusion"] = [f for _, f in sorted(fusion, key=lambda t: t[0])]
        recipes.append(rec)
    # Every recipe the sheet does not show (machines, furnaces; scripts/extract_machine_recipes.py). A recipe
    # with several outputs (the centrifuge) is listed under each of them, so every output can be looked up.
    m = read_json("data/recipes_machines.json")
    machine_kind = {}
    for k, v in m["items"].items():
        items.setdefault(k, v[:3])
        machine_kind[k] = v[3]
    cat_of = {str(c[0]).lower(): i for i, c in enumerate(r["cats"])}
    machine_per_cat = [0] * len(r["cats"])
    for mr in m["recipes"]:
        if mr["brand"] not in cat_of:
            die(f"{mr['id']}: no recipe tab for {mr['brand']}")
        cat = cat_of[mr["brand"]]
        machine_per_cat[cat] += 1
        facts = {k: mr[k] for k in ("time", "water", "xp", "dimension", "share") if k in mr}
        for o in mr["outputs"]:
            recipes.append({
                "key": f"{mr['id']}>{o['id']}", "cat": cat, "result": o["id"], "count": o["n"], "grid": None,
                "station": mr["station"], "search": m["search"][mr["id"]],
                "fusion": [{"id": i["id"], "n": i["n"]} for i in mr["inputs"]],
                "inputs": mr["inputs"], "outputs": mr["outputs"], "facts": facts,
            })
    counts = {"workbench": 0, "crucible": 0}
    for st in m["stations"]:
        counts[st["id"]] = 0
    for rec in recipes:
        if not rec.get("outputs"):
            counts[rec["station"]] = counts.get(rec["station"], 0) + 1
    for mr in m["recipes"]:
        counts[mr["station"]] += 1
    station_item = {"workbench": "minecraft:crafting_table", "crucible": "cherry:resonance_crucible",
                    **{st["id"]: st["item"] for st in m["stations"]}}
    # 2026-10-05: the "tsubomi" placeholder chip (a brewing station that never had a recipe, with the
    # message "Tsubomi has not been released") is gone: Tsubomi is released and has its own tab.
    stations = [{"id": sid, "item": station_item[sid], "count": n} for sid, n in counts.items()]
    missing_kind = sorted(k for k in items if k not in kinds and k not in machine_kind)
    return {
        "total": r["total"] + len(m["recipes"]),
        "sources": r["sources"],
        "cats": [{"index": i, "name": c[0], "icon": items.get(c[1], [None, None, None])[2],
                  "count": c[2] + machine_per_cat[i]}
                 for i, c in enumerate(r["cats"])],
        "allTabIcon": items.get(r["all_tab_icon"], [None, None, None])[2],
        "items": {k: {"ja": v[0], "en": v[1], "icon": v[2],
                      "kind": kinds.get(k) or machine_kind.get(k) or ("none" if v[2] is None else "flat")}
                  for k, v in items.items()},
        "recipes": recipes,
        "stations": stations,
        "kindsUnknown": missing_kind,
    }


def recipes_lang(lang: str, shared: dict, bundle: dict) -> dict:
    tr = (bundle.get("recipes") or {}).get("items") or {}
    names, subs, search = {}, {}, {}
    for iid, it in shared["items"].items():
        if lang == "ja":
            name = it["ja"]
            sub = it["en"] if it["en"] and it["en"] != it["ja"] else None
        elif lang == "en":
            name, sub = it["en"], None
        else:
            name = tr.get(iid) or it["en"]
            sub = None if (iid in tr and tr[iid] == it["en"]) else it["en"]
        names[iid] = name
        if sub:
            subs[iid] = sub
    for rec in shared["recipes"]:
        rid = rec["result"]
        # The pre-4.0 portal's exact rule: card text, local name, sub-line (an empty sub still adds its space).
        search[rec["key"]] = " ".join((rec["search"], normalise(names.get(rid, "")), normalise(subs.get(rid, ""))))
    cat_names = (bundle.get("recipes") or {}).get("cat_names") or [c["name"] for c in shared["cats"]]
    if len(cat_names) != len(shared["cats"]):
        die(f"data/i18n/{lang}.json recipes.cat_names has {len(cat_names)} names for {len(shared['cats'])} categories")
    return {"names": names, "subs": subs, "search": search, "catNames": cat_names}


# ------------------------------------------------------------------ changelog

def corvus_title(notes: str) -> str:
    first = re.split(r"\n\s*\n", notes.strip())[0].strip()
    m = re.match(r"^(.*?[.!?])(?:\s|$)", first, re.S)
    title = m.group(1) if m and len(m.group(1)) >= 20 else first
    title = re.sub(r"\s+", " ", title)
    if len(title) > 148:
        title = title[:147].rstrip() + "…"
    return title


def series_of(release: str) -> str:
    return BCL.brand_group_label(release)


def changelog_lang(lang: str, bundle: dict, launcher_notes: dict) -> list[dict]:
    structural = BCL.load_brand_structural()
    brands = []
    with contextlib.redirect_stdout(_quiet):
        for brand in BCL.brand_order():
            if brand == BCL.DEFAULT_BRAND:
                entries = BCL.merged_entries(bundle, lang)
                releases = []
                for e in reversed(entries):
                    releases.append({
                        "id": e["id"], "brand": brand, "version": e["release"], "date": e.get("date"),
                        "type": e.get("type", "release"), "series": series_of(e["release"]),
                        "title": e.get("title", ""), "summary": e.get("summary", ""),
                        "highlights": e.get("highlights") or [], "balance": e.get("balance_changes") or [],
                        "warnings": e.get("warnings") or [], "limits": e.get("known_limitations") or [],
                    })
            else:
                entries = BCL.merged_brand_entries(bundle, lang, brand, structural[brand])
                releases = []
                for e in reversed(entries):
                    releases.append({
                        "id": e["id"], "brand": brand, "version": e["release"], "date": e.get("date"),
                        "type": e.get("type", "release"), "series": series_of(e["release"]),
                        "title": e.get("title", ""), "summary": e.get("summary", ""),
                        "highlights": e.get("highlights") or [], "balance": e.get("balance_changes") or [],
                        "warnings": e.get("warnings") or [], "limits": e.get("known_limitations") or [],
                    })
            brands.append({"id": brand, "name": SC.NAV_LABEL_FALLBACK[brand], "releases": releases})
    corvus = []
    for version in sorted(launcher_notes, key=SC.launcher_version_key, reverse=True):
        notes = launcher_notes[version]
        corvus.append({
            "id": f"corvus-{version}", "brand": "corvus", "version": version, "date": None, "type": "release",
            "series": series_of(version), "title": corvus_title(notes), "summary": "",
            "highlights": [], "balance": [], "warnings": [], "limits": [],
            "paragraphs": [p.strip() for p in re.split(r"\n\s*\n", notes.strip()) if p.strip()],
        })
    brands.append({"id": "corvus", "name": "Corvus Store", "releases": corvus})
    return brands


# ------------------------------------------------------------------ cherry controls (token grammar)

def controls_tokens(text: str, lang: str) -> list:
    out: list = []
    nb = re.compile("(" + "|".join(re.escape(n) for n in CC.NO_BREAK) + ")")

    def plain(s: str) -> None:
        for i, part in enumerate(nb.split(s)):
            if i % 2:
                out.append({"t": "nobreak", "v": part})
            elif part:
                out.append(part)
    at = 0
    for m in CC.TOKEN.finditer(text):
        plain(text[at:m.start()])
        if m.group(1) is not None:
            label = CC.KEYCAP[lang].get(m.group(1), m.group(1))
            out.append({"t": "key", "id": m.group(1), "label": label,
                        "dir": "rtl" if CC.ARABIC.search(label) else "ltr"})
        elif m.group(2) is not None:
            out.append({"t": "en", "v": m.group(2)})
        elif m.group(3) == "release":
            out.append({"t": "release", "v": "Cherry " + CC.CONTROLS_FOR})
        else:
            out.append({"t": "path", "steps": list(CC.PATH[lang]), "sep": " › "})
        at = m.end()
    plain(text[at:])
    return out


def controls_lang(lang: str) -> dict:
    ctl, intro = CC.CONTROLS[lang], CC.INTRO[lang]

    def card(key: str) -> dict:
        p = ctl[key]
        return {
            "id": key, "anchor": "cc-" + key,
            "title": controls_tokens(p["title"], lang),
            "facts": [controls_tokens(f, lang) for f in p["facts"]],
            "keys": [{"action": controls_tokens(a, lang), "how": controls_tokens(h, lang)} for a, h in p["keys"]],
            "lists": [{"title": controls_tokens(t, lang), "items": [controls_tokens(x, lang) for x in items]}
                      for t, items in p["lists"]],
        }
    return {
        "title": intro["title"], "description": intro["desc"], "heading": ctl["heading"],
        "controlsFor": CC.CONTROLS_FOR,
        "note": controls_tokens(CC._fill(intro["note"], lang), lang),
        "layout": controls_tokens(CC._fill(intro["layout"], lang), lang),
        "cards": [card("air"), card("sea")],
    }


# ------------------------------------------------------------------ "model", never "brand"

# Owner, 2026-10-04: 「ライブサイトからブランドという単語を全て削除 モデルに置き換えてください」. The
# portal's own copy (web/src/i18n) says "model" already; this rewrites the word where it reaches the site
# from elsewhere — the Store catalogue inside the launcher jar, the wiki's page copy, the changelog history
# — phrase by phrase, so each language's genders, articles and particles still agree. Only what the site
# shows changes: the files themselves stay as they are (the launcher and the bot read them).
# scripts/check-export.mjs fails any page that still shows the word.
MODEL_WORDS: dict[str, list[tuple[str, str]]] = {
    "ja": [("最上位のブランド", "最上位のモデル"), ("に位置するブランド", "に位置するモデル"), ("基礎ブランド", "基礎モデル"),
           ("注目のブランド", "注目のモデル"), ("は別のブランドで", "は別のモデルで"), ("ブランドを選ぶと", "モデルを選ぶと"),
           ("別ブランドの MOD", "別モデルの MOD")],
    "en": [("Foundation Brand", "Foundation Model"), ("Featured brand", "Featured model"),
           ("Choose a brand to see", "Choose a model to see"),
           ("a separate mod brand that installs", "a separate model that installs")],
    "es": [("Marca Cimiento", "Modelo Cimiento"), ("Marca destacada", "Modelo destacado"),
           ("Elige una marca para ver", "Elige un modelo para ver"),
           ("una marca de mods aparte que se instala", "un modelo aparte que se instala")],
    "fr": [("Marque Fondation", "Modèle Fondation"), ("Marque à l'honneur", "Modèle à l'honneur"),
           ("Choisissez une marque pour voir", "Choisissez un modèle pour voir"),
           ("une marque de mods distincte, qui s'installe", "un modèle distinct, qui s'installe")],
    "zh": [("最高级别的品牌", "最高级别的型号"), ("之下的品牌", "之下的型号"), ("基石品牌", "基石型号"),
           ("精选品牌", "精选型号"), ("选择一个品牌", "选择一个型号"), ("独立模组品牌", "独立型号")],
    "ko": [("최상위 브랜드입니다", "최상위 모델입니다"), ("자리한 브랜드입니다", "자리한 모델입니다"), ("토대 브랜드", "토대 모델"),
           ("추천 브랜드", "추천 모델"), ("별개의 브랜드이며", "별개의 모델이며"), ("브랜드를 고르면", "모델을 고르면"),
           ("별도의 MOD 브랜드입니다", "별도의 MOD 모델입니다")],
    "pt-br": [("Marca Fundação", "Modelo Fundação"), ("Marca em destaque", "Modelo em destaque"),
              ("Escolha uma marca para ver", "Escolha um modelo para ver"),
              ("uma marca de mods à parte, que se instala", "um modelo à parte, que se instala")],
    "it": [("Marchio Fondamenta", "Modello Fondamenta"), ("Brand in evidenza", "Modello in evidenza"),
           ("Scegli un marchio per vedere", "Scegli un modello per vedere"),
           ("un marchio di mod a sé, che si installa", "un modello a sé, che si installa")],
    "ar": [("علامة الأساس", "طراز الأساس"), ("علامة مميزة", "طراز مميز"), ("اختر علامة لترى", "اختر طرازًا لترى"),
           ("علامة مودات مستقلة تُثبَّت", "طراز مستقل يُثبَّت")],
    "ru": [("Бренд-фундамент", "Модель-фундамент"), ("Избранный бренд", "Избранная модель"),
           ("Выберите бренд, чтобы", "Выберите модель, чтобы"),
           ("отдельный бренд модов, который устанавливается", "отдельная модель, которая устанавливается")],
    "id": [("Merek Fondasi", "Model Fondasi"), ("Merek unggulan", "Model unggulan"),
           ("Pilih merek untuk melihat", "Pilih model untuk melihat"),
           ("merek mod terpisah yang dipasang", "model terpisah yang dipasang")],
    "de": [("Fundament-Marke", "Fundament-Modell"), ("Ausgewählte Marke", "Ausgewähltes Modell"),
           ("Wähle eine Marke, um zu sehen", "Wähle ein Modell, um zu sehen"),
           ("eine eigene Mod-Marke, die neben Alpha installiert wird", "ein eigenes Modell, das neben Alpha installiert wird")],
    "tr": [("Temel Taş Markası", "Temel Taş Modeli"), ("Öne çıkan marka", "Öne çıkan model"),
           ("bir marka seçin", "bir model seçin"), ("ayrı bir mod markası", "ayrı bir model")],
}
# The Corvus Store's own release notes (data/launcher_notes.json) are English on every language's page.
ENGLISH_BRAND = re.compile(r"\b([Bb])rand(s|'s)?\b")
MODEL_USED: set[tuple[str, str]] = set()

# The model tiers (owner, 2026-10-04): 「ASTRAEA→頂点モデル OUKA→Xhighモデル Cherry→Highモデル
# Tsubomi→ミディアムモデル AureumとNoctuaには階級はありません。」 The Store's badge slot is where a tier
# shows ("badge · category" in the list, the pill on the hub's card), so a tiered model's badge is its
# tier and an untiered one has none (Noctua's "Server Sovereign" read as a rank there). OUKA's and
# Cherry's lines stated their old places ("the highest tier, above Cherry", "the tier just below OUKA");
# they now state the tier. Pinnacle is a name, like Xhigh and High, in every language (owner, 2026-10-04:
# 「日英どちらもPinnacleを使用します。」); Medium is ミディアム in Japanese, 미디엄 in Korean.
TIERS: dict[str, dict[str, str]] = {
    "ja": {"halia": "Maxモデル", "astraea": "Pinnacleモデル", "ouka": "Xhighモデル", "cherry": "Highモデル", "tsubomi": "ミディアムモデル"},
    "en": {"halia": "Max Model", "astraea": "Pinnacle Model", "ouka": "Xhigh Model", "cherry": "High Model", "tsubomi": "Medium Model"},
    "es": {"halia": "Modelo Max", "astraea": "Modelo Pinnacle", "ouka": "Modelo Xhigh", "cherry": "Modelo High", "tsubomi": "Modelo Medium"},
    "fr": {"halia": "Modèle Max", "astraea": "Modèle Pinnacle", "ouka": "Modèle Xhigh", "cherry": "Modèle High", "tsubomi": "Modèle Medium"},
    "zh": {"halia": "Max 型号", "astraea": "Pinnacle 型号", "ouka": "Xhigh 型号", "cherry": "High 型号", "tsubomi": "Medium 型号"},
    "ko": {"halia": "Max 모델", "astraea": "Pinnacle 모델", "ouka": "Xhigh 모델", "cherry": "High 모델", "tsubomi": "미디엄 모델"},
    "pt-br": {"halia": "Modelo Max", "astraea": "Modelo Pinnacle", "ouka": "Modelo Xhigh", "cherry": "Modelo High", "tsubomi": "Modelo Medium"},
    "it": {"halia": "Modello Max", "astraea": "Modello Pinnacle", "ouka": "Modello Xhigh", "cherry": "Modello High", "tsubomi": "Modello Medium"},
    "ar": {"halia": "طراز Max", "astraea": "طراز Pinnacle", "ouka": "طراز Xhigh", "cherry": "طراز High", "tsubomi": "طراز Medium"},
    "ru": {"halia": "Модель Max", "astraea": "Модель Pinnacle", "ouka": "Модель Xhigh", "cherry": "Модель High", "tsubomi": "Модель Medium"},
    "id": {"halia": "Model Max", "astraea": "Model Pinnacle", "ouka": "Model Xhigh", "cherry": "Model High", "tsubomi": "Model Medium"},
    "de": {"halia": "Max-Modell", "astraea": "Pinnacle-Modell", "ouka": "Xhigh-Modell", "cherry": "High-Modell", "tsubomi": "Medium-Modell"},
    "tr": {"halia": "Max Modeli", "astraea": "Pinnacle Modeli", "ouka": "Xhigh Modeli", "cherry": "High Modeli", "tsubomi": "Medium Modeli"},
}
TIER_LINES: dict[str, list[tuple[str, str]]] = {
    "ja": [("Cherry の上に立つ、最上位のモデル。", "Xhighモデル。"), ("OUKA のすぐ下に位置するモデル。", "Highモデル。")],
    "en": [("The highest tier, above Cherry.", "The Xhigh model."), ("The tier just below OUKA.", "The High model.")],
    "es": [("El nivel más alto, por encima de Cherry.", "El modelo Xhigh."), ("El nivel justo por debajo de OUKA.", "El modelo High.")],
    "fr": [("Le niveau le plus élevé, au-dessus de Cherry.", "Le modèle Xhigh."),
           ("Le niveau juste en dessous d'OUKA.", "Le modèle High.")],
    "zh": [("位于 Cherry 之上,最高级别的型号。", "Xhigh 型号。"), ("位于 OUKA 之下的型号。", "High 型号。")],
    "ko": [("Cherry 위에 서는 최상위 모델입니다.", "Xhigh 모델입니다."), ("OUKA 바로 아래에 자리한 모델입니다.", "High 모델입니다.")],
    "pt-br": [("O nível mais alto, acima do Cherry.", "O modelo Xhigh."), ("O nível logo abaixo de OUKA.", "O modelo High.")],
    "it": [("Il livello più alto, sopra Cherry.", "Il modello Xhigh."), ("Il livello appena sotto OUKA.", "Il modello High.")],
    "ar": [("المستوى الأعلى، فوق Cherry.", "طراز Xhigh."), ("المستوى الذي يلي OUKA مباشرة.", "طراز High.")],
    "ru": [("Высший уровень — выше Cherry.", "Модель Xhigh."), ("Уровень сразу под OUKA.", "Модель High.")],
    "id": [("Tingkat tertinggi, di atas Cherry.", "Model Xhigh."), ("Tingkat tepat di bawah OUKA.", "Model High.")],
    "de": [("Die höchste Stufe, über Cherry.", "Das Xhigh-Modell."), ("Die Stufe direkt unter OUKA.", "Das High-Modell.")],
    "tr": [("En üst seviye; Cherry'nin üzerinde.", "Xhigh modeli."), ("OUKA'nın hemen altındaki seviye.", "High modeli.")],
}


def _walk_strings(obj, fn):
    if isinstance(obj, dict):
        return {k: _walk_strings(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk_strings(v, fn) for v in obj]
    return fn(obj) if isinstance(obj, str) else obj


def say_model(lang: str, data):
    """Every string of one language's page data, with "brand" said as "model" (MODEL_WORDS) and OUKA's and
    Cherry's lines stating their tiers (TIER_LINES)."""
    pairs = MODEL_WORDS.get(lang, []) + TIER_LINES.get(lang, [])

    def fix(s: str) -> str:
        for old, new in pairs:
            if old in s:
                s = s.replace(old, new)
                MODEL_USED.add((lang, old))
        return s
    return _walk_strings(data, fix)


def with_tiers(lang: str, data: dict) -> dict:
    """The tier in the badge slot: a tiered model's badge is its tier (TIERS); Aureum, Noctua and Alpha have none."""
    tiers = TIERS[lang]
    for pid, product in data["products"].items():
        product["badge"] = tiers.get(pid)
    strings = data["launcher"]["storeStrings"]
    for key in [k for k in strings if re.fullmatch(r"store\.[a-z]+\.badge", k)]:
        pid = key.split(".")[1]
        if pid in tiers:
            strings[key] = tiers[pid]
        else:
            del strings[key]
    for pid, tier in tiers.items():
        strings[f"store.{pid}.badge"] = tier
    return data


def english_model(data):
    """English text (the launcher's release notes): brand → model, brands → models, brand's → model's."""
    return _walk_strings(data, lambda s: ENGLISH_BRAND.sub(lambda m: ("M" if m.group(1) == "B" else "m") + "odel" + (m.group(2) or ""), s))


# ------------------------------------------------------------------ per language

def build_lang(lang: str, ctx: dict) -> dict:
    with contextlib.redirect_stdout(_quiet):
        b = SC.load_bundle(lang)
    ui, dl, ap = b["ui"], b["download"], b["aureum_page"]
    leg = ctx["legacy"]["langs"][lang]
    man = ctx["manifest"]
    store = ctx["store"]["messages"][lang]
    up = ctx["upcoming"].get(lang) or die(f"data/upcoming.json has no {lang} block")
    dcb = ctx["discordBot"].get(lang) or die(f"data/discord_bot.json has no {lang} block")

    def need(d: dict, key: str, where: str):
        v = d.get(key)
        if v in (None, ""):
            die(f"{where}.{key} is missing for {lang}")
        return v

    def notice(k: str) -> str:
        return BAL.NOTICE[lang][k].format(**ctx["alphaFacts"])

    retired = ctx["retirement"]
    chrome = {
        "siteTitle": SC.SITE_TITLE,
        "skipLink": ui["skip_link"],
        "home": ui["nav"]["home"],
        "launcher": leg["chrome"]["launcherLabel"],
        "brands": leg["chrome"]["brandsLabel"],
        "recipes": ui["nav"]["recipes"],
        "changelog": ui["nav"]["changelog"],
        "upcoming": up["title"],
        "skin": leg["chrome"]["skinLabel"],
        "discord": dcb["nav"],
        "download": ui["nav"]["download"],
        "menu": ui["menu_toggle"],
        "close": ui["common"]["close"],
        "language": ui["lang_switch_label"],
        "primary": leg["chrome"]["primaryLabel"],
        "footerBrands": leg["chrome"]["brandsLabel"],
        "footerGetStarted": leg["chrome"]["footerGetStarted"],
        "footerReference": leg["chrome"]["footerReference"],
        "footerStatus": leg["chrome"]["footerStatus"],
        "legalTitle": leg["chrome"]["legalTitle"],
        "tagline": ui["site_tagline"],
        "footerNote": ui["footer_note"],
        "arrow": ui["common"]["read_more"],
        "copy": leg["copyButton"]["label"],
        "copied": leg["copyButton"]["done"],
        "fileSize": dl["size_label"],
        "sha256": dl["sha_label"],
        "version": dl["version_label"],
        "launcherVersion": dl["launcher_version_label"],
        "primaryCta": dl["primary_cta"],
    }

    # Products: the Store's own catalogue, with the site's facts.
    products = {}
    for pid in product_ids():
        # A product added after the legacy capture (Halia, 2026-10-11) has no legacy entry: the Store's own strings say it all.
        legp = leg["store"]["products"].get(pid) or {"name": "", "jp": None, "category": "", "tagline": "", "headline": ""}
        avail = availability(pid, man, retired)
        cat_key = "store.category.archive" if pid == "alpha" else f"store.{pid}.category"
        p = {
            "id": pid,
            "name": legp["name"] or SC.NAV_LABEL_FALLBACK.get(pid, pid),
            "jp": legp.get("jp"),
            "availability": avail,
            "category": store.get(cat_key) or legp["category"],
            "badge": store.get(f"store.{pid}.badge"),
            "tagline": store.get(f"store.{pid}.tagline") or legp["tagline"],
            "headline": store.get(f"store.{pid}.headline") or legp["headline"],
            "story": store.get(f"store.{pid}.story"),
            "icon": f"icons/{pid}.png",
            "art": {"ouka": "art/ouka.png", "cherry": "art/cherry.png", "aureum": "art/aureum.jpg"}.get(pid),
            "version": (man.get(pid) or {}).get("latest") or (retired.get("retired_version") if pid == "alpha" else ""),
            "compat": ("" if avail != "available" or pid == "alpha" else
                       "Palworld · Dedicated Server" if pid == "noctua" else f"Minecraft {ctx['mc']} · Fabric"),
            # Every model has a page of its own; launcher/ only as a fallback for one added before its page.
            "href": f"{pid}/" if pid in MODEL_PAGES else f"launcher/#{pid}",
        }
        if pid in ("ouka", "cherry"):
            p["requires"] = [f"{r['label']} {r['value']}" for r in ctx["requires"][pid]]
        elif pid == "aureum":
            p["requires"] = list(BA.REQUIREMENTS)
        else:
            p["requires"] = []
        p["about"] = {"aureum": ap["closing_line"], "alpha": notice("lede")}.get(pid, p["tagline"])
        if pid in ("ouka", "cherry"):
            copy = (BO if pid == "ouka" else BC).COPY[lang]
            p["lede"] = copy["lede"]
        products[pid] = p

    launcher = man["launcher"]
    native = []
    for pid, ext, label in SC.NATIVE_LAUNCHER_PLATFORMS:
        f = launcher["native"].get(pid)
        if f:
            native.append({"platform": pid, "label": label, "ext": ext,
                           **file_facts(f["file_name"], f["download_url"], f["file_size"], f["sha256"])})
    launcher_files = {
        "version": launcher["latest"],
        "native": native,
        "jar": file_facts(launcher["file_name"], launcher["download_url"], launcher["file_size"], launcher["sha256"]),
        "notes": [p for p in launcher["notes"].split("\n\n") if p.strip()],
    }

    home = {
        "title": SC.SITE_TITLE,
        "eyebrow": leg["home"]["eyebrow"],
        "sub": leg["home"]["sub"],
        "description": leg["home"]["sub"],
        "ctaStore": f"Corvus Store {major_minor(launcher['latest'])}",
        "symbolLabel": leg["home"]["symbolLabel"],
        "brandsTitle": leg["home"]["brandsTitle"],
        "hint": leg["home"]["hint"],
        "explore": leg["home"]["explore"],
        "skinTile": leg["home"]["skinTile"],
        "storeTagline": leg["store"]["tagline"],
    }

    stext = dict(leg["store"]["text"])
    stext["close"] = ui["common"]["close"]
    stext["version"] = dl["version_label"]
    stext["readMore"] = ui["common"]["read_more"]
    stext["archivedTitle"] = notice("desc")
    sections = []
    for sec in b["launcher_page"]["sections"]:
        sections.append({"id": sec["id"], "title": sec["title"],
                         "html": re.sub(r'\sclass="[^"]*"', "", sec["body_html"])})
    launcher_page = {
        "title": "Corvus Store",
        "description": leg["store"]["tagline"],
        "hub": leg["store"]["copy"],
        "text": stext,
        "modsHeading": leg["store"]["modsHeading"],
        "macNote": leg["store"]["macNote"],
        "whatsNew": leg["store"]["whatsNew"],
        "notesEnglishOnly": leg["store"]["notesEnglishOnly"],
        "versionHistory": leg["store"]["versionHistory"],
        "guideTitle": leg["store"]["guideTitle"],
        "guideNote": leg["store"]["guideNote"],
        "guideIntro": b["launcher_page"]["intro"],
        "guide": sections,
        "body": dl["launcher_body"],
        "nativeNote": dl["launcher_native_note"],
        "nativeHeading": dl["launcher_native_heading"],
        "jarNote": dl["launcher_jar_note"],
        "cta": dl["launcher_cta"],
        "perch": {k[len("perch."):]: v for k, v in store.items() if k.startswith("perch.")},
        "perchToggle": {"title": store.get("account.perch.toggle.title", ""),
                        "description": store.get("account.perch.toggle.description", "")},
        "storeStrings": {k: v for k, v in store.items() if k.startswith("store.")},
    }

    aureum_file = man["aureum"]
    astraea_file = man.get("astraea")
    tsubomi_file = man.get("tsubomi")
    halia_file = man.get("halia")
    noctua_file = man.get("noctua")
    mc_reqs = [{"label": "Minecraft", "value": f"{ctx['mc']} · Fabric"}]
    download_page = {
        "title": ui["page_titles"]["download"],
        "heading": ui["nav"]["download"],
        "description": leg["download"]["metaDescription"],
        "body": dl["launcher_body"],
        "nativeHeading": dl["launcher_native_heading"],
        "nativeNote": dl["launcher_native_note"],
        "changelogLink": dl["changelog_link_text"],
        "aureum": {"heading": dl["aureum_heading"], "body": dl["aureum_body"], "note": dl["aureum_note"],
                   "cta": dl["aureum_cta"], "version": aureum_file["latest"],
                   "file": file_facts(aureum_file["file_name"], aureum_file["download_url"],
                                      aureum_file["file_size"], aureum_file["sha256"])},
        "astraea": astraea_file and {"version": astraea_file["latest"], "requirements": mc_reqs,
                                     "file": file_facts(astraea_file["file_name"], astraea_file["download_url"],
                                                        astraea_file["file_size"], astraea_file["sha256"])},
        "tsubomi": tsubomi_file and {"version": tsubomi_file["latest"], "requirements": mc_reqs,
                                     "file": file_facts(tsubomi_file["file_name"], tsubomi_file["download_url"],
                                                        tsubomi_file["file_size"], tsubomi_file["sha256"])},
        "halia": halia_file and {"version": halia_file["latest"], "requirements": mc_reqs,
                                 "file": file_facts(halia_file["file_name"], halia_file["download_url"],
                                                    halia_file["file_size"], halia_file["sha256"])},
        "noctua": noctua_file and {"version": noctua_file["latest"],
                                   "requirements": [{"label": "Palworld", "value": "Dedicated Server"}],
                                   "file": file_facts(noctua_file["file_name"], noctua_file["download_url"],
                                                      noctua_file["file_size"], noctua_file["sha256"])},
        "discord": {"heading": dl["discord_heading"], "body": dl["discord_body"], "cta": dl["discord_invite_cta"]},
        "alphaNote": leg["download"]["alphaNote"],
        "alphaVersion": retired.get("retired_version", ""),
    }

    def brand_release(brand: str, module) -> dict:
        m = man[brand]
        return {
            "version": m["latest"], "codename": module.CODENAME,
            "file": file_facts(m["file_name"], m["download_url"], m["file_size"], m["sha256"]),
            "requirements": ctx["requires"][brand],
        }

    ouka = BO.COPY[lang]
    cherry = BC.COPY[lang]
    brands = {
        "ouka": {"title": ouka["title"], "description": ouka["desc"], "eyebrow": ouka["lede"], "line": ouka["line"],
                 "player": {"track": BO.TRACK, "play": BO.PLAY[lang], "pause": BO.PAUSE[lang]},
                 "release": brand_release("ouka", BO)},
        "cherry": {"title": cherry["title"], "description": cherry["desc"], "eyebrow": cherry["lede"],
                   "line": cherry["line"], "controlsLabel": CC.link_label(lang),
                   "release": brand_release("cherry", BC)},
        "aureum": {
            "title": ui["page_titles"].get("aureum") or SC.NAV_LABEL_FALLBACK["aureum"],
            "description": ui["page_descriptions"]["aureum"],
            "version": aureum_file["latest"], "tagline": ap["tagline"],
            "download": {"label": dl["aureum_cta"], "url": aureum_file["download_url"]},
            "detailsLabel": ap["cta_secondary"],
            "statsHeading": ap["section_numbers"],
            "stats": [{"value": BA.STAT_HEAP_VALUE, "label": ap["stat_heap_label"]},
                      {"value": BA.STAT_GEN_VALUE, "label": ap["stat_gen_label"]},
                      {"value": ap["stat_mspt_value"], "label": ap["stat_mspt_label"]}],
            "sections": [{"heading": dl["aureum_heading"], "paragraphs": [dl["aureum_body"], dl["aureum_note"]]},
                         {"heading": ap["section_config"], "paragraphs": [ap["config_body"]],
                          "requirements": {"heading": ap["section_requirements"], "items": list(BA.REQUIREMENTS)}}],
            "closingLine": ap["closing_line"], "sha256": aureum_file["sha256"],
        },
        "controls": controls_lang(lang),
    }

    alpha = {
        "title": SC.PACK_NAME, "description": notice("desc"), "version": retired.get("retired_version", ""),
        "lede": notice("lede"), "ctaRetirement": notice("cta_dl"), "ctaChangelog": notice("cta_log"),
        "sections": [{"heading": notice(f"h{i}"), "body": notice(f"p{i}")} for i in (1, 2, 3, 4)],
    }

    common = ui["common"]
    cl_labels = dict(leg["changelog"]["labels"])
    changelog = {
        "title": ui["page_titles"]["changelog"],
        "description": ui["page_descriptions"]["changelog"],
        "labels": cl_labels,
        "noteBrands": list(BCL.NOTE_BRANDS),
        "brands": changelog_lang(lang, b, ctx["launcherNotes"]),
    }

    rec_labels = dict(leg["recipes"]["labels"])
    rec_labels["machine"] = MACHINE_LABELS[lang]
    recipes = {
        "title": ui["page_titles"]["recipes"],
        "navTitle": ui["nav"]["recipes"],
        "description": ui["page_descriptions"]["recipes"],
        "intro": common["recipes_intro"].replace("{count}", str(ctx["recipes"]["total"])),
        "labels": rec_labels,
        **recipes_lang(lang, ctx["recipes"], b),
    }

    gate = ctx["skinGate"]
    skin_labels = dict(leg["skin"]["labels"])
    for key, table in (("lede", BSG.LEDE), ("note", BSG.NOTE), ("pinLabel", BSG.PIN_LABEL),
                       ("working", BSG.WORKING), ("wrong", BSG.WRONG), ("done", BSG.DONE)):
        if lang in table:
            skin_labels[key] = table[lang]
    skin = {
        "title": BSG.TITLE.get(lang) or leg["chrome"]["skinLabel"],
        "description": leg["skin"]["description"],
        "labels": skin_labels,
    }

    upcoming = {
        "title": up["title"], "description": up["description"], "intro": up["intro"],
        "disclaimer": up["disclaimer"], "more": leg["upcoming"]["more"],
        "nodes": [
            {"id": pid, "kind": "product", "icon": f"icons/{pid}.png", "status": "soon", "headline": products[pid]["name"],
             "body": products[pid]["tagline"], "href": products[pid]["href"], "linkName": products[pid]["name"]}
            for pid in product_ids() if products[pid]["availability"] == "soon"
        ],
    }

    # Every advance notice the board has published (data/teasers.json, scripts/build_teaser_archive.py), newest first.
    teasers = []
    for t in ctx["teasers"]:
        p = (t.get("prose") or {}).get(lang) or die(f"data/teasers.json: {t['id']} has no {lang} prose")
        brand = "alpha" if t.get("kind") in (None, "pack") else t["kind"]
        teasers.append({
            "id": t["id"], "brand": brand, "name": (products.get(brand) or {}).get("name", brand),
            "icon": f"icons/{brand}.png", "announced": t["announced"], "retired": t.get("retired"),
            "headline": p["headline"], "target": p.get("target_label", ""), "body": p.get("body", ""),
            "items": list(p.get("items") or []), "href": t.get("url_path") or "upcoming/",
        })
    teasers.sort(key=lambda x: (x["announced"], x["id"]), reverse=True)

    commands = ctx["discordCommands"]
    groups = []
    for g in commands["groups"]:
        subs = BDC._ordered(g["subcommands"])
        groups.append({
            "name": g["name"], "gloss": dcb["cmd"].get(g["name"], ""),
            "subcommands": [{"name": s["name"], "admin": bool(s.get("admin")),
                             "gloss": dcb["cmd"].get(f"{g['name']} {s['name']}", ""),
                             "params": [p["name"] for p in s.get("parameters") or []]} for s in subs],
        })
    discord = {
        **{k: dcb[k] for k in dcb if k != "cmd"},
        "eyebrow": leg["discord"]["eyebrow"],
        "status": {k: leg["discord"][k] for k in ("statusTitle", "statusInvite", "statusPermissions", "statusLatest",
                                                    "statusFeed", "published", "statusNote")},
        "groups": groups,
    }

    nf = B404.MESSAGES[lang]
    return {
        "lang": lang, "dir": SC.LANG_DIR[lang], "hreflang": SC.HREFLANG_TAG[lang], "name": SC.LANG_NAME[lang],
        "chrome": chrome, "home": home, "products": products, "launcher": launcher_page, "launcherFiles": launcher_files,
        "download": download_page, "brands": brands, "alpha": alpha, "changelog": changelog, "recipes": recipes,
        "skin": skin, "upcoming": upcoming, "teasers": teasers, "discord": discord,
        "notFound": {"heading": nf[0], "body": nf[1]},
        "typeBadge": ui.get("type_badge", {}),
        "pageTitles": ui.get("page_titles", {}),
    }


def skin_public() -> dict | None:
    """The public skin, checked: the file must be the skin the sealed blob carries, byte for byte."""
    path = WIKI / "data" / "skin_public.json"
    if not path.exists():
        return None
    pub = json.loads(path.read_text(encoding="utf-8"))
    data = (WIKI / pub["file"]).read_bytes()
    gate = read_json("data/skin_gate.json")
    digest = hashlib.sha256(data).hexdigest()
    if digest != pub["sha256"] or len(data) != pub["bytes"]:
        die(f"{pub['file']} is not the file data/skin_public.json describes ({digest[:12]}…, {len(data)} B)")
    if digest != gate["plain_sha256"]:
        die(f"{pub['file']} is not the skin the sealed blob carries (data/skin_gate.json plain_sha256)")
    return {"file": pub["file"], "name": pub["name"], "sha256": digest, "bytes": len(data)}


def main() -> None:
    legacy = json.loads((WEB / "src" / "i18n" / "legacy.json").read_text(encoding="utf-8"))
    manifest = read_json("glimpse_manifest.json")
    retirement = SC.alpha_retirement()
    versions = read_json("data/versions.json")
    with contextlib.redirect_stdout(_quiet):
        alpha_facts = BAL.facts()
    problems = CC.problems_in(LANGS)
    if problems:
        die("cherry-controls copy problems:\n  " + "\n  ".join(problems))
    requires = {}
    for brand in ("ouka", "cherry"):
        reqs, rel = requirements_of(brand)
        if rel["sha256"] != manifest[brand]["sha256"] or rel["bytes"] != manifest[brand]["file_size"]:
            die(f"{brand}: the zip on disk and glimpse_manifest.json disagree (rebuild the feeds first)")
        requires[brand] = reqs
    invite, configured = BD._discord_invite()
    discord_cfg = read_json("data/discord.json")
    releases = read_json("releases.json")
    upcoming_feed = read_json("upcoming.json")
    ctx = {
        "legacy": legacy, "manifest": manifest, "retirement": retirement, "mc": versions.get("mc_version", ""),
        "alphaFacts": alpha_facts, "requires": requires, "store": store_catalogue(manifest),
        "upcoming": read_json("data/upcoming.json"), "discordBot": read_json("data/discord_bot.json"),
        "discordCommands": read_json("data/discord_commands.json"),
        "launcherNotes": english_model(read_json("data/launcher_notes.json")),
        "skinGate": read_json("data/skin_gate.json"),
        "teasers": read_json("data/teasers.json")["teasers"],
        "recipes": recipes_shared(legacy),
    }
    langs = {lang: with_tiers(lang, say_model(lang, build_lang(lang, ctx))) for lang in LANGS}
    stale = [f"{lang}: {old!r}" for lang in LANGS for old, _ in MODEL_WORDS.get(lang, []) + TIER_LINES.get(lang, [])
             if (lang, old) not in MODEL_USED]
    if stale:
        # Not fatal: the wiki may have reworded a line itself. check-export still fails a page that shows "brand".
        print(f"extract_wiki: {len(stale)} MODEL_WORDS/TIER_LINES phrase(s) no longer occur: " + "; ".join(stale),
              file=sys.stderr)
    rel0 = (releases.get("releases") or [releases])[0] if isinstance(releases, dict) else releases[0]
    out = {
        "schema": SCHEMA,
        "build": git_facts(),
        "site": {
            "title": SC.SITE_TITLE, "baseUrl": BASE_URL, "basePath": BASE_PATH, "sections": SECTIONS,
            "languages": [{"code": c, "name": n, "dir": d, "hreflang": SC.HREFLANG_TAG[c]} for c, n, d in SC.LANGUAGES
                          if c in LANGS],
            "notFoundTitle": legacy["notFoundTitle"],
        },
        "versions": {"mc": versions.get("mc_version", ""), "launcher": manifest["launcher"]["latest"],
                     **{k: manifest[k]["latest"] for k in ("ouka", "cherry", "aureum", "astraea", "tsubomi", "halia")
                        if k in manifest}},
        "store": {"jar": ctx["store"]["jar"], "version": ctx["store"]["version"]},
        "discord": {
            "clientId": discord_cfg.get("client_id", ""), "permissions": discord_cfg.get("permissions", ""),
            "invite": invite if configured else None,
            "languages": ctx["discordCommands"].get("languages") or [],
            "languageNames": ctx["discordCommands"].get("language_names") or {},
            "routeKinds": ctx["discordCommands"].get("route_kinds") or [],
            "latest": {"title": rel0.get("title", ""), "date": str(rel0.get("published_at", ""))[:10]},
            "feed": {"date": str(upcoming_feed.get("generated_at", ""))[:10],
                     "count": len(upcoming_feed.get("entries") or [])},
        },
        "skinGate": {k: ctx["skinGate"][k] for k in ("blob", "plain_name", "plain_sha256", "plain_bytes", "salt_hex",
                                                      "iterations", "magic")},
        # The owner made the skin public (data/skin_public.json): the model wears it and the file downloads as is.
        "skinPublic": skin_public(),
        "recipes": ctx["recipes"],
        # The films the studio has posted (data/announcements.json), newest first, for the Announcement page.
        "films": read_json("data/announcements.json")["films"],
        "alpha": {"retired": bool(retirement.get("retired")), "version": retirement.get("retired_version", ""),
                  "date": retirement.get("date", alpha_facts.get("date", "")), "modules": alpha_facts["modules"]},
        "langs": langs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size = OUT.stat().st_size
    unknown = ctx["recipes"]["kindsUnknown"]
    print(f"extract_wiki: {len(langs)} languages, {ctx['recipes']['total']} recipes, "
          f"{sum(len(b['releases']) for b in langs['ja']['changelog']['brands'])} changelog entries, "
          f"store {ctx['store']['version']} -> {OUT.relative_to(WEB)} ({size // 1024} KB)"
          + (f"; {len(unknown)} recipe items with no 3D kind (shown flat): {', '.join(unknown[:5])}" if unknown else ""))


if __name__ == "__main__":
    main()
