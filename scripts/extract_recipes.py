#!/usr/bin/env python3
"""
Generates レシピ早見表.html from the actual recipe JSON + texture PNGs of the seven
sorakaze mods (no hand-authored recipe data - re-run this any time a recipe or texture
changes, per UPDATE-v1.1.md section 7's "drift prevention via script" requirement).

Since 2026-08-04 the sheet is rendered as a Minecraft recipe-book style page
(owner's request): a browsable slot grid of all result items, category tabs,
click-to-open crafting recipes (3x3 grid in real positions), and MC-style hover
tooltips showing 日本語名 + English name. The page is still ONE self-contained
HTML file (no external requests), and every texture payload is embedded exactly
once (content-hash dedup + verified-lossless PNG recompression) instead of once
per occurrence, which is what keeps the file size in check.

The data layer (recipe parsing, texture resolution, SPECIAL_ITEMS, the food
catalogue reader, YOMI sorting and its warnings) is unchanged: a card per grid
recipe + a card per no-recipe item, same categories, same五十音 order. Only the
presentation/emission changed. Zero warnings on a healthy run is still the bar.

Usage: python3 tools/gen_recipe_sheet.py

---------------------------------------------------------------------------
ADAPTED FOR THE GLIMPSE ALPHA WIKI (corvus-dev repo).
This is a copy of the mod pack's own tools/gen_recipe_sheet.py, kept
byte-identical from the top of the file down through the end of main()'s
data-assembly + validation logic (every hard-won bug fix / self-check stays
intact). Only the final few lines of main() differ: instead of splicing
everything into one giant self-contained HTML file, it dumps the same
underlying data as data/recipes.json + individual PNGs, which this repo's
own recipes/ page renders with the wiki's own look. See the bottom of
main() for the actual diff.

This script reads from the *source* mod-pack project (mods-src/, the vanilla
client jar, lang files, etc.) which is NOT part of this repo — only the
generated JSON/PNG output is committed here. Re-run this any time the source
project's recipes or textures change, same as the original.
---------------------------------------------------------------------------
"""
import json
import base64
import hashlib
import io
import math
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

# The project root is this repo's parent. It was a typed absolute path until
# 2026-09-10, when the owner renamed the folder to "Corvus developer" and the
# typed path silently pointed at nothing.
ROOT = Path(__file__).resolve().parents[2]
OUT_HTML = ROOT / "レシピ早見表.html"  # unused here; original single-file output
SITE_ROOT = Path(__file__).resolve().parent.parent
OUT_DATA_DIR = SITE_ROOT / "data"
OUT_IMG_DIR = SITE_ROOT / "assets" / "img" / "recipes"

# ---------------------------------------------------------------------------
# モジュールの資源がどこにあるか(2026-09-20)
# ---------------------------------------------------------------------------
# Alpha の 13 モジュールは mods-src の作業木にソースとして在る。Cherry と OUKA は
# **別ブランドの別リポジトリ**で、この機械には jar でしか来ない —— だから配布済みの
# zip(downloads/)から取り出して、同じ "src/main/resources" の形に並べ直したものを
# ここに登録する。
#
# ⚠ **出典は配布物であって、誰かの作業木ではない。**作業木を読むと、まだ配られて
#    いないレシピを早見表に載せてしまう(= 手元にないアイテムの作り方が載る)。
#    extract_versions.py が「downloads/ に実在する zip」を読むのと同じ理由。
MOD_RESOURCE_ROOT = {}
BRAND_JAR = {}      # block -> 配布済み jar の写し(コードの中のレシピを読むため)


def mod_resources(mod_dir):
    """そのモジュールの src/main/resources に当たる場所。"""
    staged = MOD_RESOURCE_ROOT.get(mod_dir)
    if staged is not None:
        return staged
    return ROOT / "mods-src" / mod_dir / "src/main/resources"


MODS = [
    ("sorakaze-guns", "sorakaze_guns", "銃"),
    ("sorakaze-rail", "sorakaze_rail", "電車"),
    ("sorakaze-deco", "sorakaze_deco", "建材"),
    ("sorakaze-vehicles", "sorakaze_vehicles", "乗り物"),
    ("sorakaze-boss", "sorakaze_boss", "ボス"),
    # V1.4.1: 天空 MOD。これを入れ忘れると天空ブロックとエンジェルアローが早見表から丸ごと落ちる。
    ("sorakaze-sky", "sorakaze_sky", "天空"),
    # v1.5.0: サバイバル MOD(7 つ目)。仮面・大盾・水筒・真珠/ルビーの精錬。
    ("sorakaze-survival", "sorakaze_survival", "サバイバル"),
    # v1.8.1: 電力 MOD(8 つ目)。ケーブル・変圧器・分電盤・発電機・原子力発電所・暖炉・エアコン。
    # **ここに足し忘れると 10 レシピが早見表から丸ごと落ちる**(§31.4 と同じ形の欠落。
    # 生成器はカテゴリが未知なら落ちるが、MODS に無いモジュールは黙って存在しないことになる)。
    ("sorakaze-power", "sorakaze_power", "電力"),
    # V2.0.0: 二相楽園(Planarcadia)MOD。**V2.0.0 で初めて配布されたのに、ここに 2 度の
    # ラウンドを跨いで足されないままだった** —— つまり 2 枚のレシピが V2.0.0・V2.1.0 の
    # どちらの早見表にも一度も出ていない。§31.4 / §39 と同じ「MODS に無いものは黙って
    # 存在しないことになる」欠落である。同じことを 3 度やらないために、この直後の
    # `check_mods_roster()` が **一覧を手で信じるのをやめ、mods-src を数えて突き合わせる**。
    ("sorakaze-planarcadia", "sorakaze_planarcadia", "二相楽園"),
    # V4.2.2: 灰街圏(Fallout)MOD。V4.2.0 で配布されたのに 2 版のあいだ MODS に無く、
    # `check_mods_roster()` が V4.2.2 の抽出で初めて名指しで止めた(13 レシピ)。
    ("sorakaze-fallout", "sorakaze_fallout", "灰街圏"),
]

# ---------------------------------------------------------------------------
# 別ブランド(Cherry / OUKA)を配布物から取り込む(2026-09-20)
# ---------------------------------------------------------------------------
# 所有者の指示:「レシピ集に Cherry Mods のアイテム、OUKA のアイテムの作成方法が
# 書かれていない」。これらは Alpha の 13 モジュールではなく **別の製品**なので、
# 独立したタブとして載せる(「同梱 MOD が 15 個になった」のではない)。
#
# ⚠ **一覧を手で書かない。**どのブランドが配布済みかは glimpse_manifest.json が
#    知っている —— ここに名前を書き写せば、次に増えるブランドがまた黙って落ちる
#    (§31.4 / §39 の planarcadia・fallout と同じ形)。マニフェストを**数えて**、
#    数えたものが全部取り込めたかを検証する。
BRAND_CATEGORY = {
    "cherry": "Cherry",
    "ouka": "OUKA",
    # ASTRAEA V1.0.0 (2026-09-30): its own product, its own tab, like Cherry and OUKA.
    "astraea": "ASTRAEA",
    # Tsubomi V1.0.1 (2026-10-05): its own product, its own tab. Unlike the three above it is published as ONE
    # bare jar (downloads/tsubomi-<v>.jar), not a zip of jars - see stage_published_brands().
    "tsubomi": "Tsubomi",
    # Halia V1.1.0 (2026-10-12): the Halia Blade brought its first recipes. One bare jar, like Tsubomi. Its items
    # are drawn by code, so their pictures and readings come from data/halia_icons/ (see the Halia section).
    "halia": "Halia",
}
BRAND_TAB_ICON = {
    "Cherry": "cherry:apex1_rocket",
    "OUKA": "ouka:ouka_caster",
    "ASTRAEA": "astraea:celestial_blade",
    "Tsubomi": "tsubomi:teleport_elevator",
    "Halia": "halia:halia_blade",
}
# Manifest blocks that are published as a bare jar AND have no recipe at all, so they are deliberately not a
# recipe source. This is a CLAIM, not an exemption: stage_published_brands() opens each such jar and counts its
# recipe json, so the day one of them gains a recipe the generation stops (the NO_RECIPE_MODULES rule).
BARE_JAR_WITHOUT_RECIPES = {
    "aureum": "an optimisation mod; its jar carries no data/ at all",
    "xhard": "Corvus XHard (server difficulty, 5.1.0): a server-side mod with no recipe",
}


def _alpha_retired():
    """True once data/retirement.json says Alpha is retired (2026-09-28, owner: 「抹消」).

    Retired means Alpha is not part of the recipe sheet at all: its 13 modules, its special and food cards
    and the 使い方 tab (Alpha's wiring guide) are all left out, and the downloads folder no longer carries
    the pack zip this script used to read them from. The sheet is Cherry + OUKA.
    """
    rp = SITE_ROOT / "data" / "retirement.json"
    if not rp.exists():
        return False
    return bool((json.loads(rp.read_text(encoding="utf-8")).get("alpha") or {}).get("retired"))


RETIRED = _alpha_retired()


def _retired_brands():
    """Brand blocks that data/retirement.json says are retired (ASTRAEA, 2026-10-16: end of service).

    A retired brand is not part of the recipe sheet at all: no tab, no cards, no items, no how-to text, and its
    jar is not read. Its jar stays published (the Store and the Agent read the manifest); the sheet just stops
    describing it. This is the same rule as Alpha's, for every product, so the next retirement is one line in
    data/retirement.json.
    """
    rp = SITE_ROOT / "data" / "retirement.json"
    if not rp.exists():
        return frozenset()
    blocks = json.loads(rp.read_text(encoding="utf-8"))
    return frozenset(k for k, v in blocks.items() if isinstance(v, dict) and v.get("retired"))


RETIRED_BRANDS = _retired_brands()
LIVE_BRAND_CATEGORY = {b: c for b, c in BRAND_CATEGORY.items() if b not in RETIRED_BRANDS}


def _recipe_pack_source(manifest):
    """(version, zip file name) of the pack zip the recipe sheet is generated from, or (None, None)
    when Alpha is retired and the pack is not a source of the sheet any more."""
    if RETIRED:
        return None, None
    pack = manifest.get("pack") or {}
    return pack.get("latest"), pack.get("file_name")


def recipe_sources():
    """この実行が読んだ配布物の版。data/recipes.json に書き、検査が突き合わせる。"""
    manifest = json.loads((SITE_ROOT / "glimpse_manifest.json").read_text(encoding="utf-8"))
    out = {}
    pack_version, _pack_zip = _recipe_pack_source(manifest)
    if pack_version:
        out["pack"] = pack_version
    for block in sorted(LIVE_BRAND_CATEGORY):
        info = manifest.get(block) or {}
        if info.get("latest"):
            out[block] = info["latest"]
    if not out:
        raise SystemExit("ERROR: no published version could be recorded, so nothing would ever "
                         "notice this sheet going stale.")
    return out


def stage_published_pack(staging_root):
    """Alpha の 13 モジュールも、配布済み pack zip の jar から並べ直す。

    2026-09-20、Alpha セッションの指摘で入った。この生成器は Alpha を作業木
    (mods-src)から読んでいたが、**作業木は 26.2、配布されている jar は 26.3**
    (mods-src-mc263 から作られたもの)である。中身は当時たまたま一致していたが、
    「配布物を説明するのに別の木を読む」こと自体が誤りで、実測すると
    `sorakaze_boss/enhanced_beacon_{alpha,beta}.json` の 2 件は**内容が違って**いた
    (published 側だけ fabric:load_conditions を持つ)。

    ⚠ **名前ではなく中身で一致を見る**のが要点。旧版の突き合わせはファイル名しか
      見ておらず、その 2 件を素通りさせていた([[a gate can measure the wrong
      quantity]] と同じ形)。配布物そのものから読めば、突き合わせる相手がいなくなる。

    戻り値: 並べ直したモジュール数。
    """
    manifest = json.loads((SITE_ROOT / "glimpse_manifest.json").read_text(encoding="utf-8"))
    _pack_version, zip_name = _recipe_pack_source(manifest)
    if not zip_name:
        raise SystemExit("ERROR: glimpse_manifest.json has no pack.file_name.")
    zip_path = SITE_ROOT / "downloads" / zip_name
    if not zip_path.exists():
        raise SystemExit(f"ERROR: {zip_path} is not there; the pack cannot be read.")

    # 別ブランドは既に自分の zip から並べ済みなので、ここでは対象外にする
    # (混ぜると「pack から 12 個」と、配布物が違うものまで数えてしまう)。
    wanted = {modid: mod_dir for mod_dir, modid, _cat in MODS
              if mod_dir not in MOD_RESOURCE_ROOT}
    staged = 0
    staged_dirs = set()
    with zipfile.ZipFile(zip_path) as zf:
        jars = [n for n in zf.namelist() if n.endswith(".jar")]
        if not jars:
            raise SystemExit(f"ERROR: {zip_name} contains no jar.")
        for name in jars:
            data = zf.read(name)
            with zipfile.ZipFile(io.BytesIO(data)) as jf:
                members = jf.namelist()
                ids = {m.split("/")[1] for m in members
                       if m.startswith("assets/") and m.count("/") > 1}
                ids |= {m.split("/")[1] for m in members
                        if m.startswith("data/") and m.count("/") > 1}
                mine = sorted(i for i in ids if i in wanted)
                if not mine:
                    continue
                for modid in mine:
                    mod_dir = wanted[modid]
                    dest = staging_root / mod_dir / "src/main/resources"
                    for member in members:
                        if member.endswith("/"):
                            continue
                        if not member.startswith((f"assets/{modid}/", f"data/{modid}/")):
                            continue
                        out = dest / member
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(jf.read(member))
                    # 同じ modid の資源が複数の jar に散っていることがある。dest は
                    # modid ごとに 1 つなので、後から来たぶんは**足される**(上書き
                    # ではない)。だから数えるのは「寄与した jar の数」であって
                    # モジュールの数ではない —— そこを取り違えた数え方を一度書いた。
                    MOD_RESOURCE_ROOT[mod_dir] = dest
                    staged_dirs.add(mod_dir)
                    staged += 1
    missing = sorted(set(wanted.values()) - staged_dirs)
    if missing:
        raise SystemExit(
            "ERROR: %d module(s) in MODS were not found in the published pack %s: %s. "
            "Reading them from the working tree instead is what this staging exists to stop."
            % (len(missing), zip_name, ", ".join(missing)))
    print(f"pack staged: {len(staged_dirs)} module(s) from {zip_name} in {staged} jar "
          f"contribution(s) - recipes, textures and names now come from the jars players "
          f"install")
    return staged


def stage_nested_jars(jar_bytes, modid, dest, wanted):
    """A bare brand jar may carry other jars inside itself (Halia 1.2.0: the Aerie, META-INF/jars/
    halia_aerie-1.2.0.jar, listed in its own fabric.mod.json "jars"). Their resources belong to the same mod id,
    and the players who install the one file get them too, so they are staged beside the outer jar's own:
    recipes, tags and lang. A file that both jars carry must be the same bytes, except the two lang files, which
    are merged key by key; a key in both with different text stops the generation.

    Only what the sheet reads is taken from a nested jar: its recipes, its item tags and its lang files. Its other
    resources (models, sounds, textures, advancements) are not read here, and two jars may legitimately differ in
    them (Halia's sounds.json and the Aerie's do), so they are not compared.

    Returns the number of resource files written from the nested jars."""
    written = 0
    wanted_nested = (f"data/{modid}/recipe/", f"data/{modid}/tags/", f"assets/{modid}/lang/")
    with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jf:
        listed = [e["file"] for e in json.loads(jf.read("fabric.mod.json").decode("utf-8")).get("jars", [])]
        blobs = [(name, jf.read(name)) for name in listed]
    for name, blob in blobs:
        with zipfile.ZipFile(io.BytesIO(blob)) as nf:
            nmeta = json.loads(nf.read("fabric.mod.json").decode("utf-8"))
            n_files = n_recipes = 0
            for member in nf.namelist():
                if member.endswith("/") or not member.startswith(wanted_nested):
                    continue
                data = nf.read(member)
                out = dest / member
                if out.exists():
                    if member.endswith(".json") and "/lang/" in member:
                        have = json.loads(out.read_text(encoding="utf-8"))
                        more = json.loads(data.decode("utf-8"))
                        clash = sorted(k for k in set(have) & set(more) if have[k] != more[k])
                        # Halia 1.3.0: the Aerie and the Vigil each title their own config screen under the one
                        # key halia.configuration.title. A config-screen title names no item and no card, so that
                        # key alone is not a clash for the sheet (the first jar's text is kept, and it is printed).
                        cfg = [k for k in clash if k.endswith(".configuration.title")]
                        for k in cfg:
                            print(f"note: {name} titles its config screen {more[k]!r}; kept {have[k]!r} ({k})")
                            more[k] = have[k]
                        clash = [k for k in clash if k not in cfg]
                        if clash:
                            raise SystemExit(f"ERROR: {name} and the outer jar both translate {member} "
                                             f"differently ({len(clash)} key(s), e.g. {clash[0]!r}).")
                        have.update(more)
                        out.write_text(json.dumps(have, ensure_ascii=False, indent=1), encoding="utf-8")
                        continue
                    if out.read_bytes() != data:
                        raise SystemExit(f"ERROR: {name} and the outer jar both carry {member} with different "
                                         f"bytes. Refusing to pick one.")
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                n_files += 1
                if member.startswith(f"data/{modid}/recipe/") and member.endswith(".json"):
                    n_recipes += 1
            written += n_files
            print(f"nested jar staged: {nmeta['id']} {nmeta['version']} from {name} "
                  f"({n_files} new resource file(s), {n_recipes} recipe json)")
    return written


def stage_published_brands(staging_root):
    """配布済みブランドの jar を downloads/ から取り出し、資源を mods-src と同じ形に並べる。

    戻り値: [(mod_dir, modid, category), ...] —— MODS に足すぶん。
    マニフェストが数えたブランドのうち 1 つでも取り込めなければ **止まる**。
    """
    manifest_path = SITE_ROOT / "glimpse_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"ERROR: {manifest_path} is missing - run build_glimpse_manifest.py first. "
                         f"Without it there is no list of published brands, and an empty list "
                         f"would make 'every brand was staged' vacuously true.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # ブランドの見分け方は名前ではなく**形**: mod_id を持ち、(a) jars を持つ zip の束、または (b) file_name が
    # .jar の**裸の jar**(Tsubomi、Aureum。2026-10-05 に (b) を足した)。(a) だけ見ていたので、Tsubomi は
    # 「ブランドが 1 つも無い」のではなく**黙って数えられない**ブロックだった。
    def is_zip_brand(v):
        return isinstance(v, dict) and "mod_id" in v and isinstance(v.get("jars"), dict)

    def is_bare_jar_brand(v):
        return (isinstance(v, dict) and "mod_id" in v and "jars" not in v
                and str(v.get("file_name", "")).endswith(".jar"))

    def is_external_pin(v):
        # A third-party mod the Store installs straight from its own source (Punchy!, Fabric API: 2026-10-26/27). Corvus
        # holds no copy (the licence forbids hosting or it is simply not ours), so there is no jar to read recipes from and
        # it is never a recipe source: it is named here, not silently skipped, and its own pin gates check it.
        return isinstance(v, dict) and v.get("hosted_by_corvus") is False

    external = sorted(k for k, v in manifest.items() if is_external_pin(v))
    blocks = {k: v for k, v in manifest.items()
              if (is_zip_brand(v) or is_bare_jar_brand(v)) and not is_external_pin(v)}
    if external:
        print("external pin(s), not hosted by Corvus and not a recipe source: " + ", ".join(external))
    if not blocks:
        raise SystemExit("ERROR: glimpse_manifest.json declares no brand block (mod_id + jars). "
                         "That is not 'no brands are published' - it means this reader is looking "
                         "at the wrong shape, and nothing would be added without a word.")

    staged = []
    unknown = []
    skipped_no_recipe = []
    skipped_retired = []
    for block, info in sorted(blocks.items()):
        if block in RETIRED_BRANDS:
            # Retired (data/retirement.json): not a source of the sheet, and its jar is not read at all.
            skipped_retired.append(block)
            continue
        modid = info["mod_id"]
        bare = is_bare_jar_brand(info)
        cat = BRAND_CATEGORY.get(block)
        zip_path = SITE_ROOT / "downloads" / info["file_name"]
        if cat is None and bare and block in BARE_JAR_WITHOUT_RECIPES:
            # The claim "this jar has no recipe" is checked, not trusted.
            if not zip_path.exists():
                raise SystemExit(f"ERROR: the manifest publishes {block} as {info['file_name']}, but "
                                 f"{zip_path} is not there.")
            with zipfile.ZipFile(zip_path) as jf:
                recipes_in = [m for m in jf.namelist()
                              if m.startswith(f"data/{modid}/recipe/") and m.endswith(".json")]
            if recipes_in:
                raise SystemExit(f"ERROR: {block} is listed in BARE_JAR_WITHOUT_RECIPES ("
                                 f"{BARE_JAR_WITHOUT_RECIPES[block]}), but {info['file_name']} carries "
                                 f"{len(recipes_in)} recipe json. Give it a BRAND_CATEGORY entry instead.")
            skipped_no_recipe.append(block)
            continue
        if cat is None:
            unknown.append(block)
            continue
        if not zip_path.exists():
            raise SystemExit(f"ERROR: the manifest publishes {block} as {info['file_name']}, but "
                             f"{zip_path} is not there. The sheet must be generated from the bytes "
                             f"players download, not from a working tree.")
        if bare:
            # The published artefact IS the mod jar. Its bytes must be the ones the manifest names.
            jar_bytes = zip_path.read_bytes()
            got = hashlib.sha256(jar_bytes).hexdigest()
            if got != info["sha256"]:
                raise SystemExit(f"ERROR: {info['file_name']} hashes {got}, but the manifest says "
                                 f"{info['sha256']}. Refusing to document a jar that is not the "
                                 f"published one.")
            with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jf:
                meta = json.loads(jf.read("fabric.mod.json").decode("utf-8"))
            if meta.get("id") != modid or meta.get("version") != info["latest"]:
                raise SystemExit(f"ERROR: {info['file_name']}'s own fabric.mod.json says "
                                 f"{meta.get('id')!r} {meta.get('version')!r}, the manifest says "
                                 f"{modid!r} {info['latest']!r}.")
            jar_entry = {"version": meta["version"]}
        else:
            jar_entry = info["jars"].get(modid)
            if jar_entry is None:
                raise SystemExit(f"ERROR: {block}'s manifest block has no jar named {modid!r} "
                                 f"(it lists {sorted(info['jars'])}). Its own jar is what carries the "
                                 f"recipes, so there is nothing to read.")
            with zipfile.ZipFile(zip_path) as zf:
                jar_bytes = zf.read(jar_entry["path"])
            got = hashlib.sha256(jar_bytes).hexdigest()
            if got != jar_entry["sha256"]:
                raise SystemExit(f"ERROR: {jar_entry['path']} inside {info['file_name']} hashes {got}, "
                                 f"but the manifest says {jar_entry['sha256']}. Refusing to document "
                                 f"a jar that is not the published one.")

        dest = staging_root / block / "src/main/resources"
        dest.parent.mkdir(parents=True, exist_ok=True)
        jar_copy = dest.parent / "published.jar"
        jar_copy.write_bytes(jar_bytes)
        BRAND_JAR[block] = jar_copy
        wanted = (f"assets/{modid}/", f"data/{modid}/")
        n = 0
        with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jf:
            for member in jf.namelist():
                if member.endswith("/") or not member.startswith(wanted):
                    continue
                out = dest / member
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(jf.read(member))
                n += 1
        if bare:
            n += stage_nested_jars(jar_bytes, modid, dest, wanted)
        recipes = len(list((dest / "data" / modid / "recipe").glob("*.json")))
        if recipes == 0:
            raise SystemExit(f"ERROR: {block} staged {n} resource file(s) but no recipe json. "
                             f"A brand with zero recipes would be added as an empty tab, which "
                             f"reads as 'this brand has nothing to craft' rather than as a fault.")
        MOD_RESOURCE_ROOT[block] = dest
        staged.append((block, modid, cat))
        print(f"brand staged: {block} {jar_entry['version']} from {info['file_name']} "
              f"({n} resource file(s), {recipes} recipe json)")

    if unknown:
        raise SystemExit(
            "ERROR: the manifest publishes %d brand(s) this script has no category for: %s. "
            "Add them to BRAND_CATEGORY and BRAND_TAB_ICON - leaving them out is how a whole "
            "product's recipes go missing without a word."
            % (len(unknown), ", ".join(sorted(unknown))))
    if len(staged) + len(skipped_no_recipe) + len(skipped_retired) != len(blocks):
        raise SystemExit(f"ERROR: the manifest counts {len(blocks)} brand(s) but only "
                         f"{len(staged)} were staged, {len(skipped_no_recipe)} set aside as "
                         f"recipe-less and {len(skipped_retired)} retired.")
    if skipped_no_recipe:
        print("brand set aside (bare jar, verified to carry no recipe): " + ", ".join(skipped_no_recipe))
    if skipped_retired:
        print("brand retired (data/retirement.json), not in the sheet: " + ", ".join(skipped_retired))
    return staged


# ---------------------------------------------------------------------------
# コードの中にしか無いレシピ(2026-09-20)
# ---------------------------------------------------------------------------
# Cherry の「分子共鳴融合炉」は data/cherry/recipe/ を使わない —— 融合の式は
# FusionRecipes.catalystFormula() に**コードとして**書かれている。だから json だけを
# 読むと、アストラル触媒は「レシピの無いアイテム」として出てしまう。実際には
# 炉で作れるので、それは嘘になる。
#
# ⚠ **式を手で書き写さない。**配布済み jar のバイトコードから読む。写した瞬間、
#    次に係数が変わったときに早見表だけが古いことを言い続ける(§電力ガイドの
#    「134 値すべて実装から読む」と同じ規律)。読めなければ**止まる**。
FUSION_READERS = {
    # block -> (クラス, メソッド, 生成物の item id, 装置の item id)
    "cherry": ("com/cherry/v1/common/block/FusionRecipes.class", "catalystFormula",
               "cherry:astral_catalyst", "cherry:resonance_crucible"),
}


def read_code_only_recipes(reg):
    """コードの中だけにあるレシピを SPECIAL_ITEMS と同じ形のタプル列にして返す。"""
    out = []
    for block, (cls, method, result_id, device_id) in sorted(FUSION_READERS.items()):
        jar = BRAND_JAR.get(block)
        if jar is None:
            raise SystemExit(f"ERROR: {block} has a code-only recipe to read but was never staged.")
        with zipfile.ZipFile(jar) as jf:
            if cls not in jf.namelist():
                raise SystemExit(
                    f"ERROR: {cls} is not in the published {block} jar any more. The fusion "
                    f"formula was read from it, so the sheet would quietly stop describing how "
                    f"{result_id} is made. Find where the recipe moved to.")
            with tempfile.TemporaryDirectory(prefix="fusion-") as td:
                target = Path(td) / "K.class"
                target.write_bytes(jf.read(cls))
                try:
                    dis = subprocess.run(["javap", "-p", "-c", str(target)],
                                         capture_output=True, text=True, timeout=120)
                except (OSError, subprocess.TimeoutExpired) as e:
                    raise SystemExit(
                        f"ERROR: cannot run javap to read {block}'s fusion formula ({e}). The "
                        f"formula is not written down anywhere else on purpose - typing it here "
                        f"by hand is what this check exists to prevent. Install a JDK.")
        if dis.returncode != 0:
            raise SystemExit(f"ERROR: javap failed on {cls}: {dis.stderr.strip()[:300]}")

        # catalystFormula() の本体だけを見る。put(ITEM, N) が並んでいる。
        body = dis.stdout.split(f"{method}();", 1)
        if len(body) < 2:
            raise SystemExit(f"ERROR: {cls} no longer has a {method}() to read.")
        body = body[1].split("\n  public ", 1)[0].split("\n  private ", 1)[0]
        pairs = re.findall(
            r"Field com/cherry/v1/common/item/CherryItems\.([A-Z0-9_]+):.*?\n\s*\d+:\s*"
            r"(?:iconst_(\d)|bipush\s+(\d+)|sipush\s+(\d+))",
            body, flags=re.S)
        formula = []
        for name, a, b, c in pairs:
            formula.append((f"{block}:{name.lower()}", int(a or b or c)))
        if not formula:
            raise SystemExit(
                f"ERROR: read {cls}'s {method}() but found no ingredient at all. An empty "
                f"formula would print '{result_id} is made from nothing', which is worse than "
                f"not printing it. The bytecode shape has changed.")

        parts = []
        for item_id, count in formula:
            ja, _en, _tex = reg.register(item_id)
            if ja == item_id.split(":", 1)[1]:
                raise SystemExit(
                    f"ERROR: {item_id} has no display name, so the fusion recipe would read "
                    f"'{ja} x{count}'. Either the id was renamed or the lang file lost a key.")
            parts.append(f"{ja} {count} 個")
        device_ja, _e, _t = reg.register(device_id)
        how = "%sに、%sを入れて融合させる(作業台では作れない)" % (device_ja, "・".join(parts))
        modid, name = result_id.split(":", 1)
        out.append((modid, name, how, BRAND_CATEGORY[block]))
        print(f"code-only recipe: {result_id} <- {' + '.join(f'{i} x{c}' for i, c in formula)} "
              f"(read from {jar.name})")
    return out


# ---------------------------------------------------------------------------
# 配られていないレシピを載せない(2026-09-20)
# ---------------------------------------------------------------------------
# この生成器は Alpha のレシピを **作業木**(mods-src)から読む。作業木には、まだ
# 配布されていない版の作業が入っていることがある —— 実際 2026-09-20 の時点で
# `sorakaze_fallout/approach_flare_from_stubs.json` が木にだけ在り、配布済みの
# alpha-fallout-4.4.0.1 には無かった(V4.4.1 は保留中)。そのまま作り直すと
# **手元のゲームでは作れない作り方**を早見表に載せることになる。
#
# ⚠ これは「載せ忘れ」の逆側の失敗で、見つけにくい: 出力は増えるので、数が減る
#    検査には引っかからない。だから配布物のほうを**正**として突き合わせる。
def published_recipe_names():
    """配布済み zip のなかに実在するレシピ名を modid ごとに集める。

    戻り値: {modid: {"foo.json", ...}}。ここに無い名前は早見表に載せない。
    """
    manifest_path = SITE_ROOT / "glimpse_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _pack_version, zip_name = _recipe_pack_source(manifest)
    if not zip_name:
        raise SystemExit("ERROR: glimpse_manifest.json has no pack.file_name, so there is no "
                         "published pack to check the recipes against. Refusing to guess.")
    zip_path = SITE_ROOT / "downloads" / zip_name
    if not zip_path.exists():
        raise SystemExit(f"ERROR: the manifest publishes the pack as {zip_name}, but {zip_path} "
                         f"is not there.")
    by_modid = {}
    with zipfile.ZipFile(zip_path) as zf:
        jars = [n for n in zf.namelist() if n.endswith(".jar")]
        if not jars:
            raise SystemExit(f"ERROR: {zip_name} contains no jar at all - this reader is looking "
                             f"at the wrong shape, and an empty answer would withhold EVERY "
                             f"recipe rather than none.")
        for name in jars:
            with zipfile.ZipFile(io.BytesIO(zf.read(name))) as jf:
                for member in jf.namelist():
                    m = re.match(r"^data/([a-z0-9_]+)/recipe/(.+\.json)$", member)
                    if m:
                        by_modid.setdefault(m.group(1), set()).add(m.group(2))
    if not by_modid:
        raise SystemExit(f"ERROR: no recipe json found in any jar inside {zip_name}.")
    return by_modid


# ---------------------------------------------------------------------------
# MODS の取りこぼし検出(V2.1.0 で新設)
# ---------------------------------------------------------------------------
# ⚠ **「無い」と宣言することが、無いことを検出する仕掛けを切る。**
#    バックルームズは「レシピが 0 件だから MODS に要らない」と分かっていた。
#    その判断は正しかったが、同じ判断の下で **本当にレシピを持つ二相楽園も**
#    黙って外れていた。だから下の一覧は「免除リスト」ではなく **主張** であり、
#    `check_mods_roster()` は毎回その主張を **実際に数え直して検証する**。
#    ここに載っているモジュールが 1 件でもレシピを持ったら、生成は止まる。
NO_RECIPE_MODULES = {
    "sorakaze-backrooms": "階層そのものが中身で、クラフト可能なアイテムを 1 つも持たない",
    "sorakaze-sapporo": "V2.1.0 には同梱されていない(V2.2 へ持ち越し)",
}

# 「今日 mods-src にレシピを持つモジュールがいくつあるか」の下限。
# 数が減る = 数え方が壊れた(パスの構造が変わった等)ということなので、
# **0 件や 1 件を『見つからなかった』ではなく『無い』と読んで素通りする**のを防ぐ。
MODS_FLOOR = 9


def check_mods_roster():
    """mods-src を歩いて、レシピを持つモジュールが全部 MODS に載っているか確かめる。

    出典は **ディスク上の mods-src ただ 1 つ**。ここに名前を書き写さない ——
    書き写した瞬間に、次に増えるモジュールがまた黙って落ちる。
    バックアップ用の複製(`sorakaze-boss.pre-...` のように名前に `.` を含む)は
    出荷対象ではないので数えない。
    """
    src = ROOT / "mods-src"
    if not src.is_dir():
        raise SystemExit(f"ERROR: {src} is not a directory - the roster check cannot run, and "
                         f"skipping it is exactly how sorakaze-planarcadia went missing")
    found = {}          # mod_dir -> レシピ json の数
    for d in sorted(src.iterdir()):
        if not d.is_dir() or not d.name.startswith("sorakaze-") or "." in d.name:
            continue
        modid = "sorakaze_" + d.name[len("sorakaze-"):]
        n = 0
        for sub in ("recipe", "recipes"):
            n += len(list((d / "src/main/resources/data" / modid / sub).glob("*.json")))
        found[d.name] = n

    if not found:
        raise SystemExit(
            f"ERROR: no sorakaze-* module directories found under {src}. That is not "
            f"'the suite has no modules' - it means this walk is looking in the wrong place, "
            f"and an empty roster would make every check below vacuously true.")

    # 取り込んだ別ブランドは mods-src に無くて当たり前なので、この検査の対象外。
    listed = {mod_dir for mod_dir, _, _ in MODS if mod_dir not in MOD_RESOURCE_ROOT}
    with_recipes = {name for name, n in found.items() if n > 0}

    missing = sorted(with_recipes - listed)
    if missing:
        raise SystemExit(
            "ERROR: %d module(s) ship craftable recipes but are not in MODS, so every one of "
            "their recipes would be silently absent from the sheet: %s"
            % (len(missing), ", ".join(f"{m} ({found[m]} recipe json)" for m in missing)))

    # 「レシピが無い」という主張のほうを検証する。増えていたら止まる。
    for name, why in sorted(NO_RECIPE_MODULES.items()):
        if name not in found:
            print(f"NOTE: NO_RECIPE_MODULES lists {name}, but it is not in mods-src any more "
                  f"(claim: {why}) - remove the entry once that is intentional")
            continue
        if found[name] > 0:
            raise SystemExit(
                "ERROR: %s is declared recipe-less (%s) but now has %d recipe json(s). "
                "The declaration is what switches off the missing-module detector, so it must "
                "not be allowed to go stale: add %s to MODS (with a category, a cat_order entry "
                "and a CATEGORY_TAB_ICON) instead."
                % (name, why, found[name], name))

    # 一覧に載っているのに mods-src に無いもの(名前の打ち間違い)も黙って通さない。
    ghosts = sorted(listed - set(found))
    if ghosts:
        raise SystemExit(
            "ERROR: MODS names %d directory(ies) that do not exist under mods-src: %s"
            % (len(ghosts), ", ".join(ghosts)))

    if len(found) < MODS_FLOOR:
        raise SystemExit(
            "ERROR: only %d sorakaze-* module(s) found under %s, below the floor of %d. "
            "A count that shrank means the walk broke, not that modules were deleted."
            % (len(found), src, MODS_FLOOR))

    unlisted = sorted(set(found) - listed)
    print("mods roster: %d module dir(s) in mods-src, %d in MODS, %d recipe json(s) total; "
          "recipe-less and declared: %s"
          % (len(found), len(listed), sum(found.values()), ", ".join(unlisted) or "(none)"))


# V4.2.2: V4.2.0 以前の扉 102 種は消えた。残るのは装甲扉 2 種とキット扉 10 種で、
# 規則(*_door / *_hatch)から外れる 4 つ(門 3 つと落とし格子)だけをここで拾う。
DOOR_IDS = {"studded_double_gate", "hangar_blast_gate", "geared_gate", "portcullis"}

# ===========================================================================
# 名前が無いまま出荷されているもの(v1.8.4 時点で判明した 17 件)
# ===========================================================================
# `display_name()` は lang に鍵が無いと **生の id をそのまま返す**。だから
# 「ミサイルランチャー」ではなく `missile_launcher` と書かれたカードが、
# **警告も出さずに**出てしまう(読みの検査も ASCII をローマ字として読めるので通る)。
# 実際に v1.8.4 のページで 17 枚がそうなっていた —— しかもこれは早見表だけの
# 問題ではなく、**ゲーム内でも翻訳鍵がそのまま名前として出る**(= jar の欠陥)。
#
# ⚠ この一覧は<b>減らすためだけにある</b>。
#   ・ここに無いものが新しく名前を失ったら **生成を止める**(退行を通さない)。
#   ・ここに載っているものが直ったら、やはり **生成を止めて** 削除を促す
#     (直ったのに載ったままだと、一覧が「まだ壊れている」と嘘をつく。
#      `USED_FACTS` の「使われない読み取りは死んでいる」と同じ規律)。
#
# 直しかた: 各 MOD の `lang/ja_jp.json` と `lang/en_us.json` に
#   `block.sorakaze_guns.missile_launcher` / `block.sorakaze_deco.<色>_reinforced_glass_pane`
# を足して **その MOD を再ビルドして dist に入れ直す**(lang だけ直しても jar は古いまま)。
KNOWN_UNNAMED = frozenset({
    # ⚠ `sorakaze_guns:missile_launcher` は 2026-08-09 に**直したので外した**。
    #    表示名・ツールチップ 4 行・パネルの 46 鍵をまとめて両言語に入れてある
    #    (所有者の「発射台はどこにあるんですか?」への対応)。この行を戻すと、
    #    上の規律どおり「直ったのに載っている」で生成が止まる。
    # ⚠ 建材 v1.7.7 の強化ガラスの窓 16 件(黒以外の全色 + 無色)は
    #    **2026-08-17 に直ったので外した**。同日の「遮光付き強化ガラス」作業で
    #    `block.sorakaze_deco.<色>_reinforced_glass_pane` が ja_jp / en_us の
    #    両方に入り、この生成器が自分から
    #      「ERROR: 16 id(s) in KNOWN_UNNAMED now have a proper name」
    #    と言って **exit 1 で生成を拒んだ**(上の規律どおり)。だから消したので
    #    あって、通すために消したのではない。1 件でも戻れば `regressions` 側で
    #    また止まる。
    #
    # ここが空になった = 「名前の無いまま出荷されているものは 0 件」。
    # 新しく名前を失ったものが出れば `regressions` で生成が止まる(空集合でも
    # 検査は空虚にならない: 引き算の向きが逆なので下の `fixed` 検査だけが無効化される)。
})

# レシピを持たない(=クラフト不可の)特別入手アイテム。早見表には「入手方法」カードとして掲載する
# (V1.3.0update.md §6.2: 強化ビーコンは「ボスドロップ」表記)。
SPECIAL_ITEMS = [
    # (modid, item_name, 入手方法テキスト, カテゴリ)
    ("sorakaze_boss", "enhanced_beacon", "スカルクゴーレム討伐のドロップ(クラフト不可)", "ボス"),
    ("sorakaze_boss", "excalibur", "ロックロック(ネザーのボス)討伐のドロップ(クラフト不可)", "ボス"),
    # v1.4 のボス 5 体の専用ツール(過剰エンチャント付き。クラフト不可)。
    ("sorakaze_boss", "runecore_pickaxe", "ルーンコア・コロッサス討伐のドロップ(クラフト不可)", "ボス"),
    ("sorakaze_boss", "ember_axe", "エンバーロード討伐のドロップ(クラフト不可)", "ボス"),
    ("sorakaze_boss", "treant_hoe", "エルダー・トレント討伐のドロップ(クラフト不可)", "ボス"),
    ("sorakaze_boss", "void_spear", "ヴォイド・ストーカー討伐のドロップ(クラフト不可)", "ボス"),
    ("sorakaze_boss", "frost_shovel", "フロスト・リッチ・キング討伐のドロップ(クラフト不可)", "ボス"),
    # V1.4.1: 巨大ボス 3 体の専用ドロップ。
    ("sorakaze_boss", "grim_reapers_scythe",
     "グレイブバウンド・リーパー討伐のドロップ(クラフト不可)。範囲攻撃つき", "ボス"),
    ("sorakaze_boss", "abyssal_trident",
     "アビサル・クラウン・クラーケン討伐のドロップ(クラフト不可)。水中で強化", "ボス"),
    ("sorakaze_boss", "thunder_spear",
     "テンペスト・タイタン討伐のドロップ(クラフト不可)。命中で落雷", "ボス"),
    # V1.4.1 §1.4: エンジェル装備は矢以外クラフト不可 — エンジェルから購入する。
    ("sorakaze_sky", "angels_sword", "天空都市のエンジェルから購入(30 エメラルド〜)", "天空"),
    ("sorakaze_sky", "angels_bow", "天空都市のエンジェルから購入(30 エメラルド〜)", "天空"),
    ("sorakaze_sky", "angels_shield", "天空都市のエンジェルから購入(30 エメラルド〜)", "天空"),
    ("sorakaze_sky", "angels_halo", "天空都市のエンジェルから購入(30 エメラルド〜)", "天空"),
    ("sorakaze_sky", "angels_plate", "天空都市のエンジェルから購入(30 エメラルド〜)", "天空"),
    ("sorakaze_sky", "angels_trousers", "天空都市のエンジェルから購入(30 エメラルド〜)", "天空"),
    ("sorakaze_sky", "angels_boots", "天空都市のエンジェルから購入(30 エメラルド〜)", "天空"),
    ("sorakaze_sky", "angels_wings",
     "天空都市のエンジェルから購入(30 エメラルド〜)。チェストプレートとは同時装備できない", "天空"),
    # v1.4.6 §7-2: 天空のボス(スカイ・アークエンジェル)の確定ドロップ。クラフト不可。
    ("sorakaze_sky", "angels_staff",
     "天空城のボス「スカイ・アークエンジェル」討伐の確定ドロップ(クラフト不可)。空中で威力1.5倍", "天空"),
    # v1.4.8 §2-6: クリスタル・ワイバーンの卵。討伐のドロップ・クラフト不可。
    # ※ v1.5.2 §4-3 でドロップ率 100% → 20% に変更。
    ("sorakaze_sky", "crystal_wyvern_egg",
     "クリスタル・ワイバーン討伐でまれにドロップ(20%・クラフト不可)。孵化装置に入れると、なつくワイバーンが孵る",
     "天空"),
    # v1.5.2 §4-2: 王族装備。矢だけがクラフト可能で、本体 6 種は王国商人からの購入限定
    # (宝箱にも入らない)。エンジェル装備と同じ「入手方法」カードで載せないと、
    # 早見表を見た人には「存在しないアイテム」に見えてしまう。
    ("sorakaze_sky", "royal_sword",
     "天空王国の王国商人から購入(クラフト不可)。エメラルドブロック 2 枠 = 1,000 エメラルド以上", "天空"),
    ("sorakaze_sky", "royal_bow",
     "天空王国の王国商人から購入(クラフト不可)。エメラルドブロック 2 枠 = 1,000 エメラルド以上", "天空"),
    ("sorakaze_sky", "royal_crown",
     "天空王国の王国商人から購入(クラフト不可)。エメラルドブロック 2 枠 = 1,000 エメラルド以上", "天空"),
    ("sorakaze_sky", "royal_chestplate",
     "天空王国の王国商人から購入(クラフト不可)。エメラルドブロック 2 枠 = 1,000 エメラルド以上", "天空"),
    ("sorakaze_sky", "royal_leggings",
     "天空王国の王国商人から購入(クラフト不可)。エメラルドブロック 2 枠 = 1,000 エメラルド以上", "天空"),
    ("sorakaze_sky", "royal_boots",
     "天空王国の王国商人から購入(クラフト不可)。エメラルドブロック 2 枠 = 1,000 エメラルド以上", "天空"),
    # v1.5.2 §4-3: REX の卵。討伐でまれにドロップ(30%)・クラフト不可。
    ("sorakaze_sky", "rex_egg",
     "野生の REX 討伐でまれにドロップ(30%・クラフト不可)。孵化装置に入れると、なつく REX が孵る", "天空"),
    # ---- V1.7.0 -------------------------------------------------------------
    # ここから下は v1.7.0 で増えた「レシピを持たないアイテム」。
    # **登録済みアイテムとレシピの差を機械的に取って洗い出した**(手で思い出したのではない)。
    # 載せ忘れると §29.6-11 の王族装備と同じで「早見表には存在しないアイテム」になる。
    ("sorakaze_boss", "universal_harvester",
     "ウィザーストーム討伐の確定ドロップ(クラフト不可)。壊したブロックをそのまま回収できる", "ボス"),
    # v1.9.0: ウィザーストーム全面刷新にともなう新しい確定ドロップ 2 種。
    ("sorakaze_boss", "universal_harvester_alpha",
     "ウィザーストーム討伐の確定ドロップ(クラフト不可)。金のツルハシと同じ耐久32・エンチャント不可。"
     "無印の万物採集器とは別アイテム", "ボス"),
    ("sorakaze_survival", "spark_doll_alpha",
     "ウィザーストーム討伐の確定ドロップ(クラフト不可)。トーテム・オブ・アンダイイングの2倍の効果を、"
     "回数無制限(発動後3分クールダウン)で発揮する花火人形の上位版", "サバイバル"),
    ("sorakaze_sky", "siege_maul",
     "「鎧の侵略者」(天空王国を襲う襲撃ボス)からの戦利品(クラフト不可)。遅いが一撃が重い", "天空"),
    ("sorakaze_deco", "special_atm",
     "シンガポール都市国家に置かれている金色の ATM(クラフト不可)。"
     "第 3 の「特別口座」を扱える(利息 6%/ゲーム内日・利息が付くのは 500 万エメラルドまで)", "建材"),
    ("sorakaze_sky", "estate_deed",
     "天空王国の物件を買うと受け取る記念の証書(クラフト不可)。所有権はサーバーの台帳が持っているので、失っても物件は失われない", "天空"),
    ("sorakaze_sky", "estate_ledger",
     "天空王国に置かれている物件売買の台帳(クラフト不可)。買いたい区画の上に立って素手で右クリック", "天空"),
    ("sorakaze_sky", "grocery_counter",
     "シンガポール都市国家の店にある食料品の棚(クラフト不可)。エメラルドを持って押すと食料品を買える", "天空"),
]

# V1.7.0: 食料品 300 種。レシピが無い(店で買う)ので、上の SPECIAL_ITEMS と同じ
# 「入手方法」カードとして載せる。**値段と品名は FoodCatalog.java(生成物の唯一の出典)から
# 直接読む**ので、あちらの表に行を足せば早見表も自動で追随する = 二重管理にならない。
FOOD_CATALOG_JAVA = (ROOT / "mods-src/sorakaze-sky/src/main/java/net/sorakaze"
                     "/sorakaze_sky/food/FoodCatalog.java")


def load_food_specials():
    """FoodCatalog.java の ENTRIES を読んで SPECIAL_ITEMS と同じ形のタプル列を返す。"""
    if not FOOD_CATALOG_JAVA.exists():
        raise SystemExit(f"ERROR: {FOOD_CATALOG_JAVA} が見つかりません。"
                         f"食料品のカードが黙って 0 枚になるので中断します。")
    text = FOOD_CATALOG_JAVA.read_text(encoding="utf-8")
    rows = re.findall(
        r'new Entry\(\s*"(\w+)"\s*,\s*"\w+"\s*,\s*Category\.\w+\s*,\s*(\d+)\s*,'
        r'\s*[\d.]+F?\s*,\s*(\d+)\s*,\s*\d+\s*\)', text)
    declared = re.search(r'COUNT\s*=\s*(\d+)', text)
    if declared and len(rows) != int(declared.group(1)):
        # 表と COUNT がずれたら黙って少ない枚数を出さずに落とす(§20.6-5 と同じ趣旨)。
        raise SystemExit(f"ERROR: FoodCatalog の COUNT={declared.group(1)} に対し "
                         f"実際に読めた行は {len(rows)} 件です。正規表現が古い可能性があります。")
    out = []
    for food_id, nutrition, price in rows:
        out.append((
            "sorakaze_sky", food_id,
            f"シンガポール都市国家のお店の棚で購入(1 個 {price} エメラルド・クラフト不可)。"
            f"満腹度 +{nutrition}",
            "天空"))
    return out

VANILLA_CLIENT_JAR = Path.home() / ".gradle/caches/fabric-loom/26.3/minecraft-client.jar"

VANILLA_JA_NAMES = {
    "furnace": "かまど",
    "glass": "ガラス",
    "glass_pane": "板ガラス",
    "glowstone": "グロウストーン",
    "gray_concrete": "灰色のコンクリート",
    "gunpowder": "火薬",
    "iron_block": "鉄ブロック",
    "iron_ingot": "鉄インゴット",
    "iron_nugget": "鉄塊",
    "oak_planks": "オークの板材",
    "paper": "紙",
    "redstone": "レッドストーン",
    "red_dye": "赤色の染料",
    "white_concrete": "白色のコンクリート",
    "yellow_concrete": "黄色のコンクリート",
    "chest": "チェスト",
    "ender_pearl": "エンダーパール",
    "iron_bars": "鉄格子",
    "leather": "革",
    "oak_door": "オークのドア",
    "spruce_planks": "トウヒの板材",
    "stick": "棒",
    "stone": "石",
    "amethyst_shard": "アメジストの欠片",
    "black_dye": "黒色の染料",
    "black_wool": "黒色の羊毛",
    "diamond": "ダイヤモンド",
    "gold_ingot": "金インゴット",
    "ladder": "はしご",
    "quartz_block": "クォーツブロック",
    "redstone_lamp": "レッドストーンランプ",
    "white_dye": "白色の染料",
    "yellow_dye": "黄色の染料",
}
# a handful of vanilla items don't have a simple flat "item/<name>.png" or
# "block/<name>.png" texture (multi-face blocks, pane models that borrow another
# block's texture) - map those to the closest single representative texture.
VANILLA_TEXTURE_OVERRIDE = {
    # Halia V1.3.0 (2026-10-18): vanilla ingredients of the Vigil's recipes with no item/<name>.png.
    "birch_fence_gate": "block/birch_planks",
    "jungle_fence_gate": "block/jungle_planks", "acacia_fence_gate": "block/acacia_planks",
    "smoker": "block/smoker_front",
    "suspicious_sand": "block/suspicious_sand_0", "suspicious_gravel": "block/suspicious_gravel_0",
    "enchanted_golden_apple": "item/golden_apple",
    # V4.0.1: V4 の材料 3 種。いずれも面ごとに別テクスチャのブロックで item/<name>.png を持たない。
    # 音響タレット(スカルクセンサー)、虚空ポーチ(樽)、共鳴レール(石のハーフブロック = block/stone)。
    "sculk_sensor": "block/sculk_sensor_top",
    "barrel": "block/barrel_side",
    "stone_slab": "block/stone",
    # V4.0.1 の手引きの図が使う 3 つ。ロードストーンは面ごと、コンパスは 32 コマのアニメ、
    # 雪ブロックは block/snow を流用して描かれる。
    "lodestone": "block/lodestone_side",
    "compass": "item/compass_16",
    "snow_block": "block/snow",
    # V4.2.2 の工場の手引き: 自動製作機は面ごとのテクスチャで item/crafter.png を持たない。
    "crafter": "block/crafter_top",
    "furnace": "block/furnace_front",
    # Tsubomi 2.0.0 (2026-10-18): the stonecutter is a station now; item/stonecutter.png does not exist.
    "stonecutter": "block/stonecutter_top",
    # Tsubomi 2.0.0 の材料(どれも item/<name>.png を持たない。tall_grass は下の compose_grass_tinted_icon で色を付ける)。
    "white_carpet": "block/white_wool", "blue_carpet": "block/blue_wool", "cactus": "block/cactus_side",
    "mycelium": "block/mycelium_side", "crossbow": "item/crossbow_standby",
    "glass_pane": "block/glass",
    # ASTRAEA V1.5.0 の素材。いずれも item/<name>.png を持たない(面ごとのテクスチャ、または元のブロックの流用)。
    # (smithing_table・heavy_weighted_pressure_plate・stonecutter・spruce_slab・dark_oak_slab・ender_chest も同じ理由で絵が無いが、
    #  すでに絵なしで公開されているので、公開済みテクスチャの番人がここでの追加を拒む。別の作業で扱うこと。)
    "dispenser": "block/dispenser_front",
    "melon": "block/melon_side", "stone_button": "block/stone",
    "cobblestone_slab": "block/cobblestone",
    "acacia_slab": "block/acacia_planks", "birch_slab": "block/birch_planks", "cherry_slab": "block/cherry_planks", "crimson_slab": "block/crimson_planks", "jungle_slab": "block/jungle_planks", "mangrove_slab": "block/mangrove_planks", "pale_oak_slab": "block/pale_oak_planks", "warped_slab": "block/warped_planks",
    "quartz_block": "block/quartz_block_side",
    # V1.4.1: 召喚石の素材。どちらも item/<name>.png を持たない(面ごとに別テクスチャの
    # ブロック)ので、代表的な側面を明示する。指定しないと空欄のカードになる。
    "ancient_debris": "block/ancient_debris_side",
    "sculk_catalyst": "block/sculk_catalyst_top",
    # マグマブロックのテクスチャ名は block/magma(block/magma_block ではない)。
    "magma_block": "block/magma",
    # v1.4.4(ドア 40 種の素材)。どちらも item/<name>.png も block/<name>.png も持たない。
    "bone_block": "block/bone_block_side",
    # ハーフブロックは専用テクスチャを持たず、元の板材テクスチャを流用して描かれる。
    "oak_slab": "block/oak_planks",
    "observer": "block/observer_front",
    # v1.5.0(列車 30 種・車両 100 種・サバイバルの新素材)。いずれも面ごとに別テクスチャの
    # ブロック、または実体モデルで描かれるアイテムで、item/<name>.png を持たない。
    "hay_block": "block/hay_block_side",
    "blast_furnace": "block/blast_furnace_front",
    # v1.7.7(ロケット弾のレシピ材料・強化ガラス系のレシピ材料候補)。TNT も面ごとに
    # 別テクスチャ(tnt_top/tnt_bottom/tnt_side)で、item/tnt.png も block/tnt.png も無い。
    "tnt": "block/tnt_side",
    # レシピブック UI の「すべて」タブのアイコン(作業台)。これも面ごとに別テクスチャ。
    "crafting_table": "block/crafting_table_front",
    # v1.8.0(自動仕分けブロック 9 種+フィルター記憶カードのレシピ材料)。
    # 時計は 64 コマのアニメーション(item/clock_00 〜 clock_63)なので、
    # 静止画の代表として 00 コマを使う。ピストンとドロッパーは面ごとに別テクスチャで、
    # item/<name>.png も block/<name>.png も持たない(furnace / observer と同じ扱い)。
    "clock": "item/clock_00",
    "piston": "block/piston_top",
    "dropper": "block/dropper_front",
    # v1.8.2(太陽光パネルのレシピ材料・「使い方」タブの感知器の図)。日照センサーも
    # 面ごとに別テクスチャ(daylight_detector_top / _side)で、item も block も持たない。
    "daylight_detector": "block/daylight_detector_top",
    # ASTRAEA 1.0.0(油圧式重装ゲートの材料)。ピストンと同じく面ごとに別テクスチャで、
    # 指定しないと空欄のカードになる(粘着面は piston_top_sticky)。
    "sticky_piston": "block/piston_top_sticky",
    # ※ 盾は 1 枚のテクスチャで表せないので compose_shield_icon() で合成する。
}

# MOD ブロックのうち、フラットな単一テクスチャもモデル texture マップ(models/block/<name>.json)も
# 持たないもの(マルチパートブロック等)の代表テクスチャを明示指定する。
MOD_TEXTURE_OVERRIDE = {
    "sorakaze_deco:table": "block/table_top",
    # ---- 自動仕分け 9 種(v1.8.1)------------------------------------------
    # ⚠ **指定しないと、9 枚とも同じ絵になる。**
    # この 9 種は平面の `item/<名前>.png` を持たず、下の解決順は最後に
    # `models/block/<名前>.json` の texture マップへ落ちる。そこで選ばれる鍵は
    # TEXTURE_KEY_PREFERENCE の先頭に近い "top" で、v1.8.0 の天面は 9 種で
    # **共有の 1 枚**だった。結果、v1.8.0 の早見表は 9 枚のカードが
    # **1 つのテクスチャ(t140)を指す**状態になっていた
    # (実際に出荷済みの HTML を読んで確認済み。所有者が仕分け機を覚えようとして
    #  開く当の資料で、9 種が同じ灰色の四角に見えていた)。
    #
    # ゲーム内のホットバーは `items/<名前>.json` の display_context セレクトにより
    # **`item/<名前>_icon`** を出す。早見表もそれに合わせる — 資料と画面で
    # 違う絵が出るほうが混乱するからである。
    # (v1.8.1 で天面も 9 種別々にしたので放っておいても重複はしないが、
    #  「たまたま違う」ではなく「ホットバーと同じ絵」を指す方が正しい。)
    "sorakaze_deco:sorting_filter": "item/sorting_filter_icon",
    "sorakaze_deco:category_sorter": "item/category_sorter_icon",
    "sorakaze_deco:round_robin_splitter": "item/round_robin_splitter_icon",
    "sorakaze_deco:overflow_valve": "item/overflow_valve_icon",
    "sorakaze_deco:void_trash": "item/void_trash_icon",
    "sorakaze_deco:item_pump": "item/item_pump_icon",
    "sorakaze_deco:item_counter": "item/item_counter_icon",
    "sorakaze_deco:stock_indicator": "item/stock_indicator_icon",
    "sorakaze_deco:item_collector": "item/item_collector_icon",
}


# ===========================================================================
# あいうえお順(五十音順)の並べ替え と 検索用の読みがな
# ===========================================================================
# アイテム名は「電車」「特急形電車」「スパークルの仮面」のように漢字・かな混じりである。
# 生の文字列をソートすると **Unicode のコードポイント順** になり、漢字は意味のない順に並ぶ
# (「あいうえお順」には絶対にならない)。五十音順に並べるには **読み(yomi)** が要る。
#
# この環境には日本語辞書が無いので、読みは下の YOMI 表(形態素・複合語の表)から
# **最長一致**で組み立てる。アイテム名はほぼ規則的な複合語(<素材>の<形状>)なので、
# 表に無い語が出たときだけ WARNING を出して検出できる(黙って間違った順に並べない)。
#
# 表に足すときの注意: 長い語を先に当てたいときは、長い語をそのまま登録すればよい
# (照合は常に「その位置で一致する最長のキー」を選ぶ)。
#   例) 「金庫」を入れておかないと「金」+「庫」に割れる。「格子戸」は「格子」に勝つ。
YOMI = {
    # (Halia 1.4.0, 2026-10-22, proposed and NOT reviewed) the one name the 1.4.0 dry run found with no reading.
    "木炭": "もくたん",
    # --- OUKA V1.7 55114 (2026-10-25): バッテリー充電ソケット。読みは一般的な読み(じゅうでん)で、未確認。 ---
    "充電": "じゅうでん",
    "充": "じゅう",
    # --- Tsubomi V2.3.0.1 (2026-10-21) 星桜の道具。読みは tsubomi-src/docs/JA_READINGS_V2.3.0.1.json(未確認)。均は「地均し」で読む。 ---
    "地均し": "じならし",
    "星桜合金インゴット": "ほしざくらごうきんいんごっと", "星桜の削岩鎚": "ほしざくらのさくがんづち", "星桜の大伐斧": "ほしざくらのだいばつおの",
    "星桜の地均しシャベル": "ほしざくらのじならししゃべる", "星桜の豊穣クワ": "ほしざくらのほうじょうくわ", "星桜の光槍": "ほしざくらのこうそう",
    # --- Tsubomi V2.3.0.3 (2026-10-21) 星桜の防具・盾・弓・矢。読みは tsubomi-src/docs/JA_READINGS_V2.3.0.3.json(未確認)。 ---
    "星桜のヘルメット": "ほしざくらのへるめっと", "星桜の胸当て": "ほしざくらのむねあて", "星桜のレギンス": "ほしざくらのれぎんす", "星桜のブーツ": "ほしざくらのぶーつ", "星桜の盾": "ほしざくらのたて", "星桜の弓": "ほしざくらのゆみ", "星桜の矢": "ほしざくらのや",
    # --- Tsubomi V2.3.0.311 (2026-10-22) 星桜 Max(強化版)。読みは tsubomi-src-max/docs/JA_READINGS_V2.3.0.311.json(未確認。盾・弓・矢・合金・道具の 13 件。地均しシャベル・豊穣クワ・光槍は特に不確か)。 ---
    "星桜Max合金インゴット": "ほしざくらまっくすごうきんいんごっと", "星桜Maxの削岩鎚": "ほしざくらまっくすのさくがんづち", "星桜Maxの大伐斧": "ほしざくらまっくすのだいばつおの", "星桜Maxの地均しシャベル": "ほしざくらまっくすのじならししゃべる", "星桜Maxの豊穣クワ": "ほしざくらまっくすのほうじょうくわ", "星桜Maxの光槍": "ほしざくらまっくすのこうそう", "星桜Maxのヘルメット": "ほしざくらまっくすのへるめっと",
    "星桜Maxの胸当て": "ほしざくらまっくすのむねあて", "星桜Maxのレギンス": "ほしざくらまっくすのれぎんす", "星桜Maxのブーツ": "ほしざくらまっくすのぶーつ", "星桜Maxの盾": "ほしざくらまっくすのたて", "星桜Maxの弓": "ほしざくらまっくすのゆみ", "星桜Maxの矢": "ほしざくらまっくすのや",
    # --- Tsubomi V2.3 1024 (2026-10-22) 星桜 Ultra(14 件、ハサミを含む)。読みは未確認。盾・弓・矢・合金・道具(地均しシャベル・豊穣クワ・光槍は特に不確か)。 ---
    "星桜Ultra合金インゴット": "ほしざくらうるとらごうきんいんごっと", "星桜Ultraの削岩鎚": "ほしざくらうるとらのさくがんづち", "星桜Ultraの大伐斧": "ほしざくらうるとらのだいばつおの", "星桜Ultraの地均しシャベル": "ほしざくらうるとらのじならししゃべる", "星桜Ultraの豊穣クワ": "ほしざくらうるとらのほうじょうくわ", "星桜Ultraの光槍": "ほしざくらうるとらのこうそう", "星桜Ultraのヘルメット": "ほしざくらうるとらのへるめっと",
    "星桜Ultraの胸当て": "ほしざくらうるとらのむねあて", "星桜Ultraのレギンス": "ほしざくらうるとらのれぎんす", "星桜Ultraのブーツ": "ほしざくらうるとらのぶーつ", "星桜Ultraの盾": "ほしざくらうるとらのたて", "星桜Ultraの弓": "ほしざくらうるとらのゆみ", "星桜Ultraの矢": "ほしざくらうるとらのや", "星桜Ultraのハサミ": "ほしざくらうるとらのはさみ",
    # --- Tsubomi V2.3 1167 (2026-10-22) 星桜 UltraFast(14 件、釣り竿を含む)と青森の証(1 件)。読みは未確認。地均しシャベル・豊穣クワ・光槍は特に不確か。 ---
    "星桜UltraFast合金インゴット": "ほしざくらうるとらふぁすとごうきんいんごっと", "星桜UltraFastの削岩鎚": "ほしざくらうるとらふぁすとのさくがんづち", "星桜UltraFastの大伐斧": "ほしざくらうるとらふぁすとのだいばつおの", "星桜UltraFastの地均しシャベル": "ほしざくらうるとらふぁすとのじならししゃべる", "星桜UltraFastの豊穣クワ": "ほしざくらうるとらふぁすとのほうじょうくわ", "星桜UltraFastの光槍": "ほしざくらうるとらふぁすとのこうそう", "星桜UltraFastのヘルメット": "ほしざくらうるとらふぁすとのへるめっと",
    "星桜UltraFastの胸当て": "ほしざくらうるとらふぁすとのむねあて", "星桜UltraFastのレギンス": "ほしざくらうるとらふぁすとのれぎんす", "星桜UltraFastのブーツ": "ほしざくらうるとらふぁすとのぶーつ", "星桜UltraFastの盾": "ほしざくらうるとらふぁすとのたて", "星桜UltraFastの弓": "ほしざくらうるとらふぁすとのゆみ", "星桜UltraFastの矢": "ほしざくらうるとらふぁすとのや", "星桜UltraFastの釣り竿": "ほしざくらうるとらふぁすとのつりざお",
    "青森の証": "あおもりのあかし",
    # --- Tsubomi V2.3 2408 (2026-10-22) 星桜 UltraCore(14 件、鎌を含む)と森の証(1 件)。読みは未確認。地均しシャベル・豊穣クワ・光槍・鎌は特に不確か。 ---
    "星桜UltraCore合金インゴット": "ほしざくらうるとらこあごうきんいんごっと", "星桜UltraCoreの削岩鎚": "ほしざくらうるとらこあのさくがんづち", "星桜UltraCoreの大伐斧": "ほしざくらうるとらこあのだいばつおの", "星桜UltraCoreの地均しシャベル": "ほしざくらうるとらこあのじならししゃべる", "星桜UltraCoreの豊穣クワ": "ほしざくらうるとらこあのほうじょうくわ", "星桜UltraCoreの光槍": "ほしざくらうるとらこあのこうそう", "星桜UltraCoreのヘルメット": "ほしざくらうるとらこあのへるめっと",
    "星桜UltraCoreの胸当て": "ほしざくらうるとらこあのむねあて", "星桜UltraCoreのレギンス": "ほしざくらうるとらこあのれぎんす", "星桜UltraCoreのブーツ": "ほしざくらうるとらこあのぶーつ", "星桜UltraCoreの盾": "ほしざくらうるとらこあのたて", "星桜UltraCoreの弓": "ほしざくらうるとらこあのゆみ", "星桜UltraCoreの矢": "ほしざくらうるとらこあのや", "星桜UltraCoreの鎌": "ほしざくらうるとらこあのかま",
    "森の証": "もりのあかし",
    # --- Tsubomi V2.3 2477 (2026-10-23 サイト日付) 星桜 Ultimate(13 件)。読みは tsubomi-src-ult/docs/JA_READINGS_V2.3_2477.json(未確認。地均しシャベル・豊穣クワ・光槍は特に不確か)。 ---
    "星桜Ultimate合金インゴット": "ほしざくらあるてぃめっとごうきんいんごっと", "星桜Ultimateの削岩鎚": "ほしざくらあるてぃめっとのさくがんづち", "星桜Ultimateの大伐斧": "ほしざくらあるてぃめっとのだいばつおの", "星桜Ultimateの地均しシャベル": "ほしざくらあるてぃめっとのじならししゃべる", "星桜Ultimateの豊穣クワ": "ほしざくらあるてぃめっとのほうじょうくわ", "星桜Ultimateの光槍": "ほしざくらあるてぃめっとのこうそう", "星桜Ultimateのヘルメット": "ほしざくらあるてぃめっとのへるめっと",
    "星桜Ultimateの胸当て": "ほしざくらあるてぃめっとのむねあて", "星桜Ultimateのレギンス": "ほしざくらあるてぃめっとのれぎんす", "星桜Ultimateのブーツ": "ほしざくらあるてぃめっとのぶーつ", "星桜Ultimateの盾": "ほしざくらあるてぃめっとのたて", "星桜Ultimateの弓": "ほしざくらあるてぃめっとのゆみ", "星桜Ultimateの矢": "ほしざくらあるてぃめっとのや",
    # --- Tsubomi V2.3 3124 (2026-10-23 サイト日付) 星桜 Corvus(13 件)・Corvus の勲章・ネザースターの束・ネザースターインゴット・エリトラ For Corvus(4 件)。読みは tsubomi-src-corvus/docs/JA_READINGS_V2.3_3124.json(未確認。地均しシャベル・豊穣クワ・光槍・エリトラ For Corvus は特に不確か)。 ---
    "星桜Corvus合金インゴット": "ほしざくらこるうすごうきんいんごっと", "星桜Corvusの削岩鎚": "ほしざくらこるうすのさくがんづち", "星桜Corvusの大伐斧": "ほしざくらこるうすのだいばつおの",
    "星桜Corvusの地均しシャベル": "ほしざくらこるうすのじならししゃべる", "星桜Corvusの豊穣クワ": "ほしざくらこるうすのほうじょうくわ", "星桜Corvusの光槍": "ほしざくらこるうすのこうそう",
    "星桜Corvusのヘルメット": "ほしざくらこるうすのへるめっと", "星桜Corvusの胸当て": "ほしざくらこるうすのむねあて", "星桜Corvusのレギンス": "ほしざくらこるうすのれぎんす",
    "星桜Corvusのブーツ": "ほしざくらこるうすのぶーつ", "星桜Corvusの盾": "ほしざくらこるうすのたて", "星桜Corvusの弓": "ほしざくらこるうすのゆみ",
    "星桜Corvusの矢": "ほしざくらこるうすのや", "Corvusの勲章": "こるうすのくんしょう", "ネザースターの束": "ねざーすたーのたば",
    "ネザースターインゴット": "ねざーすたーいんごっと", "エリトラ For Corvus": "えりとらふぉーこるうす",
    # --- Tsubomi V2.4 0204 (2026-10-25 サイト日付) 星桜 Corvus ミシック(13 件)・ミシック パール(13 件)・Wings・ネザースターブロック。読みは tsubomi-src-v24/docs/JA_READINGS_V2.4_0204.json(未確認。地均しシャベル・豊穣クワ・光槍(両系統)は特に不確か)。 ---
    "星桜Corvusミシック合金インゴット": "ほしざくらこるうすみしっくごうきんいんごっと",
    "星桜Corvusミシックの削岩鎚": "ほしざくらこるうすみしっくのさくがんづち",
    "星桜Corvusミシックの大伐斧": "ほしざくらこるうすみしっくのだいばつおの",
    "星桜Corvusミシックの地均しシャベル": "ほしざくらこるうすみしっくのじならししゃべる",
    "星桜Corvusミシックの豊穣クワ": "ほしざくらこるうすみしっくのほうじょうくわ",
    "星桜Corvusミシックの光槍": "ほしざくらこるうすみしっくのこうそう",
    "星桜Corvusミシックのヘルメット": "ほしざくらこるうすみしっくのへるめっと",
    "星桜Corvusミシックの胸当て": "ほしざくらこるうすみしっくのむねあて",
    "星桜Corvusミシックのレギンス": "ほしざくらこるうすみしっくのれぎんす",
    "星桜Corvusミシックのブーツ": "ほしざくらこるうすみしっくのぶーつ",
    "星桜Corvusミシックの盾": "ほしざくらこるうすみしっくのたて",
    "星桜Corvusミシックの弓": "ほしざくらこるうすみしっくのゆみ",
    "星桜Corvusミシックの矢": "ほしざくらこるうすみしっくのや",
    "星桜Corvusミシックパール合金インゴット": "ほしざくらこるうすみしっくぱーるごうきんいんごっと",
    "星桜Corvusミシックパールの削岩鎚": "ほしざくらこるうすみしっくぱーるのさくがんづち",
    "星桜Corvusミシックパールの大伐斧": "ほしざくらこるうすみしっくぱーるのだいばつおの",
    "星桜Corvusミシックパールの地均しシャベル": "ほしざくらこるうすみしっくぱーるのじならししゃべる",
    "星桜Corvusミシックパールの豊穣クワ": "ほしざくらこるうすみしっくぱーるのほうじょうくわ",
    "星桜Corvusミシックパールの光槍": "ほしざくらこるうすみしっくぱーるのこうそう",
    "星桜Corvusミシックパールのヘルメット": "ほしざくらこるうすみしっくぱーるのへるめっと",
    "星桜Corvusミシックパールの胸当て": "ほしざくらこるうすみしっくぱーるのむねあて",
    "星桜Corvusミシックパールのレギンス": "ほしざくらこるうすみしっくぱーるのれぎんす",
    "星桜Corvusミシックパールのブーツ": "ほしざくらこるうすみしっくぱーるのぶーつ",
    "星桜Corvusミシックパールの盾": "ほしざくらこるうすみしっくぱーるのたて",
    "星桜Corvusミシックパールの弓": "ほしざくらこるうすみしっくぱーるのゆみ",
    "星桜Corvusミシックパールの矢": "ほしざくらこるうすみしっくぱーるのや",
    "Wings": "うぃんぐす",
    "ネザースターブロック": "ねざーすたーぶろっく",
    # --- Tsubomi V2.4 1017 (2026-10-26 サイト日付) 星桜 Phoenix・Phoenix ミシック・Phoenix ゼニス(各 13 件)と各系列の Wings。読みは tsubomi-src-v25/docs/JA_READINGS_V2.4_1017.json(未確認。日本語名そのものはオーナー未承認)。 ---
    "星桜Phoenix合金インゴット": "ほしざくらふぇにっくすごうきんいんごっと",
    "星桜Phoenixの削岩鎚": "ほしざくらふぇにっくすのさくがんづち",
    "星桜Phoenixの大伐斧": "ほしざくらふぇにっくすのだいばつおの",
    "星桜Phoenixの地均しシャベル": "ほしざくらふぇにっくすのじならししゃべる",
    "星桜Phoenixの豊穣クワ": "ほしざくらふぇにっくすのほうじょうくわ",
    "星桜Phoenixの光槍": "ほしざくらふぇにっくすのこうそう",
    "星桜Phoenixのヘルメット": "ほしざくらふぇにっくすのへるめっと",
    "星桜Phoenixの胸当て": "ほしざくらふぇにっくすのむねあて",
    "星桜Phoenixのレギンス": "ほしざくらふぇにっくすのれぎんす",
    "星桜Phoenixのブーツ": "ほしざくらふぇにっくすのぶーつ",
    "星桜Phoenixの盾": "ほしざくらふぇにっくすのたて",
    "星桜Phoenixの弓": "ほしざくらふぇにっくすのゆみ",
    "星桜Phoenixの矢": "ほしざくらふぇにっくすのや",
    "星桜Phoenixミシック合金インゴット": "ほしざくらふぇにっくすみしっくごうきんいんごっと",
    "星桜Phoenixミシックの削岩鎚": "ほしざくらふぇにっくすみしっくのさくがんづち",
    "星桜Phoenixミシックの大伐斧": "ほしざくらふぇにっくすみしっくのだいばつおの",
    "星桜Phoenixミシックの地均しシャベル": "ほしざくらふぇにっくすみしっくのじならししゃべる",
    "星桜Phoenixミシックの豊穣クワ": "ほしざくらふぇにっくすみしっくのほうじょうくわ",
    "星桜Phoenixミシックの光槍": "ほしざくらふぇにっくすみしっくのこうそう",
    "星桜Phoenixミシックのヘルメット": "ほしざくらふぇにっくすみしっくのへるめっと",
    "星桜Phoenixミシックの胸当て": "ほしざくらふぇにっくすみしっくのむねあて",
    "星桜Phoenixミシックのレギンス": "ほしざくらふぇにっくすみしっくのれぎんす",
    "星桜Phoenixミシックのブーツ": "ほしざくらふぇにっくすみしっくのぶーつ",
    "星桜Phoenixミシックの盾": "ほしざくらふぇにっくすみしっくのたて",
    "星桜Phoenixミシックの弓": "ほしざくらふぇにっくすみしっくのゆみ",
    "星桜Phoenixミシックの矢": "ほしざくらふぇにっくすみしっくのや",
    "星桜Phoenixゼニス合金インゴット": "ほしざくらふぇにっくすぜにすごうきんいんごっと",
    "星桜Phoenixゼニスの削岩鎚": "ほしざくらふぇにっくすぜにすのさくがんづち",
    "星桜Phoenixゼニスの大伐斧": "ほしざくらふぇにっくすぜにすのだいばつおの",
    "星桜Phoenixゼニスの地均しシャベル": "ほしざくらふぇにっくすぜにすのじならししゃべる",
    "星桜Phoenixゼニスの豊穣クワ": "ほしざくらふぇにっくすぜにすのほうじょうくわ",
    "星桜Phoenixゼニスの光槍": "ほしざくらふぇにっくすぜにすのこうそう",
    "星桜Phoenixゼニスのヘルメット": "ほしざくらふぇにっくすぜにすのへるめっと",
    "星桜Phoenixゼニスの胸当て": "ほしざくらふぇにっくすぜにすのむねあて",
    "星桜Phoenixゼニスのレギンス": "ほしざくらふぇにっくすぜにすのれぎんす",
    "星桜Phoenixゼニスのブーツ": "ほしざくらふぇにっくすぜにすのぶーつ",
    "星桜Phoenixゼニスの盾": "ほしざくらふぇにっくすぜにすのたて",
    "星桜Phoenixゼニスの弓": "ほしざくらふぇにっくすぜにすのゆみ",
    "星桜Phoenixゼニスの矢": "ほしざくらふぇにっくすぜにすのや",
    "Phoenix Wings": "ふぇにっくすうぃんぐす",
    "Phoenix Mythic Wings": "ふぇにっくすみしっくうぃんぐす",
    "Phoenix Zenith Wings": "ふぇにっくすぜにすうぃんぐす",
    # --- Tsubomi V2.4 1779 (2026-10-29 サイト日付) 星桜 Ziz The Final(13 件)と Ziz Wings。読みは tsubomi-src-v26/docs/JA_READINGS_V2.4_1779.json(未確認。日本語名そのものはオーナー未承認)。 ---
    "星桜Ziz The Final合金インゴット": "ほしざくらずぃーずざふぁいなるごうきんいんごっと",
    "星桜Ziz The Finalの削岩鎚": "ほしざくらずぃーずざふぁいなるのさくがんづち",
    "星桜Ziz The Finalの大伐斧": "ほしざくらずぃーずざふぁいなるのだいばつおの",
    "星桜Ziz The Finalの地均しシャベル": "ほしざくらずぃーずざふぁいなるのじならししゃべる",
    "星桜Ziz The Finalの豊穣クワ": "ほしざくらずぃーずざふぁいなるのほうじょうくわ",
    "星桜Ziz The Finalの光槍": "ほしざくらずぃーずざふぁいなるのこうそう",
    "星桜Ziz The Finalのヘルメット": "ほしざくらずぃーずざふぁいなるのへるめっと",
    "星桜Ziz The Finalの胸当て": "ほしざくらずぃーずざふぁいなるのむねあて",
    "星桜Ziz The Finalのレギンス": "ほしざくらずぃーずざふぁいなるのれぎんす",
    "星桜Ziz The Finalのブーツ": "ほしざくらずぃーずざふぁいなるのぶーつ",
    "星桜Ziz The Finalの盾": "ほしざくらずぃーずざふぁいなるのたて",
    "星桜Ziz The Finalの弓": "ほしざくらずぃーずざふぁいなるのゆみ",
    "星桜Ziz The Finalの矢": "ほしざくらずぃーずざふぁいなるのや",
    "星桜Ziz Wings": "ほしざくらずぃーずうぃんぐす",
    "Ziz Wings": "ずぃーずうぃんぐす",
    # --- Tsubomi V2.3.0.1 の Halia 1.3.0.2 / OUKA 1.7.2 の名前(表に無く WARNING が出たもの)。読みは未確認(この作業の当て字)。 ---
    "看板": "かんばん", "編成票": "へんせいひょう", "運行指令盤": "うんこうしれいばん", "展望車": "てんぼうしゃ",
    "電源車": "でんげんしゃ", "定位置停止コイル": "ていいちていしこいる", "測量器": "そくりょうき",
    # --- Tsubomi V2.2.0 (2026-10-19) 500 ブロック + 海洋の証(501 件)。読みは tsubomi-src/docs/JA_READINGS_V2.2.0.json(未確認)。 ---
    "神代檜（ヒノキ）レンガ": "じんだいひのきれんが", "模様入り神代檜（ヒノキ）": "もよういりじんだいひのき", "神代檜（ヒノキ）の柱": "じんだいひのきのはしら", "神代檜（ヒノキ）タイル": "じんだいひのきたいる", "神代檜（ヒノキ）ランプ": "じんだいひのきらんぷ", "神代檜（ヒノキ）グレーティング": "じんだいひのきぐれーてぃんぐ", "神代檜（ヒノキ）強化装甲板": "じんだいひのききょうかそうこうばん", "神代檜（ヒノキ）の階段": "じんだいひのきのかいだん", "神代檜（ヒノキ）のハーフブロック": "じんだいひのきのはーふぶろっく", "神代檜（ヒノキ）の塀": "じんだいひのきのへい",
    "焼杉（ヤキスギ）レンガ": "やきすぎれんが", "模様入り焼杉（ヤキスギ）": "もよういりやきすぎ", "焼杉（ヤキスギ）の柱": "やきすぎのはしら", "焼杉（ヤキスギ）タイル": "やきすぎたいる", "焼杉（ヤキスギ）ランプ": "やきすぎらんぷ", "焼杉（ヤキスギ）グレーティング": "やきすぎぐれーてぃんぐ", "焼杉（ヤキスギ）強化装甲板": "やきすぎきょうかそうこうばん", "焼杉（ヤキスギ）の階段": "やきすぎのかいだん", "焼杉（ヤキスギ）のハーフブロック": "やきすぎのはーふぶろっく", "焼杉（ヤキスギ）の塀": "やきすぎのへい",
    "白鷺漆喰レンガ": "しらさぎしっくいれんが", "模様入り白鷺漆喰": "もよういりしらさぎしっくい", "白鷺漆喰の柱": "しらさぎしっくいのはしら", "白鷺漆喰タイル": "しらさぎしっくいたいる", "白鷺漆喰ランプ": "しらさぎしっくいらんぷ", "白鷺漆喰グレーティング": "しらさぎしっくいぐれーてぃんぐ", "白鷺漆喰強化装甲板": "しらさぎしっくいきょうかそうこうばん", "白鷺漆喰の階段": "しらさぎしっくいのかいだん", "白鷺漆喰のハーフブロック": "しらさぎしっくいのはーふぶろっく", "白鷺漆喰の塀": "しらさぎしっくいのへい",
    "いぶし瓦石レンガ": "いぶしかわらいしれんが", "模様入りいぶし瓦石": "もよういりいぶしかわらいし", "いぶし瓦石の柱": "いぶしかわらいしのはしら", "いぶし瓦石タイル": "いぶしかわらいしたいる", "いぶし瓦石ランプ": "いぶしかわらいしらんぷ", "いぶし瓦石グレーティング": "いぶしかわらいしぐれーてぃんぐ", "いぶし瓦石強化装甲板": "いぶしかわらいしきょうかそうこうばん", "いぶし瓦石の階段": "いぶしかわらいしのかいだん", "いぶし瓦石のハーフブロック": "いぶしかわらいしのはーふぶろっく", "いぶし瓦石の塀": "いぶしかわらいしのへい",
    "桐箪笥材レンガ": "きりたんすざいれんが", "模様入り桐箪笥材": "もよういりきりたんすざい", "桐箪笥材の柱": "きりたんすざいのはしら", "桐箪笥材タイル": "きりたんすざいたいる", "桐箪笥材ランプ": "きりたんすざいらんぷ", "桐箪笥材グレーティング": "きりたんすざいぐれーてぃんぐ", "桐箪笥材強化装甲板": "きりたんすざいきょうかそうこうばん", "桐箪笥材の階段": "きりたんすざいのかいだん", "桐箪笥材のハーフブロック": "きりたんすざいのはーふぶろっく", "桐箪笥材の塀": "きりたんすざいのへい",
    "墨硯石レンガ": "すみすずりいしれんが", "模様入り墨硯石": "もよういりすみすずりいし", "墨硯石の柱": "すみすずりいしのはしら", "墨硯石タイル": "すみすずりいしたいる", "墨硯石ランプ": "すみすずりいしらんぷ", "墨硯石グレーティング": "すみすずりいしぐれーてぃんぐ", "墨硯石強化装甲板": "すみすずりいしきょうかそうこうばん", "墨硯石の階段": "すみすずりいしのかいだん", "墨硯石のハーフブロック": "すみすずりいしのはーふぶろっく", "墨硯石の塀": "すみすずりいしのへい",
    "本朱漆塗レンガ": "ほんしゅうるしぬりれんが", "模様入り本朱漆塗": "もよういりほんしゅうるしぬり", "本朱漆塗の柱": "ほんしゅうるしぬりのはしら", "本朱漆塗タイル": "ほんしゅうるしぬりたいる", "本朱漆塗ランプ": "ほんしゅうるしぬりらんぷ", "本朱漆塗グレーティング": "ほんしゅうるしぬりぐれーてぃんぐ", "本朱漆塗強化装甲板": "ほんしゅうるしぬりきょうかそうこうばん", "本朱漆塗の階段": "ほんしゅうるしぬりのかいだん", "本朱漆塗のハーフブロック": "ほんしゅうるしぬりのはーふぶろっく", "本朱漆塗の塀": "ほんしゅうるしぬりのへい",
    "黒呂色漆塗レンガ": "くろろいろうるしぬりれんが", "模様入り黒呂色漆塗": "もよういりくろろいろうるしぬり", "黒呂色漆塗の柱": "くろろいろうるしぬりのはしら", "黒呂色漆塗タイル": "くろろいろうるしぬりたいる", "黒呂色漆塗ランプ": "くろろいろうるしぬりらんぷ", "黒呂色漆塗グレーティング": "くろろいろうるしぬりぐれーてぃんぐ", "黒呂色漆塗強化装甲板": "くろろいろうるしぬりきょうかそうこうばん", "黒呂色漆塗の階段": "くろろいろうるしぬりのかいだん", "黒呂色漆塗のハーフブロック": "くろろいろうるしぬりのはーふぶろっく", "黒呂色漆塗の塀": "くろろいろうるしぬりのへい",
    "錆鉄レンガ": "さびてつれんが", "模様入り錆鉄": "もよういりさびてつ", "錆鉄の柱": "さびてつのはしら", "錆鉄タイル": "さびてつたいる", "錆鉄ランプ": "さびてつらんぷ", "錆鉄グレーティング": "さびてつぐれーてぃんぐ", "錆鉄強化装甲板": "さびてつきょうかそうこうばん", "錆鉄の階段": "さびてつのかいだん", "錆鉄のハーフブロック": "さびてつのはーふぶろっく", "錆鉄の塀": "さびてつのへい",
    "塗り壁土レンガ": "ぬりかべつちれんが", "模様入り塗り壁土": "もよういりぬりかべつち", "塗り壁土の柱": "ぬりかべつちのはしら", "塗り壁土タイル": "ぬりかべつちたいる", "塗り壁土ランプ": "ぬりかべつちらんぷ", "塗り壁土グレーティング": "ぬりかべつちぐれーてぃんぐ", "塗り壁土強化装甲板": "ぬりかべつちきょうかそうこうばん", "塗り壁土の階段": "ぬりかべつちのかいだん", "塗り壁土のハーフブロック": "ぬりかべつちのはーふぶろっく", "塗り壁土の塀": "ぬりかべつちのへい",
    "緋色金（ヒイロガネ）レンガ": "ひいろがねれんが", "模様入り緋色金（ヒイロガネ）": "もよういりひいろがね", "緋色金（ヒイロガネ）の柱": "ひいろがねのはしら", "緋色金（ヒイロガネ）タイル": "ひいろがねたいる", "緋色金（ヒイロガネ）ランプ": "ひいろがねらんぷ", "緋色金（ヒイロガネ）グレーティング": "ひいろがねぐれーてぃんぐ", "緋色金（ヒイロガネ）強化装甲板": "ひいろがねきょうかそうこうばん", "緋色金（ヒイロガネ）の階段": "ひいろがねのかいだん", "緋色金（ヒイロガネ）のハーフブロック": "ひいろがねのはーふぶろっく", "緋色金（ヒイロガネ）の塀": "ひいろがねのへい",
    "赤銅（シャクドウ）レンガ": "しゃくどうれんが", "模様入り赤銅（シャクドウ）": "もよういりしゃくどう", "赤銅（シャクドウ）の柱": "しゃくどうのはしら", "赤銅（シャクドウ）タイル": "しゃくどうたいる", "赤銅（シャクドウ）ランプ": "しゃくどうらんぷ", "赤銅（シャクドウ）グレーティング": "しゃくどうぐれーてぃんぐ", "赤銅（シャクドウ）強化装甲板": "しゃくどうきょうかそうこうばん", "赤銅（シャクドウ）の階段": "しゃくどうのかいだん", "赤銅（シャクドウ）のハーフブロック": "しゃくどうのはーふぶろっく", "赤銅（シャクドウ）の塀": "しゃくどうのへい",
    "四分一銀合金レンガ": "しぶいちぎんごうきんれんが", "模様入り四分一銀合金": "もよういりしぶいちぎんごうきん", "四分一銀合金の柱": "しぶいちぎんごうきんのはしら", "四分一銀合金タイル": "しぶいちぎんごうきんたいる", "四分一銀合金ランプ": "しぶいちぎんごうきんらんぷ", "四分一銀合金グレーティング": "しぶいちぎんごうきんぐれーてぃんぐ", "四分一銀合金強化装甲板": "しぶいちぎんごうきんきょうかそうこうばん", "四分一銀合金の階段": "しぶいちぎんごうきんのかいだん", "四分一銀合金のハーフブロック": "しぶいちぎんごうきんのはーふぶろっく", "四分一銀合金の塀": "しぶいちぎんごうきんのへい",
    "積層ダマスカス鋼レンガ": "せきそうだますかすこうれんが", "模様入り積層ダマスカス鋼": "もよういりせきそうだますかすこう", "積層ダマスカス鋼の柱": "せきそうだますかすこうのはしら", "積層ダマスカス鋼タイル": "せきそうだますかすこうたいる", "積層ダマスカス鋼ランプ": "せきそうだますかすこうらんぷ", "積層ダマスカス鋼グレーティング": "せきそうだますかすこうぐれーてぃんぐ", "積層ダマスカス鋼強化装甲板": "せきそうだますかすこうきょうかそうこうばん", "積層ダマスカス鋼の階段": "せきそうだますかすこうのかいだん", "積層ダマスカス鋼のハーフブロック": "せきそうだますかすこうのはーふぶろっく", "積層ダマスカス鋼の塀": "せきそうだますかすこうのへい",
    "重装タングステンレンガ": "じゅうそうたんぐすてんれんが", "模様入り重装タングステン": "もよういりじゅうそうたんぐすてん", "重装タングステンの柱": "じゅうそうたんぐすてんのはしら", "重装タングステンタイル": "じゅうそうたんぐすてんたいる", "重装タングステンランプ": "じゅうそうたんぐすてんらんぷ", "重装タングステングレーティング": "じゅうそうたんぐすてんぐれーてぃんぐ", "重装タングステン強化装甲板": "じゅうそうたんぐすてんきょうかそうこうばん", "重装タングステンの階段": "じゅうそうたんぐすてんのかいだん", "重装タングステンのハーフブロック": "じゅうそうたんぐすてんのはーふぶろっく", "重装タングステンの塀": "じゅうそうたんぐすてんのへい",
    "高密度エーテリウム装甲レンガ": "こうみつどえーてりうむそうこうれんが", "模様入り高密度エーテリウム装甲": "もよういりこうみつどえーてりうむそうこう", "高密度エーテリウム装甲の柱": "こうみつどえーてりうむそうこうのはしら", "高密度エーテリウム装甲タイル": "こうみつどえーてりうむそうこうたいる", "高密度エーテリウム装甲ランプ": "こうみつどえーてりうむそうこうらんぷ", "高密度エーテリウム装甲グレーティング": "こうみつどえーてりうむそうこうぐれーてぃんぐ", "高密度エーテリウム装甲強化装甲板": "こうみつどえーてりうむそうこうきょうかそうこうばん", "高密度エーテリウム装甲の階段": "こうみつどえーてりうむそうこうのかいだん", "高密度エーテリウム装甲のハーフブロック": "こうみつどえーてりうむそうこうのはーふぶろっく", "高密度エーテリウム装甲の塀": "こうみつどえーてりうむそうこうのへい",
    "コバルトクロム合金レンガ": "こばるとくろむごうきんれんが", "模様入りコバルトクロム合金": "もよういりこばるとくろむごうきん", "コバルトクロム合金の柱": "こばるとくろむごうきんのはしら", "コバルトクロム合金タイル": "こばるとくろむごうきんたいる", "コバルトクロム合金ランプ": "こばるとくろむごうきんらんぷ", "コバルトクロム合金グレーティング": "こばるとくろむごうきんぐれーてぃんぐ", "コバルトクロム合金強化装甲板": "こばるとくろむごうきんきょうかそうこうばん", "コバルトクロム合金の階段": "こばるとくろむごうきんのかいだん", "コバルトクロム合金のハーフブロック": "こばるとくろむごうきんのはーふぶろっく", "コバルトクロム合金の塀": "こばるとくろむごうきんのへい",
    "琥珀金レンガ": "こはくきんれんが", "模様入り琥珀金": "もよういりこはくきん", "琥珀金の柱": "こはくきんのはしら", "琥珀金タイル": "こはくきんたいる", "琥珀金ランプ": "こはくきんらんぷ", "琥珀金グレーティング": "こはくきんぐれーてぃんぐ", "琥珀金強化装甲板": "こはくきんきょうかそうこうばん", "琥珀金の階段": "こはくきんのかいだん", "琥珀金のハーフブロック": "こはくきんのはーふぶろっく", "琥珀金の塀": "こはくきんのへい",
    "浪人ガンメタルレンガ": "ろうにんがんめたるれんが", "模様入り浪人ガンメタル": "もよういりろうにんがんめたる", "浪人ガンメタルの柱": "ろうにんがんめたるのはしら", "浪人ガンメタルタイル": "ろうにんがんめたるたいる", "浪人ガンメタルランプ": "ろうにんがんめたるらんぷ", "浪人ガンメタルグレーティング": "ろうにんがんめたるぐれーてぃんぐ", "浪人ガンメタル強化装甲板": "ろうにんがんめたるきょうかそうこうばん", "浪人ガンメタルの階段": "ろうにんがんめたるのかいだん", "浪人ガンメタルのハーフブロック": "ろうにんがんめたるのはーふぶろっく", "浪人ガンメタルの塀": "ろうにんがんめたるのへい",
    "バナジウム鋼レンガ": "ばなじうむこうれんが", "模様入りバナジウム鋼": "もよういりばなじうむこう", "バナジウム鋼の柱": "ばなじうむこうのはしら", "バナジウム鋼タイル": "ばなじうむこうたいる", "バナジウム鋼ランプ": "ばなじうむこうらんぷ", "バナジウム鋼グレーティング": "ばなじうむこうぐれーてぃんぐ", "バナジウム鋼強化装甲板": "ばなじうむこうきょうかそうこうばん", "バナジウム鋼の階段": "ばなじうむこうのかいだん", "バナジウム鋼のハーフブロック": "ばなじうむこうのはーふぶろっく", "バナジウム鋼の塀": "ばなじうむこうのへい",
    "コルヴス黒曜装甲レンガ": "こるゔすこくようそうこうれんが", "模様入りコルヴス黒曜装甲": "もよういりこるゔすこくようそうこう", "コルヴス黒曜装甲の柱": "こるゔすこくようそうこうのはしら", "コルヴス黒曜装甲タイル": "こるゔすこくようそうこうたいる", "コルヴス黒曜装甲ランプ": "こるゔすこくようそうこうらんぷ", "コルヴス黒曜装甲グレーティング": "こるゔすこくようそうこうぐれーてぃんぐ", "コルヴス黒曜装甲強化装甲板": "こるゔすこくようそうこうきょうかそうこうばん", "コルヴス黒曜装甲の階段": "こるゔすこくようそうこうのかいだん", "コルヴス黒曜装甲のハーフブロック": "こるゔすこくようそうこうのはーふぶろっく", "コルヴス黒曜装甲の塀": "こるゔすこくようそうこうのへい",
    "ニューラル回路基板レンガ": "にゅーらるかいろきばんれんが", "模様入りニューラル回路基板": "もよういりにゅーらるかいろきばん", "ニューラル回路基板の柱": "にゅーらるかいろきばんのはしら", "ニューラル回路基板タイル": "にゅーらるかいろきばんたいる", "ニューラル回路基板ランプ": "にゅーらるかいろきばんらんぷ", "ニューラル回路基板グレーティング": "にゅーらるかいろきばんぐれーてぃんぐ", "ニューラル回路基板強化装甲板": "にゅーらるかいろきばんきょうかそうこうばん", "ニューラル回路基板の階段": "にゅーらるかいろきばんのかいだん", "ニューラル回路基板のハーフブロック": "にゅーらるかいろきばんのはーふぶろっく", "ニューラル回路基板の塀": "にゅーらるかいろきばんのへい",
    "量子ポリマー白壁レンガ": "りょうしぽりまーしろかべれんが", "模様入り量子ポリマー白壁": "もよういりりょうしぽりまーしろかべ", "量子ポリマー白壁の柱": "りょうしぽりまーしろかべのはしら", "量子ポリマー白壁タイル": "りょうしぽりまーしろかべたいる", "量子ポリマー白壁ランプ": "りょうしぽりまーしろかべらんぷ", "量子ポリマー白壁グレーティング": "りょうしぽりまーしろかべぐれーてぃんぐ", "量子ポリマー白壁強化装甲板": "りょうしぽりまーしろかべきょうかそうこうばん", "量子ポリマー白壁の階段": "りょうしぽりまーしろかべのかいだん", "量子ポリマー白壁のハーフブロック": "りょうしぽりまーしろかべのはーふぶろっく", "量子ポリマー白壁の塀": "りょうしぽりまーしろかべのへい",
    "六角グラフェン装甲レンガ": "ろっかくぐらふぇんそうこうれんが", "模様入り六角グラフェン装甲": "もよういりろっかくぐらふぇんそうこう", "六角グラフェン装甲の柱": "ろっかくぐらふぇんそうこうのはしら", "六角グラフェン装甲タイル": "ろっかくぐらふぇんそうこうたいる", "六角グラフェン装甲ランプ": "ろっかくぐらふぇんそうこうらんぷ", "六角グラフェン装甲グレーティング": "ろっかくぐらふぇんそうこうぐれーてぃんぐ", "六角グラフェン装甲強化装甲板": "ろっかくぐらふぇんそうこうきょうかそうこうばん", "六角グラフェン装甲の階段": "ろっかくぐらふぇんそうこうのかいだん", "六角グラフェン装甲のハーフブロック": "ろっかくぐらふぇんそうこうのはーふぶろっく", "六角グラフェン装甲の塀": "ろっかくぐらふぇんそうこうのへい",
    "イオンプラズマ導管レンガ": "いおんぷらずまどうかんれんが", "模様入りイオンプラズマ導管": "もよういりいおんぷらずまどうかん", "イオンプラズマ導管の柱": "いおんぷらずまどうかんのはしら", "イオンプラズマ導管タイル": "いおんぷらずまどうかんたいる", "イオンプラズマ導管ランプ": "いおんぷらずまどうかんらんぷ", "イオンプラズマ導管グレーティング": "いおんぷらずまどうかんぐれーてぃんぐ", "イオンプラズマ導管強化装甲板": "いおんぷらずまどうかんきょうかそうこうばん", "イオンプラズマ導管の階段": "いおんぷらずまどうかんのかいだん", "イオンプラズマ導管のハーフブロック": "いおんぷらずまどうかんのはーふぶろっく", "イオンプラズマ導管の塀": "いおんぷらずまどうかんのへい",
    "ホログラム結晶壁レンガ": "ほろぐらむけっしょうへきれんが", "模様入りホログラム結晶壁": "もよういりほろぐらむけっしょうへき", "ホログラム結晶壁の柱": "ほろぐらむけっしょうへきのはしら", "ホログラム結晶壁タイル": "ほろぐらむけっしょうへきたいる", "ホログラム結晶壁ランプ": "ほろぐらむけっしょうへきらんぷ", "ホログラム結晶壁グレーティング": "ほろぐらむけっしょうへきぐれーてぃんぐ", "ホログラム結晶壁強化装甲板": "ほろぐらむけっしょうへききょうかそうこうばん", "ホログラム結晶壁の階段": "ほろぐらむけっしょうへきのかいだん", "ホログラム結晶壁のハーフブロック": "ほろぐらむけっしょうへきのはーふぶろっく", "ホログラム結晶壁の塀": "ほろぐらむけっしょうへきのへい",
    "冷却リアクター外装レンガ": "れいきゃくりあくたーがいそうれんが", "模様入り冷却リアクター外装": "もよういりれいきゃくりあくたーがいそう", "冷却リアクター外装の柱": "れいきゃくりあくたーがいそうのはしら", "冷却リアクター外装タイル": "れいきゃくりあくたーがいそうたいる", "冷却リアクター外装ランプ": "れいきゃくりあくたーがいそうらんぷ", "冷却リアクター外装グレーティング": "れいきゃくりあくたーがいそうぐれーてぃんぐ", "冷却リアクター外装強化装甲板": "れいきゃくりあくたーがいそうきょうかそうこうばん", "冷却リアクター外装の階段": "れいきゃくりあくたーがいそうのかいだん", "冷却リアクター外装のハーフブロック": "れいきゃくりあくたーがいそうのはーふぶろっく", "冷却リアクター外装の塀": "れいきゃくりあくたーがいそうのへい",
    "吸音ステルス複合材レンガ": "きゅうおんすてるすふくごうざいれんが", "模様入り吸音ステルス複合材": "もよういりきゅうおんすてるすふくごうざい", "吸音ステルス複合材の柱": "きゅうおんすてるすふくごうざいのはしら", "吸音ステルス複合材タイル": "きゅうおんすてるすふくごうざいたいる", "吸音ステルス複合材ランプ": "きゅうおんすてるすふくごうざいらんぷ", "吸音ステルス複合材グレーティング": "きゅうおんすてるすふくごうざいぐれーてぃんぐ", "吸音ステルス複合材強化装甲板": "きゅうおんすてるすふくごうざいきょうかそうこうばん", "吸音ステルス複合材の階段": "きゅうおんすてるすふくごうざいのかいだん", "吸音ステルス複合材のハーフブロック": "きゅうおんすてるすふくごうざいのはーふぶろっく", "吸音ステルス複合材の塀": "きゅうおんすてるすふくごうざいのへい",
    "軌道耐熱セラミックレンガ": "きどうたいねつせらみっくれんが", "模様入り軌道耐熱セラミック": "もよういりきどうたいねつせらみっく", "軌道耐熱セラミックの柱": "きどうたいねつせらみっくのはしら", "軌道耐熱セラミックタイル": "きどうたいねつせらみっくたいる", "軌道耐熱セラミックランプ": "きどうたいねつせらみっくらんぷ", "軌道耐熱セラミックグレーティング": "きどうたいねつせらみっくぐれーてぃんぐ", "軌道耐熱セラミック強化装甲板": "きどうたいねつせらみっくきょうかそうこうばん", "軌道耐熱セラミックの階段": "きどうたいねつせらみっくのかいだん", "軌道耐熱セラミックのハーフブロック": "きどうたいねつせらみっくのはーふぶろっく", "軌道耐熱セラミックの塀": "きどうたいねつせらみっくのへい",
    "硫黄結晶レンガ": "いおうけっしょうれんが", "模様入り硫黄結晶": "もよういりいおうけっしょう", "硫黄結晶の柱": "いおうけっしょうのはしら", "硫黄結晶タイル": "いおうけっしょうたいる", "硫黄結晶ランプ": "いおうけっしょうらんぷ", "硫黄結晶グレーティング": "いおうけっしょうぐれーてぃんぐ", "硫黄結晶強化装甲板": "いおうけっしょうきょうかそうこうばん", "硫黄結晶の階段": "いおうけっしょうのかいだん", "硫黄結晶のハーフブロック": "いおうけっしょうのはーふぶろっく", "硫黄結晶の塀": "いおうけっしょうのへい",
    "血月瑪瑙（メノウ）レンガ": "けつげつめのうれんが", "模様入り血月瑪瑙（メノウ）": "もよういりけつげつめのう", "血月瑪瑙（メノウ）の柱": "けつげつめのうのはしら", "血月瑪瑙（メノウ）タイル": "けつげつめのうたいる", "血月瑪瑙（メノウ）ランプ": "けつげつめのうらんぷ", "血月瑪瑙（メノウ）グレーティング": "けつげつめのうぐれーてぃんぐ", "血月瑪瑙（メノウ）強化装甲板": "けつげつめのうきょうかそうこうばん", "血月瑪瑙（メノウ）の階段": "けつげつめのうのかいだん", "血月瑪瑙（メノウ）のハーフブロック": "けつげつめのうのはーふぶろっく", "血月瑪瑙（メノウ）の塀": "けつげつめのうのへい",
    "月光透石膏レンガ": "げっこうとうせっこうれんが", "模様入り月光透石膏": "もよういりげっこうとうせっこう", "月光透石膏の柱": "げっこうとうせっこうのはしら", "月光透石膏タイル": "げっこうとうせっこうたいる", "月光透石膏ランプ": "げっこうとうせっこうらんぷ", "月光透石膏グレーティング": "げっこうとうせっこうぐれーてぃんぐ", "月光透石膏強化装甲板": "げっこうとうせっこうきょうかそうこうばん", "月光透石膏の階段": "げっこうとうせっこうのかいだん", "月光透石膏のハーフブロック": "げっこうとうせっこうのはーふぶろっく", "月光透石膏の塀": "げっこうとうせっこうのへい",
    "夕暮れタンザナイトレンガ": "ゆうぐれたんざないとれんが", "模様入り夕暮れタンザナイト": "もよういりゆうぐれたんざないと", "夕暮れタンザナイトの柱": "ゆうぐれたんざないとのはしら", "夕暮れタンザナイトタイル": "ゆうぐれたんざないとたいる", "夕暮れタンザナイトランプ": "ゆうぐれたんざないとらんぷ", "夕暮れタンザナイトグレーティング": "ゆうぐれたんざないとぐれーてぃんぐ", "夕暮れタンザナイト強化装甲板": "ゆうぐれたんざないときょうかそうこうばん", "夕暮れタンザナイトの階段": "ゆうぐれたんざないとのかいだん", "夕暮れタンザナイトのハーフブロック": "ゆうぐれたんざないとのはーふぶろっく", "夕暮れタンザナイトの塀": "ゆうぐれたんざないとのへい",
    "特異点触媒": "とくいてんしょくばい",
    "虚空特異点石レンガ": "こくうとくいてんせきれんが", "模様入り虚空特異点石": "もよういりこくうとくいてんせき", "虚空特異点石の柱": "こくうとくいてんせきのはしら", "虚空特異点石タイル": "こくうとくいてんせきたいる", "虚空特異点石ランプ": "こくうとくいてんせきらんぷ", "虚空特異点石グレーティング": "こくうとくいてんせきぐれーてぃんぐ", "虚空特異点石強化装甲板": "こくうとくいてんせききょうかそうこうばん", "虚空特異点石の階段": "こくうとくいてんせきのかいだん", "虚空特異点石のハーフブロック": "こくうとくいてんせきのはーふぶろっく", "虚空特異点石の塀": "こくうとくいてんせきのへい",
    "星雲オパールレンガ": "せいうんおぱーるれんが", "模様入り星雲オパール": "もよういりせいうんおぱーる", "星雲オパールの柱": "せいうんおぱーるのはしら", "星雲オパールタイル": "せいうんおぱーるたいる", "星雲オパールランプ": "せいうんおぱーるらんぷ", "星雲オパールグレーティング": "せいうんおぱーるぐれーてぃんぐ", "星雲オパール強化装甲板": "せいうんおぱーるきょうかそうこうばん", "星雲オパールの階段": "せいうんおぱーるのかいだん", "星雲オパールのハーフブロック": "せいうんおぱーるのはーふぶろっく", "星雲オパールの塀": "せいうんおぱーるのへい",
    "赫陽シトリンレンガ": "かくようしとりんれんが", "模様入り赫陽シトリン": "もよういりかくようしとりん", "赫陽シトリンの柱": "かくようしとりんのはしら", "赫陽シトリンタイル": "かくようしとりんたいる", "赫陽シトリンランプ": "かくようしとりんらんぷ", "赫陽シトリングレーティング": "かくようしとりんぐれーてぃんぐ", "赫陽シトリン強化装甲板": "かくようしとりんきょうかそうこうばん", "赫陽シトリンの階段": "かくようしとりんのかいだん", "赫陽シトリンのハーフブロック": "かくようしとりんのはーふぶろっく", "赫陽シトリンの塀": "かくようしとりんのへい",
    "雷撃閃電岩レンガ": "らいげきせんでんがんれんが", "模様入り雷撃閃電岩": "もよういりらいげきせんでんがん", "雷撃閃電岩の柱": "らいげきせんでんがんのはしら", "雷撃閃電岩タイル": "らいげきせんでんがんたいる", "雷撃閃電岩ランプ": "らいげきせんでんがんらんぷ", "雷撃閃電岩グレーティング": "らいげきせんでんがんぐれーてぃんぐ", "雷撃閃電岩強化装甲板": "らいげきせんでんがんきょうかそうこうばん", "雷撃閃電岩の階段": "らいげきせんでんがんのかいだん", "雷撃閃電岩のハーフブロック": "らいげきせんでんがんのはーふぶろっく", "雷撃閃電岩の塀": "らいげきせんでんがんのへい",
    "霞天青石レンガ": "かすみてんせいせきれんが", "模様入り霞天青石": "もよういりかすみてんせいせき", "霞天青石の柱": "かすみてんせいせきのはしら", "霞天青石タイル": "かすみてんせいせきたいる", "霞天青石ランプ": "かすみてんせいせきらんぷ", "霞天青石グレーティング": "かすみてんせいせきぐれーてぃんぐ", "霞天青石強化装甲板": "かすみてんせいせききょうかそうこうばん", "霞天青石の階段": "かすみてんせいせきのかいだん", "霞天青石のハーフブロック": "かすみてんせいせきのはーふぶろっく", "霞天青石の塀": "かすみてんせいせきのへい",
    "橄欖石レンガ": "かんらんせきれんが", "模様入り橄欖石": "もよういりかんらんせき", "橄欖石の柱": "かんらんせきのはしら", "橄欖石タイル": "かんらんせきたいる", "橄欖石ランプ": "かんらんせきらんぷ", "橄欖石グレーティング": "かんらんせきぐれーてぃんぐ", "橄欖石強化装甲板": "かんらんせききょうかそうこうばん", "橄欖石の階段": "かんらんせきのかいだん", "橄欖石のハーフブロック": "かんらんせきのはーふぶろっく", "橄欖石の塀": "かんらんせきのへい",
    "魂炎ガーネットレンガ": "こんえんがーねっとれんが", "模様入り魂炎ガーネット": "もよういりこんえんがーねっと", "魂炎ガーネットの柱": "こんえんがーねっとのはしら", "魂炎ガーネットタイル": "こんえんがーねっとたいる", "魂炎ガーネットランプ": "こんえんがーねっとらんぷ", "魂炎ガーネットグレーティング": "こんえんがーねっとぐれーてぃんぐ", "魂炎ガーネット強化装甲板": "こんえんがーねっときょうかそうこうばん", "魂炎ガーネットの階段": "こんえんがーねっとのかいだん", "魂炎ガーネットのハーフブロック": "こんえんがーねっとのはーふぶろっく", "魂炎ガーネットの塀": "こんえんがーねっとのへい",
    "吉野桜花大理石レンガ": "よしのおうかだいりせきれんが", "模様入り吉野桜花大理石": "もよういりよしのおうかだいりせき", "吉野桜花大理石の柱": "よしのおうかだいりせきのはしら", "吉野桜花大理石タイル": "よしのおうかだいりせきたいる", "吉野桜花大理石ランプ": "よしのおうかだいりせきらんぷ", "吉野桜花大理石グレーティング": "よしのおうかだいりせきぐれーてぃんぐ", "吉野桜花大理石強化装甲板": "よしのおうかだいりせききょうかそうこうばん", "吉野桜花大理石の階段": "よしのおうかだいりせきのかいだん", "吉野桜花大理石のハーフブロック": "よしのおうかだいりせきのはーふぶろっく", "吉野桜花大理石の塀": "よしのおうかだいりせきのへい",
    "紅葉碧玉レンガ": "もみじへきぎょくれんが", "模様入り紅葉碧玉": "もよういりもみじへきぎょく", "紅葉碧玉の柱": "もみじへきぎょくのはしら", "紅葉碧玉タイル": "もみじへきぎょくたいる", "紅葉碧玉ランプ": "もみじへきぎょくらんぷ", "紅葉碧玉グレーティング": "もみじへきぎょくぐれーてぃんぐ", "紅葉碧玉強化装甲板": "もみじへきぎょくきょうかそうこうばん", "紅葉碧玉の階段": "もみじへきぎょくのかいだん", "紅葉碧玉のハーフブロック": "もみじへきぎょくのはーふぶろっく", "紅葉碧玉の塀": "もみじへきぎょくのへい",
    "富士白雪御影石レンガ": "ふじしらゆきみかげいしれんが", "模様入り富士白雪御影石": "もよういりふじしらゆきみかげいし", "富士白雪御影石の柱": "ふじしらゆきみかげいしのはしら", "富士白雪御影石タイル": "ふじしらゆきみかげいしたいる", "富士白雪御影石ランプ": "ふじしらゆきみかげいしらんぷ", "富士白雪御影石グレーティング": "ふじしらゆきみかげいしぐれーてぃんぐ", "富士白雪御影石強化装甲板": "ふじしらゆきみかげいしきょうかそうこうばん", "富士白雪御影石の階段": "ふじしらゆきみかげいしのかいだん", "富士白雪御影石のハーフブロック": "ふじしらゆきみかげいしのはーふぶろっく", "富士白雪御影石の塀": "ふじしらゆきみかげいしのへい",
    "浅間溶岩スコリアレンガ": "あさまようがんすこりあれんが", "模様入り浅間溶岩スコリア": "もよういりあさまようがんすこりあ", "浅間溶岩スコリアの柱": "あさまようがんすこりあのはしら", "浅間溶岩スコリアタイル": "あさまようがんすこりあたいる", "浅間溶岩スコリアランプ": "あさまようがんすこりあらんぷ", "浅間溶岩スコリアグレーティング": "あさまようがんすこりあぐれーてぃんぐ", "浅間溶岩スコリア強化装甲板": "あさまようがんすこりあきょうかそうこうばん", "浅間溶岩スコリアの階段": "あさまようがんすこりあのかいだん", "浅間溶岩スコリアのハーフブロック": "あさまようがんすこりあのはーふぶろっく", "浅間溶岩スコリアの塀": "あさまようがんすこりあのへい",
    "緑電気石レンガ": "りょくでんきせきれんが", "模様入り緑電気石": "もよういりりょくでんきせき", "緑電気石の柱": "りょくでんきせきのはしら", "緑電気石タイル": "りょくでんきせきたいる", "緑電気石ランプ": "りょくでんきせきらんぷ", "緑電気石グレーティング": "りょくでんきせきぐれーてぃんぐ", "緑電気石強化装甲板": "りょくでんきせききょうかそうこうばん", "緑電気石の階段": "りょくでんきせきのかいだん", "緑電気石のハーフブロック": "りょくでんきせきのはーふぶろっく", "緑電気石の塀": "りょくでんきせきのへい",
    "黒曜縞瑪瑙レンガ": "こくようしまめのうれんが", "模様入り黒曜縞瑪瑙": "もよういりこくようしまめのう", "黒曜縞瑪瑙の柱": "こくようしまめのうのはしら", "黒曜縞瑪瑙タイル": "こくようしまめのうたいる", "黒曜縞瑪瑙ランプ": "こくようしまめのうらんぷ", "黒曜縞瑪瑙グレーティング": "こくようしまめのうぐれーてぃんぐ", "黒曜縞瑪瑙強化装甲板": "こくようしまめのうきょうかそうこうばん", "黒曜縞瑪瑙の階段": "こくようしまめのうのかいだん", "黒曜縞瑪瑙のハーフブロック": "こくようしまめのうのはーふぶろっく", "黒曜縞瑪瑙の塀": "こくようしまめのうのへい",
    "琉球珊瑚石灰岩レンガ": "りゅうきゅうさんごせっかいがんれんが", "模様入り琉球珊瑚石灰岩": "もよういりりゅうきゅうさんごせっかいがん", "琉球珊瑚石灰岩の柱": "りゅうきゅうさんごせっかいがんのはしら", "琉球珊瑚石灰岩タイル": "りゅうきゅうさんごせっかいがんたいる", "琉球珊瑚石灰岩ランプ": "りゅうきゅうさんごせっかいがんらんぷ", "琉球珊瑚石灰岩グレーティング": "りゅうきゅうさんごせっかいがんぐれーてぃんぐ", "琉球珊瑚石灰岩強化装甲板": "りゅうきゅうさんごせっかいがんきょうかそうこうばん", "琉球珊瑚石灰岩の階段": "りゅうきゅうさんごせっかいがんのかいだん", "琉球珊瑚石灰岩のハーフブロック": "りゅうきゅうさんごせっかいがんのはーふぶろっく", "琉球珊瑚石灰岩の塀": "りゅうきゅうさんごせっかいがんのへい",
    "万年氷河岩レンガ": "まんねんひょうががんれんが", "模様入り万年氷河岩": "もよういりまんねんひょうががん", "万年氷河岩の柱": "まんねんひょうががんのはしら", "万年氷河岩タイル": "まんねんひょうががんたいる", "万年氷河岩ランプ": "まんねんひょうががんらんぷ", "万年氷河岩グレーティング": "まんねんひょうががんぐれーてぃんぐ", "万年氷河岩強化装甲板": "まんねんひょうががんきょうかそうこうばん", "万年氷河岩の階段": "まんねんひょうががんのかいだん", "万年氷河岩のハーフブロック": "まんねんひょうががんのはーふぶろっく", "万年氷河岩の塀": "まんねんひょうががんのへい",
    "湯の花黄金石灰華レンガ": "ゆのはなおうごんせっかいかれんが", "模様入り湯の花黄金石灰華": "もよういりゆのはなおうごんせっかいか", "湯の花黄金石灰華の柱": "ゆのはなおうごんせっかいかのはしら", "湯の花黄金石灰華タイル": "ゆのはなおうごんせっかいかたいる", "湯の花黄金石灰華ランプ": "ゆのはなおうごんせっかいからんぷ", "湯の花黄金石灰華グレーティング": "ゆのはなおうごんせっかいかぐれーてぃんぐ", "湯の花黄金石灰華強化装甲板": "ゆのはなおうごんせっかいかきょうかそうこうばん", "湯の花黄金石灰華の階段": "ゆのはなおうごんせっかいかのかいだん", "湯の花黄金石灰華のハーフブロック": "ゆのはなおうごんせっかいかのはーふぶろっく", "湯の花黄金石灰華の塀": "ゆのはなおうごんせっかいかのへい",
    "永劫盤装甲レンガ": "えいごうばんそうこうれんが", "模様入り永劫盤装甲": "もよういりえいごうばんそうこう", "永劫盤装甲の柱": "えいごうばんそうこうのはしら", "永劫盤装甲タイル": "えいごうばんそうこうたいる", "永劫盤装甲ランプ": "えいごうばんそうこうらんぷ", "永劫盤装甲グレーティング": "えいごうばんそうこうぐれーてぃんぐ", "永劫盤装甲強化装甲板": "えいごうばんそうこうきょうかそうこうばん", "永劫盤装甲の階段": "えいごうばんそうこうのかいだん", "永劫盤装甲のハーフブロック": "えいごうばんそうこうのはーふぶろっく", "永劫盤装甲の塀": "えいごうばんそうこうのへい",
    "海洋の証": "かいようのあかし",
    # --- Halia V1.3.0 (2026-10-18): the Vigil's 593 warded blocks are all named 護りの<plain block>. ---
    "護り": "まもり",
    "ひび割れた": "ひびわれた", "塀": "へい", "凝灰岩": "ぎょうかいがん", "固めた泥": "かためたどろ", "強力な": "きょうりょくな",
    "硫黄": "いおう", "書見台": "しょけんだい", "彩釉": "さいゆう", "模様入り": "もよういり", "樹皮を剥いだ": "じゅひをはいだ",
    "表皮を剥いだ": "ひょうひをはいだ", "樹脂": "じゅし", "桃色": "ももいろ", "橙色": "だいだいいろ", "歪んだ": "ゆがんだ",
    "菌糸": "きんし", "真紅": "しんく", "研がれた": "とがれた", "辰砂": "しんしゃ", "秘めた": "ひめた", "吊り看板": "つりかんばん",
    "竹細工": "たけざいく", "粗い土": "あらいつち", "粘着": "ねんちゃく", "色あせた": "いろあせた", "赤紫色": "あかむらさきいろ",
    "青緑色": "あおみどりいろ", "黄緑色": "きみどりいろ", "黄色": "きいろ", "電球": "でんきゅう", "玄武岩": "げんぶがん",
    # --- Tsubomi V2.1.0 (2026-10-18) 不吉な瓶 Lv.6〜13。読みは tsubomi-src/docs/JA_READINGS_V2.1.0.json(未確認)。 ---
    "不吉な瓶 Lv.6": "ふきつなびん えるぶいろく", "不吉な瓶 Lv.7": "ふきつなびん えるぶいなな", "不吉な瓶 Lv.8": "ふきつなびん えるぶいはち", "不吉な瓶 Lv.9": "ふきつなびん えるぶいきゅう", "不吉な瓶 Lv.10": "ふきつなびん えるぶいじゅう", "不吉な瓶 Lv.11": "ふきつなびん えるぶいじゅういち", "不吉な瓶 Lv.12": "ふきつなびん えるぶいじゅうに", "不吉な瓶 Lv.13": "ふきつなびん えるぶいじゅうさん",
    # Tsubomi V2.0.0 のスポーンエッグ(バニラの表示名)で YOMI に無い漢字を含む 4 つ: 表示名まるごとの読み。
    "洞窟グモのスポーンエッグ": "どうくつぐものすぽーんえっぐ", "商人のラマのスポーンエッグ": "しょうにんのらまのすぽーんえっぐ",
    "熱帯魚のスポーンエッグ": "ねったいぎょのすぽーんえっぐ", "行商人のスポーンエッグ": "ぎょうしょうにんのすぽーんえっぐ",
    # --- Tsubomi V2.0.0 (2026-10-18) の行列 200 枚 + エンチャントリンゴ。V1.1.0 と同じく表示名まるごとを 1 語として入れる。
    #     読みは Tsubomi 担当が書いた未確認のもの(tsubomi-src/docs/JA_READINGS_V2.0.0.json)。 ---
    "窯焼き陶土レンガ": "かまやきとうどれんが", "模様入り窯焼き陶土": "もよういりかまやきとうど", "窯焼き陶土の柱": "かまやきとうどのはしら", "窯焼き陶土タイル": "かまやきとうどたいる", "窯焼き陶土ランプ": "かまやきとうどらんぷ",
    "窯焼き陶土グレーティング": "かまやきとうどぐれーてぃんぐ", "窯焼き陶土強化装甲板": "かまやきとうどきょうかそうこうばん", "窯焼き陶土の階段": "かまやきとうどのかいだん", "窯焼き陶土のハーフブロック": "かまやきとうどのはーふぶろっく", "窯焼き陶土の塀": "かまやきとうどのへい",
    "藍青金石レンガ": "あいせいきんせきれんが", "模様入り藍青金石": "もよういりあいせいきんせき", "藍青金石の柱": "あいせいきんせきのはしら", "藍青金石タイル": "あいせいきんせきたいる", "藍青金石ランプ": "あいせいきんせきらんぷ",
    "藍青金石グレーティング": "あいせいきんせきぐれーてぃんぐ", "藍青金石強化装甲板": "あいせいきんせききょうかそうこうばん", "藍青金石の階段": "あいせいきんせきのかいだん", "藍青金石のハーフブロック": "あいせいきんせきのはーふぶろっく", "藍青金石の塀": "あいせいきんせきのへい",
    "ハリア蒼結晶レンガ": "はりあそうけっしょうれんが", "模様入りハリア蒼結晶": "もよういりはりあそうけっしょう", "ハリア蒼結晶の柱": "はりあそうけっしょうのはしら", "ハリア蒼結晶タイル": "はりあそうけっしょうたいる", "ハリア蒼結晶ランプ": "はりあそうけっしょうらんぷ",
    "ハリア蒼結晶グレーティング": "はりあそうけっしょうぐれーてぃんぐ", "ハリア蒼結晶強化装甲板": "はりあそうけっしょうきょうかそうこうばん", "ハリア蒼結晶の階段": "はりあそうけっしょうのかいだん", "ハリア蒼結晶のハーフブロック": "はりあそうけっしょうのはーふぶろっく", "ハリア蒼結晶の塀": "はりあそうけっしょうのへい",
    "藤黒曜石レンガ": "ふじこくようせきれんが", "模様入り藤黒曜石": "もよういりふじこくようせき", "藤黒曜石の柱": "ふじこくようせきのはしら", "藤黒曜石タイル": "ふじこくようせきたいる", "藤黒曜石ランプ": "ふじこくようせきらんぷ",
    "藤黒曜石グレーティング": "ふじこくようせきぐれーてぃんぐ", "藤黒曜石強化装甲板": "ふじこくようせききょうかそうこうばん", "藤黒曜石の階段": "ふじこくようせきのかいだん", "藤黒曜石のハーフブロック": "ふじこくようせきのはーふぶろっく", "藤黒曜石の塀": "ふじこくようせきのへい",
    "天界紫水晶レンガ": "てんかいむらさきすいしょうれんが", "模様入り天界紫水晶": "もよういりてんかいむらさきすいしょう", "天界紫水晶の柱": "てんかいむらさきすいしょうのはしら", "天界紫水晶タイル": "てんかいむらさきすいしょうたいる", "天界紫水晶ランプ": "てんかいむらさきすいしょうらんぷ",
    "天界紫水晶グレーティング": "てんかいむらさきすいしょうぐれーてぃんぐ", "天界紫水晶強化装甲板": "てんかいむらさきすいしょうきょうかそうこうばん", "天界紫水晶の階段": "てんかいむらさきすいしょうのかいだん", "天界紫水晶のハーフブロック": "てんかいむらさきすいしょうのはーふぶろっく", "天界紫水晶の塀": "てんかいむらさきすいしょうのへい",
    "戦術カーボンレンガ": "せんじゅつかーぼんれんが", "模様入り戦術カーボン": "もよういりせんじゅつかーぼん", "戦術カーボンの柱": "せんじゅつかーぼんのはしら", "戦術カーボンタイル": "せんじゅつかーぼんたいる", "戦術カーボンランプ": "せんじゅつかーぼんらんぷ",
    "戦術カーボングレーティング": "せんじゅつかーぼんぐれーてぃんぐ", "戦術カーボン強化装甲板": "せんじゅつかーぼんきょうかそうこうばん", "戦術カーボンの階段": "せんじゅつかーぼんのかいだん", "戦術カーボンのハーフブロック": "せんじゅつかーぼんのはーふぶろっく", "戦術カーボンの塀": "せんじゅつかーぼんのへい",
    "氷華プリズマリンレンガ": "ひょうかぷりずまりんれんが", "模様入り氷華プリズマリン": "もよういりひょうかぷりずまりん", "氷華プリズマリンの柱": "ひょうかぷりずまりんのはしら", "氷華プリズマリンタイル": "ひょうかぷりずまりんたいる", "氷華プリズマリンランプ": "ひょうかぷりずまりんらんぷ",
    "氷華プリズマリングレーティング": "ひょうかぷりずまりんぐれーてぃんぐ", "氷華プリズマリン強化装甲板": "ひょうかぷりずまりんきょうかそうこうばん", "氷華プリズマリンの階段": "ひょうかぷりずまりんのかいだん", "氷華プリズマリンのハーフブロック": "ひょうかぷりずまりんのはーふぶろっく", "氷華プリズマリンの塀": "ひょうかぷりずまりんのへい",
    "深孔雀石レンガ": "ふかくじゃくせきれんが", "模様入り深孔雀石": "もよういりふかくじゃくせき", "深孔雀石の柱": "ふかくじゃくせきのはしら", "深孔雀石タイル": "ふかくじゃくせきたいる", "深孔雀石ランプ": "ふかくじゃくせきらんぷ",
    "深孔雀石グレーティング": "ふかくじゃくせきぐれーてぃんぐ", "深孔雀石強化装甲板": "ふかくじゃくせききょうかそうこうばん", "深孔雀石の階段": "ふかくじゃくせきのかいだん", "深孔雀石のハーフブロック": "ふかくじゃくせきのはーふぶろっく", "深孔雀石の塀": "ふかくじゃくせきのへい",
    "雪白大理石レンガ": "せっぱくだいりせきれんが", "模様入り雪白大理石": "もよういりせっぱくだいりせき", "雪白大理石の柱": "せっぱくだいりせきのはしら", "雪白大理石タイル": "せっぱくだいりせきたいる", "雪白大理石ランプ": "せっぱくだいりせきらんぷ",
    "雪白大理石グレーティング": "せっぱくだいりせきぐれーてぃんぐ", "雪白大理石強化装甲板": "せっぱくだいりせききょうかそうこうばん", "雪白大理石の階段": "せっぱくだいりせきのかいだん", "雪白大理石のハーフブロック": "せっぱくだいりせきのはーふぶろっく", "雪白大理石の塀": "せっぱくだいりせきのへい",
    "幻影合金レンガ": "げんえいごうきんれんが", "模様入り幻影合金": "もよういりげんえいごうきん", "幻影合金の柱": "げんえいごうきんのはしら", "幻影合金タイル": "げんえいごうきんたいる", "幻影合金ランプ": "げんえいごうきんらんぷ",
    "幻影合金グレーティング": "げんえいごうきんぐれーてぃんぐ", "幻影合金強化装甲板": "げんえいごうきんきょうかそうこうばん", "幻影合金の階段": "げんえいごうきんのかいだん", "幻影合金のハーフブロック": "げんえいごうきんのはーふぶろっく", "幻影合金の塀": "げんえいごうきんのへい",
    "翠竹石レンガ": "すいちくせきれんが", "模様入り翠竹石": "もよういりすいちくせき", "翠竹石の柱": "すいちくせきのはしら", "翠竹石タイル": "すいちくせきたいる", "翠竹石ランプ": "すいちくせきらんぷ",
    "翠竹石グレーティング": "すいちくせきぐれーてぃんぐ", "翠竹石強化装甲板": "すいちくせききょうかそうこうばん", "翠竹石の階段": "すいちくせきのかいだん", "翠竹石のハーフブロック": "すいちくせきのはーふぶろっく", "翠竹石の塀": "すいちくせきのへい",
    "影玄武岩レンガ": "かげげんぶがんれんが", "模様入り影玄武岩": "もよういりかげげんぶがん", "影玄武岩の柱": "かげげんぶがんのはしら", "影玄武岩タイル": "かげげんぶがんたいる", "影玄武岩ランプ": "かげげんぶがんらんぷ",
    "影玄武岩グレーティング": "かげげんぶがんぐれーてぃんぐ", "影玄武岩強化装甲板": "かげげんぶがんきょうかそうこうばん", "影玄武岩の階段": "かげげんぶがんのかいだん", "影玄武岩のハーフブロック": "かげげんぶがんのはーふぶろっく", "影玄武岩の塀": "かげげんぶがんのへい",
    "虹彩ビスマスレンガ": "こうさいびすますれんが", "模様入り虹彩ビスマス": "もよういりこうさいびすます", "虹彩ビスマスの柱": "こうさいびすますのはしら", "虹彩ビスマスタイル": "こうさいびすますたいる", "虹彩ビスマスランプ": "こうさいびすますらんぷ",
    "虹彩ビスマスグレーティング": "こうさいびすますぐれーてぃんぐ", "虹彩ビスマス強化装甲板": "こうさいびすますきょうかそうこうばん", "虹彩ビスマスの階段": "こうさいびすますのかいだん", "虹彩ビスマスのハーフブロック": "こうさいびすますのはーふぶろっく", "虹彩ビスマスの塀": "こうさいびすますのへい",
    "星輝ネザーレンガ": "せいきねざーれんが", "模様入り星輝ネザーレンガ": "もよういりせいきねざーれんが", "星輝ネザーレンガの柱": "せいきねざーれんがのはしら", "星輝ネザーレンガタイル": "せいきねざーれんがたいる", "星輝ネザーレンガランプ": "せいきねざーれんがらんぷ",
    "星輝ネザーレンガグレーティング": "せいきねざーれんがぐれーてぃんぐ", "星輝ネザーレンガ強化装甲板": "せいきねざーれんがきょうかそうこうばん", "星輝ネザーレンガの階段": "せいきねざーれんがのかいだん", "星輝ネザーレンガのハーフブロック": "せいきねざーれんがのはーふぶろっく", "星輝ネザーレンガの塀": "せいきねざーれんがのへい",
    "エンチャントリンゴ": "えんちゃんとりんご",
    #     **仮の読み**(読みが揺れうる、と担当が挙げた 6 系統: pale_serpentine, ouka_steel, kurogane_titanium, crimson_tamahagane, golden_kintsugi, ancient_shrine_stone。所有者の確認待ち):
    "桜花鋼レンガ": "おうかこうれんが", "模様入り桜花鋼": "もよういりおうかこう", "桜花鋼の柱": "おうかこうのはしら", "桜花鋼タイル": "おうかこうたいる", "桜花鋼ランプ": "おうかこうらんぷ",
    "桜花鋼グレーティング": "おうかこうぐれーてぃんぐ", "桜花鋼強化装甲板": "おうかこうきょうかそうこうばん", "桜花鋼の階段": "おうかこうのかいだん", "桜花鋼のハーフブロック": "おうかこうのはーふぶろっく", "桜花鋼の塀": "おうかこうのへい",
    "黒鉄チタニウムレンガ": "くろがねちたにうむれんが", "模様入り黒鉄チタニウム": "もよういりくろがねちたにうむ", "黒鉄チタニウムの柱": "くろがねちたにうむのはしら", "黒鉄チタニウムタイル": "くろがねちたにうむたいる", "黒鉄チタニウムランプ": "くろがねちたにうむらんぷ",
    "黒鉄チタニウムグレーティング": "くろがねちたにうむぐれーてぃんぐ", "黒鉄チタニウム強化装甲板": "くろがねちたにうむきょうかそうこうばん", "黒鉄チタニウムの階段": "くろがねちたにうむのかいだん", "黒鉄チタニウムのハーフブロック": "くろがねちたにうむのはーふぶろっく", "黒鉄チタニウムの塀": "くろがねちたにうむのへい",
    "赫灼玉鋼レンガ": "かくしゃくたまはがねれんが", "模様入り赫灼玉鋼": "もよういりかくしゃくたまはがね", "赫灼玉鋼の柱": "かくしゃくたまはがねのはしら", "赫灼玉鋼タイル": "かくしゃくたまはがねたいる", "赫灼玉鋼ランプ": "かくしゃくたまはがねらんぷ",
    "赫灼玉鋼グレーティング": "かくしゃくたまはがねぐれーてぃんぐ", "赫灼玉鋼強化装甲板": "かくしゃくたまはがねきょうかそうこうばん", "赫灼玉鋼の階段": "かくしゃくたまはがねのかいだん", "赫灼玉鋼のハーフブロック": "かくしゃくたまはがねのはーふぶろっく", "赫灼玉鋼の塀": "かくしゃくたまはがねのへい",
    "金継ぎ黒石レンガ": "きんつぎくろいしれんが", "模様入り金継ぎ黒石": "もよういりきんつぎくろいし", "金継ぎ黒石の柱": "きんつぎくろいしのはしら", "金継ぎ黒石タイル": "きんつぎくろいしたいる", "金継ぎ黒石ランプ": "きんつぎくろいしらんぷ",
    "金継ぎ黒石グレーティング": "きんつぎくろいしぐれーてぃんぐ", "金継ぎ黒石強化装甲板": "きんつぎくろいしきょうかそうこうばん", "金継ぎ黒石の階段": "きんつぎくろいしのかいだん", "金継ぎ黒石のハーフブロック": "きんつぎくろいしのはーふぶろっく", "金継ぎ黒石の塀": "きんつぎくろいしのへい",
    "淡蛇紋石レンガ": "たんじゃもんせきれんが", "模様入り淡蛇紋石": "もよういりたんじゃもんせき", "淡蛇紋石の柱": "たんじゃもんせきのはしら", "淡蛇紋石タイル": "たんじゃもんせきたいる", "淡蛇紋石ランプ": "たんじゃもんせきらんぷ",
    "淡蛇紋石グレーティング": "たんじゃもんせきぐれーてぃんぐ", "淡蛇紋石強化装甲板": "たんじゃもんせききょうかそうこうばん", "淡蛇紋石の階段": "たんじゃもんせきのかいだん", "淡蛇紋石のハーフブロック": "たんじゃもんせきのはーふぶろっく", "淡蛇紋石の塀": "たんじゃもんせきのへい",
    "古社寺石レンガ": "こしゃじせきれんが", "模様入り古社寺石": "もよういりこしゃじせき", "古社寺石の柱": "こしゃじせきのはしら", "古社寺石タイル": "こしゃじせきたいる", "古社寺石ランプ": "こしゃじせきらんぷ",
    "古社寺石グレーティング": "こしゃじせきぐれーてぃんぐ", "古社寺石強化装甲板": "こしゃじせききょうかそうこうばん", "古社寺石の階段": "こしゃじせきのかいだん", "古社寺石のハーフブロック": "こしゃじせきのはーふぶろっく", "古社寺石の塀": "こしゃじせきのへい",
    # --- ASTRAEA V1.5.0 (2026-10-11) の 112 枚(バニラ素材の数枚を含む)。Tsubomi と同じく表示名まるごとを 1 語として入れる
    #     (最長一致なので、ほかの語の読みを動かさない)。読みは ASTRAEA 担当が書いたもの。足さないと 112 枚が
    #     「未登録の文字」の警告のまま五十音順の間違った場所に並ぶ。 ---
    "NPC 契約書": "えぬぴーしーけいやくしょ", "アカシアの肘掛け椅子": "あかしあのひじかけいす", "アストレア・シアンのセイバー結晶": "あすとれあしあんのせいばーけっしょう", "アメジスト・パープルのセイバー結晶": "あめじすとぱーぷるのせいばーけっしょう", "エメラルド・グリーンのセイバー結晶": "えめらるどぐりーんのせいばーけっしょう", "オークの肘掛け椅子": "おーくのひじかけいす",
    "ガス除去装置": "がすじょきょそうち", "ガラス展示ケース": "がらすてんじけーす", "クォーツの肘掛け椅子": "くぉーつのひじかけいす", "サクラの肘掛け椅子": "さくらのひじかけいす", "シラカバの肘掛け椅子": "しらかばのひじかけいす", "スイカの薄切り": "すいかのうすぎり",
    "スクリプトリア活版印刷機": "すくりぷとりあかっぱんいんさつき", "ソーラー・ゴールドのセイバー結晶": "そーらーごーるどのせいばーけっしょう", "ダイヤモンドの馬鎧": "だいやもんどのうまよろい", "ダイヤモンド研磨台": "だいやもんどけんまだい", "ダークオークの肘掛け椅子": "だーくおーくのひじかけいす", "チェリー・クリムゾンのセイバー結晶": "ちぇりーくりむぞんのせいばーけっしょう",
    "トウヒの肘掛け椅子": "とうひのひじかけいす", "トリカブトの煎じ薬": "とりかぶとのせんじぐすり", "ホログラム看板": "ほろぐらむかんばん", "マングローブの肘掛け椅子": "まんぐろーぶのひじかけいす", "主権の冠": "しゅけんのかんむり", "光学プリズム": "こうがくぷりずむ",
    "創造の Codex": "そうぞうのこーでっくす", "収容セル監視装置": "しゅうようせるかんしそうち", "収容隔壁": "しゅうようかくへき", "合成アメジスト": "ごうせいあめじすと", "合成アメジストブロック": "ごうせいあめじすとぶろっく", "合成クォーツ": "ごうせいくぉーつ",
    "合成クォーツブロック": "ごうせいくぉーつぶろっく", "合成ダイヤモンド": "ごうせいだいやもんど", "合成ダイヤモンドブロック": "ごうせいだいやもんどぶろっく", "合成ネザライト": "ごうせいねざらいと", "合成ネザライトブロック": "ごうせいねざらいとぶろっく", "合成樹脂": "ごうせいじゅし",
    "合成樹脂ブロック": "ごうせいじゅしぶろっく", "合成金": "ごうせいきん", "合成金ブロック": "ごうせいきんぶろっく", "合成鉄": "ごうせいてつ", "合成鉄ブロック": "ごうせいてつぶろっく", "合成銅": "ごうせいどう",
    "合成銅ブロック": "ごうせいどうぶろっく", "安全弁": "あんぜんべん", "密閉マスク": "みっぺいますく", "微細ボクセルチゼル": "びさいぼくせるちぜる", "懸垂バー": "けんすいばー", "暗視ゴーグル": "あんしごーぐる",
    "月光の霊薬": "げっこうのれいやく", "有刺鉄線": "ゆうしてっせん", "歪んだのシャンデリア": "ゆがんだのしゃんでりあ", "歪んだのスツール": "ゆがんだのすつーる", "歪んだのソファ": "ゆがんだのそふぁ", "歪んだのテーブル": "ゆがんだのてーぶる",
    "歪んだのバスタブ": "ゆがんだのばすたぶ", "歪んだのベンチ": "ゆがんだのべんち", "歪んだのランプ": "ゆがんだのらんぷ", "歪んだの暖炉": "ゆがんだのだんろ", "歪んだの椅子": "ゆがんだのいす", "歪んだの肘掛け椅子": "ゆがんだのひじかけいす",
    "歪んだ板材": "ゆがんだいたざい", "毒スパイクピット": "どくすぱいくぴっと", "汚染浄化装置": "おせんじょうかそうち", "活力の指輪": "かつりょくのゆびわ", "浮遊の外套": "ふゆうのがいとう", "火打石": "ひうちいし",
    "熱交換器": "ねつこうかんき", "生命維持ユニット": "せいめいいじゆにっと", "疾風の護符": "しっぷうのごふ", "真紅のシャンデリア": "しんくのしゃんでりあ", "真紅のスツール": "しんくのすつーる", "真紅のソファ": "しんくのそふぁ",
    "真紅のテーブル": "しんくのてーぶる", "真紅のバスタブ": "しんくのばすたぶ", "真紅のベンチ": "しんくのべんち", "真紅のランプ": "しんくのらんぷ", "真紅の暖炉": "しんくのだんろ", "真紅の板材": "しんくのいたざい",
    "真紅の椅子": "しんくのいす", "真紅の肘掛け椅子": "しんくのひじかけいす", "碍子トランス": "がいしとらんす", "神託合成作業台": "しんたくごうせいさぎょうだい", "窒息ガス缶": "ちっそくがすかん", "粉砕機の外装": "ふんさいきのがいそう",
    "粘土玉": "ねんどだま", "純化装置": "じゅんかそうち", "純白のセイバー結晶": "じゅんぱくのせいばーけっしょう", "結晶化槽": "けっしょうかそう", "網膜スキャナー": "もうまくすきゃなー", "羽根落ちの帯": "はねおちのおび",
    "聖なる金床台座": "せいなるかなとこだいざ", "蒸留塔": "じょうりゅうとう", "蔵書棚": "ぞうしょだな", "血塗られた怨嗟の祠": "ちぬられたえんさのほこら", "装甲車(梱包)": "そうこうしゃこんぽう", "複葉戦闘機(梱包)": "ふくようせんとうきこんぽう",
    "警報ストロボ": "けいほうすとろぼ", "車両シャーシ(梱包)": "しゃりょうしゃーしこんぽう", "迎撃ミサイル": "げいげきみさいる", "迎撃ミサイル砲台": "げいげきみさいるほうだい", "迷彩モジュール": "めいさいもじゅーる", "造幣機": "ぞうへいき",
    "金の馬鎧": "きんのうまよろい", "鉄の馬鎧": "てつのうまよろい", "鋼鉄の守護騎士の印章": "こうてつのしゅごきしのいんしょう", "鍾乳石": "しょうにゅうせき", "鐘": "かね", "陽光の部族長の印章": "ようこうのぶぞくちょうのいんしょう",
    "雷鳴の首飾り": "らいめいのくびかざり", "霜原の巨獣の印章": "そうげんのきょじゅうのいんしょう", "高熱切断レーザー": "こうねつせつだんれーざー", "魂魄抽出器": "こんぱくちゅうしゅつき",
    # --- Tsubomi V1.1.0 (2026-10-11) の 100 枚。表示名まるごとを 1 語として入れる(最長一致なので、ほかの語の読みを
    #     動かさない)。読みは Tsubomi 担当が書いた未確認のもの(tsubomi-src/docs/JA_READINGS_V1.1.json)。足さないと
    #     86 枚が「未登録の文字」の警告のまま五十音順の間違った場所に並ぶ。 ---
    "桜晶ブロック": "おうしょうぶろっく", "母岩桜晶": "ぼがんおうしょう", "群生桜晶": "ぐんせいおうしょう", "極小桜晶芽": "ごくしょうおうしょうが", "中型桜晶芽": "ちゅうがたおうしょうが",
    "大型桜晶芽": "おおがたおうしょうが", "磨かれた桜晶": "みがかれたおうしょう", "桜晶レンガ": "おうしょうれんが", "模様入り桜晶": "もよういりおうしょう", "桜晶の柱": "おうしょうのはしら",
    "紅琥珀ブロック": "べにこはくぶろっく", "磨かれた紅琥珀": "みがかれたべにこはく", "紅琥珀レンガ": "べにこはくれんが", "陽光方解石": "ようこうほうかいせき",
    "磨かれた陽光方解石": "みがかれたようこうほうかいせき", "陽光方解石タイル": "ようこうほうかいせきたいる", "霊基ガラス": "れいきがらす", "遮光霊基ガラス": "しゃこうれいきがらす",
    "桜晶ランプ": "おうしょうらんぷ", "共鳴核ブロック": "きょうめいかくぶろっく", "霊木原木": "れいぼくげんぼく", "表皮を剥いだ霊木原木": "ひょうひをむいだれいぼくげんぼく",
    "霊木木部": "れいぼくもくぶ", "表皮を剥いだ霊木木部": "ひょうひをむいだれいぼくもくぶ", "霊木の板材": "れいぼくのいたざい", "霊木のモザイク": "れいぼくのもざいく", "霊木の葉": "れいぼくのは",
    "開花した霊木の葉": "かいかしたれいぼくのは", "霊木の階段": "れいぼくのかいだん", "霊木のハーフブロック": "れいぼくのはーふぶろっく", "霊木のフェンス": "れいぼくのふぇんす",
    "霊木のフェンスゲート": "れいぼくのふぇんすげーと", "霊木のドア": "れいぼくのどあ", "霊木のトラップドア": "れいぼくのとらっぷどあ", "霊木の感圧板": "れいぼくのかんあつばん",
    "霊木のボタン": "れいぼくのぼたん", "紅竹ブロック": "こうちくぶろっく", "表皮を剥いだ紅竹": "ひょうひをむいだこうちく", "紅竹の板材": "こうちくのいたざい", "紅竹モザイク": "こうちくもざいく",
    "純白磁ブロック": "じゅんはくじぶろっく", "磨かれた白磁": "みがかれたはくじ", "白磁タイル": "はくじたいる", "ひび割れた白磁タイル": "ひびわれたはくじたいる",
    "模様入り白磁": "もよういりはくじ", "白磁の柱": "はくじのはしら", "硬玉岩": "こうぎょくがん", "磨かれた硬玉": "みがかれたこうぎょく", "硬玉レンガ": "こうぎょくれんが",
    "模様入り硬玉": "もよういりこうぎょく", "灰燼粘板岩": "かいじんねんばんがん", "磨かれた灰燼粘板岩": "みがかれたかいじんねんばんがん", "灰燼粘板岩レンガ": "かいじんねんばんがんれんが",
    "灰燼粘板岩タイル": "かいじんねんばんがんたいる", "模様入り灰燼粘板岩": "もよういりかいじんねんばんがん", "白磁の階段": "はくじのかいだん", "白磁のハーフブロック": "はくじのはーふぶろっく",
    "白磁の塀": "はくじのへい", "機巧ケーシング": "きこうけーしんぐ", "黄銅ケーシング": "おうどうけーしんぐ", "銅ケーシング": "どうけーしんぐ", "風化した銅ケーシング": "ふうかしたどうけーしんぐ",
    "錆びた銅ケーシング": "さびたどうけーしんぐ", "酸化した銅ケーシング": "さんかしたどうけーしんぐ", "歯車機構ブロック": "はぐるまきこうぶろっく", "黄銅ガーダー": "おうどうがーだー",
    "機巧配管": "きこうはいかん", "黄銅配管": "おうどうはいかん", "ガラス被覆配管": "がらすひふくはいかん", "排気ベントブロック": "はいきべんとぶろっく",
    "圧力計ブロック": "あつりょくけいぶろっく", "黄銅足場": "おうどうあしば", "機巧炉心ブロック": "きこうろしんぶろっく", "黄銅枠ガラス": "おうどうわくがらす",
    "強化機巧ガラス": "きょうかきこうがらす", "黄銅の鉄格子": "おうどうのてつごうし", "機巧トラップドア": "きこうとらっぷどあ", "機巧ドア": "きこうどあ", "神域の灯篭": "しんいきのとうろう",
    "吊り神域灯篭": "つりしんいきとうろう", "祭儀台ブロック": "さいぎだいぶろっく", "ルーン配列基盤": "るーんはいれつきばん", "覚醒ルーン基盤": "かくせいるーんきばん",
    "結界核ブロック": "けっかいかくぶろっく", "結界境界石": "けっかいきょうかいせき", "神聖土壌": "しんせいどじょう", "霊基の絨毯": "れいきのじゅうたん", "香炉ブロック": "こうろぶろっく",
    "金箔神域柱頭": "きんぱくしんいきちゅうとう", "霊縛の鎖": "れいばくのくさり", "幽体固定錨": "ゆうたいこていびょう", "虚無中和ケーシング": "きょむちゅうわけーしんぐ",
    "天体儀ブロック": "てんたいぎぶろっく", "蕾の祭壇台座": "つぼみのさいだんだいざ",
    #     **仮の読み**(読みが揺れうる、と担当が挙げた 6 枚。所有者の確認待ち):
    "朱漆白磁": "しゅうるしはくじ", "朱漆白磁タイル": "しゅうるしはくじたいる", "神鈴ブロック": "かみすずぶろっく", "神輿枠組ブロック": "みこしわくぐみぶろっく",
    "霊織機ブロック": "れいおりきぶろっく", "朱塗り神域柱": "しゅぬりしんいきばしら",
    # --- ASTRAEA V1.0.0(2026-09-30)の 17 枚。語ごとに入れる(漢字 1 字ずつでは「天星」を「あまほし」とも読める)。
    #     出典: 名前は所有者の仕様書(ASTRAEA_V1.0_Update.md)と MOD の ja_jp.json だが、どちらにも読みは無い。
    #     (1) ふつうの語 —— 辞書どおりの読み: 天球・暗号・暗証・錠・極低温・断熱・重装・豊穣・削岩・地鎮・鎌・鍬。
    #     (2) ASTRAEA の造語 —— **仮の読み**(所有者の確認待ち、2026-09-30): 天星・宿星・宿星刀・大伐斧・
    #         豊穣鎌・削岩鎚・地鎮鍬・聖槍。確認で変われば、ここだけを直して作り直す。 ---
    "天球": "てんきゅう", "暗号": "あんごう", "暗証": "あんしょう", "錠": "じょう", "暗証錠": "あんしょうじょう",
    "極低温": "ごくていおん", "断熱": "だんねつ", "重装": "じゅうそう", "豊穣": "ほうじょう", "削岩": "さくがん",
    "地鎮": "じちん", "鎌": "かま", "鍬": "くわ", "鎚": "つい",
    "天星": "てんせい", "宿星": "しゅくせい", "宿星刀": "しゅくせいとう", "大伐斧": "だいばつふ",  # 仮
    "豊穣鎌": "ほうじょうがま", "削岩鎚": "さくがんつい", "地鎮鍬": "じちんくわ", "聖槍": "せいそう",  # 仮
    # --- Tsubomi V1.0.1(2026-10-05)。名前は配布済み jar の ja_jp.json。**全部ふつうの辞書語**で、造語は無い
    #     (仮の読みは 0 個)。ただし「石英」は表にあった「石」(いし)に割れて「どういし英」と読まれ、
    #     「茶葉」は「葉」(は)で「ちゃは」と読まれていた —— **警告が出ない誤読**なので、語として入れる。
    #     「樹液」はカードの無い材料だが、検索語の読みに使われる。 ---
    "卓上": "たくじょう", "盆栽": "ぼんさい", "携帯": "けいたい", "石英": "せきえい",
    "冒険者": "ぼうけんしゃ", "茶葉": "ちゃば", "樹液": "じゅえき",
    # --- 別ブランド Cherry / OUKA(2026-09-20)。所有者の「レシピ集に Cherry と
    #     OUKA の作り方が無い」への対応で早見表に入った 19 枚ぶん。ここを足さないと
    #     V4.3.2 の 22 枚と同じで、五十音順の**間違った場所に並ぶ**カードになる。 ---
    # --- ついでに片づけた Alpha の 10 枚(2026-09-20)。Cherry / OUKA を足すために
    #     この表を開いたところ、V4.2〜V4.4 の扉・建材・灰街圏の語が未登録のまま
    #     残っていた —— どれも五十音順の**間違った場所**に並んでいたということなので、
    #     同じ手で直しておく(1240/1250 → 1250/1250)。 ---
    "ノッカーの玄関扉": "のっかーのげんかんとびら", "玄関": "げんかん", "玄": "げん",
    "厩の扉": "うまやのとびら", "厩": "うまや",
    "市松の石蓋": "いちまつのいしぶた", "市松": "いちまつ", "市": "いち", "松": "まつ",
    "石蓋": "いしぶた", "蓋": "ふた",
    "引き違いのガラス戸": "ひきちがいのがらすど", "引き違い": "ひきちがい", "違": "ちがい",
    "絞りのハッチ": "しぼりのはっち", "絞": "しぼり",
    "閂の扉": "かんぬきのとびら", "閂": "かんぬき",
    "杭の木戸": "くいのきど", "杭": "くい",
    "貸金庫の棚": "かしきんこのたな", "貸金庫": "かしきんこ", "貸": "かし",
    "吹流し": "ふきながし", "吹流": "ふきなが", "吹": "ふき", "流": "なが",
    "滑走路床": "かっそうろゆか", "滑走路": "かっそうろ", "滑走": "かっそう",
    "滑": "かつ", "走": "そう", "路": "ろ",
    # Cherry V1.2.0 の 4 語（2026-09-28）。V1.2.0 は読み無しのまま公開され、
    # 生成器は毎回「未登録の文字」と警告していた —— その 4 枚は五十音順の
    # **間違った場所**に並んでいた。読みは jar の ja_jp の表示名から。
    "高度分子加工機": "こうどぶんしかこうき", "高度": "こうど", "加工機": "かこうき", "加工": "かこう", "加": "か",
    "過塩素酸推進剤": "かえんそさんすいしんざい", "過塩素酸": "かえんそさん", "過": "か", "塩": "えん", "酸": "さん",
    "レゴリス粉末": "れごりすふんまつ", "粉末": "ふんまつ", "末": "まつ",
    "耐寒の内張り": "たいかんのうちばり", "耐寒": "たいかん", "内張り": "うちばり",
    "内": "うち", "寒": "かん", "張": "はり",
    # Cherry(月と軌道)
    "発射台コンプレックス": "はっしゃだいこんぷれっくす", "発射台": "はっしゃだい",
    "発射": "はっしゃ", "発": "はつ", "射": "しゃ",
    "気密フィールド投射機": "きみつふぃーるどとうしゃき", "気密": "きみつ", "密": "みつ",
    "投射機": "とうしゃき", "投射": "とうしゃ", "投": "とう",
    "与圧スーツ": "よあつすーつ", "与圧": "よあつ", "与": "よ",
    "推進剤キャニスター": "すいしんざいきゃにすたー", "推進剤": "すいしんざい",
    "推進": "すいしん", "推": "すい", "進": "しん", "剤": "ざい",
    "分子共鳴融合炉": "ぶんしきょうめいゆうごうろ", "共鳴": "きょうめい",
    "融合炉": "ゆうごうろ", "融合": "ゆうごう", "分子": "ぶんし",
    "分": "ぶん", "子": "し", "融": "ゆう", "炉": "ろ",
    "超音波カッター": "ちょうおんぱかったー", "超音波": "ちょうおんぱ",
    "超音": "ちょうおん", "超": "ちょう", "音波": "おんぱ", "波": "は",
    # Cherry V1.1.0 の 11 枚（2026-09-20 夜、Cherry セッションの配信前に先回りして）。
    # ここを足さずに作り直すと、11 枚だけ五十音順の**間違った場所**に並ぶ。
    # Aegis-X / Stratos-900 は ASCII なので読みは要らない。
    "着艦ワイヤー": "ちゃくかんわいやー", "着艦": "ちゃくかん", "着": "ちゃく", "艦": "かん",
    "管制ホログラフィック・コンソール": "かんせいほろぐらふぃっくこんそーる",
    "管制レーダー・ドーム": "かんせいれーだーどーむ", "管制": "かんせい", "制": "せい",
    "電磁カタパルトの軌道": "でんじかたぱるとのきどう", "電磁": "でんじ", "磁": "じ",
    "軌道": "きどう", "軌": "き", "道": "どう",
    "誘導ミサイル": "ゆうどうみさいる", "誘導": "ゆうどう", "誘": "ゆう", "導": "どう",
    "PAPI 進入角指示灯": "ぱぴしんにゅうかくしじとう", "進入角": "しんにゅうかく",
    "進入": "しんにゅう", "角": "かく", "指示灯": "しじとう", "指示": "しじ",
    "指": "し", "示": "じ", "灯": "とう",
    "滑走路中心線灯": "かっそうろちゅうしんせんとう", "中心線": "ちゅうしんせん",
    "中心": "ちゅうしん", "中": "ちゅう", "心": "しん", "線": "せん",
    "級": "きゅう",
    # OUKA(桜花)
    "桜花合金インゴット": "おうかごうきんいんごっと", "桜花合金": "おうかごうきん",
    "桜花の杖": "おうかのつえ", "桜花": "おうか", "桜": "おう",
    "弾幕の焦点": "だんまくのしょうてん", "弾幕": "だんまく", "幕": "まく",
    "焦点": "しょうてん", "焦": "しょう",
    # --- OUKA V1.2 の機械 20 枚(2026-09-24)。生成器が「未登録の文字」として名指しで警告した 20 枚の名前を、
    #     語ごとに足した(足す前 1264/1284 → 足したあと 1284/1284)。物流・油圧・出力は、字ごとの読み(もの・なが・
    #     あぶら)では間違って読まれていた —— 語で足した。既にある読みで変わるものは無い(1,515 の名前で確かめた)。 ---
    "自律型": "じりつがた", "自律": "じりつ", "製材": "せいざい", "培養": "ばいよう",
    "電弧": "でんこ", "重熱": "じゅうねつ", "精錬": "せいれん", "重水": "じゅうすい",
    "減速型": "げんそくがた", "減速": "げんそく", "分裂": "ぶんれつ", "平面鏡": "へいめんきょう",
    "平面": "へいめん", "超高圧": "ちょうこうあつ", "高圧": "こうあつ", "取水": "しゅすい",
    "高速": "こうそく", "超伝導": "ちょうでんどう", "伝導": "でんどう", "遠心分離": "えんしんぶんり",
    "遠心": "えんしん", "分離": "ぶんり", "抽出": "ちゅうしゅつ", "高精度": "こうせいど",
    "精度": "せいど", "蓄電": "ちくでん", "太陽熱": "たいようねつ", "太陽": "たいよう",
    "集光": "しゅうこう", "蓄熱": "ちくねつ", "波長": "はちょう", "分光式": "ぶんこうしき",
    "分光": "ぶんこう", "地殻": "ちかく", "深層": "しんそう", "掘削": "くっさく",
    "送電": "そうでん", "量子": "りょうし", "圧縮": "あっしゅく", "外殻": "がいかく",
    "耐熱": "たいねつ", "入出力": "にゅうしゅつりょく", "油圧": "ゆあつ", "出力": "しゅつりょく",
    "物流": "ぶつりゅう",
    "律": "りつ", "製": "せい", "材": "ざい", "培": "ばい", "養": "よう", "弧": "こ", "熱": "ねつ", "精": "せい", "錬": "れん", "減": "げん",
    "裂": "れつ", "鏡": "きょう", "面": "めん", "取": "しゅ", "伝": "でん", "速": "そく", "遠": "えん", "離": "り", "抽": "ちゅう", "度": "ど",
    "蓄": "ちく", "陽": "よう", "集": "しゅう", "光": "こう", "長": "ちょう", "掘": "くつ", "削": "さく", "層": "そう", "深": "しん", "殻": "かく",
    "送": "そう", "縮": "しゅく", "量": "りょう", "耐": "たい", "出": "しゅつ", "型": "がた", "自": "じ", "高": "こう", "太": "たい", "電": "でん",
    "重": "じゅう", "力": "りょく",
    # --- V4.3.2 の工業 20 種 + V4.3.3 の 4 種(2026-09-09)。 ---
    #     ⚠ V4.3.2 はこの 22 語を足さずに出荷していた —— 生成器は毎回
    #     「未登録の文字」と名指しで警告していたが、その警告は読み飛ばされ、
    #     レシピ表の五十音順に 22 枚だけ**間違った場所に並ぶ**カードが残っていた。
    #     4.3.3 で 4 語増えるので、増やす前に 22 語まとめて片づける
    #     (足す前 1184/1206 → 足したあと 1206/1206)。
    "圧延板": "あつえんばん", "圧延": "あつえん", "圧": "あつ", "延": "のべ",
    "鋲の箱": "びょうのはこ", "鋲": "びょう",
    "焼入れ棒": "やきいればう", "焼入れ": "やきいれ", "入": "い",
    "軸受レース": "じくうけれーす", "軸受": "じくうけ", "軸": "じく", "受": "うけ",
    "点火セル": "てんかせる", "点火": "てんか", "点": "てん",
    "気化器本体": "きかきほんたい", "気化器": "きかき", "本体": "ほんたい",
    "気": "き", "化": "か", "体": "たい",
    "多岐管鋳物": "たきかんいもの", "多岐": "たき", "鋳物": "いもの",
    "多": "た", "岐": "き", "管": "かん", "鋳": "い",
    "冷却コア": "れいきゃくこあ", "冷却": "れいきゃく", "冷": "れい", "却": "きゃく",
    "タイヤ素地": "たいやそじ", "素地": "そじ", "素": "そ", "地": "じ",
    "風防": "ふうぼう", "風": "ふう", "防": "ぼう",
    "外板": "がいはん", "外": "がい",
    "燃料管": "ねんりょうかん",
    "オイル差し": "おいるさし", "差": "さ",
    "V8 機関キット": "ぶいはちきかんきっと",
    "V12 機関キット": "ぶいじゅうにきかんきっと",
    "水平対向機関キット": "すいへいたいこうきかんきっと",
    "航法キット": "こうほうきっと",
    "機関": "きかん", "関": "かん", "水平": "すいへい", "平": "へい",
    "対向": "たいこう", "対": "たい", "向": "こう", "航法": "こうほう",
    "航": "こう", "法": "ほう",
    "組立台": "くみたてだい", "組立": "くみたて", "組": "くみ", "立": "たて", "台": "だい",
    "灰雀": "はいすずめ", "雀": "すずめ",
    # --- V4.3.3 §3 の 4 語 ---
    "駐車チョーク": "ちゅうしゃちょーく", "駐車": "ちゅうしゃ", "駐": "ちゅう",
    "予備輪": "よびりん", "予備": "よび", "予": "よ", "備": "び",
    "格納フック": "かくのうふっく", "格納": "かくのう", "格": "かく", "納": "のう",
    # --- V4.3.1: 災害と工業の 9 語(2026-09-07)。生成器が「未登録の文字」として
    #     名指しで警告したものだけを足した(足す前 1167/1176 → 足したあと 1176/1176)。 ---
    "工業": "こうぎょう", "工": "こう", "業": "ぎょう",
    "足場": "あしば", "足": "あし", "場": "ば",
    "ライン印": "らいんじるし", "印": "しるし",
    "鉱滓": "こうさい", "鉱": "こう", "滓": "かす",
    "汚染": "おせん", "汚": "よご", "染": "そ",
    "スクラバー塔": "すくらばーとう", "塔": "とう",
    "季節": "きせつ", "季": "き", "節": "せつ",
    "排水": "はいすい", "排": "はい",
    # --- V4.3.0: Stackworks の 7 語(2026-09-06)。生成器が「未登録の文字」として
    #     名指しで警告したものだけを足した。複合語は音便のため語ごとに登録する。 ---
    "灰庫": "はいこ", "庫": "こ", "煤床": "すすゆか", "煤": "すす",
    "貨物錨": "かもついかり", "貨物切符": "かもつきっぷ", "貨物": "かもつ",
    "錨": "いかり", "切符": "きっぷ", "符": "ふ",
    "残渣火室": "ざんさかしつ", "火室": "かしつ", "火": "ひ", "室": "しつ",
    "発作歯車箱": "ほっさはぐるまばこ", "歯車": "はぐるま", "歯": "は",
    "洗浄残渣": "せんじょうざんさ", "洗浄": "せんじょう",
    # --- V4.2.5: 揺籃板・揺籃鑿・解体湾・発作核・縁ビーコン(2026-09-05)。 ---
    "揺籃": "ようらん", "鑿": "のみ", "解体湾": "かいたいわん", "解体": "かいたい", "湾": "わん",
    "発作核": "ほっさかく", "発作": "ほっさ", "核": "かく", "縁": "ふち",
    # --- V4.2.4: 環状本管図・圧力弁(2026-09-05)。 ---
    "環状本管": "かんじょうほんかん", "本管": "ほんかん", "環状": "かんじょう", "図": "ず",
    "圧力弁": "あつりょくべん", "圧力": "あつりょく", "弁": "べん",
    # --- V4.2.3: 南京錠・点検鍵・槽煉瓦(2026-09-05)。 ---
    "南京錠": "なんきんじょう", "点検": "てんけん", "鍵": "かぎ", "煉瓦": "れんが",
    # --- V4.2.2: 2026-09-05 の実行で 142 件が未登録だった(V4.1 の産業化 40 種・化学強化ガラス・灰街圏・新しい扉)。
    #     複合語は音便のためまとめて登録(最長一致)。 ---
    "化学強化": "かがくきょうか", "槽": "そう", "通電した": "つうでんした", "通電": "つうでん",
    "X字補強": "えっくすじほきょう", "補強": "ほきょう", "上り坂": "のぼりざか", "坂": "さか",
    "コークス炉": "こーくすろ", "炉": "ろ", "再処理機": "さいしょりき", "再処理": "さいしょり",
    "井戸": "いど", "仕分け門": "しわけもん", "門扉": "もんぴ", "門": "もん",
    "作業安全警報": "さぎょうあんぜんけいほう", "円形": "えんけい", "凝縮": "ぎょうしゅく",
    "加圧": "かあつ", "流体弁": "りゅうたいべん", "流体": "りゅうたい", "動力軸": "どうりょくじく",
    "取水口": "しゅすいこう", "圧延機": "あつえんき", "安定化": "あんていか", "導水渠": "どうすいきょ",
    "工場制御盤": "こうじょうせいぎょばん", "工場足場": "こうじょうあしば", "工場": "こうじょう",
    "工業用燻製塔": "こうぎょうようくんせいとう", "工業用蒸留器": "こうぎょうようじょうりゅうき", "工業用": "こうぎょうよう",
    "手回し": "てまわし", "旋盤": "せんばん", "暗証番号式": "あんしょうばんごうしき", "防爆": "ぼうばく",
    "歩廊": "ほろう", "歯車駆動": "はぐるまくどう", "昇降扉": "しょうこうとびら", "昇降": "しょうこう",
    "残渣": "ざんさ", "水量計": "すいりょうけい", "洗鉱機": "せんこうき", "浄水器": "じょうすいき",
    "測量図": "そくりょうず", "漂白": "ひょうはく", "濾過": "ろか", "灰": "はい",
    "燃料発電機": "ねんりょうはつでんき", "燃料": "ねんりょう", "独房": "どくぼう", "粉砕機": "ふんさいき",
    "組立腕": "くみたてうで", "給水口": "きゅうすいこう", "給水塔": "きゅうすいとう", "耐火煉瓦": "たいかれんが",
    "蒸気": "じょうき", "設計図": "せっけいず", "貯水槽": "ちょすいそう", "鉄帯": "てつおび",
    "電動機": "でんどうき", "電動": "でんどう", "電気炉": "でんきろ", "高架": "こうか", "床": "ゆか", "高炉": "こうろ",
    # --- V4.0.1: V3〜V4 で増えた名前(2026-09-02 の実行で 25 件が未登録だった)。複合語は音便のためまとめて登録 ---
    "音響": "おんきょう", "共鳴": "きょうめい", "穀物": "こくもつ", "配送": "はいそう", "受取": "うけとり",
    "ろ過": "ろか", "遮光": "しゃこう", "重機": "じゅうき", "時間停止碇": "じかんていしいかり",
    "次元鏡": "じげんきょう", "重力反転機": "じゅうりょくはんてんき", "無効化領域発生器": "むこうかりょういきはっせいき",
    "空間転移杖": "くうかんてんいじょう", "反響探知機": "はんきょうたんちき", "運動減衰": "うんどうげんすい",
    "虚空": "こくう", "空間導管": "くうかんどうかん", "空間": "くうかん", "大気採集機": "たいきさいしゅうき",
    "自動製作機": "じどうせいさくき", "生体織機": "せいたいしょっき", "注射器": "ちゅうしゃき",
    "地殻掘削機": "ちかくくっさくき", "砂利": "じゃり", "熱機関発電機": "ねつきかんはつでんき",
    # --- 形状・共通の接尾語 -------------------------------------------------
    "円柱": "えんちゅう", "縦": "たて", "板材": "いたざい", "階段": "かいだん",
    "柱": "はしら", "扉": "とびら", "戸": "ど", "石": "いし", "盾": "たて",
    "剣": "けん", "弓": "ゆみ", "矢": "や", "槍": "やり", "斧": "おの",
    "杖": "つえ", "輪": "わ", "翼": "つばさ", "卵": "たまご", "弾": "だん",
    "機": "き", "車": "しゃ", "木": "き", "氷": "こおり", "森": "もり",
    "雲": "くも", "雷": "かみなり", "銀": "ぎん", "鉄": "てつ", "鋼": "はがね",
    "王": "おう", "骨": "ほね", "駅": "えき", "枚": "まい", "式": "しき",
    "軽": "けい", "手": "て", "口": "くち",
    # --- v1.8.1: 電力 MOD の語(複合語は音便のためまとめて登録)-----------------
    "原子力発電所": "げんしりょくはつでんしょ", "原子炉": "げんしろ",
    "発電機": "はつでんき", "発電": "はつでん", "分電盤": "ぶんでんばん",
    "変圧器": "へんあつき", "絶縁": "ぜつえん", "暖炉": "だんろ",
    "機械": "きかい", "筐体": "きょうたい", "遮蔽": "しゃへい",
    # --- v1.9.3: 蓄電池(発電機・原子力発電所の下流に新設)-------------------
    "蓄電池": "ちくでんち",
    # --- v1.8.2: 再生可能エネルギー 3 種。いずれも「発電機」の前に付く語で、
    #     1 文字ずつでは読めない(「水+流」「風+力」「太陽+光」)ので複合語で登録する。
    "太陽光": "たいようこう", "水流": "すいりゅう", "風力": "ふうりょく",
    # --- v1.8.4 -------------------------------------------------------------
    # 「太径」はケーブル業界の読みかたに合わせる(太径電線 = ふとけいでんせん)。
    # 「照明」「注入」は 1 文字ずつだと読みが割れる(入 = い / にゅう)ので複合語で登録。
    "太径": "ふとけい", "照明": "しょうめい", "注入": "ちゅうにゅう",
    "移動": "いどう", "水道管": "すいどうかん",
    # ギリシャ文字。かなに開いておかないと「読めない文字」として末尾に飛ばされ、
    # 強化ビーコンの 3 枚が離ればなれに並んでしまう。
    "α": "あるふぁ", "β": "べーた",
    # --- 建材の素材名 -------------------------------------------------------
    "安山岩": "あんざんがん", "磨かれた": "みがかれた", "滑らかな": "なめらかな",
    "深層岩": "しんそうがん", "砂岩": "さがん", "花崗岩": "かこうがん",
    "閃緑岩": "せんりょくがん", "丸石": "まるいし", "黒石": "くろいし",
    "白石": "しろいし", "雲石": "くもいし", "黒曜石縁取り": "こくようせきふちどり",
    "黒曜石": "こくようせき", "天空石": "てんくうせき", "天空": "てんくう",
    "真鍮": "しんちゅう", "赤い": "あかい", "屋根瓦": "やねがわら", "瑠璃": "るり",
    "光輝": "こうき", "金縁": "きんぶち", "金装飾": "きんそうしょく",
    "木製": "もくせい", "鉄製": "てつせい", "鋼製": "こうせい", "縞鋼板": "しまこうはん",
    "金網": "かなあみ", "金庫": "きんこ", "鉄格子": "てつごうし",
    # --- 色 -----------------------------------------------------------------
    "桃色": "ももいろ", "橙色": "だいだいいろ", "灰色": "はいいろ", "薄灰色": "うすはいいろ",
    "白色": "しろいろ", "空色": "そらいろ", "紫色": "むらさきいろ", "緑色": "みどりいろ",
    "茶色": "ちゃいろ", "赤色": "あかいろ", "赤紫色": "あかむらさきいろ",
    "青色": "あおいろ", "青緑色": "あおみどりいろ", "黄色": "きいろ", "黄緑色": "きみどりいろ",
    "黒色": "くろいろ", "赤": "あか",
    # --- 帯(列車の塗装)------------------------------------------------------
    "橙帯": "だいだいおび", "緑帯": "みどりおび", "赤帯": "あかおび",
    "青帯": "あおおび", "黄帯": "きおび",
    # --- 電車 ---------------------------------------------------------------
    "通勤形電車": "つうきんがたでんしゃ", "快速形電車": "かいそくがたでんしゃ",
    "特急形電車": "とっきゅうがたでんしゃ", "超高速列車": "ちょうこうそくれっしゃ",
    "超特急列車": "ちょうとっきゅうれっしゃ", "路面電車": "ろめんでんしゃ",
    "貨物機関車": "かもつきかんしゃ", "貨物車": "かもつしゃ", "客車": "きゃくしゃ",
    "電車": "でんしゃ", "先頭車": "せんとうしゃ", "中間車": "ちゅうかんしゃ",
    # --- v1.9.3: 架線(装飾用の設置アイテム)---------------------------------
    "架線": "かせん",
    # --- 2026-08-17: この日の作業で入った 67 枚のぶん ------------------------
    # ここに足さないと **64 枚が五十音順の外へ落ちる**(警告は出るが生成は通るので、
    # 黙って並びだけが壊れる形になる)。読みは複合語のまま登録する ——
    # 「遮光」+「付き」に割ると「つき」が「月」と同じ扱いになり、色ちがい 51 枚が
    # 「遮光付き〜」でまとまらなくなる。
    "遮光付き": "しゃこうつき",              # 建材: 遮光付き強化ガラス 51 種
    "防護服": "ぼうごふく",                   # 銃: Hazmat Suit
    "定義": "ていぎ",                         # 銃: データ定義銃(Data-Defined Firearm)
    "携行": "けいこう",                       # 乗り物: 携行缶(缶 は登録済み)
    # ⚠ 「空」は 2 通りに読む。「空の携行缶」= そら、「空気清浄機」= くう。
    #    1 文字の「空」を そら にしたうえで、**くう と読むほうを複合語で先に取る**。
    #    (「空色」= そらいろ は既に上で複合語として登録済みなので影響しない。)
    "空気清浄機": "くうきせいじょうき",        # 電力: Air Purifier(V2 §10)
    "空": "そら",
    "鍛冶": "かじ", "祭壇": "さいだん", "核": "かく",   # ボス: 鍛冶祭壇の核
    "霜": "しも",                             # ボス: 霜の祭壇
    "溶融": "ようゆう",                       # ボス: 溶融の王冠
    "原初": "げんしょ",                       # ボス: 原初の卵
    "心臓": "しんぞう",                       # ボス: スカルクの心臓
    "魂血": "こんけつ",                       # ボス: 魂血の祭壇(Soul Blood Altar)
    "冷蔵庫": "れいぞうこ",                    # サバイバル: Refrigerator
    "蛇口": "じゃぐち",                        # サバイバル: Water Tap(口 は くち で登録済み)
    # --- V2.1.0: この回で早見表に初めて出るぶん ------------------------------
    # ⚠ 足さないと **警告は出るが生成は通り、並びだけが黙って壊れる**。
    #    銃工作台は V2.0.0 の時点で jar に入っていたのに、MODS ではなく
    #    再生成をしていなかったせいで今まで表に出ていなかった。
    "工作台": "こうさくだい",                  # 銃: 銃工作台(銃 は じゅう で登録済み)
    # 二相楽園(Planarcadia)。ジャンル名そのものと、その 2 枚のカード。
    "二相楽園": "にそうらくえん",
    "次元": "じげん", "跳躍": "ちょうやく", "壁画": "へきが",  # 次元跳躍の壁画
    # --- 乗り物 -------------------------------------------------------------
    "大型旅客機": "おおがたりょかくき", "大型": "おおがた", "小型": "こがた",
    "平床": "ひらゆか", "箱型": "はこがた", "農業用": "のうぎょうよう",
    "救急車": "きゅうきゅうしゃ", "消防車": "しょうぼうしゃ", "収集車": "しゅうしゅうしゃ",
    # --- 銃 -----------------------------------------------------------------
    "機関部": "きかんぶ", "銃床": "じゅうしょう", "銃身": "じゅうしん",
    "散弾": "さんだん", "小口径弾": "しょうこうけいだん", "自動": "じどう",
    "撃退": "げきたい", "除け": "よけ",
    # --- 建材(設備)---------------------------------------------------------
    "点字": "てんじ", "誘導": "ゆうどう", "警告灯": "けいこくとう", "警告": "けいこく",
    "薄型": "うすがた", "航空障害灯": "こうくうしょうがいとう",
    "車両用信号機": "しゃりょうようしんごうき", "歩行者用信号機": "ほこうしゃようしんごうき",
    "電柱": "でんちゅう", "電線": "でんせん", "腕金付き": "うでがねつき",
    "受信機": "じゅしんき", "発信機": "はっしんき", "防犯": "ぼうはん",
    # --- 銃 v1.8.5(ミサイルランチャーに表示名が付き、弾頭 2 種にレシピが付いた) ---
    "核弾頭": "かくだんとう", "弾頭": "だんとう",
    # --- ドア ---------------------------------------------------------------
    "観音扉": "かんのんとびら", "鏡板": "かがみいた", "無地": "むじ",
    "装飾": "そうしょく", "格子戸": "こうしど", "落とし格子": "おとしごうし",
    "格子": "こうし", "入り": "いり", "山形": "やまがた", "彫り飾り": "ほりかざり",
    "彫刻": "ちょうこく", "鋲打ち": "びょううち", "筋交い": "すじかい",
    "二重扉": "にじゅうとびら", "大扉": "おおとびら", "高扉": "たかとびら",
    "気密扉": "きみつとびら", "隔壁扉": "かくへきとびら", "回転扉風": "かいてんとびらふう",
    "両開き": "りょうびらき", "吹き抜け": "ふきぬけ", "全面": "ぜんめん",
    "枠付き": "わくつき", "巻き上げ": "まきあげ", "片引き戸": "かたびきど",
    "引き戸": "ひきど", "欄間付き": "らんまつき", "板戸": "いたど", "雨戸": "あまど",
    "障子": "しょうじ", "にじり口": "にじりぐち", "隠し": "かくし", "錆びた": "さびた",
    "倉庫": "そうこ", "宝物庫": "ほうもつこ", "格納庫": "かくのうこ", "城門": "じょうもん",
    "教会": "きょうかい", "店舗入口": "てんぽいりぐち", "防火": "ぼうか",
    # --- 天空 ---------------------------------------------------------------
    "天使": "てんし", "王冠": "おうかん", "王族": "おうぞく", "胸当て": "むねあて",
    "脚当て": "あしあて", "孵化装置": "ふかそうち",
    # --- ボス ---------------------------------------------------------------
    "召喚石": "しょうかんせき", "召喚": "しょうかん", "強化": "きょうか",
    "死神": "しにがみ", "大鎌": "おおがま", "灼熱": "しゃくねつ", "虚無": "きょむ",
    "深淵": "しんえん", "墓縛り": "はかしばり", "刈り手": "かりて", "嵐帝": "らんてい",
    # v1.7.4: ペスト医師召喚石。「ペスト」はカタカナで自動変換されるので「医師」だけでよい。
    "医師": "いし",
    # v1.7.7: 列車自動停止ブロック(鉄道)・強化ガラスの窓(建材)・花火人形(サバイバル)。
    # 「列車」「停止」は音便・濁音化があるので 1 文字ずつではなく複合語として登録する
    # (列+車を単純結合すると「れつしゃ」になり「れっしゃ」の促音が抜ける)。
    "列車": "れっしゃ", "停止": "ていし", "窓": "まど",
    "花火": "はなび", "人形": "にんぎょう",
    # 2026-08-04: 建材の「色付きガラス板」17 色(並行作業ラウンドで追加されたレシピ)。
    "色付き": "いろつき",
    # --- サバイバル ---------------------------------------------------------
    "仮面": "かめん", "大盾": "おおだて", "水筒": "すいとう", "真珠": "しんじゅ",
    # --- ジャンル名(検索でジャンルごと絞り込めるように)----------------------
    "銃": "じゅう", "建材": "けんざい", "乗り物": "のりもの",
    # --- バニラの素材(3×3 のマスに出てくる材料。検索でも読みで引けるようにする)--------
    "欠片": "かけら", "原木": "げんぼく", "木材": "もくざい", "板": "いた",
    "棒": "ぼう", "火薬": "かやく", "染料": "せんりょう", "紙": "かみ", "金": "きん",
    "鉄塊": "てっかい", "金塊": "きんかい", "塊": "かたまり", "革": "かわ",
    "羊毛": "ようもう", "骨粉": "こっぷん", "石炭": "せきたん", "鉱石": "こうせき",
    "松明": "たいまつ", "感圧板": "かんあつばん", "羽根": "はね", "糸": "いと",
    "種": "たね", "砂": "すな", "土": "つち", "皮": "かわ", "鎖": "くさり",
    "額縁": "がくぶち", "本": "ほん", "樽": "たる", "旗": "はた", "網": "あみ",
    "銅": "どう", "玉": "たま", "水": "みず", "苔": "こけ", "泥": "どろ",
    # --- V1.7.0: 新規アイテム(ドロップ・購入・構造物内で見つかるもの)-----------
    # これらは「入手方法」カードとして SPECIAL_ITEMS に載る。読みが無いと
    # あいうえお順から外れて WARNING で名指しされるので、ここに足しておく。
    "襲撃": "しゅうげき", "角笛": "つのぶえ",
    "万物": "ばんぶつ", "採集器": "さいしゅうき",
    "特別": "とくべつ",
    "物件": "ぶっけん", "権利": "けんり", "証書": "しょうしょ",
    "不動産": "ふどうさん", "台帳": "だいちょう",
    "食料品": "しょくりょうひん", "棚": "たな",
    "攻城": "こうじょう", "大槌": "おおづち",
    # --- V1.7.0: 食料品 300 種(シンガポール都市国家の店で買う)-----------------
    # 下の表は「実際の ja_jp.json に現れる漢字の連なり」を機械的に洗い出して作った
    # (tools 側で正規表現で抽出 -> 全件に読みを付けた)。長い語から順に当たるので、
    # 複合語をそのまま登録してある = 1 文字ずつに割れて誤読になることがない。
    "乳酸菌飲料": "にゅうさんきんいんりょう", "冷凍白身魚": "れいとうしろみざかな",
    "低脂肪乳": "ていしぼうにゅう", "冷凍層状": "れいとうそうじょう",
    "冷凍春巻": "れいとうはるまき", "冷凍枝豆": "れいとうえだまめ",
    "冷凍餃子": "れいとうぎょうざ", "大麦飲料": "おおむぎいんりょう",
    "木綿豆腐": "もめんどうふ", "甘口醤油": "あまくちしょうゆ",
    "豆乳飲料": "とうにゅういんりょう", "五香粉": "ごこうふん",
    "全粒粉": "ぜんりゅうふん", "即席麺": "そくせきめん", "叉焼飯": "ちゃーしゅーはん",
    "大根餅": "だいこんもち", "大麦水": "おおむぎみず", "大麦茶": "おおむぎちゃ",
    "小豆氷": "あずきごおり", "手羽先": "てばさき", "料理用": "りょうりよう",
    "板菓子": "いたがし", "氷砂糖": "こおりざとう", "生姜茶": "しょうがちゃ",
    "生春巻": "なまはるまき", "空芯菜": "くうしんさい", "菊花茶": "きっかちゃ",
    "薄力粉": "はくりきこ", "車海老": "くるまえび", "酸梅湯": "さんばいとう",
    "下味": "したあじ", "丸鶏": "まるどり", "乾麺": "かんめん", "仙草": "せんそう",
    "冷凍": "れいとう", "加糖": "かとう", "卵麺": "たまごめん", "叉焼": "ちゃーしゅー",
    "味付": "あじつけ", "団子": "だんご", "塩卵": "しおたまご", "塩漬": "しおづけ",
    "小分": "こわけ", "小粒": "こつぶ", "層状": "そうじょう", "平打": "ひらうち",
    "惣菜": "そうざい", "果物": "くだもの", "椎茸": "しいたけ", "海苔": "のり",
    "涼茶": "りょうちゃ", "濃厚": "のうこう", "焼豚": "やきぶた", "煮干": "にぼし",
    "煮込": "にこみ", "牛乳": "ぎゅうにゅう", "牛肉": "ぎゅうにく", "玄米": "げんまい",
    "発酵": "はっこう", "白貝": "しろがい", "箱入": "はこいり", "米菓": "べいか",
    "米麺": "こめめん", "粗塩": "あらじお", "緑茶": "りょくちゃ", "缶入": "かんいり",
    "缶詰": "かんづめ", "腸粉": "ちょうふん", "菓子": "かし", "薬膳": "やくぜん",
    "角煮": "かくに", "豆乳": "とうにゅう", "豆入": "まめいり", "豆花": "とうふぁ",
    "豚肋": "ぶたあばら", "豚足": "とんそく", "貝柱": "かいばしら", "身入": "みいり",
    "身包": "みつつみ", "醤油": "しょうゆ", "野菜": "やさい", "風味": "ふうみ",
    "飲料": "いんりょう", "餃子": "ぎょうざ", "鴨飯": "かもめし", "鶏卵": "けいらん",
    "鶏飯": "けいはん", "麦芽": "ばくが",
    "串": "くし", "切": "きり", "合": "ごう", "和": "わ", "実": "み", "巻": "まき",
    "干": "ほし", "引": "ひき", "房": "ふさ", "折": "おり", "揚": "あげ", "板": "いた",
    "梅": "うめ", "油": "あぶら", "炊": "たき", "炒": "いため", "焼": "やき",
    "煎": "いり", "牛": "ぎゅう", "物": "もの", "甘": "あま", "生": "なま",
    "白": "しろ", "盛": "もり", "箱": "はこ", "米": "こめ", "粉": "こな",
    "粥": "かゆ", "缶": "かん", "肉": "にく", "茶": "ちゃ", "茹": "ゆで",
    "葉": "は", "蒸": "むし", "蓮": "はす", "豚": "ぶた", "身": "み", "込": "こみ",
    "青": "あお", "風": "かぜ", "食": "しょく", "飯": "めし", "飲": "のみ",
    "香": "こう", "魚": "さかな", "鶏": "とり", "麺": "めん",
    # --- v1.8.0: 建材の自動仕分けブロック 9 種+フィルター記憶カード ------------
    # 「振り分け」「仕分」は 1 文字ずつに割ると読みが崩れる(分 = ぶん/わけ の
    # どちらにもなる)ので、複合語のまま登録して最長一致に勝たせる。
    "振り分け": "ふりわけ", "仕分": "しわ", "分配": "ぶんぱい",
    "集荷": "しゅうか", "計数": "けいすう", "搬送": "はんそう",
    "在庫": "ざいこ", "表示": "ひょうじ", "廃棄": "はいき", "装置": "そうち",
    "記憶": "きおく", "防止": "ぼうし", "溢": "あふ", "弁": "べん", "器": "き",
    # --- OUKA V1.3.0「The Washitsu Architectural Masterpiece」(2026-09-29 に用意し、公開のコミットで足す)。
    #     和室 30 種と工業化 第 2 弾の 13 種、合わせて 43 枚。読みは jar の ja_jp の表示名から。足さないと 43 枚とも
    #     「未登録の文字」の警告のまま五十音順の**間違った場所**に並ぶ(Cherry V1.2.0 の 4 枚と同じ)。1 字ずつでは
    #     読みが崩れる語(縁側・長押・行灯・雪見灯籠・金箔・生け花・抹茶・重箱 など)は、複合語のまま登録して
    #     最長一致に勝たせる。1 字の読みは、表に無かった字(93 字)の控え。 ---
    # 和室 01–06(床と建築)
    "藺草仕立て": "いぐさじたて", "藺草": "いぐさ", "仕立て": "したて", "藺": "い", "草": "くさ",
    "仕": "し", "畳": "たたみ", "市松畳": "いちまつだたみ", "桧": "ひのき", "磨": "みが",
    "縁側": "えんがわ", "側": "がわ",
    "杉": "すぎ", "目": "め", "透": "す", "天井": "てんじょう", "天": "てん", "井": "い",
    "聚楽": "じゅらく", "聚": "じゅ", "楽": "らく", "壁": "かべ", "鴨居": "かもい", "鴨": "かも",
    "居": "い", "長押": "なげし", "押": "おし",
    # 和室 07–12(建具)
    "金箔": "きんぱく", "箔": "はく", "山水": "さんすい", "山": "やま", "襖": "ふすま",
    "欄間": "らんま", "欄": "らん", "間": "ま", "透かし彫り": "すかしぼり", "彫": "ほ",
    "四曲": "よんきょく", "四": "よん", "曲": "きょく", "金屏風": "きんびょうぶ",
    "屏風": "びょうぶ", "屏": "びょう", "竹簾": "たけすだれ", "竹": "たけ", "簾": "すだれ",
    "藍染": "あいぞめ", "藍": "あい", "家紋": "かもん", "家": "いえ", "紋": "もん",
    "暖簾": "のれん", "暖": "だん",
    # 工業化 第 2 弾(I-01〜I-10)
    "転送": "てんそう", "転": "てん", "共振": "きょうしん", "共": "きょう", "振": "しん",
    "直結": "ちょっけつ", "直": "ちょく", "結": "けつ", "火山": "かざん", "熱水": "ねっすい",
    "造石": "ぞうせき", "造": "ぞう", "生体": "せいたい", "粉砕": "ふんさい", "砕": "さい",
    "同期": "どうき", "同": "どう", "期": "き", "端末": "たんまつ", "端": "たん",
    # 和室 13–18(調度)
    "欅": "けやき", "無垢": "むく", "無": "む", "垢": "あか", "座卓": "ざたく", "座": "ざ",
    "卓": "たく", "錦": "にしき", "織": "おり", "座布団": "ざぶとん", "布団": "ふとん", "布": "ぬの",
    "団": "だん",
    "殿様": "とのさま", "殿": "との", "様": "さま", "脇息": "きょうそく", "脇": "わき",
    "息": "いき", "座椅子": "ざいす", "椅子": "いす", "椅": "い", "漆": "うるし", "金具": "かなぐ",
    "具": "ぐ", "桐箪笥": "きりだんす", "箪笥": "たんす", "桐": "きり", "箪": "たん", "笥": "す",
    "茶筅": "ちゃせん", "筅": "せん", "抹茶碗": "まっちゃわん", "抹茶": "まっちゃ", "抹": "まつ",
    "碗": "わん", "塗": "ぬ", "重箱": "じゅうばこ",
    # 和室 19–30(床の間・灯り・庭)
    "絞り": "しぼり", "丸太": "まるた", "丸": "まる", "床柱": "とこばしら", "四季": "しき",
    "掛": "か", "竹筒": "たけづつ", "筒": "つつ", "生け花": "いけばな", "花": "はな",
    "二本掛け": "にほんがけ", "二": "に", "刀掛け": "かたなかけ", "刀": "かたな", "青磁": "せいじ",
    "伽羅": "きゃら", "伽": "か", "羅": "ら", "銘木": "めいぼく", "銘": "めい", "水石": "すいせき",
    "行灯": "あんどん", "行": "こう", "六角": "ろっかく", "六": "ろく", "雪洞": "ぼんぼり",
    "雪": "ゆき", "洞": "どう", "御影石": "みかげいし", "御影": "みかげ", "御": "お", "影": "かげ",
    "雪見灯籠": "ゆきみどうろう", "雪見": "ゆきみ", "見": "み", "灯籠": "とうろう", "籠": "かご",
    "庭園": "ていえん", "庭": "にわ", "園": "えん", "鹿威し": "ししおどし", "鹿": "しか",
    "威": "い", "鉄器": "てっき", "風鈴": "ふうりん", "鈴": "すず", "榧": "かや", "碁盤": "ごばん",
    "碁": "ご",
    "盤": "ばん", "将棋盤": "しょうぎばん", "将棋": "しょうぎ", "将": "しょう", "棋": "ぎ",
    # --- OUKA V1.4.0「The Kinetic Overdrive」(2026-10-05 に用意し、公開のコミットで足す)。銃 15 + 弾 6 + 部品 14 + 風力発電機 + シェルターガラス 7 = 43 枚。
    #     読みは jar の ja_jp の表示名から。「」(銘を囲む括弧)は読みなし、ひと文字の銘(鏡・灯・重)は括弧ごと登録して読みを決める
    #     (重 = かさね、灯 = あかり、鏡 = かがみ。1 字の重・灯・鏡 は別の読みで既にある)。足さないと 43 枚とも「未登録の文字」の警告のまま
    #     五十音順の間違った場所に並ぶ。 ---
    "「": "", "」": "", "「重」": "かさね", "「鏡」": "かがみ", "「灯」": "あかり", "風神": "ふうじん", "草薙": "くさなぎ",
    "薙": "なぎ", "雷神": "らいじん", "雷切": "らいきり", "突撃": "とつげき", "突": "とつ", "撃": "げき", "不動": "ふどう",
    "不": "ふ", "動": "どう", "迦具土": "かぐつち", "迦": "か", "隼": "はやぶさ", "連射": "れんしゃ", "連": "れん",
    "短": "たん", "村正": "むらまさ", "村": "むら", "正": "まさ", "二口径": "にこうけい", "径": "けい", "浪人": "ろうにん",
    "浪": "ろう", "人": "にん", "竜巻": "たつまき", "竜": "たつ", "鬼火": "おにび", "鬼": "おに", "横一文字": "よこいちもんじ",
    "横": "よこ", "一": "いち", "文": "もん", "字": "じ", "小次郎": "こじろう", "小": "しょう", "次": "じ", "郎": "ろう",
    "大口径": "だいこうけい", "大": "だい", "月光": "げっこう", "月": "げつ", "増幅": "ぞうふく", "増": "ぞう", "幅": "ふく",
    "狙撃": "そげき", "狙": "そ", "須佐之男": "すさのお", "須": "す", "佐": "さ", "之": "の", "男": "おとこ",
    "神話": "しんわ", "神": "かみ", "話": "わ", "三星": "みつぼし", "三連": "さんれん", "三": "さん", "星": "ほし",
    "雀蜂": "すずめばち", "蜂": "はち", "戦術": "せんじゅつ", "戦": "せん", "術": "じゅつ", "蛍": "ほたる", "鳶": "とび",
    "倍": "ばい", "可変": "かへん", "可": "か", "変": "へん", "陽炎": "かげろう", "炎": "えん", "楔": "くさび",
    "霞": "かすみ", "囁": "ささやき", "亜": "あ", "音": "おん", "燕": "つばめ", "疾風": "はやて", "疾": "しつ",
    "早抜き": "はやぬき", "早": "はや", "抜": "ぬ", "拡張": "かくちょう", "拡": "かく", "太鼓": "たいこ", "鼓": "こ",
    "巌": "いわお", "安定": "あんてい", "安": "あん", "定": "てい", "照準": "しょうじゅん", "照": "しょう", "準": "じゅん",
    # OUKA V1.6.0(和室の調度 50 と敷居、重工業の機械 30 と素材 32)
    "溝つき桧の敷居": "みぞつきひのきのしきい",
    "枝折戸": "しおりど",
    "蹲": "つくばい",
    "筧": "かけい",
    "水琴窟": "すいきんくつ",
    "井筒と釣瓶": "いづつとつるべ",
    "朱塗り欄干": "しゅぬりらんかん",
    "置灯籠": "おきどうろう",
    "提灯": "ちょうちん",
    "ガラス風鈴": "がらすふうりん",
    "琴": "こと",
    "門松": "かどまつ",
    "達磨": "だるま",
    "鯉のぼり": "こいのぼり",
    "積み布団": "つみふとん",
    "菱格子障子": "ひしごうししょうじ",
    "雪見障子": "ゆきみしょうじ",
    "太鼓襖": "たいこふすま",
    "御簾": "みす",
    "千本格子戸": "せんぼんごうしど",
    "麻の葉組子障子": "あさのはくみこしょうじ",
    "格子窓": "こうしまど",
    "丸窓": "まるまど",
    "衝立": "ついたて",
    "螺鈿細工文机": "らでんざいくふづくえ",
    "銘木違い棚": "めいぼくちがいだな",
    "花梨の一枚板飾り台": "かりんのいちまいいたかざりだい",
    "純金茶釜": "じゅんきんちゃがま",
    "青銅製釣灯籠": "せいどうせいつりどうろう",
    "枕屏風": "まくらびょうぶ",
    "衣桁": "いこう",
    "見台": "けんだい",
    "お膳": "おぜん",
    "徳利と盃": "とっくりとさかずき",
    "床框": "とこがまち",
    "付書院": "つけしょいん",
    "囲炉裏": "いろり",
    "自在鉤と鉄鍋": "じざいかぎとてつなべ",
    "火鉢": "ひばち",
    "白砂利波紋": "しろじゃりはもん",
    "砂紋の縁石": "さもんのふちいし",
    "立石・三尊石組": "たていしさんぞんいしぐみ",
    "立石(高)": "たていしこう",
    "飛石": "とびいし",
    "敷石": "しきいし",
    "苔山": "こけやま",
    "竹垣(密)": "たけがきみつ",
    "四ツ目垣": "よつめがき",
    "人工太陽磁気核融合炉": "じんこうたいようじきかくゆうごうろ",
    "高温溶融塩熱交換タワー": "こうおんようゆうえんねっこうかんたわー",
    "工業用蓄電フライホイール": "こうぎょうようちくでんふらいほいーる",
    "強制通風冷却塔": "きょうせいつうふうれいきゃくとう",
    "プラント統括制御盤": "ぷらんととうかつせいぎょばん",
    "真空ポンプ": "しんくうぽんぷ",
    "ガス圧縮機": "がすあっしゅくき",
    "冷却材循環ポンプ": "れいきゃくざいじゅんかんぽんぷ",
    "超音速ジェットミル粉砕機": "ちょうおんそくじぇっとみるふんさいき",
    "極低温電解酸素精製機": "きょくていおんでんかいさんそせいせいき",
    "タングステン原石": "たんぐすてんげんせき",
    "タングステンの粉": "たんぐすてんのこな",
    "タングステンの板": "たんぐすてんのいた",
    "超高純度チタンのインゴット": "ちょうこうじゅんどちたんのいんごっと",
    "チタンの板": "ちたんのいた",
    "鉄の超微粉": "てつのちょうびふん",
    "銅の超微粉": "どうのちょうびふん",
    "金の超微粉": "きんのちょうびふん",
    "チタンの超微粉": "ちたんのちょうびふん",
    "タングステンの超微粉": "たんぐすてんのちょうびふん",
    "炭化タングステンの鋳片": "たんかたんぐすてんのちゅうへん",
    "炭化タングステンの板": "たんかたんぐすてんのいた",
    "液体酸素の缶": "えきたいさんそのかん",
    "希ガスの缶": "きがすのかん",
    "アルゴンの缶": "あるごんのかん",
    "重水素セル": "じゅうすいそせる",
    "合成ガスの缶": "ごうせいがすのかん",
    "灯油の缶": "とうゆのかん",
    "ガソリンの缶": "がそりんのかん",
    "耐火レンガ": "たいかれんが",
    "触媒ペレット": "しょくばいぺれっと",
    "硝酸塩": "しょうさんえん",
    "微細回路基板": "びさいかいろきばん",
    "量子チップ": "りょうしちっぷ",
    "精密モジュール": "せいみつもじゅーる",
    "超伝導コイル": "ちょうでんどうこいる",
    "電解銅板": "でんかいどうばん",
    "単結晶引き上げ炉": "たんけっしょうひきあげろ",
    "連続レーザーアブレーション加工機": "れんぞくれーざーあぶれーしょんかこうき",
    "高圧イオン注入機": "こうあついおんちゅうにゅうき",
    "自動キャリブレーションマニピュレータ": "じどうきゃりぶれーしょんまにぴゅれーた",
    "触媒熱化学溶鉱炉": "しょくばいねつかがくようこうろ",
    "真空焼結炉": "しんくうしょうけつろ",
    "熱間等方圧加圧機": "ねっかんとうほうあつかあつき",
    "回転式焼成炉": "かいてんしきしょうせいろ",
    "超伝導コイル巻線機": "ちょうでんどうこいるまきせんき",
    "重力遠心気相分離塔": "じゅうりょくえんしんきそうぶんりとう",
    "重水電解濃縮槽": "じゅうすいでんかいのうしゅくそう",
    "高圧熱分解炭素重合機": "こうあつねつぶんかいたんそじゅうごうき",
    "電解精錬槽": "でんかいせいれんそう",
    "触媒造粒機": "しょくばいぞうりゅうき",
    "超伝導精留塔": "ちょうでんどうせいりゅうとう",
    "プラズマアーク廃棄物分解炉": "ぷらずまあーくはいきぶつぶんかいろ",
    "合成ガス触媒反応器": "ごうせいがすしょくばいはんのうき",
    "ガスタービン発電機": "がすたーびんはつでんき",
    "配管点検ドローンステーション": "はいかんてんけんどろーんすてーしょん",
}

# 最長一致のための索引(先頭文字 -> その文字で始まるキーを長い順に)。
_YOMI_INDEX = {}
for _k in YOMI:
    _YOMI_INDEX.setdefault(_k[0], []).append(_k)
for _v in _YOMI_INDEX.values():
    _v.sort(key=len, reverse=True)

# 五十音の基準列。「ん」は最後。
GOJUON = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわゐゑをん"
_GOJUON_INDEX = {c: i for i, c in enumerate(GOJUON)}

# ひらがな -> (清音の基準文字, 濁点ランク, 小書きランク)
# 濁点ランク: 0=清音 1=濁音 2=半濁音 / 小書きランク: 0=直音 1=拗音・促音
_KANA_DECOMP = {c: (c, 0, 0) for c in GOJUON}
for _voiced, _plain in zip("がぎぐげござじずぜぞだぢづでどばびぶべぼゔ",
                           "かきくけこさしすせそたちつてとはひふへほう"):
    _KANA_DECOMP[_voiced] = (_plain, 1, 0)
for _p, _plain in zip("ぱぴぷぺぽ", "はひふへほ"):
    _KANA_DECOMP[_p] = (_plain, 2, 0)
for _small, _large in zip("ぁぃぅぇぉっゃゅょゎゕゖ", "あいうえおつやゆよわかけ"):
    _base, _voice, _ = _KANA_DECOMP[_large]
    _KANA_DECOMP[_small] = (_base, _voice, 1)

# 長音符「ー」を直前の音の母音に開くための表(国語辞典の慣例: カー = カア)。
_VOWEL_OF = {}
for _i, _c in enumerate("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもらりるれろ"):
    _VOWEL_OF[_c] = "あいうえお"[_i % 5]
_VOWEL_OF.update({"や": "あ", "ゆ": "う", "よ": "お",
                  "わ": "あ", "ゐ": "い", "ゑ": "え", "を": "お", "ん": "ん"})


def kana_fold(s):
    """カタカナをひらがなに畳む(長音符「ー」はそのまま)。検索・読みの共通前処理。"""
    out = []
    for ch in s:
        o = ord(ch)
        if 0x30A1 <= o <= 0x30F6:          # ァ..ヶ
            out.append(chr(o - 0x60))
        else:
            out.append(ch)
    return "".join(out)


def search_norm(s):
    """検索用の正規化。JS 側の norm() と **同じ規則**でなければ検索が外れる。
    ①小文字化 ②全角 ASCII -> 半角 ③全角スペース -> 半角 ④カタカナ -> ひらがな。
    """
    s = s.lower()
    out = []
    for ch in s:
        o = ord(ch)
        if 0xFF01 <= o <= 0xFF5E:
            out.append(chr(o - 0xFEE0))
        elif o == 0x3000:
            out.append(" ")
        elif 0x30A1 <= o <= 0x30F6:
            out.append(chr(o - 0x60))
        else:
            out.append(ch)
    return "".join(out)


def reading_of(name):
    """表示名の読み(ひらがな)を返す。戻り値: (読み, 読めなかった文字のリスト)。

    かな・英数字・記号はそのまま(カタカナはひらがなへ)。漢字は YOMI 表の最長一致。
    表に無い漢字は **そのまま残したうえで報告する** ので、黙って間違った順に並ぶことはない。
    """
    out = []
    unknown = []
    i = 0
    n = len(name)
    while i < n:
        hit = None
        for key in _YOMI_INDEX.get(name[i], ()):
            if name.startswith(key, i):
                hit = key
                break
        if hit:
            out.append(YOMI[hit])
            i += len(hit)
            continue
        ch = name[i]
        o = ord(ch)
        if 0x30A1 <= o <= 0x30F6:            # カタカナ
            out.append(chr(o - 0x60))
        elif 0x3041 <= o <= 0x3096 or ch in "ー":
            out.append(ch)
        elif ch.isascii() or ch in "()（）×・、。〜 　∞✦":
            out.append(ch)
        else:                                 # 未登録の漢字など
            unknown.append(ch)
            out.append(ch)
        i += 1
    return "".join(out), unknown


def _expand_choon(yomi):
    """「ー」を直前の音の母音に開く(レーザー -> れえざあ)。辞書の並べ方に合わせる。"""
    out = []
    for ch in yomi:
        if ch == "ー":
            prev = out[-1] if out else ""
            base = _KANA_DECOMP.get(prev, (prev, 0, 0))[0]
            v = _VOWEL_OF.get(base)
            if v:
                out.append(v)
            continue
        out.append(ch)
    return "".join(out)


def gojuon_key(name):
    """五十音順の比較キーを作る。文字ごとに (種別, 位置, 濁点, 小書き) の組を並べる。

    種別: 0=記号・空白 / 1=数字 / 2=英字 / 3=かな / 4=読めなかった文字(最後に回す)
    → 数字・英字(ATM, SUV, REX ...)が先、次にかな。同じ音なら 清音 < 濁音 < 半濁音、
      直音 < 拗音。最後に元の文字列を足して同点を無くす(実行ごとに順が変わらない)。
    """
    yomi, _unknown = reading_of(name)
    key = []
    for ch in _expand_choon(kana_fold(yomi)):
        d = _KANA_DECOMP.get(ch)
        if d:
            base, voice, small = d
            key.append((3, _GOJUON_INDEX[base], voice, small))
        elif ch.isdigit() and ch.isascii():
            key.append((1, ord(ch), 0, 0))
        elif ch.isalpha() and ch.isascii():
            key.append((2, ord(ch.lower()), 0, 0))
        elif ch.isascii() or ch in "()（）×・、。〜　":
            key.append((0, ord(ch), 0, 0))
        else:
            key.append((4, ord(ch), 0, 0))
    return key, name


def compose_chest_icon(zf):
    """The chest has no flat texture (it's an entity-rendered block whose 64x64 UV
    atlas lives at entity/chest/normal.png). Compose a recognizable 16x16 front view
    from the atlas regions (lid front + body front + latch), script-reproducibly."""
    import io
    from PIL import Image
    atlas = Image.open(io.BytesIO(zf.read("assets/minecraft/textures/entity/chest/normal.png"))).convert("RGBA")
    icon = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    lid_front = atlas.crop((14, 15, 28, 20))    # 14x5
    body_front = atlas.crop((14, 33, 28, 43))   # 14x10
    icon.paste(lid_front, (1, 1))
    icon.paste(body_front, (1, 6))
    latch = atlas.crop((1, 1, 3, 5))            # 2x4 latch strip
    icon.paste(latch, (7, 4))
    buf = io.BytesIO()
    icon.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def load_vanilla_zip():
    if not VANILLA_CLIENT_JAR.exists():
        raise SystemExit(f"vanilla client jar not found at {VANILLA_CLIENT_JAR} - run a gradle build first")
    return zipfile.ZipFile(VANILLA_CLIENT_JAR)


def compose_skull_icon(zf, entity_texture):
    """頭部エンティティ(ウィザースケルトンの頭など)のアイコンを合成する。

    頭系のアイテムは item/*.png を持たない — ゲーム内ではエンティティモデルとして描かれるため。
    スキン画像の「頭の正面」(8,8)-(16,16) と、その上に重なる帽子レイヤー (40,8)-(48,8+8) を
    切り出して重ね、16px に拡大する。バニラのスキン UV 規約そのままで、推測値ではない。
    """
    from PIL import Image
    import io
    src = Image.open(io.BytesIO(zf.read(entity_texture))).convert("RGBA")
    face = src.crop((8, 8, 16, 16))
    hat = src.crop((40, 8, 48, 16))
    face.alpha_composite(hat)
    out = face.resize((16, 16), Image.NEAREST)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def compose_shield_icon(zf):
    """バニラの盾のアイコンを合成する(v1.5.0: 大盾のレシピ素材)。

    盾は item/shield.png を持たない — 実体モデル(ShieldModel)として描かれるため。
    無地の盾のテクスチャ entity/shield/shield_base_nopattern.png から、盾板(12x22x1、
    texOffs(0,0))の<b>正面</b>にあたる矩形 (1,1)-(13,23) を切り出す。これはバニラの
    箱 UV 規約(正面 = u[d, d+w], v[d, d+h])そのままで、目分量ではない。
    16x16 のセルに縦横比を保って収める。
    """
    from PIL import Image
    import io
    src = Image.open(io.BytesIO(zf.read(
        "assets/minecraft/textures/entity/shield/shield_base_nopattern.png"))).convert("RGBA")
    plate = src.crop((1, 1, 13, 23))                      # 12x22 の盾板の正面
    scaled = plate.resize((9, 16), Image.NEAREST)         # 縦を 16 に合わせる(12:22 ≒ 9:16)
    out = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    out.paste(scaled, (4, 0))
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# 頭系アイテム -> 元になるエンティティテクスチャ。
SKULL_ENTITY_TEXTURE = {
    "wither_skeleton_skull": "assets/minecraft/textures/entity/skeleton/wither_skeleton.png",
    "skeleton_skull": "assets/minecraft/textures/entity/skeleton/skeleton.png",
}


def compose_water_bottle_icon(zf):
    """The icon of a Water Bottle, composed from the client jar (2026-10-05, for Tsubomi's herbal tea).

    The vanilla potion item is two layers (models/item/potion.json): layer0 = potion_overlay (the liquid, grey)
    tinted by the item definition's potion tint, layer1 = potion (the glass bottle) untinted. Water has no
    effect colour, so the tint is the definition's own default. Nothing is typed here: the layer names and the
    tint come out of the jar, and a jar that changes either stops the generation instead of drawing a wrong
    bottle."""
    from PIL import Image
    model = json.loads(zf.read("assets/minecraft/models/item/potion.json").decode("utf-8"))
    tex = model["textures"]
    if list(tex) != ["layer0", "layer1"]:
        raise SystemExit("ERROR: models/item/potion.json no longer has exactly layer0 + layer1 (%s) - the "
                         "water bottle icon cannot be composed as before." % list(tex))
    tints = json.loads(zf.read("assets/minecraft/items/potion.json").decode("utf-8"))["model"]["tints"]
    if len(tints) != 1 or tints[0].get("type") != "minecraft:potion" or "default" not in tints[0]:
        raise SystemExit("ERROR: items/potion.json no longer carries one potion tint with a default.")
    argb = tints[0]["default"] & 0xFFFFFFFF
    r, g, b = (argb >> 16) & 255, (argb >> 8) & 255, argb & 255

    def load(ref):
        ns, name = ref.split(":", 1)
        return Image.open(io.BytesIO(zf.read(f"assets/{ns}/textures/{name}.png"))).convert("RGBA")
    liquid, bottle = load(tex["layer0"]), load(tex["layer1"])
    px = liquid.load()
    for y in range(liquid.height):
        for x in range(liquid.width):
            pr, pg, pb, pa = px[x, y]
            px[x, y] = (pr * r // 255, pg * g // 255, pb * b // 255, pa)
    liquid.alpha_composite(bottle)
    buf = io.BytesIO()
    liquid.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def compose_grass_tinted_icon(zf, name):
    """An item whose definition tints its one layer with the grass colour (tall grass): the layer times the
    colormap colour at the definition's own temperature and downfall, as the game draws it. Read from the jar;
    a definition of another shape stops the generation instead of drawing a grey plant."""
    from PIL import Image
    node = json.loads(zf.read(f"assets/minecraft/items/{name}.json").decode("utf-8"))["model"]
    tints = node.get("tints") or []
    if node.get("type") != "minecraft:model" or len(tints) != 1 or tints[0].get("type") != "minecraft:grass":
        raise SystemExit(f"ERROR: items/{name}.json is no longer one model with one grass tint.")
    model = json.loads(zf.read("assets/minecraft/models/" + node["model"].split(":", 1)[1] + ".json").decode("utf-8"))
    layer = model["textures"]["layer0"].split(":", 1)[-1]
    temp = min(max(float(tints[0]["temperature"]), 0.0), 1.0)
    down = min(max(float(tints[0]["downfall"]), 0.0), 1.0) * temp
    cmap = Image.open(io.BytesIO(zf.read("assets/minecraft/textures/colormap/grass.png"))).convert("RGB")
    cr, cg, cb = cmap.getpixel((int((1.0 - temp) * 255), int((1.0 - down) * 255)))
    img = Image.open(io.BytesIO(zf.read(f"assets/minecraft/textures/{layer}.png"))).convert("RGBA")
    px = [(r * cr // 255, g * cg // 255, b * cb // 255, a) for r, g, b, a in img.getdata()]
    img.putdata(px)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


GRASS_TINTED_ITEMS = {"tall_grass"}


def vanilla_texture_b64(zf, name):
    if name in GRASS_TINTED_ITEMS:
        return compose_grass_tinted_icon(zf, name)
    if name == "chest":
        return compose_chest_icon(zf)
    if name == "shield":
        try:
            return compose_shield_icon(zf)
        except (KeyError, OSError) as exc:
            print(f"WARNING: could not compose shield icon: {exc}")
    skull = SKULL_ENTITY_TEXTURE.get(name)
    if skull:
        try:
            return compose_skull_icon(zf, skull)
        except (KeyError, OSError) as exc:
            print(f"WARNING: could not compose skull icon for {name}: {exc}")
    override = VANILLA_TEXTURE_OVERRIDE.get(name)
    candidates = [override] if override else [f"item/{name}", f"block/{name}"]
    for c in candidates:
        path = f"assets/minecraft/textures/{c}.png"
        try:
            data = zf.read(path)
            return base64.b64encode(data).decode()
        except KeyError:
            continue
    print(f"WARNING: no vanilla texture found for {name}")
    return None


TEXTURE_KEY_PREFERENCE = ["particle", "top", "front", "end", "wool", "north", "all", "side", "tex"]

_VANILLA_ZIP = None


def vanilla_zip():
    """公式クライアント jar を 1 回だけ開いて使い回す(カードごとに開き直さない)。"""
    global _VANILLA_ZIP
    if _VANILLA_ZIP is None:
        _VANILLA_ZIP = load_vanilla_zip()
    return _VANILLA_ZIP


_VANILLA_ITEM_TAG_CACHE = {}


def vanilla_item_tag(name, _seen=None):
    """`#minecraft:<name>` を **公式 jar の中のタグ定義**から実アイテム id の並びに開く。

    2026-08-17 に必要になった。`sorakaze_vehicles:gasoline` が材料に
    `#minecraft:coals` を使いはじめ、`register()` の「未知の名前空間」の枝に落ちて
    **カードの 4 マスが `#minecraft:coals` という生の文字とアイコン無しの空欄**になった
    (生成は WARNING だけで通る = 黙って劣化する形。あの枝の注記が
    「今は存在しないが、現れたら」と書いていた当のものが現れた)。

    出典は**バニラの jar 1 つだけ**である。ここにタグの中身を書き写さない ——
    写した瞬間に、Mojang がタグを変えた日に早見表だけが嘘になる。
    入れ子の `#...` 参照は再帰で開く。**取れなければ生成を止める**:
    材料の分からないレシピを出すより、生成を落としたほうがよい。
    """
    if name in _VANILLA_ITEM_TAG_CACHE:
        return _VANILLA_ITEM_TAG_CACHE[name]
    seen = _seen or set()
    if name in seen:
        raise SystemExit("ERROR: vanilla item tag #minecraft:%s refers to itself (cycle)" % name)
    seen.add(name)
    path = "data/minecraft/tags/item/%s.json" % name
    try:
        raw = vanilla_zip().read(path)
    except KeyError:
        raise SystemExit(
            "ERROR: a recipe uses the vanilla item tag #minecraft:%s, but %s is not in the "
            "client jar (%s). Either the tag was renamed in this Minecraft version or the "
            "recipe has a typo - a card with an unresolvable ingredient must not ship."
            % (name, path, VANILLA_CLIENT_JAR))
    out = []
    for v in json.loads(raw.decode("utf-8"))["values"]:
        vid = v["id"] if isinstance(v, dict) else v
        if vid.startswith("#"):
            out.extend(vanilla_item_tag(vid.split(":", 1)[1], seen))
        elif vid not in out:
            out.append(vid)
    if not out:
        raise SystemExit(
            "ERROR: vanilla item tag #minecraft:%s resolved to nothing - the card would show "
            "an empty slot where an ingredient belongs" % name)
    _VANILLA_ITEM_TAG_CACHE[name] = out
    return out


def crop_to_used_uv(assets, name, png_path):
    """アイテムモデルが**実際に使っている uv の範囲**にテクスチャを切り詰める。

    v1.5.4 の仮面 2 種は 128x128 の中に「顔のキャンバス + 裏面用の小さなパッチ +
    余白」が同居する UV アトラスである。そのまま貼ると早見表のアイコンに
    **未使用の暗い帯**が写り込む。ここではモデル JSON の north 面の uv を
    実際に走査して、絵がある矩形だけを切り出す(目分量の定数ではない)。

    16px の普通のアイテムは uv が 0..16 いっぱいなので、この関数は何もしない。
    """
    model_path = assets / "models/item" / f"{name}.json"
    if not model_path.exists():
        return None
    try:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    els = model.get("elements") or []
    if not els:
        return None
    u0 = v0 = 16.0
    u1 = v1 = 0.0
    for el in els:
        face = (el.get("faces") or {}).get("north")
        if not face or "uv" not in face:
            continue
        a, b, c, d = face["uv"]
        u0, u1 = min(u0, a, c), max(u1, a, c)
        v0, v1 = min(v0, b, d), max(v1, b, d)
    if u1 <= u0 or v1 <= v0 or (u0 <= 0.01 and v0 <= 0.01 and u1 >= 15.99 and v1 >= 15.99):
        return None
    from PIL import Image
    import io
    with Image.open(png_path) as img:
        w, h = img.size
        box = (int(u0 / 16.0 * w), int(v0 / 16.0 * h),
               max(int(u1 / 16.0 * w), int(u0 / 16.0 * w) + 1),
               max(int(v1 / 16.0 * h), int(v0 / 16.0 * h) + 1))
        out = img.convert("RGBA").crop(box)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _png_b64_for_ref(ref, default_ns):
    """`ns:textures/以下のパス` 1 個を base64 に。見つからなければ None。"""
    ns, path = ref.split(":", 1) if ":" in ref else (default_ns, ref)
    if ns == "minecraft":
        try:
            return base64.b64encode(vanilla_zip().read(
                f"assets/minecraft/textures/{path}.png")).decode()
        except KeyError:
            return None
    for mdir, mid, _ in MODS:
        if mid == ns:
            p = mod_resources(mdir) / "assets" / mid / "textures" / f"{path}.png"
            if p.exists():
                return base64.b64encode(p.read_bytes()).decode()
    return None


def _model_chain_texture(model_id, depth=0):
    """モデル id から代表テクスチャを 1 枚返す。**`parent` を辿る。**

    `#name` の参照(子モデルが埋めるつもりの変数)は素材ではないので飛ばす。
    """
    if depth > 8:
        return None
    ns, path = model_id.split(":", 1) if ":" in model_id else ("minecraft", model_id)
    data = None
    if ns == "minecraft":
        try:
            data = json.loads(vanilla_zip().read(f"assets/minecraft/models/{path}.json"))
        except KeyError:
            return None
    else:
        for mdir, mid, _ in MODS:
            if mid == ns:
                p = mod_resources(mdir) / "assets" / mid / "models" / f"{path}.json"
                if p.exists():
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                    except Exception:  # noqa: BLE001
                        data = None
                break
    if data is None:
        return None
    tex_map = {k: v for k, v in (data.get("textures") or {}).items()
               if isinstance(v, str) and not v.startswith("#")}
    chosen = None
    for key in ("layer0",) + tuple(TEXTURE_KEY_PREFERENCE):
        if key in tex_map:
            chosen = tex_map[key]
            break
    if chosen is None and tex_map:
        chosen = next(iter(tex_map.values()))
    if chosen:
        got = _png_b64_for_ref(chosen, ns)
        if got:
            return got
    parent = data.get("parent")
    return _model_chain_texture(parent, depth + 1) if parent else None


def _gui_model_of_item_definition(node, depth=0):
    """`items/<name>.json` の木から **GUI に出るモデル id** を選ぶ。

    26.2 の items 定義は `minecraft:select` などの木である。この MOD 群は
    「GUI・fixed・on_shelf = 2D アイコン / それ以外 = 3D」という分岐を多用しているので
    (§12・§14)、**`when` に "gui" を含む枝を最優先**で選ぶ。無ければ fallback、
    それも無ければ最初の枝。

    ⚠ ここを決め打ちの id 一覧にすると、§27.5-10(ドア 90 種)と同じ
    「手書きの表から外れた物が黙って絵を失う」失敗を作る。だから**構造で辿る**。
    """
    if depth > 8 or not isinstance(node, dict):
        return None
    if node.get("type") == "minecraft:model" and isinstance(node.get("model"), str):
        return node["model"]
    cases = node.get("cases")
    if isinstance(cases, list):
        for want_gui in (True, False):
            for case in cases:
                if not isinstance(case, dict):
                    continue
                when = case.get("when")
                whens = when if isinstance(when, list) else [when]
                if want_gui and "gui" not in whens:
                    continue
                got = _gui_model_of_item_definition(case.get("model"), depth + 1)
                if got:
                    return got
            if node.get("fallback") is not None:
                got = _gui_model_of_item_definition(node["fallback"], depth + 1)
                if got:
                    return got
    for key in ("fallback", "model", "on_false", "on_true"):
        got = _gui_model_of_item_definition(node.get(key), depth + 1)
        if got:
            return got
    return None


def mod_texture_b64(mod_dir, modid, name):
    if modid == "halia":
        # Drawn by code in the game; the picture is the GUI render kept beside the index (see the Halia section).
        if name == "halia_blade":
            return halia_icon_b64("blades", "")
        return halia_icon_b64("items", f"halia:{name}")
    assets = mod_resources(mod_dir) / "assets" / modid
    textures = assets / "textures"
    override = MOD_TEXTURE_OVERRIDE.get(f"{modid}:{name}")
    if override:
        p = textures / f"{override}.png"
        if p.exists():
            return base64.b64encode(p.read_bytes()).decode()
    for sub in ("item", "block"):
        p = textures / sub / f"{name}.png"
        if p.exists():
            cropped = crop_to_used_uv(assets, name, p) if sub == "item" else None
            return cropped if cropped else base64.b64encode(p.read_bytes()).decode()
    # V1.7.0: テクスチャが item/ 直下ではなく**サブフォルダ**に置かれていることがある
    # (食料品 300 種は textures/item/food/<name>.png)。ここを決め打ちのフォルダ名の
    # 一覧にすると、§27.5-10 のドア 90 種と同じ「手書きリストから外れた物が黙って
    # 消える」失敗をまた作ることになるので、**再帰的に探す**。
    # `<name>_3d.png`(UV アトラス)は名前が違うので、この検索には引っかからない。
    nested = sorted((q for q in textures.rglob(f"{name}.png") if q.is_file()),
                    key=lambda q: (len(q.parts), str(q)))
    if nested:
        return base64.b64encode(nested[0].read_bytes()).decode()
    # V1.4.1: 平面アイコンを持たず 3D モデルだけのアイテム(巨大ボス 3 体のドロップ)。
    # ゲーム内は items/<name>.json が 3D モデルを指すので正しく描かれる(§19.2 の方針どおり)が、
    # 早見表のサムネイル用の平面 PNG が無い。空欄にするよりは実物の絵を出す。
    # ※ これは UV アトラスなので見栄えは良くない。平面アイコンを作ったらこの分岐は不要になる。
    p3d = textures / "item" / f"{name}_3d.png"
    if p3d.exists():
        return base64.b64encode(p3d.read_bytes()).decode()
    # v1.7.7: 強化ガラスの窓(pane)17 種はどれも自分専用のテクスチャを持たない。
    # blockstate は "multipart"(post/side/side_alt の組)で単一の block/<name>.json を
    # 持たないため、下の block モデル経路では解決できず、17 枚とも WARNING で
    # 抜け落ちていた。実際に読まれる item モデル(parent: minecraft:item/generated)
    # 自身の layer0 が「同じ色の板ガラスブロックのテクスチャ」(例:
    # sorakaze_deco:block/white_reinforced_glass、"_pane" 抜き)を指しているので、
    # ここでそれを辿る。他 MOD のテクスチャや vanilla を指す場合にも対応しておく
    # (§20-5 が建材バリアント 414 枚で踏んだ「MOD 名前空間しか探さない」失敗の再演を防ぐ)。
    item_model_path = assets / "models/item" / f"{name}.json"
    if item_model_path.exists():
        try:
            item_model = json.loads(item_model_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            item_model = {}
        tex_map = item_model.get("textures", {})
        for key in ("layer0", "layer1", "texture", "all", "particle"):
            ref = tex_map.get(key)
            if not ref:
                continue
            ref_ns, ref_path = ref.split(":", 1) if ":" in ref else (modid, ref)
            if ref_ns == "minecraft":
                try:
                    data = vanilla_zip().read(f"assets/minecraft/textures/{ref_path}.png")
                    return base64.b64encode(data).decode()
                except KeyError:
                    pass
            else:
                for mdir, mid, _ in MODS:
                    if mid == ref_ns:
                        p = mod_resources(mdir) / "assets" / mid / "textures" / f"{ref_path}.png"
                        if p.exists():
                            return base64.b64encode(p.read_bytes()).decode()
            break
    # No flat "<name>.png" - the item icon is a multi-texture block model (e.g. traffic
    # lights, poles, tactile paving). Read the block model's texture map and pick the
    # most representative single face, in the same spirit as Mojang's own "particle"
    # texture convention (the face used for break particles / inventory fallback icons).
    model_path = assets / "models/block" / f"{name}.json"
    if model_path.exists():
        model = json.loads(model_path.read_text(encoding="utf-8"))
        tex_map = model.get("textures", {})
        chosen = None
        for key in TEXTURE_KEY_PREFERENCE:
            if key in tex_map:
                chosen = tex_map[key]
                break
        if chosen is None and tex_map:
            chosen = next(iter(tex_map.values()))
        if chosen:
            chosen_ns, chosen_path = chosen.split(":", 1) if ":" in chosen else (modid, chosen)
            # V1.4.1: モデルがバニラのテクスチャを直接指している場合(建材バリアント 138 種は
            # すべてこの形 — 例 {"tex": "minecraft:block/stone"})、MOD の assets には存在しない。
            # 公式 jar から読む。これが無いと 400 枚以上のカードが絵の無いまま出力される。
            if chosen_ns == "minecraft":
                try:
                    data = vanilla_zip().read(f"assets/minecraft/textures/{chosen_path}.png")
                    return base64.b64encode(data).decode()
                except KeyError:
                    pass
            for mdir, mid, _ in MODS:
                if mid == chosen_ns:
                    p = mod_resources(mdir) / "assets" / mid / "textures" / f"{chosen_path}.png"
                    if p.exists():
                        return base64.b64encode(p.read_bytes()).decode()
    # v1.8.4: ここまでで解決できないのは、**平面テクスチャも block/<name>.json も持たず、
    # `items/<name>.json` の分岐から先にしか絵が無い**ブロックである(水道管がそれで、
    # 絵は item/water_pipe_icon にあった)。26.2 の items 定義を構造どおり辿って
    # 「GUI に出るモデル」を選び、そのモデル(と parent)のテクスチャを読む。
    #
    # ⚠ **わざと最後に置いてある。**上の経路で既に解決している 900 枚あまりの絵に
    # 1 枚も触れないためで、実際に生成前後で画像ハッシュを突き合わせて確認している。
    item_def_path = assets / "items" / f"{name}.json"
    if item_def_path.exists():
        try:
            item_def = json.loads(item_def_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            item_def = {}
        gui_model = _gui_model_of_item_definition(item_def.get("model"))
        if gui_model:
            got = _model_chain_texture(gui_model)
            if got:
                return got
    print(f"WARNING: no texture found for {modid}:{name}")
    return None


def load_lang(mod_dir, modid, locale="ja_jp"):
    p = mod_resources(mod_dir) / "assets" / modid / f"lang/{locale}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def display_name(lang, modid, name):
    for prefix in ("item", "block"):
        key = f"{prefix}.{modid}.{name}"
        if key in lang:
            return lang[key]
    return name


# ===========================================================================
# バニラの公式表示名(ja_jp / en_us)
# ===========================================================================
# 旧版はバニラ素材の名前を手書きの VANILLA_JA_NAMES(約 35 語)だけで引いていたため、
# 表に無い 111 種の素材(銅インゴット・石レンガなど)がツールチップに生 id
# ("copper_ingot")のまま出ていた。レシピブック化でツールチップが主役になるので、
# 実際のバニラ言語ファイルから正式名を引く。
#   ja: ランチャーの asset store(index の sha1 で検証してから読む。ローカルに実在する
#       Mojang 配布物で、テクスチャを公式クライアント jar から読むのと同じ正規ルート)
#   en: 公式クライアント jar 同梱の en_us.json
# どちらも見つからなければ従来の VANILLA_JA_NAMES → 生 id の順で落ちる(=今までと
# 同じ表示に戻るだけ)が、その劣化は黙って起きないよう WARNING で名指しする。
VANILLA_ASSET_BASES = [
    Path.home() / "Library/Application Support/minecraft/assets",
    Path.home() / ".gradle/caches/fabric-loom/assets",
]


def find_vanilla_asset(rel_path):
    """ランチャーの asset store から 1 ファイルを読む(index の sha1 で検証してから)。

    戻り値: (bytes, 使った index 名) / 見つからなければ (None, None)。
    ja_jp.json と UI クリック音がこの経路を共用する。
    """
    import hashlib
    indexes = []
    for base in VANILLA_ASSET_BASES:
        d = base / "indexes"
        if d.is_dir():
            indexes += list(d.glob("*.json"))
    indexes.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    objdirs = [b / "objects" for b in VANILLA_ASSET_BASES if (b / "objects").is_dir()]
    for idx_path in indexes:
        try:
            obj = json.loads(idx_path.read_text(encoding="utf-8"))["objects"][rel_path]
            h = obj["hash"]
        except Exception:  # noqa: BLE001 - 壊れた index / 未収載は次の候補へ
            continue
        for od in objdirs:
            f = od / h[:2] / h
            if not f.is_file():
                continue
            data = f.read_bytes()
            if hashlib.sha1(data).hexdigest() != h:
                continue
            return data, idx_path.name
    return None, None


def load_vanilla_ja():
    data, idx_name = find_vanilla_asset("minecraft/lang/ja_jp.json")
    if data is not None:
        lang = json.loads(data.decode("utf-8"))
        print(f"vanilla ja_jp.json: {idx_name} ({len(lang)} keys)")
        return lang
    print("WARNING: vanilla ja_jp.json not found in local asset stores - vanilla "
          "ingredient names fall back to VANILLA_JA_NAMES / raw ids")
    return {}


def load_click_wav_b64():
    """バニラの UI クリック音(random/click.ogg)を、ブラウザがどれでも復号できる
    小さな WAV(モノラル 16-bit・無音を刈り込み)にして base64 で返す。

    OGG のまま埋めないのは Safari の decodeAudioData が OGG Vorbis を読めないため。
    音源はテクスチャ・ja_jp.json と同じ正規ルート(所有者のランチャーの asset store、
    sha1 検証つき)。取り出せない/復号器が無いときは WARNING を出して None を返し、
    ページ側は合成ブリップ(WebAudio)に切りかわる = 黙って無音にはならない。
    """
    data, idx_name = find_vanilla_asset("minecraft/sounds/random/click.ogg")
    if data is None:
        print("WARNING: vanilla click.ogg not found in local asset stores - "
              "the page will fall back to a synthesized click, not the Minecraft one")
        return None
    import shutil
    import subprocess
    import tempfile
    import wave
    import array
    import io
    oggdec = shutil.which("oggdec")
    if not oggdec:
        print("WARNING: oggdec not found on PATH - cannot transcode click.ogg; "
              "the page will fall back to a synthesized click, not the Minecraft one")
        return None
    try:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "click.ogg"
            dst = Path(td) / "click.wav"
            src.write_bytes(data)
            subprocess.run([oggdec, "-Q", "-o", str(dst), str(src)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with wave.open(str(dst), "rb") as wf:
                nch, sw, rate = wf.getnchannels(), wf.getsampwidth(), wf.getframerate()
                frames = wf.readframes(wf.getnframes())
        if sw != 2:
            raise ValueError(f"unexpected sample width {sw}")
        samples = array.array("h")
        samples.frombytes(frames)
        if nch == 2:                       # ステレオ -> モノラル(単純平均)
            samples = array.array(
                "h", ((samples[i] + samples[i + 1]) // 2 for i in range(0, len(samples), 2)))
        elif nch != 1:
            raise ValueError(f"unexpected channel count {nch}")
        peak = max(1, max(abs(v) for v in samples))
        thr = max(48, peak // 200)         # 約 -46dB を無音とみなす
        first = next((i for i, v in enumerate(samples) if abs(v) > thr), 0)
        last = next((i for i in range(len(samples) - 1, -1, -1) if abs(samples[i]) > thr),
                    len(samples) - 1)
        pad = rate // 400                  # 前後 2.5ms の余白
        first = max(0, first - pad)
        last = min(len(samples), last + 1 + pad)
        samples = samples[first:last]
        max_len = int(rate * 0.35)         # クリック音は 0.1〜0.2 秒。保険の上限
        if len(samples) > max_len:
            samples = samples[:max_len]
        buf = io.BytesIO()
        with wave.open(buf, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(samples.tobytes())
        raw = buf.getvalue()
        if len(raw) > 65536:
            print(f"WARNING: transcoded click.wav is unexpectedly large ({len(raw)} bytes)")
        print(f"click sound: {idx_name} random/click.ogg ({len(data)} B) -> "
              f"mono WAV {len(samples) / rate * 1000:.0f} ms @ {rate} Hz ({len(raw)} B, "
              f"{len(base64.b64encode(raw))} B as base64)")
        return base64.b64encode(raw).decode()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: could not transcode click.ogg ({exc}) - "
              f"the page will fall back to a synthesized click, not the Minecraft one")
        return None


def load_vanilla_en(zf):
    try:
        return json.loads(zf.read("assets/minecraft/lang/en_us.json").decode("utf-8"))
    except KeyError:
        print("WARNING: en_us.json not found in the vanilla client jar - "
              "English names fall back to title-cased ids")
        return {}


# ===========================================================================
# テクスチャの一意化(content-hash dedup)+ 可逆な再圧縮
# ===========================================================================
def recompress_png(data):
    """PNG をピクセル完全一致のまま小さくできたら小さい方を返す。

    候補は ①元のまま ②optimize 付き再エンコード ③256 色以下ならパレット化。
    どの候補も **デコードし直して RGBA が元とバイト一致することを検証してから**
    採用する(検証に落ちた候補は捨てる)ので、見た目が変わる事故は構造的に無い。
    """
    from PIL import Image
    import io
    try:
        src = Image.open(io.BytesIO(data))
        src.load()
        rgba = src.convert("RGBA")
    except Exception:  # noqa: BLE001 - 読めない PNG はそのまま出す
        return data
    ref = rgba.tobytes()
    best = data

    def consider(candidate):
        nonlocal best
        if len(candidate) >= len(best):
            return
        try:
            back = Image.open(io.BytesIO(candidate))
            back.load()
            if back.convert("RGBA").tobytes() == ref:
                best = candidate
        except Exception:  # noqa: BLE001
            pass

    buf = io.BytesIO()
    try:
        rgba.save(buf, format="PNG", optimize=True)
        consider(buf.getvalue())
    except Exception:  # noqa: BLE001
        pass
    if rgba.getcolors(256) is not None:
        try:
            pal = rgba.convert("P", palette=Image.ADAPTIVE, colors=256,
                               dither=Image.Dither.NONE)
            buf = io.BytesIO()
            pal.save(buf, format="PNG", optimize=True)
            consider(buf.getvalue())
        except Exception:  # noqa: BLE001
            pass
    return best


def _git_bytes(*args):
    import subprocess as _sp
    out = _sp.run(["git", "-C", str(SITE_ROOT), *args], capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"ERROR: git {' '.join(args)} failed: {out.stderr.decode(errors='replace').strip()}")
    return out.stdout


PUBLISHED_REF = "origin/main"


def published_textures():
    """[(\"t<N>\", base64 payload), ...] of the recipe textures on the published branch, in numeric order.

    The published numbers must be kept: data/recipes.json names a texture by its t<N>, and the portal's recipe page
    loads assets/img/recipes/t<N>.png. A number is never reused: a picture that goes (a retired product's, 2026-10-17)
    leaves a hole, and the next new picture takes the number after the highest one (ItemRegistry.next_tex)."""
    names = _git_bytes("ls-tree", "--name-only", PUBLISHED_REF, "assets/img/recipes/").decode().split()
    numbered = sorted((int(re.fullmatch(r"assets/img/recipes/t(\d+)\.png", n).group(1)), n)
                      for n in names if re.fullmatch(r"assets/img/recipes/t(\d+)\.png", n))
    if len({n for n, _ in numbered}) != len(numbered):
        raise SystemExit(f"ERROR: the published textures on {PUBLISHED_REF} repeat a number.")
    return [(f"t{n}", base64.b64encode(_git_bytes("show", f"{PUBLISHED_REF}:{path}")).decode()) for n, path in numbered]


# 公開済みの絵のうち、意図して変える 1 件ずつの表(2026-10-05、Corvus の判断 A)。見張りは、ここに書いた品を、ここに書いた「前の鍵 → 新しい鍵」の
# 組にかぎって通す(別の鍵・別の品は今までどおり止まる)。前の鍵の絵(PNG)は、そのまま残さなければならない(下の見張りが、バイトまで見る)。
INTENDED_ICON_CHANGES = {
    "tsubomi:starbloom_axe": ("t2049", "t2057", "Tsubomi V2.3.0.2: redrawn in the vanilla Diamond axe shape, Starbloom colours (owner request 2026-10-21)"),
    "tsubomi:starbloom_ingot": ("t2050", "t2058", "Tsubomi V2.3.0.2: redrawn in the vanilla Netherite Ingot shape, Starbloom colours (owner request 2026-10-21)"),
    "tsubomi:starbloom_hoe": ("t2051", "t2059", "Tsubomi V2.3.0.2: redrawn in the vanilla Diamond hoe shape, Starbloom colours (owner request 2026-10-21)"),
    "tsubomi:starbloom_pickaxe": ("t2052", "t2060", "Tsubomi V2.3.0.2: redrawn in the vanilla Diamond pickaxe shape, Starbloom colours (owner request 2026-10-21)"),
    "tsubomi:starbloom_shovel": ("t2053", "t2061", "Tsubomi V2.3.0.2: redrawn in the vanilla Diamond shovel shape, Starbloom colours (owner request 2026-10-21)"),
    "tsubomi:starbloom_spear": ("t2054", "t2062", "Tsubomi V2.3.0.2: redrawn in the vanilla Diamond spear shape, Starbloom colours (owner request 2026-10-21)"),
    "ouka:smes_battery": ("t173", "t2258", "OUKA V1.7 88213: the SMES Quantum Battery is the Standard tier of the 12-tier family, its look changed to copper and brass"),
    "minecraft:white_carpet": (None, "t50", "Tsubomi 2.0.0 uses it; drawn with the white wool picture it already shared, never had one"),
    "minecraft:stonecutter": (None, "t889", "Tsubomi 2.0.0: the stonecutter became a station (120 recipes); it had no picture"),
    "ouka:operating_shelter_block": ("t157", "t269", "V1.4 new shelter look, owner-intended 2026-10-05"),
    "astraea:appliance_ceiling_fan": ("t396", "t730", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:appliance_faucet": ("t397", "t731", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:appliance_microwave": ("t398", "t732", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:appliance_refrigerator": ("t400", "t733", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:archive_shelf": ("t402", "t734", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:atm_terminal": ("t408", "t735", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:lockdown_console": ("t476", "t736", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:pneumatic_compressor": ("t491", "t737", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:pneumatic_drone_pad": ("t492", "t738", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:pneumatic_receiver": ("t493", "t739", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:pneumatic_safety_valve": ("t494", "t740", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:pneumatic_sender": ("t495", "t741", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:scriptoria_press": ("t538", "t742", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:sovereign_mint": ("t547", "t743", "ASTRAEA V1.5.3: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:alarm_strobe": ("t393", "t744", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:bear_trap": ("t410", "t745", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:blister_gas_canister": ("t412", "t746", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:cell_monitor": ("t417", "t747", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:choking_gas_canister": ("t421", "t748", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:claymore": ("t410", "t749", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:defense_keypad": ("t440", "t750", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:defense_retina_scanner": ("t440", "t751", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:gas_scrubber": ("t458", "t752", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:icbm_silo": ("t469", "t753", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "astraea:interceptor_battery": ("t471", "t754", "ASTRAEA V1.5.4: hand-drawn icon of the rebuilt device (owner's rebuild order 2026-10-11)"),
    "ouka:ouka_alloy_ingot": ("t120", "t2294", "OUKA V1.7 93560: the Ouka Alloy Ingot (now a 12-tier family) redrawn in the vanilla ingot shape"),
    "ouka:ouka_alloy_block": ("t103", "t2301", "OUKA V1.7 93560: the Ouka Alloy Block (now a 12-tier family) redrawn as a polished gem block"),
    "ouka:heavy_core_ingot": ("t2259", "t2302", "OUKA V1.7 93560: the Heavy Core Ingot redrawn again on the common ingot tone map"),
    "ouka:pure_titanium_ingot": ("t2273", "t2326", "OUKA V1.7 93560: the Ultra-Pure Titanium Ingot redrawn on the common ingot tone map"),
    "ouka:titanium_ingot": ("t114", "t2303", "OUKA V1.7 93560: the Titanium Ingot redrawn in the vanilla ingot shape"),
    "#ouka:transceiver_max_key": ("t2253", "t2104", "OUKA V1.7 93560: the placeholder Starbloom Max ingot now uses the Tsubomi Starbloom Max art, and the 'either of' card shows the first of them"),
    "halia:watch_eye": ("t1691", "t2102", "Halia 1.4.0.36 hotfix: the Watch Eye inventory icon was the missing-texture block"),
}


# Items that may leave the crafting sheet because the OWNER ordered their removal or because the only card that showed them
# went with a removed product (OUKA V1.7 71208: GUN MAX and all its ammunition are deleted). One id per entry, each with
# its reason; an item not named here that vanishes still reddens the guard, and the self-test proves it.
INTENDED_REMOVALS = {
    "ouka:ammo_energy": "OUKA V1.7 71208: GUN MAX and its ammunition were deleted (owner's order)",
    "ouka:ammo_heavy": "OUKA V1.7 71208: GUN MAX and its ammunition were deleted (owner's order)",
    "ouka:ammo_light": "OUKA V1.7 71208: GUN MAX and its ammunition were deleted (owner's order)",
    "ouka:ammo_mythic": "OUKA V1.7 71208: GUN MAX and its ammunition were deleted (owner's order)",
    "ouka:ammo_shotgun": "OUKA V1.7 71208: GUN MAX and its ammunition were deleted (owner's order)",
    "ouka:ammo_sniper": "OUKA V1.7 71208: GUN MAX and its ammunition were deleted (owner's order)",
    "ouka:smes_battery_plus": "OUKA V1.7 1128612: this tier is made only in the Quantum Cell Assembler, so its crafting-table card is gone; the item stays in the mod and is on the machine sheet",
    "ouka:smes_battery_super": "OUKA V1.7 1128612: this tier is made only in the Quantum Cell Assembler, so its crafting-table card is gone; the item stays in the mod and is on the machine sheet",
    "ouka:smes_battery_max": "OUKA V1.7 1128612: this tier is made only in the Quantum Cell Assembler, so its crafting-table card is gone; the item stays in the mod and is on the machine sheet",
    "ouka:smes_battery_ultra": "OUKA V1.7 1128612: this tier is made only in the Quantum Cell Assembler, so its crafting-table card is gone; the item stays in the mod and is on the machine sheet",
    "ouka:smes_battery_ultracore": "OUKA V1.7 1128612: this tier is made only in the Quantum Cell Assembler, so its crafting-table card is gone; the item stays in the mod and is on the machine sheet",
    "ouka:smes_battery_ultimate": "OUKA V1.7 1128612: this tier is made only in the Quantum Cell Assembler, so its crafting-table card is gone; the item stays in the mod and is on the machine sheet",
    "ouka:smes_battery_wonder_full": "OUKA V1.7 1128612: this tier is made only in the Quantum Cell Assembler, so its crafting-table card is gone; the item stays in the mod and is on the machine sheet",
    "ouka:smes_battery_premium": "OUKA V1.7 1128612: this tier is made only in the Quantum Cell Assembler, so its crafting-table card is gone; the item stays in the mod and is on the machine sheet",
    "ouka:smes_battery_mythos": "OUKA V1.7 1128612: this tier is made only in the Quantum Cell Assembler, so its crafting-table card is gone; the item stays in the mod and is on the machine sheet",
    "ouka:deuterium_cryo_ice": "OUKA V1.7 1128612: its only crafting-sheet cards were the SMES tier recipes that the Quantum Cell Assembler replaced; the item stays in the mod and on the machine sheet",
    "ouka:amorphous_glass_ice": "OUKA V1.7 1128612: its only crafting-sheet cards were the SMES tier recipes that the Quantum Cell Assembler replaced; the item stays in the mod and on the machine sheet",
    "ouka:bec_cryo_ice": "OUKA V1.7 1128612: its only crafting-sheet cards were the SMES tier recipes that the Quantum Cell Assembler replaced; the item stays in the mod and on the machine sheet",
    "ouka:sakura_chrono_ice": "OUKA V1.7 1128612: its only crafting-sheet cards were the SMES tier recipes that the Quantum Cell Assembler replaced; the item stays in the mod and on the machine sheet",
    "ouka:deuterium_cell": "OUKA V1.7 1128612: its only crafting-sheet cards were the SMES tier recipes that the Quantum Cell Assembler replaced; the item stays in the mod and on the machine sheet",
    "ouka:tungsten_plate": "OUKA V1.7 1128612: its only crafting-sheet cards were the SMES tier recipes that the Quantum Cell Assembler replaced; the item stays in the mod and on the machine sheet",
    "ouka:smes_battery_ultrafast": "OUKA V1.7 1128612: this tier is made only in the Quantum Cell Assembler, so its crafting-table card is gone; the item stays in the mod and is on the machine sheet",
    "ouka:superionic_ice": "OUKA V1.7 1128612: its only crafting-sheet cards were the SMES tier recipes that the Quantum Cell Assembler replaced; the item stays in the mod and on the machine sheet",
    "minecraft:end_crystal": "OUKA V1.7 1128612: its only crafting-sheet card was an SMES tier recipe that the Quantum Cell Assembler replaced (the item is vanilla and unchanged)",
    "ouka:lithium_dust": "OUKA V1.7 71208: its only crafting-sheet card was the deleted GUN MAX energy round; the item stays in the mod and on the machine sheet",
}


def icon_problems(old_items, new_items, allowed=None, removals=None):
    """Compare the items of the published sheet with the new one. Returns (problems, keys whose old PNG must still be byte-identical)."""
    allowed = INTENDED_ICON_CHANGES if allowed is None else allowed
    removals = INTENDED_REMOVALS if removals is None else removals
    problems, keep = [], []
    for item, entry in old_items.items():
        if item not in new_items and item in removals:
            continue
        if item not in new_items:
            problems.append(f"{item} was on the published sheet and is gone")
            continue
        key_old, key_new = entry[2], new_items[item][2]
        if key_old != key_new:
            grant = allowed.get(item)
            if not (grant and grant[0] == key_old and grant[1] == key_new):
                problems.append(f"{item}: texture {key_old} became {key_new}")
                continue
        if key_old is not None:
            keep.append((item, key_old))
    return problems, keep


def icon_guard_self_test():
    """Mutation check: the one intended change passes, and every other change still reddens the guard."""
    old = {"ouka:a": ["a", "A", "t157"], "ouka:b": ["b", "B", "t5"], "ouka:c": ["c", "C", None]}
    grant = {"ouka:a": ("t157", "t269", "test")}
    cases = [
        ("the intended pair passes", {"ouka:a": ["a", "A", "t269"], "ouka:b": ["b", "B", "t5"], "ouka:c": ["c", "C", None]}, True),
        ("an unchanged sheet passes", {"ouka:a": ["a", "A", "t157"], "ouka:b": ["b", "B", "t5"], "ouka:c": ["c", "C", None]}, True),
        ("the granted item moved to another key reddens", {"ouka:a": ["a", "A", "t270"], "ouka:b": ["b", "B", "t5"], "ouka:c": ["c", "C", None]}, False),
        ("another item changed reddens", {"ouka:a": ["a", "A", "t269"], "ouka:b": ["b", "B", "t6"], "ouka:c": ["c", "C", None]}, False),
        ("an item that gained a picture reddens", {"ouka:a": ["a", "A", "t269"], "ouka:b": ["b", "B", "t5"], "ouka:c": ["c", "C", "t7"]}, False),
        ("a vanished item reddens", {"ouka:a": ["a", "A", "t269"], "ouka:c": ["c", "C", None]}, False),
    ]
    bad = []
    for name, new_items, expect_green in cases:
        problems, _keep = icon_problems(old, new_items, grant, {})
        if bool(problems) == expect_green:
            bad.append(name)
    # An item named in the removals table may vanish; one that is not named still reddens, and a named one that
    # stays on the sheet is not "removed": its texture is still compared.
    only_a = {"ouka:a": ["a", "A", "t269"], "ouka:c": ["c", "C", None]}
    if icon_problems(old, only_a, grant, {"ouka:b": "test"})[0]:
        bad.append("a named removal must pass")
    if not icon_problems(old, only_a, grant, {"ouka:c": "test"})[0]:
        bad.append("an unnamed vanished item must still redden")
    kept = {"ouka:a": ["a", "A", "t269"], "ouka:b": ["b", "B", "t6"], "ouka:c": ["c", "C", None]}
    if not icon_problems(old, kept, grant, {"ouka:b": "test"})[0]:
        bad.append("a named item that stays with a changed picture must still redden")
    # 表が空なら、ふつうの見張りと同じ(許しは何も効かない)
    problems, _keep = icon_problems(old, {"ouka:a": ["a", "A", "t269"], "ouka:b": ["b", "B", "t5"], "ouka:c": ["c", "C", None]}, {})
    if not problems:
        bad.append("an empty allowance table must not pass the changed icon")
    return bad


def retired_namespaces():
    """The mod ids of the retired brands (data/retirement.json), read from their manifest blocks."""
    manifest = json.loads((SITE_ROOT / "glimpse_manifest.json").read_text(encoding="utf-8"))
    return {manifest[b]["mod_id"] for b in RETIRED_BRANDS if isinstance(manifest.get(b), dict) and "mod_id" in manifest[b]}


def retired_only_textures(old):
    """The picture keys only a retired product's items used on the published sheet `old` (its data/recipes.json).

    An item leaves the sheet with its retired product when no live card, live tab icon or guide still shows it (a
    vanilla ingredient only ASTRAEA's cards used included). Its picture may leave the folder with it, unless a live
    item uses the same picture. Returns (keys, old_live, old_retired)."""
    gone = retired_namespaces()
    # What a live part of the published sheet still shows: its cards, its tab icons and its guides.
    gone_tabs = {i for i, c in enumerate(old.get("cats") or []) if str(c[1]).split(":", 1)[0] in gone}
    live_text = json.dumps([[c for i, c in enumerate(old["cards"]) if c[0] not in gone_tabs],
                            [c for i, c in enumerate(old.get("cats") or []) if i not in gone_tabs],
                            old.get("all_tab_icon"), old.get("guides")], ensure_ascii=False)
    live_refs = set(re.findall(r'"(#?[a-z0-9_.-]+:[a-z0-9_/.-]+)"', live_text))
    old_live = {k: v for k, v in old["items"].items() if k in live_refs and k.split(":", 1)[0] not in gone}
    old_retired = {k: v for k, v in old["items"].items() if k not in old_live}
    keys = ({v[2] for v in old_retired.values() if v[2]} - {v[2] for v in old_live.values() if v[2]})
    return keys, old_live, old_retired


def guard_published_textures():
    """Every item the published sheet had keeps its texture key (but for the named intended changes), and the PNG at that path keeps its bytes.

    A retired product's items (2026-10-17, ASTRAEA) may leave the sheet, and a picture only they used may leave the folder;
    a picture a live item still uses is never exempt. Compares the files this run wrote with PUBLISHED_REF, never with
    themselves. Returns the problems (empty = green)."""
    old = json.loads(_git_bytes("show", f"{PUBLISHED_REF}:data/recipes.json"))
    new = json.loads((OUT_DATA_DIR / "recipes.json").read_text(encoding="utf-8"))
    retired_only, old_live, _old_retired = retired_only_textures(old)
    problems, keep = icon_problems(old_live, new["items"])
    # A picture only an intended removal used may leave the folder with it (a picture a surviving item still uses never does).
    still_used = {v[2] for v in new["items"].values() if v[2]}
    retired_only = set(retired_only) | ({old_live[i][2] for i in INTENDED_REMOVALS
                                         if i in old_live and i not in new["items"] and old_live[i][2]} - still_used)
    for item, key_old in keep:
        path = f"assets/img/recipes/{key_old}.png"
        if (SITE_ROOT / path).read_bytes() != _git_bytes("show", f"{PUBLISHED_REF}:{path}"):
            problems.append(f"{path} (the texture of {item}) is not byte-identical to the published one")
    for key, payload in published_textures():
        if key in retired_only:
            continue
        path = SITE_ROOT / f"assets/img/recipes/{key}.png"
        if not path.exists() or path.read_bytes() != base64.b64decode(payload):
            problems.append(f"assets/img/recipes/{key}.png changed or vanished")
    return problems


_MOD_TAG_CACHE = {}


def mod_item_tag(ns, name, _seen=None):
    """`#<modid>:<name>` -> the real item ids, read from that mod's own published data (2026-10-05, Tsubomi).

    Vanilla tags come out of the client jar (vanilla_item_tag); a tag of a staged brand lives in the brand's
    jar at data/<ns>/tags/item/<name>.json. Nested `#...` members are opened, vanilla ones through the client
    jar. A tag that cannot be read stops the generation: a card with an unresolvable ingredient must not ship."""
    key = (ns, name)
    if key in _MOD_TAG_CACHE:
        return _MOD_TAG_CACHE[key]
    seen = _seen or set()
    if key in seen:
        raise SystemExit("ERROR: item tag #%s:%s refers to itself (cycle)" % key)
    seen.add(key)
    if ns == "c":
        # Fabric's common tags (#c:ingots/iron, #c:glass_blocks ...) belong to no mod of the suite: Fabric API
        # provides them at run time. Halia 1.2.0's grids use 13 of them, so they are read from the Fabric API
        # version Halia is built against, not typed here.
        return common_tag_members(name, seen)
    for mod_dir, modid, _cat in MODS:
        if modid == ns:
            path = mod_resources(mod_dir) / "data" / ns / "tags" / "item" / f"{name}.json"
            break
    else:
        raise SystemExit("ERROR: a recipe uses the item tag #%s:%s, but no staged mod owns the namespace %r."
                         % (ns, name, ns))
    if not path.exists():
        raise SystemExit("ERROR: a recipe uses the item tag #%s:%s, but %s is not in the published jar."
                         % (ns, name, path))
    out = []
    for v in json.loads(path.read_text(encoding="utf-8"))["values"]:
        vid = v["id"] if isinstance(v, dict) else v
        if vid.startswith("#"):
            tns, tname = vid[1:].split(":", 1)
            members = (vanilla_item_tag(tname) if tns == "minecraft"
                       else mod_item_tag(tns, tname, seen))
        else:
            members = [vid]
        for m in members:
            if m not in out:
                out.append(m)
    if not out:
        raise SystemExit("ERROR: item tag #%s:%s resolved to nothing - the card would show an empty slot "
                         "where an ingredient belongs" % key)
    _MOD_TAG_CACHE[key] = out
    return out


# ===========================================================================
# Halia (V1.1.0, 2026-10-12)
# ===========================================================================
# Three things about Halia's jar that no other brand's has:
#   1. its items are drawn by code (halia:obj / halia:halia_blade special models), so the jar holds no flat item
#      texture to read. The pictures are GUI renders made by the Halia session from the real client and kept in
#      data/halia_icons/ with an index. A Halia item with no picture there STOPS the generation: a card without
#      a picture is a placeholder.
#   2. one item id is many things: every named blade is halia:halia_blade with a different halia:blade_profile,
#      and every material box is minecraft:chest with a custom name. They are keyed here the way the Water Bottle
#      is (minecraft:potion[water]): `halia:halia_blade[item.halia.yamato]`, `minecraft:chest[item.halia....]`.
#      Their names are the jar's own translations of those keys.
#   3. its recipe folder has sub-folders, and 11 of the files (creative_tab/**) can never be crafted: their one
#      ingredient is a tag whose only member is minecraft:air. That is decided by opening the tag, not by a list.
HALIA_ICON_DIR = SITE_ROOT / "data" / "halia_icons"
HALIA_BLADE = "halia:halia_blade"
HALIA_ICON_PX = 64   # the renders are larger; the sheet draws a slot at 32 px, so 64 is sharp on a 2x screen
_HALIA_INDEX = None
# What the portal needs for a Halia card that is not a 3x3 grid (the anvil half of a material box, the blast
# furnace): where it is made, what goes in, and the sentence in Japanese and English. Written beside recipes.json.
HALIA_HOW = {}


def _halia_png_b64(png, edge_to_edge=False):
    from PIL import Image
    with Image.open(png) as im:
        im = im.convert("RGBA")
        if im.width != im.height:
            raise SystemExit(f"ERROR: {png} is {im.width}x{im.height}; a Halia icon must be square.")
        # A flat item drawn edge to edge (the 1.3 sigils, grand gates, corroded pieces) has no transparent pixel
        # and is still an icon: the index marks each such picture "edge_to_edge": true, checked by eye.
        if im.getextrema()[3][0] == 255 and not edge_to_edge:
            raise SystemExit(f"ERROR: {png} has no transparent pixel at all: it is a screenshot, not an icon.")
        if im.width != HALIA_ICON_PX:
            im = im.resize((HALIA_ICON_PX, HALIA_ICON_PX), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, "PNG")
    return base64.b64encode(out.getvalue()).decode()


def halia_index():
    global _HALIA_INDEX
    if _HALIA_INDEX is None:
        path = HALIA_ICON_DIR / "index.json"
        if not path.exists():
            raise SystemExit(f"ERROR: {path} is missing. Halia's items are drawn by code; without the rendered "
                             f"icons and their index every Halia card would be a blank.")
        _HALIA_INDEX = json.loads(path.read_text(encoding="utf-8"))
    return _HALIA_INDEX


def halia_icon_b64(section, key):
    entry = (halia_index().get(section) or {}).get(key)
    if not entry or not entry.get("file"):
        # Collected, not raised: the run goes on so every missing picture is listed at once (see main()).
        HALIA_MISSING_ICONS.append((section, key))
        return HALIA_ICON_PLACEHOLDER
    png = HALIA_ICON_DIR / entry["file"]
    if not png.exists():
        raise SystemExit(f"ERROR: {png} is named by the Halia icon index but is not there.")
    return _halia_png_b64(png, bool(entry.get("edge_to_edge")))


def halia_result_id(result):
    """A recipe result -> the id its card is keyed by (see point 2 above)."""
    rid = result["id"]
    comp = result.get("components") or {}
    if rid == HALIA_BLADE:
        key = (comp.get("halia:blade_profile") or {}).get("translation_key")
        return f"{rid}[{key}]" if key else rid
    if rid == "minecraft:chest":
        key = (comp.get("minecraft:custom_name") or {}).get("translate")
        if not key:
            raise SystemExit("ERROR: a Halia recipe makes a chest with no custom name: %s" % json.dumps(result)[:200])
        return f"{rid}[{key}]"
    # Halia 1.3.0 (the Vigil): a lens tinted by its recipe (minecraft:dyed_color) and a limited watch pass
    # (halia:keycard_data) are still the one item; the card is the item, and its grid shows the dye or the pass.
    if comp and set(comp) <= {"minecraft:dyed_color", "halia:keycard_data"}:
        return rid
    if comp:
        raise SystemExit("ERROR: a Halia recipe result carries components this script cannot name: %s"
                         % json.dumps(result)[:200])
    return rid


def halia_uncraftable(data):
    """True when no ingredient of this recipe can ever be supplied: each is a tag that holds only air."""
    ings = data.get("ingredients")
    if data.get("type") != "minecraft:crafting_shapeless" or not ings:
        return False
    for ing in ings:
        ing = first(ing)
        if not (isinstance(ing, str) and ing.startswith("#")):
            return False
        ns, name = ing[1:].split(":", 1)
        if set(mod_item_tag(ns, name)) != {"minecraft:air"}:
            return False
    return True


def halia_register_readings(lang_ja):
    """The readings of Halia's names come with the icons. Each is tied to the jar's own Japanese name: an index
    that names an item differently from the jar is stale, and stops the generation."""
    idx = halia_index()
    for section, keyer in (("items", lambda k: "item." + k.replace(":", ".")), ("blades", lambda k: k),
                           ("boxes", lambda k: k)):
        for key, entry in (idx.get(section) or {}).items():
            if section == "blades" and key == "":
                key_in_lang = "item.halia.halia_blade"
            elif entry.get("lang"):
                # An item whose name the jar keys under another id (Fortune Augment I is item.halia.fortune_upgrade.1).
                key_in_lang = entry["lang"]
            else:
                key_in_lang = keyer(key)
            ja = lang_ja.get(key_in_lang) or lang_ja.get(key_in_lang.replace("item.", "block.", 1))
            if ja is None:
                raise SystemExit(f"ERROR: the Halia icon index names {section} {key!r}, which the jar's ja_jp.json "
                                 f"does not translate.")
            if entry.get("ja") != ja:
                raise SystemExit(f"ERROR: the Halia icon index calls {key!r} {entry.get('ja')!r}, the jar calls it "
                                 f"{ja!r}. Regenerate the index from the published jar.")
            yomi = entry.get("yomi")
            if not yomi:
                raise SystemExit(f"ERROR: the Halia icon index gives no reading for {ja!r}.")
            if ja not in YOMI:
                YOMI[ja] = yomi
                bucket = _YOMI_INDEX.setdefault(ja[0], [])
                bucket.append(ja)
                bucket.sort(key=len, reverse=True)


_HALIA_JAR_MODELS = None


def halia_warded_texture(name):
    """A warded block's picture, read from the published jar's own item and block models (Halia 1.3.0's Vigil,
    nested in META-INF/jars/): the vanilla texture its model names (a fence's planks, a chest's wood), so a shape
    whose plain block has no flat texture still gets the right picture. None when the model names no vanilla
    texture (the caller then draws the plain vanilla item)."""
    global _HALIA_JAR_MODELS
    if _HALIA_JAR_MODELS is None:
        _HALIA_JAR_MODELS = {}
        manifest = json.loads((SITE_ROOT / "glimpse_manifest.json").read_text(encoding="utf-8"))
        jar = SITE_ROOT / "downloads" / manifest["halia"]["file_name"]
        with zipfile.ZipFile(jar) as outer:
            for nested in [n for n in outer.namelist() if n.startswith("META-INF/jars/halia_") and n.endswith(".jar")]:
                with zipfile.ZipFile(io.BytesIO(outer.read(nested))) as nf:
                    for m in nf.namelist():
                        if m.startswith(("assets/halia/items/", "assets/halia/models/")) and m.endswith(".json"):
                            _HALIA_JAR_MODELS.setdefault(m, json.loads(nf.read(m).decode("utf-8")))
                        elif m.startswith("assets/halia/textures/") and m.endswith(".png"):
                            _HALIA_JAR_MODELS.setdefault(m, nf.read(m))

    def model_textures(ref, depth=0):
        if not ref or depth > 6:
            return {}
        ns, path = ref.split(":", 1) if ":" in ref else ("minecraft", ref)
        if ns != "halia":
            return {}
        body = _HALIA_JAR_MODELS.get(f"assets/halia/models/{path}.json") or {}
        tex = dict(model_textures(body.get("parent"), depth + 1))
        tex.update(body.get("textures") or {})
        return tex

    item = _HALIA_JAR_MODELS.get(f"assets/halia/items/{name}.json") or {}
    ref = ((item.get("model") or {}).get("model"))
    candidates = [ref] if ref else []
    candidates += [f"halia:item/{name}", f"halia:block/{name}"]
    for ref in candidates:
        tex = model_textures(ref)
        keys = [k for k in ("layer0", "all", "texture", "planks", "block", "side", "particle", "top", "end", "wall")
                if k in tex] + sorted(tex)
        for key in keys:
            v = tex.get(key)
            for _ in range(4):
                if isinstance(v, str) and v.startswith("#"):
                    v = tex.get(v[1:])
            if isinstance(v, str) and ":" not in v:
                v = "minecraft:" + v
            if isinstance(v, str) and v.startswith("halia:"):
                png = _HALIA_JAR_MODELS.get(f"assets/halia/textures/{v.split(':', 1)[1]}.png")
                if png:
                    return base64.b64encode(png).decode()
            if isinstance(v, str) and v.startswith("minecraft:"):
                try:
                    return base64.b64encode(vanilla_zip().read(f"assets/minecraft/textures/{v.split(':', 1)[1]}.png")).decode()
                except KeyError:
                    continue
    return None


HALIA_RECOLOUR = "halia:recoloring"   # the Aerie's 320 "any dye recolours this device" recipes: not cards (below)
# 2026-10-22 (Halia 1.4.0, parent's decision): a code-drawn recipe marker with no inputs and no result, set aside
# like the recolouring ones, counted and printed. Mirrored in check_recipe_sources.py.
HALIA_PLAYWRIGHT_BOOK = "halia:playwright_bookcloning"
# 2026-10-22 (Halia 1.4.0, parent's decision): brewing recipes whose input is an {item, potion_contents} stack (the
# Poison Resistance and awkward potions). The sheet has no display for them yet, so they are set aside, counted and
# named, not guessed. Mirrored in check_recipe_sources.py. Known gap on the recipe sheet.
HALIA_BREW_POTION_INPUT = "minecraft:brewing"
HALIA_SET_ASIDE_NAMES = {"playwright": [], "brew_potion_contents": []}
# Every halia icon id the run needs and does not have (section, key), collected instead of stopping at the first;
# printed in full and the run stops before anything is written.
HALIA_MISSING_ICONS = []
HALIA_ICON_PLACEHOLDER = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg+P//PwAF/gL+p9HU8QAAAABJRU5ErkJggg=="


def halia_cards(recipe_dir, mod_cat, reg, cards, no_yomi, seen_published, published):
    """Every recipe of the published Halia jar (its own and the Aerie's, staged together) -> its card(s).

    Returns (cards made, json files that can never be crafted, cards that come on top of one-per-json: the blade a
    material box turns into on the anvil, json files that are recolouring recipes and so are not cards).
    The recolouring recipes are set aside by their type, and the count is printed, so 320 recipes are never
    silently absent."""
    halia_register_readings(reg.lang_by_modid["halia"])
    files = sorted(recipe_dir.rglob("*.json"))
    published["halia"] = {q.relative_to(recipe_dir).as_posix() for q in files}
    made = uncraftable = extra = recolour = 0

    def add(card_id, cells, count, how, extra_ids=()):
        ja, en, _tex = reg.register(card_id)
        cat = category_of(mod_cat, card_id.split(":", 1)[1])
        _, unknown = reading_of(ja)
        if unknown:
            no_yomi.append((cat, ja, "".join(sorted(set(unknown)))))
        tokens = cat_tokens(cat) + item_tokens(card_id, ja) + [en] + ([how] if how else [])
        for cid in list(cells or ()) + list(extra_ids):
            if cid:
                cja, cen, _ = reg.register(cid)
                tokens += item_tokens(cid, cja)
                tokens.append(cen)
        cards.append({"cat": cat, "id": card_id, "cells": cells, "count": count, "how": how,
                      "s": search_blob(tokens)})

    def how_to(card_id, entry):
        # One sentence per card that is not a grid: the portal reads station, inputs and text from here. Two cards
        # with one key would make one of them say the other's sentence, so that stops the generation.
        # Halia 1.3.0: the Vigil cuts one warded shape from up to four warded blocks, and brews each false bucket
        # from six potions, so one item has several how-to cards. The first keeps the item's id; the others are
        # keyed "<id>@2", "<id>@3"..., and the portal pairs each card with the entry whose sentence it carries.
        key, n = card_id, 1
        while key in HALIA_HOW:
            if HALIA_HOW[key]["ja"] == entry["ja"]:
                raise SystemExit(f"ERROR: two Halia how-to cards for {card_id!r} say the same thing: {entry['ja']}")
            n += 1
            key = f"{card_id}@{n}"
        HALIA_HOW[key] = entry

    def name_of(item_id):
        return reg.register(item_id)

    for path in files:
        rel = path.relative_to(recipe_dir).as_posix()
        seen_published.add(f"halia/{rel}")
        data = json.loads(path.read_text(encoding="utf-8"))
        rtype = data.get("type")
        if rtype == HALIA_RECOLOUR:
            recolour += 1
            continue
        if rtype == HALIA_PLAYWRIGHT_BOOK:
            HALIA_SET_ASIDE_NAMES["playwright"].append(rel)
            continue
        if rtype == HALIA_BREW_POTION_INPUT and isinstance(data.get("input"), dict) and "potion_contents" in data["input"]:
            HALIA_SET_ASIDE_NAMES["brew_potion_contents"].append(rel)
            continue
        if halia_uncraftable(data):
            uncraftable += 1
            continue
        if rtype == "minecraft:blasting":
            ing = ingredient_id(data["ingredient"])
            ing_ja, _en, _t = reg.register(ing)
            secs = data["cookingtime"] / 20.0
            secs_txt = ("%d" % secs) if secs == int(secs) else ("%g" % secs)
            blast_id = halia_result_id(data["result"])
            how = "溶鉱炉で、%sを精錬する(%s 秒。作業台では作れない)" % (ing_ja, secs_txt)
            add(blast_id, None, None, how, [ing, "minecraft:blast_furnace"])
            how_to(blast_id, {"station": "blast", "inputs": [ing], "ja": how,
                              "en": "Smelt %s in a blast furnace (%s s; it cannot be made at a workbench)"
                                    % (_en, secs_txt)})
            made += 1
            continue
        if rtype == "minecraft:smelting":
            ing = ingredient_id(data["ingredient"])
            ing_ja, ing_en, _t = reg.register(ing)
            secs = data["cookingtime"] / 20.0
            secs_txt = ("%d" % secs) if secs == int(secs) else ("%g" % secs)
            res_id = halia_result_id(data["result"])
            how = "かまどで、%sを焼く(%s 秒。作業台では作れない)" % (ing_ja, secs_txt)
            add(res_id, None, None, how, [ing, "minecraft:furnace"])
            how_to(res_id, {"station": "furnace", "inputs": [ing], "ja": how,
                            "en": "Smelt %s in a furnace (%s s; it cannot be made at a workbench)"
                                  % (ing_en, secs_txt)})
            made += 1
            continue
        if rtype == "halia:storage_container_upgrade":
            # A cell upgraded in place on a crafting table: one of the sources and the part; the contents stay.
            # All sources are shown (any of them), not only the first.
            res_id = data["result"]
            srcs = list(data["sources"])
            part = data["part"]
            src_ja = [name_of(x)[0] for x in srcs]
            src_en = [name_of(x)[1] for x in srcs]
            part_ja, part_en, _t = name_of(part)
            res_ja, res_en, _t = name_of(res_id)
            src_txt_ja = ("・".join(src_ja) + " のどれか") if len(srcs) > 1 else src_ja[0]
            src_txt_en = " or ".join(src_en)
            how = "作業台で、%sと%sを並べると、中身を保ったまま%sになります。" % (src_txt_ja, part_ja, res_ja)
            add(res_id, None, None, how, srcs + [part])
            how_to(res_id, {"station": "workbench", "inputs": srcs + [part], "ja": how,
                            "en": "On a crafting table, put %s with %s: the upgrade keeps the contents, and "
                                  "the result is %s." % (src_txt_en, part_en, res_en)})
            made += 1
            continue
        if rtype == "halia:blank_augment_with_enchanted_book":
            # The Fortune I-III augments: a blank augment and an enchanted book of the named enchantment.
            ench = data["enchantment"]
            lvl = data["level"]
            ench_ja = (reg.van_ja.get("enchantment." + ench.replace(":", ".", 1)) or "").strip()
            ench_en = reg.van_en.get("enchantment." + ench.replace(":", ".", 1))
            # The Silk Touch augment's recipe says level 0, which is no roman numeral: the book is named without one
            # (the recipe says nothing more, and the sheet does not invent a level).
            if lvl == 0:
                lvl_ja = lvl_en = ""
            else:
                lvl_ja = reg.van_ja.get("enchantment.level.%d" % lvl)
                lvl_en = reg.van_en.get("enchantment.level.%d" % lvl)
            if not (ench_ja and ench_en and (lvl == 0 or (lvl_ja and lvl_en))):
                raise SystemExit(f"ERROR: the vanilla lang files do not name {ench} level {lvl} (halia/{rel}).")
            res_id = data["result"]["id"]
            blank_ja, blank_en, _t = name_of("halia:blank_augment")
            res_ja, res_en, _t = name_of(res_id)
            how = "作業台で、%sと、%s%s のエンチャントの本を並べると、%sになります。" % (
                blank_ja, ench_ja, (" " + lvl_ja) if lvl_ja else "", res_ja)
            add(res_id, None, None, how, ["halia:blank_augment", "minecraft:enchanted_book"])
            how_to(res_id, {"station": "workbench", "inputs": ["halia:blank_augment", "minecraft:enchanted_book"],
                            "ja": how,
                            "en": "On a crafting table, put a %s with an enchanted book of %s%s; the result is %s."
                                  % (blank_en, ench_en, (" " + lvl_en) if lvl_en else "", res_en)})
            made += 1
            continue
        if rtype == "minecraft:stonecutting":
            cut_id, cut_count, how, how_en, cut_ids = parse_stonecutting_recipe(path, reg)
            add(cut_id, None, cut_count, how, cut_ids + ["minecraft:stonecutter"])
            how_to(cut_id, {"station": "stonecutter", "inputs": cut_ids, "ja": how, "en": how_en})
            made += 1
            continue
        if rtype == "minecraft:brewing":
            # The Vigil's false buckets: the bucket stands in a bottle's place and the potion is the ingredient.
            base = data["input"]
            base = base["item"] if isinstance(base, dict) and set(base) == {"item"} else ingredient_id(base)
            reagent = data["reagent"]
            potion = (reagent.get("potion_contents") or {}).get("potions")
            if set(reagent) - {"item", "potion_contents"} or not potion:
                raise SystemExit(f"ERROR: halia/{rel}: a brewing reagent this script cannot name: {reagent}")
            kind = reagent["item"].split(":", 1)[1]           # potion / splash_potion / lingering_potion
            effect = potion.split(":", 1)[1].removeprefix("strong_").removeprefix("long_")
            pot_ja = reg.van_ja.get(f"item.minecraft.{kind}.effect.{effect}")
            pot_en = reg.van_en.get(f"item.minecraft.{kind}.effect.{effect}")
            strong = potion.split(":", 1)[1].startswith("strong_")
            if not (pot_ja and pot_en):
                raise SystemExit(f"ERROR: the vanilla lang files do not name {kind} of {potion} (halia/{rel}).")
            if strong:
                pot_ja, pot_en = pot_ja + " II", pot_en + " II"
            base_ja, base_en, _t = name_of(base)
            res_id = data["output"]["id"]
            how = "醸造台で、%sを瓶の場所に置き、%sを材料にする(作業台では作れない)" % (base_ja, pot_ja)
            how_en = ("In a brewing stand, put %s in a bottle's place and %s as the ingredient (it cannot be made "
                      "at a workbench)" % (base_en, pot_en))
            add(res_id, None, None, how, [base, reagent["item"], "minecraft:brewing_stand"])
            how_to(res_id, {"station": "brewing", "inputs": [base, reagent["item"]], "ja": how, "en": how_en})
            made += 1
            continue
        if rtype == "halia:framed_door":
            # The Coach-house and Keep doors: the door and five or more of one block, which becomes the frame.
            door = ingredient_id(data["door"])
            door_ja, door_en, _t = name_of(door)
            res_id = data["result"]["id"]
            how = "作業台で(並べ方は自由)、%sと、同じブロック 5 つ以上を並べる。そのブロックが枠になります。" % door_ja
            how_en = ("On a crafting table (any arrangement), put %s with five or more of one block; that block "
                      "becomes the frame." % door_en)
            add(res_id, None, None, how, [door])
            how_to(res_id, {"station": "workbench", "inputs": [door], "ja": how, "en": how_en})
            made += 1
            continue
        if rtype == "minecraft:crafting_dye":
            target = ingredient_id(data["target"])
            dye = ingredient_id(data["dye"])
            t_ja, t_en, _t = name_of(target)
            res_id = data["result"]["id"]
            how = "作業台で、%sと好きな染料を並べると、その色に染まります。" % t_ja
            how_en = "On a crafting table, put %s with any dye to colour it." % t_en
            add(res_id, None, None, how, [target, dye])
            how_to(res_id, {"station": "workbench", "inputs": [target, dye], "ja": how, "en": how_en})
            made += 1
            continue
        if rtype == "halia:limited_use_keycard_recipe":
            first_id, second_id = ingredient_id(data["first"]), ingredient_id(data["second"])
            f_ja, f_en, _t = name_of(first_id)
            s_ja, s_en, _t = name_of(second_id)
            res_id = halia_result_id(data["result"])
            cnt = int(data["result"].get("count", 1))
            how = "作業台で、%sと%sを並べると、回数に限りのある%sが %d 枚できます。" % (f_ja, s_ja, f_ja, cnt)
            how_en = "On a crafting table, put %s with %s: it makes %d %s with a limited number of uses." % (
                f_en, s_en, cnt, f_en)
            add(res_id, None, cnt, how, [first_id, second_id])
            how_to(res_id, {"station": "workbench", "inputs": [first_id, second_id], "ja": how, "en": how_en})
            made += 1
            continue
        if rtype == "halia:copy_position_component_item_recipe":
            src = ingredient_id(data["input"])
            s_ja, s_en, _t = name_of(src)
            res_id = data["result"] if isinstance(data["result"], str) else data["result"]["id"]
            how = "作業台で、設定済みの%sと新しい%sを並べると、設定を写した 2 つ目ができます。" % (s_ja, s_ja)
            how_en = "On a crafting table, put a set-up %s with a new one to copy its settings to it." % s_en
            add(res_id, None, None, how, [src])
            how_to(res_id, {"station": "workbench", "inputs": [src, src], "ja": how, "en": how_en})
            made += 1
            continue
        if rtype in ("halia:block_reinforcing_recipe", "halia:block_unreinforcing_recipe"):
            # Warding (and unwarding) any block it can ward: one json, no result of its own. The card is the tool.
            tools = [ingredient_id(t) for t in data["reinforcer"]]
            tool_ja = "・".join(name_of(t)[0] for t in tools)
            tool_en = " or ".join(name_of(t)[1] for t in tools)
            if rtype == "halia:block_reinforcing_recipe":
                how = "作業台で、護りの工具(%s のどれか)と護れるブロックを合わせると、護りのブロックになります。" % tool_ja
                how_en = ("On a crafting table, put a warding tool (%s) with any block it can ward to get the "
                          "warded block." % tool_en)
            else:
                how = "作業台で、護りのブロックと護りの工具(%s のどれか)を合わせると、元のブロックに戻ります。" % tool_ja
                how_en = ("On a crafting table, put a warded block with a warding tool (%s) to get the plain "
                          "block back." % tool_en)
            add(tools[0], None, None, how, tools)
            how_to(tools[0], {"station": "workbench", "inputs": tools, "ja": how, "en": how_en})
            made += 1
            continue
        parsed = parse_recipe(path)
        if parsed is None:
            raise SystemExit(f"ERROR: halia/{rel} (type {rtype}) is a kind of recipe this script cannot show.")
        result = data["result"]
        card_id = result if isinstance(result, str) else halia_result_id(result)
        add(card_id, parsed["cells"], parsed["count"], None)
        made += 1
        comp = {} if isinstance(result, str) else (result.get("components") or {})
        required = comp.get("halia:required_blade")
        if required is not None:
            # The box is half of the recipe: on an anvil, with the blade it names, it becomes the named blade.
            box_key = card_id[len("minecraft:chest["):-1]
            how = ((halia_index().get("anvil") or {}).get(box_key) or {}).get("ja")
            if not how:
                raise SystemExit(f"ERROR: data/halia_icons/index.json has no anvil step for {box_key!r}.")
            need_key = required.get("translation_key")
            need = f"{HALIA_BLADE}[{need_key}]" if need_key else HALIA_BLADE
            blade_id = halia_result_id(required["result"])
            add(blade_id, None, None, how, [card_id, need, "minecraft:anvil"])
            how_to(blade_id, {"station": "anvil", "inputs": [need, card_id], "ja": how,
                              "en": halia_index()["anvil"][box_key]["en"]})
            made += 1
            extra += 1
    return made, uncraftable, extra, recolour


DYE_COLOURS = ("white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray", "cyan",
               "purple", "blue", "brown", "green", "red", "black")


class ItemRegistry:
    """item id -> (日本語名, 英語名, テクスチャ key) を 1 回だけ解決して覚える。

    テクスチャは **中身(再圧縮後のバイト列)で一意化** する: 同じ絵を使う建材
    バリアント(石の縦ハーフ/円柱/スロープは全部 block/stone.png)や、何百回も
    出てくるバニラ素材が、ファイルに 1 回しか入らない。旧版はカードごとに同じ
    base64 を埋め直していた(建材だけで数 MB の重複)。
    """

    def __init__(self, van_ja, van_en, lang_by_modid, lang_en_by_modid):
        self.van_ja = van_ja
        self.van_en = van_en
        self.lang_by_modid = lang_by_modid
        self.lang_en_by_modid = lang_en_by_modid
        self.items = {}          # id -> [ja, en, tex_key or None]
        self.tex_payloads = {}   # b64 payload -> tex_key
        self.tex_order = []      # tex_key -> payload (emission order)
        self.raw_bytes = 0       # 再圧縮前の合計(統計用)
        # 公開済みの画像の番号を先に確保する(2026-09-30、ASTRAEA を足したとき): 番号は最初に登録された順に
        # 振られ、ブランドは名前順に読まれるので、"astraea" が "cherry" / "ouka" の前に来て既存の 198 枚が
        # 全部振り直された(中身は同じ、番号だけ別)。ポータルのレシピ頁は t<N> を使うので、公開済みの番号は
        # 動かさない —— 新しい画像だけが後ろ(t198…)に付く。種は origin/main の画像(公開物)で、この実行が
        # 上書きする作業木ではない。
        published = published_textures()
        for key, payload in published:
            self.tex_payloads[payload] = key
            self.tex_order.append(payload)
        self.next_tex = max((int(k[1:]) for k, _ in published), default=-1) + 1

    def _tex_key(self, b64):
        if b64 is None:
            return None
        raw = base64.b64decode(b64)
        self.raw_bytes += len(raw)
        packed = recompress_png(raw)
        payload = base64.b64encode(packed).decode()
        key = self.tex_payloads.get(payload)
        if key is None:
            key = f"t{self.next_tex}"
            self.next_tex += 1
            self.tex_payloads[payload] = key
            self.tex_order.append(payload)
        return key

    def halia_member_names(self, item_id):
        """(ja, en) of one Halia item from the jar's own lang, without a picture (for a tag's list of names)."""
        modid, name = item_id.split(":", 1)
        lang_key = (halia_index().get("items") or {}).get(item_id, {}).get("lang")
        if lang_key:
            ja, en = self.lang_by_modid["halia"].get(lang_key), self.lang_en_by_modid["halia"].get(lang_key)
        else:
            ja = display_name(self.lang_by_modid["halia"], modid, name)
            en = display_name(self.lang_en_by_modid["halia"], modid, name)
            if ja == name or en == name:
                # A dyed device (white_artificer): the jar names it with its colour and its base device, through its own
                # template item.halia.color_and_item_name ("%s %s"), and the colour is the vanilla dye name.
                color = next((c for c in sorted(DYE_COLOURS, key=len, reverse=True) if name.startswith(c + "_")), None)
                base = name[len(color) + 1:] if color else ""
                if not color or not base:
                    raise SystemExit("ERROR: the Halia jar's lang files do not name %s" % item_id)
                base_ja, base_en = (self.lang_by_modid["halia"].get("item.halia." + base)
                                    or self.lang_by_modid["halia"].get("block.halia." + base),
                                    self.lang_en_by_modid["halia"].get("item.halia." + base)
                                    or self.lang_en_by_modid["halia"].get("block.halia." + base))
                tmpl_ja = self.lang_by_modid["halia"].get("item.halia.color_and_item_name")
                tmpl_en = self.lang_en_by_modid["halia"].get("item.halia.color_and_item_name")
                col_ja = self.van_ja.get("color.minecraft." + color)
                col_en = self.van_en.get("color.minecraft." + color)
                if not (base_ja and base_en and tmpl_ja and tmpl_en and col_ja and col_en):
                    raise SystemExit("ERROR: the Halia jar's lang files do not name %s" % item_id)
                ja, en = tmpl_ja % (col_ja, base_ja), tmpl_en % (col_en, base_en)
        if not ja or not en or ja == name or en == name:
            raise SystemExit("ERROR: the Halia jar's lang files do not name %s" % item_id)
        return [ja, en, None]

    def register(self, item_id):
        entry = self.items.get(item_id)
        if entry is not None:
            return entry
        ns, name = item_id.split(":", 1)
        if (ns == "halia" and name.startswith(("warded_", "hushed_"))
                and item_id not in (halia_index().get("items") or {})):
            # Halia 1.3.0: the Vigil's 593 warded blocks (and hushed signs) are the plain vanilla block drawn with a
            # tint (assets/halia/items/warded_*.json point at minecraft:block/<plain>). The card shows the plain
            # block's picture; the name is the jar's own. A plain id vanilla does not name stops the generation.
            plain = "minecraft:" + name.split("_", 1)[1].removesuffix("_item")
            tex = halia_warded_texture(name)
            if tex is not None:
                ja = display_name(self.lang_by_modid["halia"], ns, name)
                en = display_name(self.lang_en_by_modid["halia"], ns, name)
                if ja == name or en == name:
                    raise SystemExit("ERROR: the Halia jar's lang files do not name %s" % item_id)
                entry = [ja, en, self._tex_key(tex)]
                self.items[item_id] = entry
                return entry
            if not (self.van_ja.get("block." + plain.replace(":", ".")) or self.van_ja.get("item." + plain.replace(":", "."))):
                raise SystemExit(f"ERROR: {item_id} has no picture in data/halia_icons/ and {plain} is not a vanilla block.")
            ja = display_name(self.lang_by_modid["halia"], ns, name)
            en = display_name(self.lang_en_by_modid["halia"], ns, name)
            if ja == name or en == name:
                raise SystemExit("ERROR: the Halia jar's lang files do not name %s" % item_id)
            entry = [ja, en, self.register(plain)[2]]
            self.items[item_id] = entry
            return entry
        if item_id.startswith((HALIA_BLADE + "[", "minecraft:chest[item.halia.")):
            key = item_id[item_id.index("[") + 1:-1]
            ja = self.lang_by_modid["halia"].get(key)
            en = self.lang_en_by_modid["halia"].get(key)
            if not ja or not en:
                raise SystemExit("ERROR: the Halia jar's lang files do not translate %s" % key)
            if item_id.startswith(HALIA_BLADE):
                b64 = halia_icon_b64("blades", key)
            else:
                # Every material box is a vanilla chest with a custom name: one render serves all nine.
                png = HALIA_ICON_DIR / ((halia_index().get("box_icon") or {}).get("file") or "")
                if not png.is_file():
                    raise SystemExit("ERROR: the Halia icon index names no box picture (box_icon.file).")
                b64 = _halia_png_b64(png)
            entry = [ja, en, self._tex_key(b64)]
            self.items[item_id] = entry
            return entry
        if "[" in name:
            # An ingredient that is a data-component stack (2026-10-05): `minecraft:potion[water]`, from
            # {"fabric:type":"fabric:components","base":"minecraft:potion","components":{potion_contents:...}}.
            # Only the Water Bottle is understood; any other qualifier stops the generation (see ingredient_id).
            if item_id != "minecraft:potion[water]":
                raise SystemExit("ERROR: register() does not know the qualified ingredient %s" % item_id)
            ja = self.van_ja.get("item.minecraft.potion.effect.water")
            en = self.van_en.get("item.minecraft.potion.effect.water")
            if not ja or not en:
                raise SystemExit("ERROR: the vanilla lang files have no item.minecraft.potion.effect.water")
            b64 = compose_water_bottle_icon(vanilla_zip())
            entry = [ja, en, self._tex_key(b64)]
            self.items[item_id] = entry
            return entry
        if ns.startswith("#") and ns != "#minecraft":
            # A tag of a staged mod (`#tsubomi:copper_quartz_repair`): shown as the vanilla tags are - one
            # representative icon (the first member) and a name that says any of them will do.
            members = mod_item_tag(ns[1:], name)
            if ns == "#halia":
                # Halia's Aerie lists each device in its 16 dyes, and the 16 colour variants have no pictures of their
                # own (the icon index draws the base device). The names come from the jar's lang for every member;
                # the picture is the first member that has one, which is the base device (the tag's first entries are
                # the white variants). A tag with no member that has a picture stops the generation.
                member_entries = [self.halia_member_names(m) for m in members]
                rep = next((m for m in members if m in (halia_index().get("items") or {})), None)
                if rep is None:
                    # Halia 1.3.0: the Vigil's tags list warded blocks, drawn as their plain blocks (register()).
                    rep = next((m for m in members if m.split(":", 1)[1].startswith(("warded_", "hushed_"))), None)
                if rep is None:
                    raise SystemExit("ERROR: the Halia tag #%s has no member with a picture in data/halia_icons/"
                                     % name)
                pic = self.register(rep)[2]
            else:
                member_entries = [self.register(m) for m in members]
                pic = member_entries[0][2]
            mem_ja = [e[0] for e in member_entries]
            mem_en = [e[1] for e in member_entries]
            if len(members) > 4:
                ja = "・".join(mem_ja[:4]) + f" ほか {len(members) - 4} 種のどれか"
                en = ", ".join(mem_en[:4]) + f" or {len(members) - 4} more"
            else:
                ja = "・".join(mem_ja) + " のどれか" if len(members) > 1 else mem_ja[0]
                en = " or ".join(mem_en)
            entry = [ja, en, pic]
            self.items[item_id] = entry
            return entry
        if ns == "minecraft":
            ja = (self.van_ja.get(f"item.minecraft.{name}")
                  or self.van_ja.get(f"block.minecraft.{name}")
                  or VANILLA_JA_NAMES.get(name, name))
            en = (self.van_en.get(f"item.minecraft.{name}")
                  or self.van_en.get(f"block.minecraft.{name}")
                  or name.replace("_", " ").title())
            b64 = vanilla_texture_b64(vanilla_zip(), name)
        elif ns == "#minecraft":
            # バニラのアイテムタグ(`#minecraft:coals` など)。**中身は jar から読む。**
            # 見せかたは「代表 1 個のアイコン + どれでもよいことが分かる名前」。
            # アイコンを最初の 1 個にするのは、タグの並びが**バニラ側の宣言順**
            # だからで、こちらで選び直さない(選び直すと出典が 2 つになる)。
            members = vanilla_item_tag(name)
            mem_ja, mem_en = [], []
            for mid in members:
                mname = mid.split(":", 1)[1]
                mem_ja.append(self.van_ja.get(f"item.minecraft.{mname}")
                              or self.van_ja.get(f"block.minecraft.{mname}")
                              or VANILLA_JA_NAMES.get(mname, mname))
                mem_en.append(self.van_en.get(f"item.minecraft.{mname}")
                              or self.van_en.get(f"block.minecraft.{mname}")
                              or mname.replace("_", " ").title())
            # 長いタグは全部並べても読めないので、4 個まで挙げて残りは数で言う。
            # **黙って切らない** —— 「ほか N 種」と書けば、全部ではないことが分かる。
            if len(members) > 4:
                ja = "・".join(mem_ja[:4]) + f" ほか {len(members) - 4} 種のどれか"
                en = ", ".join(mem_en[:4]) + f" or {len(members) - 4} more"
            else:
                ja = "・".join(mem_ja) + " のどれか" if len(members) > 1 else mem_ja[0]
                en = " or ".join(mem_en)
            b64 = vanilla_texture_b64(vanilla_zip(), members[0].split(":", 1)[1])
        else:
            for mod_dir, modid, _cat in MODS:
                if modid == ns:
                    lang_key = (halia_index().get("items") or {}).get(item_id, {}).get("lang") if modid == "halia" else None
                    if lang_key:
                        ja = self.lang_by_modid[modid].get(lang_key)
                        en = self.lang_en_by_modid[modid].get(lang_key)
                        if not ja or not en:
                            raise SystemExit("ERROR: the Halia icon index names %s as %s, which the jar does not translate."
                                             % (item_id, lang_key))
                    else:
                        ja = display_name(self.lang_by_modid[modid], modid, name)
                        en = display_name(self.lang_en_by_modid[modid], modid, name)
                    b64 = mod_texture_b64(mod_dir, modid, name)
                    break
            else:
                # 未知の名前空間。バニラでない MOD のタグなど。現れたら黙って
                # 空欄にせず名指しする(§20.6 系の「静かな劣化」を作らない)。
                print(f"WARNING: unknown namespace in ingredient id {item_id}")
                ja = en = item_id
                b64 = None
        entry = [ja, en, self._tex_key(b64)]
        self.items[item_id] = entry
        return entry


# ===========================================================================
# ページ用のドット絵アセット(背景の土タイル・クラフト矢印)
# ===========================================================================
def gen_bg_tile_b64(zf):
    """バニラの dirt.png を 1/4 の明るさに落として 4 倍 NEAREST 拡大したタイル。
    (Minecraft のメニュー背景と同じ作法。CSS 拡大に頼らないのは、背景画像の
    image-rendering:pixelated 対応がブラウザでまちまちなため。)"""
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(zf.read("assets/minecraft/textures/block/dirt.png")))
        img = img.convert("RGB")
        img = Image.eval(img, lambda v: v // 4)
        img = img.resize((64, 64), Image.NEAREST)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: could not build the dirt background tile: {exc}")
        return None


def gen_arrow_b64():
    """クラフト画面の「→」矢印(26x17)を PIL で作図する(jar のスプライトパスは
    版で動くので推測しない。自作なので確実に存在し、ライセンスも問題にならない)。"""
    from PIL import Image
    import io
    body = (94, 94, 94, 255)
    img = Image.new("RGBA", (26, 17), (0, 0, 0, 0))
    px = img.load()
    for y in range(6, 11):          # 軸(高さ 5px)
        for x in range(2, 16):
            px[x, y] = body
    for i, x in enumerate(range(16, 25)):   # 鏃(半幅 8 -> 0)
        hw = 8 - i
        for y in range(8 - hw, 9 + hw):
            px[x, y] = body
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


# ジャンルタブのアイコン(そのジャンルの実在カードの id)。存在しない id を書いたら
# 黙って空タブにせず WARNING + そのジャンルの先頭カードで代用する。
CATEGORY_TAB_ICON = {
    "銃": "sorakaze_guns:assault_rifle",
    "電車": "sorakaze_rail:train",
    "建材": "sorakaze_deco:guardrail",
    "ドア": "sorakaze_deco:wheel_vault_door",  # V4.2.2: 自動ドアは削除された
    "乗り物": "sorakaze_vehicles:compact_car_scarlet",
    "ボス": "sorakaze_boss:enhanced_beacon",
    "天空": "sorakaze_sky:angels_halo",
    "サバイバル": "sorakaze_survival:canteen",
    "電力": "sorakaze_power:breaker",
    "二相楽園": "sorakaze_planarcadia:portal_amethyst_block",
    "灰街圏": "sorakaze_fallout:filter_mask",
    # 別ブランド(Alpha の同梱 MOD ではない)。2026-09-20。
    **BRAND_TAB_ICON,
}
ALL_TAB_ICON = "minecraft:crafting_table"


def first(v):
    return v[0] if isinstance(v, list) else v


FABRIC_API_VERSION = "0.161.0+26.3"   # the version Halia 1.2.0 is built against (its own build file)
_CONVENTION_ZIP = None


def convention_tags_zip():
    """The Fabric convention-tags module (fabric-convention-tags-v2) that ships inside Fabric API 0.161.0+26.3,
    read from the Gradle cache of the Halia build. Stops with the reason if the cache is not there."""
    global _CONVENTION_ZIP
    if _CONVENTION_ZIP is None:
        base = Path.home() / ".gradle/caches/modules-2/files-2.1/net.fabricmc.fabric-api/fabric-api"
        hits = sorted(base.glob(f"{FABRIC_API_VERSION}/*/fabric-api-{FABRIC_API_VERSION}.jar"))
        if not hits:
            raise SystemExit(f"ERROR: Halia's recipes use Fabric's common tags (#c:...), which Fabric API "
                             f"{FABRIC_API_VERSION} provides, and no copy of that jar is in {base}. "
                             f"Without it the tags cannot be opened.")
        with zipfile.ZipFile(hits[0]) as outer:
            nested = [n for n in outer.namelist()
                      if n.startswith("META-INF/jars/fabric-convention-tags-v2-") and n.endswith(".jar")]
            if len(nested) != 1:
                raise SystemExit(f"ERROR: {hits[0]} carries {len(nested)} convention-tags module(s), not one.")
            _CONVENTION_ZIP = zipfile.ZipFile(io.BytesIO(outer.read(nested[0])))
    return _CONVENTION_ZIP


def common_tag_members(name, seen):
    """`#c:<name>` -> the item ids, opened from the convention tag file. A nested `#c:` / `#minecraft:` / `#mod:`
    reference is opened the same way; an entry marked "required": false that cannot be opened is skipped (that is
    what the flag means), anything else that cannot be opened stops the generation."""
    key = ("c", name)
    if key in _MOD_TAG_CACHE:
        return _MOD_TAG_CACHE[key]
    zf = convention_tags_zip()
    path = f"data/c/tags/item/{name}.json"
    if path not in zf.namelist():
        raise SystemExit(f"ERROR: a recipe uses the item tag #c:{name}, which the Fabric convention tags do not define.")
    out = []
    for v in json.loads(zf.read(path).decode("utf-8"))["values"]:
        optional = isinstance(v, dict) and v.get("required") is False
        vid = v["id"] if isinstance(v, dict) else v
        if vid.startswith("#"):
            tns, tname = vid[1:].split(":", 1)
            try:
                if tns == "c":
                    members = common_tag_members(tname, seen)
                elif tns == "minecraft":
                    members = vanilla_item_tag(tname)
                else:
                    members = mod_item_tag(tns, tname, seen)
            except SystemExit:
                if optional:
                    continue
                raise
        else:
            members = [vid]
        for m in members:
            if m not in out:
                out.append(m)
    if not out:
        raise SystemExit(f"ERROR: item tag #c:{name} resolved to nothing - the card would show an empty slot "
                         f"where an ingredient belongs")
    _MOD_TAG_CACHE[key] = out
    return out


def ingredient_id(ing):
    """One ingredient -> the id string the sheet keys it by.

    A plain id or `#tag` is itself (a list means "any of these"; the first is shown, as before). A
    data-component stack (Tsubomi's herbal tea asks for a Water Bottle, 2026-10-05) becomes
    `minecraft:potion[water]`. Anything else with components stops the generation: guessing would draw a plain
    potion for a recipe that needs water."""
    ing = first(ing)
    if isinstance(ing, dict):
        comp = ing.get("components") or {}
        pot = (comp.get("minecraft:potion_contents") or {}).get("potion")
        if (ing.get("fabric:type") == "fabric:components" and ing.get("base") == "minecraft:potion"
                and list(comp) == ["minecraft:potion_contents"] and pot == "minecraft:water"):
            return "minecraft:potion[water]"
        raise SystemExit("ERROR: parse_recipe met an ingredient it cannot show: %s" % json.dumps(ing))
    return ing


def parse_recipe(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    rtype = data.get("type", "")
    cells = [None] * 9
    if rtype == "minecraft:crafting_shaped":
        pattern = data["pattern"]
        key = data["key"]
        for row_i, row in enumerate(pattern):
            for col_i, ch in enumerate(row):
                if ch == " ":
                    continue
                cells[row_i * 3 + col_i] = ingredient_id(key.get(ch))
    elif rtype == "minecraft:crafting_shapeless":
        for i, ing in enumerate(data["ingredients"][:9]):
            cells[i] = ingredient_id(ing)
    else:
        return None  # skip non-crafting-table recipe types (none expected currently)
    result = data.get("result", {})
    return {"cells": cells, "result_id": result.get("id"), "count": result.get("count", 1)}


# Brands whose published recipes must ALL appear as a card (2026-10-05). The older brands skip the recipe types a
# 3x3 grid cannot show (smelting, smithing, machine recipes) - a long-standing, unchanged choice. Tsubomi has
# fifteen recipes and the owner asked for the revived Teleport Elevator to be listed, so for it a skipped recipe
# is a fault: the generation stops and names the file.
EVERY_RECIPE_SHOWN = {"tsubomi", "halia"}


def parse_campfire_recipe(path, reg):
    """A `minecraft:campfire_cooking` recipe -> (result id, how-to text, ingredient ids), else None.

    The text is assembled from the recipe's own fields (ingredient, cookingtime in ticks); nothing about the
    recipe is typed here. The ingredient is registered, so a tag is opened and named like any other."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "minecraft:campfire_cooking":
        return None
    ing = ingredient_id(data["ingredient"])
    ing_ja, _en, _t = reg.register(ing)
    ticks = data["cookingtime"]
    secs = ticks / 20.0
    secs_txt = ("%d" % secs) if secs == int(secs) else ("%g" % secs)
    how = "焚き火で、%sを焼く(%s 秒。作業台では作れない)" % (ing_ja, secs_txt)
    return data["result"]["id"], how, [ing]


def parse_stonecutting_recipe(path, reg):
    """A `minecraft:stonecutting` recipe -> (result id, count, how-to text ja, how-to text en, ingredient ids), else None.

    Tsubomi 2.0.0 (2026-10-18) ships 120 of them. A stonecutter takes one ingredient and gives the result times
    the recipe's count; the sentence is assembled from those fields only. The card is a how-to card (no grid), so
    the sheet's data shape is unchanged: the Store's album shows the sentence as it shows a campfire's."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "minecraft:stonecutting":
        return None
    ing = ingredient_id(data["ingredient"])
    ing_ja, ing_en, _t = reg.register(ing)
    result = data["result"]
    count = int(result.get("count", 1))
    if count < 1:
        raise SystemExit(f"ERROR: {path.name}: a stonecutting recipe with count {count}")
    many_ja = "" if count == 1 else "(%d 個できる)" % count
    many_en = "" if count == 1 else " (makes %d)" % count
    how = "石切台で、%sを切り出す%s(作業台では作れない)" % (ing_ja, many_ja)
    how_en = "Cut %s on a stonecutter%s (it cannot be made at a workbench)" % (ing_en, many_en)
    return result["id"], count, how, how_en, [ing]


def cat_tokens(cat):
    """ジャンル名の検索語。漢字でもひらがなでも同じ結果になるように読みも入れる
    (「電車」で 35 件・「でんしゃ」で 21 件、のような食い違いを作らない)。"""
    return [cat, kana_fold(cat), reading_of(cat)[0]]


def search_blob(tokens):
    """検索用の索引文字列を作る。JS 側は正規化済みのクエリを indexOf するだけでよい。"""
    seen = []
    for t in tokens:
        if not t:
            continue
        t = search_norm(str(t))
        if t not in seen:
            seen.append(t)
    return " ".join(seen)


def item_tokens(item_id, ja_name):
    """1 アイテムぶんの検索語(日本語名・読み・かな畳み・英語 id)を返す。"""
    yomi, _ = reading_of(ja_name)
    local = item_id.split(":", 1)[1] if ":" in item_id else item_id
    return [ja_name, kana_fold(ja_name), yomi, _expand_choon(kana_fold(yomi)),
            item_id, local, local.replace("_", " ")]


def category_of(mod_cat, result_name):
    # v1.5.0: 建材 MOD のドアは 9 種 -> 98 種に増えた。DOOR_IDS の手書きリストだけで判定していると
    # v1.4.4 の 40 種と v1.5.0 の 50 種が 254 枚の建材カードに埋もれて探せない(実際そうなっていた)。
    # 命名規則(<素材>_<意匠>_door / *_grand_door)で機械的に振り分け、
    # 規則から外れる旧名(ふすま・ハッチ・シャッター・大型ドア)だけを DOOR_IDS で拾う。
    if mod_cat == "建材" and (result_name in DOOR_IDS
                              or result_name.endswith("_door")
                              or result_name.endswith("_hatch")
                              or result_name.endswith("_hatch_large")):
        return "ドア"
    return mod_cat


# ===========================================================================
# 「使い方」タブ(v1.8.1 で新設)
# ===========================================================================
#
# **レシピのカードは「何で作るか」しか答えない。「何ができるのか」は答えない。**
# v1.8.0 で自動仕分けの 10 種を出したが、早見表からは作り方しか分からず、
# 所有者が使い方に辿り着けなかった。ここはその穴を埋めるための場所である。
#
# 方針(発注): **絵で見せる。文章で説明しない。**
# 各例は「置きかた図 / 入るもの / 出るもの / 手順」の 4 つで構成する。
#
# 拡張のしかた: `GUIDES` に dict を 1 つ足すだけでタブの中に節が増える。
# 次のラウンドで来る「電源」「ブレーカー盤」も、この表に足すだけでよい。
#
# 図のセルの書きかた:
#   ("i", "<アイテム id>", "<下に出す短い説明>")   アイコン + 説明
#   ("a", "→")                                    矢印(→ ↓ ← ↑ が使える)
#   ("n", "文字")                                  文字だけのセル
#   None                                           空白
#
# ⚠ ここで使う id は**すべて実在しなければならない**。
# 存在しない id を書くと、ページ上は「?」の四角が出るだけで、生成は成功してしまう
# (§37 で 1 枚の「?」カードとして表に出た失敗と同じ形)。
# そうならないよう、main() が 3 つの検査を行い、1 つでも欠ければ**生成を止める**:
#   ① GUIDES が触れる id が全部 register() できてテクスチャを持つこと
#   ② SORTING_KIT の 10 種が全部カードとして実在すること
#   ③ SORTING_KIT の 10 種が全部どれかの図に登場すること(= 説明されていない部品が無い)

# 自動仕分け一式(sorakaze_deco の ModSorters と同じ 10 個)。
# ③ の検査に使う。ここを増やしたのに図に足さなければ、生成が落ちる。
SORTING_KIT = [
    "sorakaze_deco:sorting_filter",
    "sorakaze_deco:category_sorter",
    "sorakaze_deco:round_robin_splitter",
    "sorakaze_deco:overflow_valve",
    "sorakaze_deco:void_trash",
    "sorakaze_deco:item_pump",
    "sorakaze_deco:item_counter",
    "sorakaze_deco:stock_indicator",
    "sorakaze_deco:item_collector",
    "sorakaze_deco:filter_card",
]

# ===========================================================================
# 電力 MOD の数値を **実装から読む**(v1.8.2 で新設)
# ===========================================================================
#
# ⚠ **手引きに数字を打ち込んではならない。**
#
# 電力の数値は複数の作業が並行して動かしている最中の物である。手で書き写すと、
# 書いた瞬間は正しくても<b>出荷される頃には嘘になっている</b>。しかも早見表は
# 「本文だから」という理由で誰も検算しないので、その嘘は永久に残る。
#
# そこで食料品 300 種を `FoodCatalog.java` から直接読んでいるのと同じ方式にする:
# **出典は Java のソースと data の JSON だけ**で、ここには写しを置かない。
# 手引きの本文は `{fact}` の置換で数値を受け取る(→ `fill_facts`)。
#
# 検査(生成を止める側):
#   ⓐ 読もうとしたフィールドが 1 つでも消える/改名されると `SystemExit`。
#      —— §31.4 の「黙って落ちる」を作らないため、**欠落は必ずエラー**である。
#   ⓑ 手引きが使う `{fact}` が表に無ければ `SystemExit`。
#   ⓒ 逆に、表にあるのにどの手引きでも使われていない fact も `SystemExit`
#      (古い数字の残骸が「読まれているように見えて実は死んでいる」状態を作らない)。

POWER_JAVA = ROOT / "mods-src/sorakaze-power/src/main/java/net/sorakaze/sorakaze_power"
SURVIVAL_JAVA = ROOT / "mods-src/sorakaze-survival/src/main/java/net/sorakaze/sorakaze_survival"
POWER_TAGS = ROOT / "mods-src/sorakaze-power/src/main/resources/data/sorakaze_power/tags/block"

_JNUM = r"(-?\d+(?:_\d+)*(?:\.\d+)?(?:[eE][-+]?\d+)?[dDfFlL]?)"


def _java_number(tok):
    """Java の数値リテラル 1 個を Python の数に。"""
    t = tok.strip().rstrip("dDfFlL").replace("_", "")
    return int(t) if re.fullmatch(r"-?\d+", t) else float(t)


_CABLE_TIERS_CACHE = None


def cable_tiers():
    """`CableTier.java` の enum 宣言を読む -> [(定数名, ブロック名, 断面積, 絶縁階級)]。

    v1.8.4 でケーブルは 2 種類から 4 種類になり、同時に `PowerSpec` の既定の抵抗値が
    **リテラルをやめて enum から導く式**(`DEFAULT_STANDARD_OHMS_PER_BLOCK /
    tier.conductorAreaFactor()`)になった。だから早見表も同じ 1 個の出典から読む ——
    ここに断面積を書き写すと、`CableTier` を触った瞬間に手引きが嘘になる。

    **取れなければ生成を止める。**黙って 2 種類のままの手引きを出すほうが害が大きい。
    """
    global _CABLE_TIERS_CACHE
    if _CABLE_TIERS_CACHE is None:
        src = (POWER_JAVA / "grid/CableTier.java").read_text(encoding="utf-8")
        hits = re.findall(r'^\t([A-Z][A-Z0-9_]*)\("([a-z_]+)",\s*(\d+),\s*Voltage\.([A-Z0-9_]+)\)',
                          src, re.M)
        if not hits:
            raise SystemExit(
                "ERROR: the 使い方 tab could not read the CableTier enum constants - the shape "
                "of grid/CableTier.java changed.\n"
                "       Fix tools/gen_recipe_sheet.py rather than shipping a stale cable guide.")
        _CABLE_TIERS_CACHE = [(n, b, int(a), v) for n, b, a, v in hits]
    return _CABLE_TIERS_CACHE


def _expand_cable_tier_calls(raw):
    """`defaultOhmsPerBlock(CableTier.X)` を `(標準の抵抗 / 断面積)` に開く。

    断面積は {@link cable_tiers} = `CableTier.java` から読むので、この関数は
    **数を 1 つも持たない**。開いた先の `DEFAULT_STANDARD_OHMS_PER_BLOCK` は
    宣言順に先に解けているので、そのまま `_resolve_java_expr` が数にできる。
    """
    if "defaultOhmsPerBlock" not in raw:
        return raw
    factors = {name: area for name, _blk, area, _v in cable_tiers()}

    def sub(m):
        tier = m.group(1)
        if tier not in factors:
            raise SystemExit(
                "ERROR: the 使い方 tab found defaultOhmsPerBlock(CableTier.%s), but that tier "
                "is not declared in grid/CableTier.java" % tier)
        return "(DEFAULT_STANDARD_OHMS_PER_BLOCK / %d)" % factors[tier]

    return re.sub(r"(?:[A-Za-z_$][\w$]*\.)?defaultOhmsPerBlock\(\s*CableTier\.([A-Z0-9_]+)\s*\)",
                  sub, raw)


def java_field_defaults(path, names):
    """`public [static final] <型> <名> = <式>;` の右辺を名前 -> 文字列で返す。

    **宣言だけを拾う**(`public` と型トークンを要求する)ので、`validate()` の中の
    `this.x = this.xClamped();` のような代入には引っかからない。
    1 つでも見つからなければ **その場で生成を止める** —— 改名を黙って見逃すと、
    手引きは古い数字を出したまま「成功」してしまう。
    """
    src = path.read_text(encoding="utf-8")
    found = {}
    for name in names:
        m = re.search(r"public\s+(?:static\s+final\s+)?[A-Za-z_$][\w$<>\[\].]*\s+"
                      + re.escape(name) + r"\s*=\s*([^;]+);", src)
        if m:
            found[name] = m.group(1).strip()
    missing = [n for n in names if n not in found]
    if missing:
        raise SystemExit(
            "ERROR: the 使い方 tab reads %d field(s) that no longer exist in %s "
            "(renamed or deleted?): %s\n"
            "       Fix tools/gen_recipe_sheet.py rather than shipping a stale number."
            % (len(missing), path.relative_to(ROOT), ", ".join(missing)))
    return found


def _resolve_java_expr(raw, known):
    """リテラル / 既知の定数 / `A / 2.0` 程度の式を数に解く(eval は数式だけに限定)。"""
    raw = _expand_cable_tier_calls(raw.strip())
    if raw in ("true", "false"):
        return raw == "true"
    if re.fullmatch(_JNUM, raw):
        return _java_number(raw)
    if re.fullmatch(r'"[^"]*"', raw):
        return raw[1:-1]
    expr = re.sub(r"\b[A-Z][A-Za-z0-9_]*\.", "", raw)          # PowerSpec.X -> X
    for key, val in sorted(known.items(), key=lambda kv: -len(kv[0])):
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            expr = re.sub(r"\b" + re.escape(key) + r"\b", repr(val), expr)
    expr = re.sub(r"(\d)[dDfFlL]\b", r"\1", expr)
    if not re.fullmatch(r"[-+*/(). 0-9eE]+", expr.strip()):
        raise SystemExit("ERROR: 使い方 tab cannot resolve the Java expression %r "
                         "(it stopped being a simple number)" % raw)
    return eval(expr, {"__builtins__": {}}, {})                # 数式のみ(上で検証済み)


def _java_regex(path, pattern, what, flags=0, many=False):
    """1 個の正規表現で読む。**取れなければ生成を止める。**"""
    src = path.read_text(encoding="utf-8")
    if many:
        hits = re.findall(pattern, src, flags)
        if not hits:
            raise SystemExit("ERROR: the 使い方 tab found no %s in %s - the shape of that "
                             "file changed" % (what, path.relative_to(ROOT)))
        return hits
    m = re.search(pattern, src, flags)
    if not m:
        raise SystemExit("ERROR: the 使い方 tab could not read %s from %s - the shape of that "
                         "file changed" % (what, path.relative_to(ROOT)))
    return m


def tag_block_ids(name):
    """`data/sorakaze_power/tags/block/<name>.json` の値を id の並びで返す。

    `{"id": ..., "required": false}` の形も素の文字列も同じに扱う。
    `#other:tag` の参照はそのまま返す(呼び出し側で除く)。
    """
    path = POWER_TAGS / (name + ".json")
    if not path.exists():
        raise SystemExit("ERROR: the 使い方 tab needs the block tag %s, which does not exist "
                         "(renamed or deleted?)" % path.relative_to(ROOT))
    out = []
    for v in json.loads(path.read_text(encoding="utf-8"))["values"]:
        out.append(v["id"] if isinstance(v, dict) else v)
    if not out:
        raise SystemExit("ERROR: block tag %s is empty - the 使い方 tab would silently "
                         "describe nothing" % name)
    return out


def _fmt(x, nd=0):
    """人が読む数(3 桁区切り。小数は必要なぶんだけ)。"""
    if isinstance(x, float) and not x.is_integer():
        return f"{x:,.{nd or 2}f}".rstrip("0").rstrip(".")
    return f"{int(x):,}"


_GATE_LANG_CACHE = {}


def ja_block_names(ids):
    """ブロック id の並び -> 「A・B・C」(日本語名を中黒でつないだ 1 つの文字列)。

    v1.8.4 で「通電すると止まる」装置が 17 → 3 になり、**数えるより名前で言うほうが
    親切な数**になったので用意した。名前は各 MOD の `ja_jp.json` から引く ——
    <b>ここに名前を書き写さない</b>。写した瞬間に 2 つ目の出典ができて、
    ブロックを改名した日に手引きだけが古くなる(このファイルが繰り返し防いできた失敗)。

    タグ参照(`#...`)は飛ばす。引けない id があれば **その場で生成を止める**:
    生の id を所有者に見せるくらいなら、生成を失敗させたほうがよい。
    """
    mod_dir_by_modid = {modid: mod_dir for mod_dir, modid, _ in MODS}
    names = []
    for iid in ids:
        if iid.startswith("#"):
            continue
        modid, name = iid.split(":", 1)
        if modid not in _GATE_LANG_CACHE:
            if modid not in mod_dir_by_modid:
                raise SystemExit(
                    "ERROR: the 使い方 tab cannot name %s - %r is not one of the MODS, so its "
                    "ja_jp.json is unknown" % (iid, modid))
            _GATE_LANG_CACHE[modid] = load_lang(mod_dir_by_modid[modid], modid)
        ja = _GATE_LANG_CACHE[modid].get("block.%s.%s" % (modid, name))
        if not ja:
            raise SystemExit(
                "ERROR: the 使い方 tab has no Japanese name for %s (block.%s.%s is missing from "
                "ja_jp.json) - the guide would print a raw id at the owner"
                % (iid, modid, name))
        names.append(ja)
    if not names:
        raise SystemExit("ERROR: the 使い方 tab was asked to name an empty set of blocks - "
                         "the guide would render a dangling sentence")
    return "・".join(names)


def read_power_facts():
    """電力の数値を実装から集める。**返る dict が手引きの唯一の数字の出典である。**"""
    cfg_path = POWER_JAVA / "config/PowerConfig.java"
    spec_path = POWER_JAVA / "grid/PowerSpec.java"

    spec_names = ["DEFAULT_STANDARD_OHMS_PER_BLOCK", "DEFAULT_INSULATED_OHMS_PER_BLOCK",
                  "DEFAULT_HEAVY_OHMS_PER_BLOCK", "DEFAULT_SHIELDED_OHMS_PER_BLOCK",
                  "DEFAULT_LOSS_BUDGET_FRACTION", "DEFAULT_REFERENCE_BRANCH_WATTS",
                  "DEFAULT_TRANSFORMER_CROSSOVER_BLOCKS", "DEFAULT_DEVICE_WATTS",
                  "DEFAULT_MAX_NODES"]
    raw_spec = java_field_defaults(spec_path, spec_names)
    spec = {}
    for n in spec_names:                       # 宣言順に解くので `A / 2.0` が解ける
        spec[n] = _resolve_java_expr(raw_spec[n], spec)

    # ⚠ v1.8.4: `hoppersRequirePower` を**読むのをやめた**。あのつまみは
    # `HopperPowerLockMixin` / `PowerFuelHoppers` ごと削除されており、
    # ここに残したままだと `java_field_defaults` が「そんなフィールドは無い」で
    # 生成を止める(実際に止まった)。**手引きの本文からも消してある** ——
    # 消えたつまみの名前を案内するのは、無い物を触らせることになるため。
    cfg_names = ["powerEnabled", "redstoneRequiresPower", "redstoneBlockDecaySeconds",
                 "redstoneBlockDecayDropsItem", "invertedConsumersRequirePower",
                 "ticksPerCoal", "reactorTicksPerCell", "reactorCellBuffer",
                 "baseOutputUnits", "poorMultiplier", "standardMultiplier",
                 "highMultiplier", "veryHighMultiplier", "energyCellMultiplier",
                 "energyCellBurnTicks", "breakerFuelEfficiency",
                 "solarOutputUnits", "windOutputUnits", "hydroOutputUnits",
                 "windBaseAltitude", "windFullAltitude", "hydroFacesForFullOutput",
                 "cellRuntimeTicks", "fireplaceTicksPerCoal",
                 "cableStandardOhmsPerBlock", "cableInsulatedOhmsPerBlock",
                 "lineLossBudgetFraction", "referenceBranchWatts",
                 "transformerCrossoverBlocks", "deviceWatts",
                 # V2 §9.2/§10(2026-08-17): 大気汚染と空気清浄機。
                 # `PowerConfig.PollutionSettings` の中の宣言だが、
                 # `java_field_defaults` はファイル全体から `public <型> <名> =` を拾うので
                 # 入れ子クラスでも同じに読める(名前はこのファイル内で一意であることを確認済み)。
                 # ⚠ ここに数を書き写さない。書き写した瞬間に config と手引きの 2 つの出典ができる。
                 "generatorRadiusBlocks", "purifierRadiusBlocks", "purifierClearSeconds",
                 "lightThreshold", "heavyThreshold", "severeThreshold", "maxLevel"]
    raw_cfg = java_field_defaults(cfg_path, cfg_names)
    cfg = {n: _resolve_java_expr(raw_cfg[n], spec) for n in cfg_names}

    # ---- enum・定数 ------------------------------------------------------
    #
    # v1.8.4: `Voltage` は「その段に要る最低ティア」を持たなくなった。持てなくなった、
    # と言うほうが正しい —— ケーブルが 4 種類になり、しかも
    # <b>ティアに全順序が無い</b>(太径は絶縁ケーブルより抵抗が小さいのに高圧を載せられない)
    # ので、「最低ティア」という 1 個の答えがそもそも存在しない。
    # いまは電圧どうしを比べる(`CableTier#supports`)ので、早見表も同じ規則で
    # <b>その段を載せられるティアを数え上げる</b>。
    volts = _java_regex(POWER_JAVA / "grid/Voltage.java",
                        r'^\t([A-Z0-9_]+)\("([a-z0-9]+)",\s*' + _JNUM +
                        r',\s*(true|false)\)',
                        "the Voltage steps", re.M, many=True)
    amp_path = POWER_JAVA / "breaker/AmpRating.java"
    steps = [int(x) for x in _java_regex(amp_path, r"int\[\]\s+STEPS\s*=\s*\{([^}]*)\}",
                                         "the amp ratings").group(1).replace("_", "").split(",")]
    headroom = _java_number(_java_regex(amp_path, r"double\s+HEADROOM\s*=\s*" + _JNUM,
                                        "the amp headroom").group(1))
    circuits = int(_java_regex(POWER_JAVA / "breaker/BreakerBlockEntity.java",
                               r"int\s+CIRCUITS\s*=\s*(\d+)", "the circuit count").group(1))
    fq = _java_regex(POWER_JAVA / "machine/FuelQuality.java",
                     r'^\t([A-Z_]+)\("([a-z_]+)",\s*' + _JNUM + r'\)',
                     "the fuel qualities", re.M, many=True)
    kinds = _java_regex(POWER_JAVA / "renewable/RenewableKind.java",
                        r'^\t([A-Z]+)\("([a-z_]+)"\)', "the renewable kinds", re.M, many=True)

    def _dim(rel, field):
        return int(_java_regex(POWER_JAVA / rel, r"int\s+%s\s*=\s*(\d+)" % field,
                               "%s of %s" % (field, rel)).group(1))

    # LED パネル照明(v1.8.4)。**光量と厚みだけを読む。**
    # 「たいまつの何倍」の実測値は Java の javadoc と ja_jp.json の説明文にしか無い散文なので、
    # ここに写すと<b>2 つ目の出典</b>ができて必ず食い違う。手引きは倍率を書かず、
    # アイテムの説明(翻訳済みで、実装と同じ場所で管理されている)へ送る。
    led_light = int(_java_regex(POWER_JAVA / "light/LedPanelBlock.java",
                                r"int\s+LIGHT_LEVEL\s*=\s*(\d+)",
                                "the LED panel light level").group(1))
    led_thickness = _java_number(_java_regex(POWER_JAVA / "light/LedPanelBlock.java",
                                             r"double\s+THICKNESS\s*=\s*" + _JNUM,
                                             "the LED panel thickness").group(1))

    mw, mh, md = (_dim("machine/MachineVolume.java", f) for f in ("WIDTH", "HEIGHT", "DEPTH"))
    aw, ah, ad = (_dim("appliance/AirConditionerVolume.java", f)
                  for f in ("WIDTH", "HEIGHT", "DEPTH"))

    # ---- 気温(数値の出典は sorakaze_survival 側)--------------------------
    #
    # v1.8.3: 「稼働中の機械がその空間を暖める」が入ったので、暖炉・エアコンだけでなく
    # 機械の熱もここから読む。**手引きに数字を打ち込まないこと**は §1263 の方針のとおり。
    #
    # ⚠ `DEFAULT_MACHINE_HEAT_CELSIUS` は数ではなく式である
    #   (`-DEFAULT_AIR_CONDITIONER_CELSIUS / MACHINES_PER_AIR_CONDITIONER`)。
    #   だから **宣言順に解く** —— 先に定数 3 つを解いてから config の項を解かないと、
    #   `_resolve_java_expr` が名前を数に置きかえられずに落ちる。
    temp_const_names = ["MACHINES_PER_AIR_CONDITIONER", "DEFAULT_AIR_CONDITIONER_CELSIUS",
                        "DEFAULT_MACHINE_HEAT_CELSIUS"]
    raw_tc = java_field_defaults(SURVIVAL_JAVA / "config/SurvivalConfig.java", temp_const_names)
    temp_const = {}
    for n in temp_const_names:
        temp_const[n] = _resolve_java_expr(raw_tc[n], temp_const)

    temp_names = ["temperatureFireplaceCelsius",
                  "temperatureAirConditionerCelsius",
                  "temperatureSourceRadiusBlocks",
                  "temperatureMachineHeatCelsius",
                  "temperatureReactorHeatMultiplier",
                  "temperatureRenewableHeatCelsius",
                  "temperatureMachineOpenAirFactor",
                  "temperatureMachineMaxSwingCelsius",
                  "temperatureComfortMaxCelsius",
                  "temperatureScorchingCelsius"]
    raw_temp = java_field_defaults(SURVIVAL_JAVA / "config/SurvivalConfig.java", temp_names)
    temp = {k: _resolve_java_expr(raw_temp[k], temp_const) for k in temp_names}

    # ---- 逆算(手で置いた数は 1 つも無い)---------------------------------
    f = cfg["lineLossBudgetFraction"]
    ref_w = cfg["referenceBranchWatts"]
    r_std = cfg["cableStandardOhmsPerBlock"]
    r_ins = cfg["cableInsulatedOhmsPerBlock"]
    dev_w = cfg["deviceWatts"]

    def reach(v, ohms):                       # L = f·V² / (P·r)
        return f * float(v) ** 2 / (ref_w * ohms)

    def devices_for(units):
        """供給 `units` 単位/tick で足りる機器の台数(需要 = 1 + floor(W / 基準W))。"""
        n = 0
        while 1 + int((n + 1) * dev_w / ref_w) <= units:
            n += 1
        return n

    volt_by_key = {k: (float(v), needs == "true") for _n, k, v, needs in volts}
    base = cfg["baseOutputUnits"]
    quality = {key: float(m) for _n, key, m in fq}

    # ---- ケーブルのティア(4 隅)------------------------------------------
    #
    # config のキー名はティアの名前から機械的に出す(`cableOhmsPerBlockClamped` の
    # switch と同じ対応)。**5 つ目を足したら `java_field_defaults` が
    # 「そんなフィールドは無い」で生成を止める**ので、手引きだけ 4 種類のまま、
    # ということが起こらない。
    tier_ja = load_lang(ROOT / "mods-src/sorakaze-power", "sorakaze_power")
    volt_const_key = {n: k for n, k, _v, _needs in volts}   # V200 -> "200v"
    tiers = []
    for const, block_name, area, insul in cable_tiers():
        key = "cable" + const.capitalize() + "OhmsPerBlock"
        ohms = _resolve_java_expr(java_field_defaults(cfg_path, [key])[key], spec)
        name = tier_ja.get("block.sorakaze_power." + block_name)
        if not name:
            raise SystemExit(
                "ERROR: the 使い方 tab has no Japanese name for the cable tier %r "
                "(block.sorakaze_power.%s missing from ja_jp.json)" % (const, block_name))
        if insul not in volt_const_key:
            raise SystemExit(
                "ERROR: cable tier %s declares insulation class Voltage.%s, which is not one "
                "of the Voltage steps" % (const, insul))
        tiers.append({"const": const, "id": "sorakaze_power:" + block_name, "name": name,
                      "area": area, "ohms": ohms,
                      "max_volts": volt_by_key[volt_const_key[insul]][0]})
    # 高圧を載せられるのはどれか。**序数ではなく電圧の比較**で決める
    # (`CableTier#supports` と同じ規則。太径は絶縁ケーブルより抵抗が小さいが高圧は不可)。
    high_v = volt_by_key["high"][0]
    high_tiers = [t for t in tiers if t["max_volts"] >= high_v]
    if not high_tiers:
        raise SystemExit("ERROR: no cable tier can carry the high-voltage step - the 使い方 tab "
                         "would tell the owner to use a cable that does not exist")
    std = next(t for t in tiers if t["const"] == "STANDARD")
    # 低圧のなかでいちばん太いもの / 全体でいちばん太いもの。**序数ではなく断面積で選ぶ**
    # (`CableTier` の javadoc が言うとおり、ティアに全順序は無い)。
    low_only = [t for t in tiers if t["max_volts"] < high_v]
    if not low_only:
        raise SystemExit("ERROR: every cable tier carries high voltage - the 使い方 tab's "
                         "「安いほうで足りる」 comparison would be meaningless")
    heavy = max(low_only, key=lambda t: t["area"])
    best = max(tiers, key=lambda t: t["area"])

    facts = {
        # --- 送電 ---
        "cable_reach_100": _fmt(reach(volt_by_key["100v"][0], r_std)),
        "cable_reach_200": _fmt(reach(volt_by_key["200v"][0], r_std)),
        "ins_reach_100": _fmt(reach(volt_by_key["100v"][0], r_ins)),
        "ins_reach_200": _fmt(reach(volt_by_key["200v"][0], r_ins)),
        "ins_ratio": _fmt(r_std / r_ins),
        "volts_100": _fmt(volt_by_key["100v"][0]),
        "volts_200": _fmt(volt_by_key["200v"][0]),
        "volts_high": _fmt(volt_by_key["high"][0]),
        # 高圧を載せられるケーブル。**1 種類とは限らない**ので数え上げて並べる。
        "high_tier": "か".join(t["name"] for t in high_tiers),
        "cable_kinds": _fmt(len(tiers)),
        # 低圧で最も太いもの / 全体で最も太いもの。名前も倍率も実装から出しているので、
        # ティアを組み替えても手引きが嘘にならない。
        "heavy_name": heavy["name"],
        "heavy_ratio": _fmt(std["ohms"] / heavy["ohms"]),
        "heavy_reach_100": _fmt(reach(volt_by_key["100v"][0], heavy["ohms"])),
        "heavy_reach_200": _fmt(reach(volt_by_key["200v"][0], heavy["ohms"])),
        "best_name": best["name"],
        "best_ratio": _fmt(std["ohms"] / best["ohms"]),
        "best_reach_100": _fmt(reach(volt_by_key["100v"][0], best["ohms"])),
        "best_reach_200": _fmt(reach(volt_by_key["200v"][0], best["ohms"])),
        "secondary_volts": _fmt(volt_by_key["200v"][0]),
        "loss_budget_pct": _fmt(f * 100),
        "crossover": _fmt(cfg["transformerCrossoverBlocks"]),
        "max_nodes": _fmt(spec["DEFAULT_MAX_NODES"]),
        # --- 分電盤 ---
        "circuits": _fmt(circuits),
        "voltage_steps": _fmt(len(volts)),
        "amp_steps": " / ".join("%dA" % a for a in steps),
        "amp_steps_count": _fmt(len(steps)),
        "amp_min": "%dA" % steps[0],
        "amp_max": "%dA" % steps[-1],
        "amp_headroom_pct": _fmt(100.0 / headroom),
        "device_watts": _fmt(dev_w),
        "branch_watts": _fmt(ref_w),
        "devices_per_branch": _fmt(ref_w / dev_w),
        "amp_min_devices_100": _fmt(int(volt_by_key["100v"][0] * steps[0] / dev_w)),
        "amp_min_devices_200": _fmt(int(volt_by_key["200v"][0] * steps[0] / dev_w)),
        "cell_minutes": _fmt(cfg["cellRuntimeTicks"] / 20.0 / 60.0),
        "breaker_fuel_pct": _fmt(cfg["breakerFuelEfficiency"] * 100),
        # --- 燃料 ---
        "coal_units": _fmt(quality["standard"] * base),
        "coal_devices": _fmt(devices_for(quality["standard"] * base)),
        "wood_units": _fmt(quality["poor"] * base),
        "wood_devices": _fmt(devices_for(quality["poor"] * base)),
        "blaze_units": _fmt(quality["high"] * base),
        "blaze_devices": _fmt(devices_for(quality["high"] * base)),
        "lava_units": _fmt(quality["very_high"] * base),
        "lava_devices": _fmt(devices_for(quality["very_high"] * base)),
        "cell_units": _fmt(quality["best"] * base),
        "cell_devices": _fmt(devices_for(quality["best"] * base)),
        "wood_ratio": _fmt(quality["standard"] / quality["poor"]),
        "coal_seconds": _fmt(cfg["ticksPerCoal"] / 20.0),
        "coal_total": _fmt(cfg["ticksPerCoal"] * quality["standard"] * base),
        "cell_seconds": _fmt(cfg["energyCellBurnTicks"] / 20.0),
        "reactor_seconds": _fmt(cfg["reactorTicksPerCell"] / 20.0),
        "reactor_buffer": _fmt(cfg["reactorCellBuffer"]),
        # --- 再生可能 ---
        "solar_units": _fmt(cfg["solarOutputUnits"]),
        "solar_devices": _fmt(devices_for(cfg["solarOutputUnits"])),
        "wind_units": _fmt(cfg["windOutputUnits"]),
        "wind_devices": _fmt(devices_for(cfg["windOutputUnits"])),
        "hydro_units": _fmt(cfg["hydroOutputUnits"]),
        "hydro_devices": _fmt(devices_for(cfg["hydroOutputUnits"])),
        "wind_base_y": _fmt(cfg["windBaseAltitude"]),
        "wind_full_y": _fmt(cfg["windFullAltitude"]),
        "hydro_faces": _fmt(cfg["hydroFacesForFullOutput"]),
        "renewable_count": _fmt(len(kinds)),
        # --- LED パネル照明 ---
        "led_light": _fmt(led_light),
        "led_thickness_px": _fmt(led_thickness),
        # --- 大きさ ---
        "machine_size": "%d×%d×%d" % (mw, md, mh),
        "aircon_size": "%d×%d×%d" % (aw, ad, ah),
        # --- 気温 ---
        "fireplace_c": _fmt(temp["temperatureFireplaceCelsius"]),
        "aircon_c": _fmt(abs(temp["temperatureAirConditionerCelsius"])),
        "temp_radius": _fmt(temp["temperatureSourceRadiusBlocks"]),
        "fireplace_seconds": _fmt(cfg["fireplaceTicksPerCoal"] / 20.0),
        # --- 機械の熱(v1.8.3)---
        # ⚠ どれも実装から読んだ値である。手で書いた数は 1 つも無い。
        "machine_heat_c": _fmt(temp["temperatureMachineHeatCelsius"]),
        "reactor_heat_c": _fmt(temp["temperatureMachineHeatCelsius"]
                               * temp["temperatureReactorHeatMultiplier"]),
        "renewable_heat_c": _fmt(temp["temperatureRenewableHeatCelsius"]),
        # エアコン 1 台が打ち消す発電機の台数(2.5 のような小数になりうる)。
        "machines_per_ac": _fmt(temp_const["MACHINES_PER_AIR_CONDITIONER"], 1),
        # 発電機 n 台を打ち消すのに要るエアコンの台数(切り上げ。買い物の答えなので整数)。
        "ac_for_four": _fmt(math.ceil(4 / temp_const["MACHINES_PER_AIR_CONDITIONER"])),
        "ac_for_eight": _fmt(math.ceil(8 / temp_const["MACHINES_PER_AIR_CONDITIONER"])),
        # 熱が飽和する台数(上限 °C ÷ 1 台ぶん)。
        "machine_cap_count": _fmt(temp["temperatureMachineMaxSwingCelsius"]
                                  / temp["temperatureMachineHeatCelsius"]),
        "machine_cap_c": _fmt(temp["temperatureMachineMaxSwingCelsius"]),
        "open_air_pct": _fmt(temp["temperatureMachineOpenAirFactor"] * 100),
        "comfort_max_c": _fmt(temp["temperatureComfortMaxCelsius"]),
        "scorching_c": _fmt(temp["temperatureScorchingCelsius"]),
        # 上がる幅(台数 × 1 台ぶん)。**絶対温度は出さない** ——
        # 拠点の元の気温は土地・高さ・屋根で変わるので、ここで 1 つの数に決めると嘘になる。
        # config が宣言しているのは「1 台が何 °C 上げるか」だけなので、幅だけを言う。
        "heat_2": _fmt(2 * temp["temperatureMachineHeatCelsius"]),
        "heat_4": _fmt(4 * temp["temperatureMachineHeatCelsius"]),
        "heat_8": _fmt(8 * temp["temperatureMachineHeatCelsius"]),
        # --- 大気汚染と空気清浄機(V2 §9.2/§10)---
        # ⚠ どれも `PowerConfig.PollutionSettings` から読んだ既定値である。
        #    手で書いた数は 1 つも無い。所有者が config を変えたら手引きも一緒に変わる。
        "pollution_radius": _fmt(cfg["generatorRadiusBlocks"]),
        "purifier_radius": _fmt(cfg["purifierRadiusBlocks"]),
        "purifier_seconds": _fmt(cfg["purifierClearSeconds"]),
        "pollution_light": _fmt(cfg["lightThreshold"]),
        "pollution_heavy": _fmt(cfg["heavyThreshold"]),
        "pollution_severe": _fmt(cfg["severeThreshold"]),
        "pollution_max": _fmt(cfg["maxLevel"]),
        # --- レッドストーン ---
        "decay_minutes": _fmt(cfg["redstoneBlockDecaySeconds"] / 60.0),
        "decay_drops": "アイテムとして落ちます" if cfg["redstoneBlockDecayDropsItem"]
                       else "そのまま消えます",
        "gated_count": _fmt(len(tag_block_ids("power_gated_source"))),
        "exempt_count": _fmt(len(tag_block_ids("power_gate_exempt_source"))),
        "inverted_count": _fmt(len(tag_block_ids("power_gate_inverted_consumer"))),
        # v1.8.4: 3 つに絞れたので **名前で言う**。「3 種」とだけ言われても、
        # 所有者は自分の拠点のどれが該当するのか分からない。
        "inverted_names": ja_block_names(tag_block_ids("power_gate_inverted_consumer")),
        # 対象から外して「電気が無くても動く」に戻したもの。**タグから数える** ——
        # 14 と書き込むと、次に 1 個戻したり外したりした日に手引きだけが嘘になる。
        # バニラのホッパーは同じタグに居るが MOD のブロックではないので別に数える。
        "freed_count": _fmt(len([i for i in tag_block_ids("power_gate_rewake")
                                 if not i.startswith("minecraft:")])),
    }
    return facts


POWER_FACTS = read_power_facts()


# ---------------------------------------------------------------------------
# V4.0.1: V4 の 20 モジュールの手引きが使う数字。電力の節と同じ規律 —— **手で書かない。**
# 各 MOD の config / 定数から読む。改名されれば java_field_defaults がその場で止める。
# ---------------------------------------------------------------------------
MODS_JAVA = ROOT / "mods-src"


def _mod_java(module, modid):
    return MODS_JAVA / module / "src/main/java/net/sorakaze" / modid


def _ticks_to_seconds(raw):
    v = _java_number(raw)
    return ("%g" % (v / 20.0))


def read_v4_facts():
    """V4 の手引きの数字。返る dict は POWER_FACTS に併合され、全部が使われることを要求される。"""
    sky = _mod_java("sorakaze-sky", "sorakaze_sky") / "config/SkyConfig.java"
    survival = _mod_java("sorakaze-survival", "sorakaze_survival") / "config/SurvivalConfig.java"
    rail = _mod_java("sorakaze-rail", "sorakaze_rail") / "config/RailConfig.java"
    guns = _mod_java("sorakaze-guns", "sorakaze_guns") / "config/GunsConfig.java"
    power = POWER_JAVA / "config/PowerConfig.java"
    f = {}
    c = java_field_defaults(sky, ["chronosAnchorRadiusBlocks", "gravityInverterRegionWidth",
                                  "gravityInverterRegionHeight", "nullZoneRadiusBlocks",
                                  "dimensionalMirrorRefreshTicks", "spatialTranspositorRangeBlocks",
                                  "spatialTranspositorCooldownTicks"])
    f["v4_chronos_side"] = str(2 * int(_java_number(c["chronosAnchorRadiusBlocks"])) + 1)
    f["v4_gravity_w"] = "%g" % _java_number(c["gravityInverterRegionWidth"])
    f["v4_gravity_h"] = "%g" % _java_number(c["gravityInverterRegionHeight"])
    f["v4_nullzone_radius"] = "%g" % _java_number(c["nullZoneRadiusBlocks"])
    f["v4_mirror_refresh_s"] = _ticks_to_seconds(c["dimensionalMirrorRefreshTicks"])
    f["v4_transpositor_range"] = "%g" % _java_number(c["spatialTranspositorRangeBlocks"])
    f["v4_transpositor_cooldown_s"] = _ticks_to_seconds(c["spatialTranspositorCooldownTicks"])
    c = java_field_defaults(survival, ["entropySiphonPercentPerLevel", "kineticBootsPowerPerBlock",
                                       "kineticBootsMaxPower", "kineticBootsDurabilityPerLanding",
                                       "glitchStriderDashBlocks", "glitchStriderInvulnerableTicks",
                                       "glitchStriderCooldownTicks"])
    f["v4_siphon_percent"] = "%g" % _java_number(c["entropySiphonPercentPerLevel"])
    f["v4_kinetic_per_block"] = "%g" % _java_number(c["kineticBootsPowerPerBlock"])
    f["v4_kinetic_max"] = "%g" % _java_number(c["kineticBootsMaxPower"])
    f["v4_kinetic_durability"] = "%g" % _java_number(c["kineticBootsDurabilityPerLanding"])
    f["v4_glitch_blocks"] = "%g" % _java_number(c["glitchStriderDashBlocks"])
    f["v4_glitch_invuln_s"] = _ticks_to_seconds(c["glitchStriderInvulnerableTicks"])
    f["v4_glitch_cooldown_s"] = _ticks_to_seconds(c["glitchStriderCooldownTicks"])
    echo = _mod_java("sorakaze-survival", "sorakaze_survival") / "echo/EchoFilter.java"
    c = java_field_defaults(echo, ["RANGE_BLOCKS", "LINGER_TICKS"])
    f["v4_echo_range"] = "%g" % _java_number(c["RANGE_BLOCKS"])
    f["v4_echo_linger_s"] = _ticks_to_seconds(c["LINGER_TICKS"])
    pocket = _mod_java("sorakaze-survival", "sorakaze_survival") / "pocket/VoidPocketData.java"
    f["v4_pocket_slots"] = "%g" % _java_number(java_field_defaults(pocket, ["SLOTS"])["SLOTS"])
    c = java_field_defaults(rail, ["resonanceRailMaxBlocksPerTick"])
    bpt = _java_number(c["resonanceRailMaxBlocksPerTick"])
    f["v4_rail_bpt"] = "%g" % bpt
    f["v4_rail_mps"] = "%g" % (bpt * 20)
    m = _java_regex(guns, r"new AcousticTurretSettings\(" + _JNUM + r",\s*" + _JNUM + r",\s*" + _JNUM
                    + r",\s*" + _JNUM + r",\s*" + _JNUM, "the acoustic turret defaults")
    f["v4_turret_range"] = "%g" % _java_number(m.group(1))
    f["v4_turret_damage"] = "%g" % _java_number(m.group(2))
    f["v4_turret_cooldown_s"] = _ticks_to_seconds(m.group(5))
    c = java_field_defaults(guns, ["cryoStacksToEncase", "cryoEncaseTicks", "cryoFrostbiteDurationTicks"])
    f["v4_cryo_stacks"] = "%g" % _java_number(c["cryoStacksToEncase"])
    f["v4_cryo_encase_s"] = _ticks_to_seconds(c["cryoEncaseTicks"])
    f["v4_cryo_frost_s"] = _ticks_to_seconds(c["cryoFrostbiteDurationTicks"])
    frost = _mod_java("sorakaze-guns", "sorakaze_guns") / "effect/FrostbiteMobEffect.java"
    f["v4_cryo_slow_percent"] = "%g" % abs(_java_number(java_field_defaults(frost, ["SLOW_PER_STACK"])["SLOW_PER_STACK"]) * 100)
    photic = _mod_java("sorakaze-deco", "sorakaze_deco") / "block/PhoticSynthesiserBlock.java"
    c = java_field_defaults(photic, ["GROW_R", "GROW_G", "GROW_B"])
    f["v4_photic_r"], f["v4_photic_g"], f["v4_photic_b"] = (c["GROW_R"], c["GROW_G"], c["GROW_B"])
    c = java_field_defaults(power, ["probeBlocks", "maxOutputUnits", "maxLinkBlocks", "ticksPerBlock",
                                    "craftIntervalTicks", "workTicks", "cycleTicks"])
    f["v4_thermo_probe"] = "%g" % _java_number(c["probeBlocks"])
    f["v4_thermo_max"] = "%g" % _java_number(c["maxOutputUnits"])
    f["v4_conduit_range"] = "%g" % _java_number(c["maxLinkBlocks"])
    f["v4_drill_ticks"] = "%g" % _java_number(c["ticksPerBlock"])
    f["v4_fabricator_s"] = _ticks_to_seconds(c["craftIntervalTicks"])
    f["v4_weaver_s"] = _ticks_to_seconds(c["workTicks"])
    f["v4_harvester_cycle_s"] = _ticks_to_seconds(c["cycleTicks"])
    return f


POWER_FACTS.update(read_v4_facts())

# 「電気が要る機器」の一覧。**タグを唯一の出典にする**ので、
# 相手の MOD に機器が増えたら(= タグに 1 行増えたら)検査⑥が生成を止める。
POWERED_DEVICE_IDS = [i for i in tag_block_ids("power_devices") if not i.startswith("#")]
# 送電網から見えるが `power_devices` には載っていない機器(建材側が自分の config で
# 判定しているもの)。ここも図に出ていなければ生成を止める。
POWERED_EXTRA_IDS = [i for i in tag_block_ids("cable_connectable")
                     if not i.startswith("#") and not i.startswith("sorakaze_power:")
                     and i not in POWERED_DEVICE_IDS]


def fill_facts(node):
    """手引きの文字列の `{fact}` を実装から読んだ値に置きかえる(再帰)。

    ⚠ 表に無い名前を書いたら **その場で生成を止める**。
       黙って `{typo}` を出力すると、所有者には「壊れた本文」としてしか見えない。
    """
    if isinstance(node, str):
        def sub(m):
            key = m.group(1)
            if key not in POWER_FACTS:
                raise SystemExit(
                    "ERROR: the 使い方 tab refers to the unknown value {%s} - either the "
                    "implementation stopped exposing it, or this is a typo. Known: %s"
                    % (key, ", ".join(sorted(POWER_FACTS))))
            USED_FACTS.add(key)
            return POWER_FACTS[key]
        return re.sub(r"\{([a-z_0-9]+)\}", sub, node)
    if isinstance(node, list):
        return [fill_facts(v) for v in node]
    if isinstance(node, tuple):
        return tuple(fill_facts(v) for v in node)
    if isinstance(node, dict):
        return {k: fill_facts(v) for k, v in node.items()}
    return node


USED_FACTS = set()


GUIDES = [
    {
        "id": "sorting",
        "icon": "sorakaze_deco:sorting_filter",
        "tab": "使い方",
        "title": "自動仕分けの使い方",
        "lede": "しまう場所を自分で決めてくれる倉庫を作ります。"
                "むずかしい配線はいりません。まずは①だけ作ってみてください。",
        "sections": [
            {
                "title": "① まず 1 台だけ置いてみる",
                "goal": "石炭だけが右の箱に入るようにします。ここが全部の基本です。",
                "diagram": {
                    "caption": "うしろの箱から取り出して、正面の箱へ入れます(横から見た図)",
                    "rows": [[
                        ("i", "minecraft:chest", "なんでも入れる箱"),
                        ("a", "→"),
                        ("i", "sorakaze_deco:sorting_filter", "仕分けフィルター"),
                        ("a", "→"),
                        ("i", "minecraft:chest", "石炭だけたまる箱"),
                    ]],
                },
                "io": {
                    "in": [("minecraft:coal", "石炭"), ("minecraft:iron_ingot", "鉄"),
                           ("minecraft:wheat", "小麦")],
                    "out": [("minecraft:coal", "石炭だけ通る")],
                },
                "steps": [
                    "箱・仕分けフィルター・箱を、この順で<b>くっつけて</b>置きます。",
                    "仕分けフィルターの<b>正面(色のついた面)が、入れたい箱の方</b>を向くように置きます。",
                    "<b>石炭を手に持って</b>仕分けフィルターを右クリックします。"
                    "これで「石炭を通す」と覚えます(<b>持っている石炭は減りません</b>)。",
                    "これで完成です。左の箱に何を入れても、石炭だけが右の箱へ移っていきます。",
                ],
                "notes": [
                    "見本を<b>何も登録していないと、何も通りません</b>(壊れているのではありません)。",
                    "登録を消すときは、同じアイテムを持ってもう一度右クリックします。"
                    "全部消すときはスニーク+右クリック。素手で右クリックすると今の一覧が出ます。",
                ],
            },
            {
                "title": "② 横に並べて「仕分け場」にする",
                "goal": "1 本の線から、種類ごとの箱へ振り分けます。倉庫らしくなるのはここからです。",
                "diagram": {
                    "caption": "上の線を流し、下へ落として仕分けます(横から見た図)",
                    "rows": [
                        [
                            ("i", "minecraft:chest", "入口の箱"),
                            ("a", "→"),
                            ("i", "sorakaze_deco:item_pump", "搬送ポンプ"),
                            ("a", "→"),
                            ("i", "sorakaze_deco:item_pump", "搬送ポンプ"),
                            ("a", "→"),
                            ("i", "sorakaze_deco:void_trash", "廃棄装置"),
                        ],
                        [
                            None, None, ("a", "↓"), None, ("a", "↓"), None,
                            ("n", "あふれた分"),
                        ],
                        [
                            None, None,
                            ("i", "sorakaze_deco:sorting_filter", "鉄を登録"),
                            None,
                            ("i", "sorakaze_deco:sorting_filter", "石炭を登録"),
                            None, None,
                        ],
                        [
                            None, None, ("a", "↓"), None, ("a", "↓"), None, None,
                        ],
                        [
                            None, None, ("i", "minecraft:chest", "鉄の箱"),
                            None, ("i", "minecraft:chest", "石炭の箱"), None, None,
                        ],
                    ],
                },
                "io": {
                    "in": [("minecraft:iron_ingot", "鉄"), ("minecraft:coal", "石炭"),
                           ("minecraft:cobblestone", "丸石")],
                    "out": [("minecraft:iron_ingot", "鉄の箱へ"), ("minecraft:coal", "石炭の箱へ"),
                            ("minecraft:cobblestone", "登録が無いので最後まで流れる")],
                },
                "steps": [
                    "<b>搬送ポンプ</b>で幹線(太い流れ)を作ります。ホッパーより速く、"
                    "1 回にひとかたまり運ぶので詰まりません。",
                    "仕分けたい種類のぶんだけ<b>仕分けフィルター</b>を下向きに置き、"
                    "それぞれに見本を登録します。",
                    "いちばん最後に<b>廃棄装置</b>を置くと、どの箱にも入らなかった物が消えます。"
                    "捨てたくない物があるなら、代わりにふつうの箱を置いてください。",
                ],
                "notes": [
                    "<b>廃棄装置も、見本に登録した物だけを消します。</b>"
                    "置いただけでは何も消えないので、先に置いてから設定しても安全です。",
                ],
            },
            {
                "title": "③ 種類が多すぎるときは、先に大きく分ける",
                "goal": "食べ物 40 種類を 1 台ずつ登録するのは大変です。まとめて分けます。",
                "diagram": {
                    "caption": "8 分類(食料・道具・鉱石・農業・レッドストーン・燃料・建材・その他)",
                    "rows": [[
                        ("i", "minecraft:chest", "なんでも入れる箱"),
                        ("a", "→"),
                        ("i", "sorakaze_deco:category_sorter", "「食料」に設定"),
                        ("a", "→"),
                        ("i", "minecraft:chest", "食べ物の箱"),
                    ]],
                },
                "io": {
                    "in": [("minecraft:bread", "パン"), ("minecraft:apple", "リンゴ"),
                           ("minecraft:iron_pickaxe", "ツルハシ")],
                    "out": [("minecraft:bread", "食料は通る"), ("minecraft:apple", "食料は通る")],
                },
                "steps": [
                    "カテゴリー仕分け機を置きます。置きかたは仕分けフィルターと同じです。",
                    "<b>素手で右クリック</b>すると分類が切りかわります。"
                    "出したい分類が出るまで押してください。",
                    "見本の登録はいりません。分類に当てはまる物が、まとめて通ります。",
                ],
                "notes": [
                    "こまかく分けたいときは、このうしろに<b>仕分けフィルター</b>を足します"
                    "(大きく分けてから、細かく分ける)。",
                ],
            },
            {
                "title": "④ かまどを何台も同時に動かす",
                "goal": "1 本の線から、かまど 5 台へ均等に配ります。",
                "diagram": {
                    "caption": "分配器にくっつけたコンテナへ、順番に 1 個ずつ配ります",
                    "rows": [
                        [None, None, ("i", "minecraft:chest", "原木の箱"), None, None],
                        [None, None, ("a", "↓"), None, None],
                        [None, None, ("i", "sorakaze_deco:round_robin_splitter", "振り分け分配器"), None, None],
                        [("a", "↓"), None, ("a", "↓"), None, ("a", "↓")],
                        [("i", "minecraft:furnace", "かまど"), None,
                         ("i", "minecraft:furnace", "かまど"), None,
                         ("i", "minecraft:furnace", "かまど")],
                    ],
                },
                "io": {
                    "in": [("minecraft:oak_log", "原木 64 個")],
                    "out": [("minecraft:oak_log", "3 台に 21〜22 個ずつ")],
                },
                "steps": [
                    "振り分け分配器のまわりに、かまど(や箱)をくっつけて置きます。",
                    "入ってきた側をのぞく<b>5 面すべて</b>が配り先になります。",
                    "見本の登録はいりません。入った物を順番に配るだけです。",
                ],
            },
            {
                "title": "⑤ 箱が満杯でも止まらないようにする",
                "goal": "行き先が満杯になると、ふつうは仕分け場ぜんぶが止まります。それを防ぎます。",
                "diagram": {
                    "caption": "正面が満杯のときだけ、横へ逃がします",
                    "rows": [
                        [None, ("i", "sorakaze_deco:overflow_valve", "溢れ防止弁"),
                         ("a", "→"), ("i", "minecraft:chest", "いつもの箱(満杯)")],
                        [None, ("a", "↓"), None, None],
                        [None, ("i", "minecraft:chest", "予備の箱"), None, None],
                    ],
                },
                "io": {
                    "in": [("minecraft:cobblestone", "丸石")],
                    "out": [("minecraft:cobblestone", "正面が空いていれば正面へ"),
                            ("minecraft:cobblestone", "満杯なら横・上下へ")],
                },
                "steps": [
                    "いつもの行き先の<b>手前</b>に溢れ防止弁を置きます。",
                    "横(または上下)に、あふれた分を受ける箱を置きます。",
                    "設定はいりません。正面が満杯のときだけ、自動で横へ逃がします。",
                ],
            },
            {
                "title": "⑥ 数える・残りを見る・設定を配る",
                "goal": "うまく動いているか確かめる道具と、同じ設定を何台にも配る道具です。",
                "diagram": {
                    "caption": "左: 通った数を数える / 中: 残量をレッドストーンに出す / 右: 設定を写して貼る",
                    "rows": [
                        [
                            ("i", "sorakaze_deco:item_counter", "アイテム計数器"),
                            ("a", "→"),
                            ("i", "minecraft:comparator", "64 個で 1 段"),
                            ("n", "　"),
                            ("i", "minecraft:chest", "見たい箱"),
                            ("a", "←"),
                            ("i", "sorakaze_deco:stock_indicator", "在庫表示ランプ"),
                        ],
                        [
                            None, None, None, None, None, None, ("a", "↓"),
                        ],
                        [
                            ("i", "sorakaze_deco:item_collector", "アイテム集荷器"),
                            ("a", "→"),
                            ("i", "minecraft:chest", "落ちものを拾って入れる"),
                            ("n", "　"),
                            ("i", "sorakaze_deco:filter_card", "フィルター記憶カード"),
                            None,
                            ("i", "minecraft:redstone_lamp", "ランプが光る"),
                        ],
                    ],
                },
                "io": {
                    "in": [("minecraft:wheat", "落ちている小麦")],
                    "out": [("minecraft:wheat", "箱の中へ")],
                },
                "steps": [
                    "<b>アイテム計数器</b>は流れの途中に置きます。素通しさせながら数を数え、"
                    "コンパレーターへ出します(右クリックで合計、スニーク+右クリックで 0 に戻る)。",
                    "<b>在庫表示ランプ</b>はアイテムを動かしません。"
                    "正面の箱の残りを読んで、しきい値を超えると光り、同じ値をコンパレーターへ出します。"
                    "遠くの倉庫の残量を配線に繋げます。",
                    "<b>アイテム集荷器</b>は、まわりに落ちているアイテムを吸い込んで正面の箱へ入れます。"
                    "畑の落し物拾いに使います。",
                    "<b>フィルター記憶カード</b>は、空のカードで仕分けフィルターを右クリックすると"
                    "設定を<b>写し</b>、中身のあるカードで右クリックすると<b>貼り</b>ます。"
                    "同じ設定を何台にも配れます(空中で右クリックすると消せます)。",
                ],
            },
        ],
    },
    # =======================================================================
    # 電力(v1.8.2 で追加)
    # =======================================================================
    # ⚠ **この節の数字はひとつも手で書いていない。**すべて `{fact}` で、
    #    実装(PowerConfig / PowerSpec / Voltage / AmpRating / FuelQuality /
    #    RenewableKind / 各 block タグ / SurvivalConfig)から読んだ値が入る。
    #    実装が変われば本文が変わり、実装から消えれば生成が止まる。
    {
        "id": "power",
        "icon": "sorakaze_power:breaker",
        "tab": "使い方",
        "title": "電気のつなぎかた",
        "lede": "電気は<b>「作る → 送る → 配る → 使う」</b>の 4 つだけです。"
                "まずは①の図のとおりに 4 個並べてみてください。"
                "分電盤は<b>置くだけで設定が済みます</b>(設定画面を開く必要はありません)。"
                "⚠ この MOD を入れると<b>レッドストーンにも電気が要ります</b> — ⑩を必ず読んでください。",
        "sections": [
            {
                "title": "① 電気のながれ(まずこれだけ)",
                "goal": "発電機・ケーブル・分電盤・機器の 4 つ。これが電気の全部です。",
                "diagram": {
                    "caption": "燃料 → 発電機 → ケーブル → 蓄電池 → エネルギーセル → 分電盤(燃料スロット)→ ケーブル → 機器"
                               "(横に長いので、指やマウスで横へずらせます)",
                    "rows": [
                        [
                            ("i", "minecraft:coal", "燃料を入れる"),
                            ("a", "→"),
                            ("i", "sorakaze_power:generator_controller", "発電機"),
                            ("a", "→"),
                            ("i", "sorakaze_power:cable", "ケーブル"),
                            ("a", "→"),
                            ("i", "sorakaze_power:battery", "蓄電池"),
                            ("a", "→"),
                            ("i", "sorakaze_guns:energy_cell", "エネルギーセル"),
                            ("a", "→"),
                            ("i", "sorakaze_power:breaker", "分電盤"),
                            ("a", "→"),
                            ("i", "sorakaze_power:cable", "ケーブル"),
                            ("a", "→"),
                            ("i", "sorakaze_deco:atm", "機器"),
                        ],
                        [
                            ("n", "▼ 使わない"),
                            None,
                            ("i", "sorakaze_power:machine_casing", "機械の筐体"),
                            None,
                            ("i", "sorakaze_power:reactor_casing", "原子炉の遮蔽ブロック"),
                            None,
                            ("n", "ただの飾りです"),
                            None, None, None, None, None, None,
                        ],
                    ],
                },
                "io": {
                    "in": [("minecraft:coal", "石炭(燃料)")],
                    "out": [("sorakaze_power:cable", "ケーブルが光ります"),
                            ("sorakaze_deco:atm", "機器が動きます")],
                },
                "steps": [
                    "<b>発電機</b>を置きます。アイテム 1 個を置くだけで、"
                    "{machine_size} の大きさの建物が自分で生えます(組み立ては要りません)。"
                    "せまい場所には置けないので、周りを空けてください。",
                    "発電機に<b>石炭を持って右クリック</b>で燃料を入れます。火が入ります。",
                    "発電機から<b>蓄電池</b>まで<b>ケーブル</b>をつなぎます。"
                    "発電機はどの面からでもつながります。"
                    "<b>⚠ 蓄電池を経由しない配線(発電機を直接ケーブルで分電盤につなぐだけ)では、電気は届きません。</b>",
                    "蓄電池に電気がたまると、自動で<b>エネルギーセル</b>ができます。"
                    "できたセルを取り出して(下からホッパーで自動化もできます。⑥を見てください)、"
                    "<b>分電盤の燃料スロット</b>に差し込みます。",
                    "分電盤から、動かしたい機器まで<b>ケーブル</b>をつなぎます。"
                    "<b>ここで設定はしません。</b>置いた時点で分電盤が系統・電圧・容量を自分で決めます。",
                    "ケーブルが<b>光ったら通電しています。</b>光らない場所には電気が届いていません。",
                ],
                "notes": [
                    "発電機は<b>電気を作るだけ</b>、蓄電池は<b>セルを作るだけ</b>、"
                    "分電盤は<b>セルを燃料にして配るだけ</b>です。どれか 1 つでも欠けると動きません。",
                    "うまくいかないときは、まず<b>ケーブルが光っているか</b>を目で追ってください。"
                    "光が途切れたところが原因の場所です。",
                    "<b>原子力発電所も同じしくみです。</b>以前は自分で作ったセルを直接ケーブルで"
                    "分電盤へ送っていましたが、いまは発電機と同じく<b>まず蓄電池へ出力を送り、"
                    "蓄電池がセルを作ります</b>(⑤を見てください)。"
                    "蓄電池が見つからないときだけ、原子炉は以前と同じやりかたで自分の中に少しだけセルをためて待ちます"
                    "(発電機にはこの仕組みが無いので、蓄電池が無いと発電機の電気はただ失われます)。",
                    "<b>「機械の筐体」と「原子炉の遮蔽ブロック」は、いまは組み立てに使いません。</b>"
                    "以前は機械を手で積む必要があったころの部品で、"
                    "いまは<b>ただの丈夫な飾りブロック</b>として残してあります"
                    "(前に建てた建物が消えないようにするためです)。買い足す必要はありません。",
                ],
            },
            {
                "title": "② ケーブルは {cable_kinds} 種類。どれを使う?",
                "goal": "選ぶ物差しは<b>2 つあります</b>。<b>太さ = 届く距離</b>、"
                        "<b>帯 = 高圧を載せられるか</b>。この 2 つは別々なので、"
                        "<b>「どれがいちばん偉い」という順番はありません</b>。",
                "diagram": {
                    "caption": "太いほど遠くへ届きます。継手に帯があるものだけが高圧を送れます"
                               "(既定値のとき)",
                    "rows": [
                        [
                            ("i", "sorakaze_power:cable", "普通のケーブル"),
                            ("n", "{volts_100}V で {cable_reach_100} ブロック"),
                            ("n", "{volts_200}V で {cable_reach_200} ブロック"),
                            ("n", "高圧は送れない"),
                        ],
                        [
                            ("i", "sorakaze_power:heavy_cable", "{heavy_name}"),
                            ("n", "{volts_100}V で {heavy_reach_100} ブロック"),
                            ("n", "{volts_200}V で {heavy_reach_200} ブロック"),
                            ("n", "高圧は送れない"),
                        ],
                        [
                            ("i", "sorakaze_power:insulated_cable", "絶縁ケーブル"),
                            ("n", "{volts_100}V で {ins_reach_100} ブロック"),
                            ("n", "{volts_200}V で {ins_reach_200} ブロック"),
                            ("n", "高圧を送れる"),
                        ],
                        [
                            ("i", "sorakaze_power:shielded_cable", "{best_name}"),
                            ("n", "{volts_100}V で {best_reach_100} ブロック"),
                            ("n", "{volts_200}V で {best_reach_200} ブロック"),
                            ("n", "高圧を送れる"),
                        ],
                    ],
                },
                "steps": [
                    "<b>まず普通のケーブルで引いてみてください。</b>光れば足りています。",
                    "途中で光が消えたら距離が足りていません。"
                    "<b>太いケーブルに替える</b>か、<b>電圧を上げる</b>(③)かのどちらかです。"
                    "普通のケーブルを 1 としたとき、届く距離は"
                    "絶縁ケーブルが <b>{ins_ratio} 倍</b>、"
                    "{heavy_name}が <b>{heavy_ratio} 倍</b>、"
                    "{best_name}が <b>{best_ratio} 倍</b>です。",
                    "<b>高圧({volts_high}V)だけは{high_tier}でないと送れません。</b>"
                    "普通のケーブルに高圧を設定すると、分電盤に「絶縁不足」と出て動きません"
                    "(黙って壊れたりはしません)。",
                ],
                "notes": [
                    "<b>⚠ {heavy_name}は絶縁ケーブルの「上位」ではありません。</b>"
                    "{heavy_name}のほうが導体は太い(= 低圧でより遠くへ届く)のに、"
                    "<b>高圧は載せられません</b>。逆に絶縁ケーブルは高圧を送れますが、"
                    "低圧での距離は{heavy_name}に負けます。"
                    "<b>両方が要るときだけ{best_name}を使ってください</b>"
                    "(いちばん高いので、それ以外の場面では買う必要がありません)。",
                    "<b>高圧に耐えるケーブルが要るのは、分電盤から変圧器までの区間だけです。</b>"
                    "変圧器から先は {secondary_volts}V に下がるので、"
                    "<b>そこから機器までは安い普通のケーブルで正解です</b>"
                    "(本物の電柱の上の変圧器と同じ考えかたです)。",
                    "1 台の分電盤がたどれるケーブルは <b>{max_nodes} 本まで</b>です。"
                    "それより広い拠点は、分電盤を 2 台に分けてください。",
                    "上の距離は「送る途中で失う電気が <b>{loss_budget_pct}%</b> になるところまで」"
                    "という決まりから出ています。そこから先はケーブルが光らず、機器も動きません。",
                ],
            },
            {
                "title": "③ 分電盤 — 系統・電圧・アンペア",
                "goal": "<b>電圧は「届く距離」を買います。アンペアは「同時に何台動かせるか」を買います。</b>"
                        "この 1 行が分電盤の全部です。",
                "diagram": {
                    "caption": "1 台の分電盤は {circuits} 系統。"
                               "ケーブルの枝ごとに自動で分かれます",
                    "rows": [
                        [
                            None,
                            ("i", "sorakaze_power:breaker", "分電盤"),
                            None, None, None,
                        ],
                        [
                            ("a", "←"), ("a", "↓"), ("a", "→"), None, None,
                        ],
                        [
                            ("i", "sorakaze_deco:atm", "系統 1"),
                            ("i", "sorakaze_guns:auto_turret", "系統 2"),
                            ("i", "sorakaze_power:air_conditioner", "系統 3"),
                            ("n", "…最大 {circuits} 系統"),
                            None,
                        ],
                    ],
                },
                "steps": [
                    "<b>ふだんは何もしなくて大丈夫です。</b>置いた時点で分電盤は"
                    "系統・名前・電圧・アンペアを自分で決めています。",
                    "<b>電圧は {voltage_steps} 段</b>({volts_100}V / {volts_200}V / 高圧 {volts_high}V)。"
                    "上げるほど遠くまで届きます — 損失は電圧の 2 乗に反比例するので、"
                    "電圧を 2 倍にすると距離はおよそ<b>4 倍</b>になります。",
                    "<b>アンペアは {amp_steps} の {amp_steps_count} 段</b>。"
                    "{volts_100}V の {amp_min} なら機器 {amp_min_devices_100} 台、"
                    "{volts_200}V の {amp_min} なら {amp_min_devices_200} 台が目安です"
                    "(機器 1 台 = {device_watts}W)。",
                    "容量を超えると<b>その系統だけが「遮断」されます</b>(他の系統は生きています)。"
                    "分電盤を開いてその行を<b>入れ直す</b>と復帰します。"
                    "同じことが続くなら、アンペアを上げるか(いちばん大きい段は {amp_max})、"
                    "機器を別の系統へ分けてください。",
                ],
                "notes": [
                    "<b>電圧を上げるとアンペアは下がります。</b>同じ機器でも "
                    "{volts_200}V にすれば電流は半分になり、遮断しにくくなります"
                    "(実際の電気工事と同じ理屈です)。",
                    "自動で決まるアンペアには余裕が入っています"
                    "(実際に使う電力が定格の {amp_headroom_pct}% までに収まる段を選びます)ので、"
                    "<b>置いた直後にいきなり落ちることはありません</b>。",
                    "分電盤の「主幹」を切ると<b>全系統がいっぺんに止まります</b>。工事のときに便利です。",
                ],
            },
            {
                "title": "④ 変圧器 — 遠いときだけ得をする",
                "goal": "高圧は遠くまで届きますが、<b>変圧器は何も使っていなくても電気を食べ続けます</b>。"
                        "だから短い配線ではかえって損です。",
                "diagram": {
                    "caption": "分電盤 →(高圧・絶縁)→ 変圧器 →({secondary_volts}V・普通のケーブル)→ 機器",
                    "rows": [[
                        ("i", "sorakaze_power:breaker", "分電盤(高圧)"),
                        ("a", "→"),
                        ("i", "sorakaze_power:insulated_cable", "絶縁ケーブル"),
                        ("a", "→"),
                        ("i", "sorakaze_power:transformer", "変圧器"),
                        ("a", "→"),
                        ("i", "sorakaze_power:cable", "普通のケーブル"),
                        ("a", "→"),
                        ("i", "sorakaze_deco:atm", "機器"),
                    ]],
                },
                "io": {
                    "in": [("sorakaze_power:insulated_cable", "高圧 {volts_high}V(絶縁が必須)")],
                    "out": [("sorakaze_power:cable", "{secondary_volts}V(安いケーブルでよい)")],
                },
                "steps": [
                    "<b>およそ {crossover} ブロックが分かれ目です。</b>"
                    "それより<b>短い</b>配線では {volts_100}V / {volts_200}V のほうが得、"
                    "<b>長い</b>配線では高圧のほうが得になります。",
                    "高圧にするときは、<b>機器の近くに変圧器</b>を置きます。"
                    "分電盤から変圧器までを<b>絶縁ケーブル</b>でつなぎます。",
                    "<b>変圧器から先は {secondary_volts}V に下がります。</b>"
                    "そこから機器までは<b>普通のケーブル</b>で構いません(そのほうが安いです)。",
                ],
                "notes": [
                    "変圧器を置き忘れて高圧にすると、分電盤に「変圧器なし」と出て動きません。",
                    "近くの拠点をつなぐだけなら<b>高圧は要りません</b>。"
                    "{volts_200}V で {cable_reach_200} ブロック届きます。",
                ],
            },
            {
                "title": "⑤ 燃料 — かまどで焼けるものは全部入ります",
                "goal": "何を入れても動きますが、<b>出る電気の量がまるで違います</b>。木はいちばん損です。",
                "diagram": {
                    "caption": "左ほど弱く、右ほど強い(1 tick あたりの出力 = 動かせる機器の数)",
                    "rows": [
                        [
                            ("i", "minecraft:oak_log", "木・板材"),
                            ("i", "minecraft:coal", "石炭・木炭"),
                            ("i", "minecraft:blaze_rod", "ブレイズロッド"),
                            ("i", "minecraft:lava_bucket", "溶岩バケツ"),
                            ("i", "sorakaze_guns:energy_cell", "エネルギーセル"),
                        ],
                        [
                            ("n", "{wood_units} 単位"),
                            ("n", "{coal_units} 単位"),
                            ("n", "{blaze_units} 単位"),
                            ("n", "{lava_units} 単位"),
                            ("n", "{cell_units} 単位"),
                        ],
                        [
                            ("n", "機器 {wood_devices} 台"),
                            ("n", "機器 {coal_devices} 台"),
                            ("n", "機器 {blaze_devices} 台"),
                            ("n", "機器 {lava_devices} 台"),
                            ("n", "機器 {cell_devices} 台"),
                        ],
                    ],
                },
                "io": {
                    "in": [("minecraft:coal", "石炭 1 個 = {coal_seconds} 秒"),
                           ("minecraft:charcoal", "木炭も木あつかいです"),
                           ("sorakaze_guns:energy_cell", "いちばん強い燃料")],
                    "out": [("sorakaze_power:cable", "電気")],
                },
                "steps": [
                    "燃料を<b>手に持って右クリック</b>で入れます。"
                    "発電機・原子力発電所・<b>分電盤</b>のどれにも入ります。",
                    "<b>木はやめたほうがいいです。</b>石炭の <b>{wood_ratio} 分の 1</b> の出力しか出ず、"
                    "しかも燃える時間も短いので、あっという間になくなります。",
                    "<b>エネルギーセルがいちばん強い燃料です</b>({cell_units} 単位 = 機器 {cell_devices} 台)。"
                    "<b>蓄電池</b>が、発電機・原子力発電所から届いた電気をためてセルを作ります(①を見てください)。"
                    "原子力発電所は、<b>蓄電池が見つからないときだけ</b>自分の中だけでセルを作る昔ながらの動きに"
                    "戻ります(1 個あたり約 {reactor_seconds} 秒、{reactor_buffer} 個たまると止まって"
                    "石炭を無駄にしません)。",
                    "<b>分電盤に直接セルを差す</b>こともできます。1 個で約 {cell_minutes} 分もちます"
                    "(たくさん電気を使っているほど早く減ります)。",
                ],
                "notes": [
                    "<b>分電盤で燃料を燃やすと、もちが {breaker_fuel_pct}% になります。</b>"
                    "非常用と考えてください。ちゃんと発電するなら発電機を建てるほうが得です。",
                    "石炭 1 個で <b>{coal_total} 単位</b>ぶんです。"
                    "機器 {coal_devices} 台を {coal_seconds} 秒動かせる計算になります。",
                    "セルは<b>燃料として燃やすと {cell_seconds} 秒</b>しかもちません"
                    "(分電盤に差して使うほうがずっと長もちします)。"
                    "原子力発電所が蓄電池なしで自分だけでセルを 1 個作るのに約 {reactor_seconds} 秒かかるので、"
                    "<b>セルを燃やしてセルを作っても増えません</b>"
                    "(蓄電池を使った場合の生産ペースは、つないだ発電機の出力によって変わります)。",
                ],
            },
            {
                "title": "⑥ ホッパーで燃料を自動で入れる",
                "goal": "毎回手で石炭を入れるのは大変です。ホッパーにつなげば自動になります。",
                "diagram": {
                    "caption": "上にホッパー = 入れる / 下にホッパー = 取り出す",
                    "rows": [
                        [None, ("i", "minecraft:chest", "石炭の箱"), None,
                         ("i", "minecraft:chest", "セルの箱")],
                        [None, ("a", "↓"), None, ("a", "↑")],
                        [None, ("i", "minecraft:hopper", "上から入れる"), None,
                         ("i", "minecraft:hopper", "下から出す")],
                        [None, ("a", "↓"), None, ("a", "↑")],
                        [None, ("i", "sorakaze_power:reactor_controller", "原子力発電所"),
                         ("a", "→"), ("n", "できたセル")],
                    ],
                },
                "io": {
                    "in": [("minecraft:coal", "石炭を上から")],
                    "out": [("sorakaze_guns:energy_cell", "セルを下から"),
                            ("minecraft:bucket", "溶岩バケツの空バケツも下から")],
                },
                "steps": [
                    "機械の<b>上か横</b>にホッパーを向けると、燃料が入ります。",
                    "機械の<b>下</b>にホッパーを置くと、できたエネルギーセルと"
                    "空バケツ(溶岩バケツを燃やしたとき)を取り出せます。",
                    "<b>{machine_size} のどのマスからでも構いません。</b>"
                    "建物のどこに当ててもホッパーは効きます。",
                    "暖炉と分電盤も同じです。暖炉は上と横から石炭を入れられます。",
                ],
                # ⚠ v1.8.4 でここは**まるごと書きかえた**。
                # v1.8.1〜v1.8.3 は「燃料を運ぶホッパーだけは例外で動く / それ以外は止まる」と
                # 書いていたが、**いまはどのホッパーも電気を要らない**(mixin ごと削除された)。
                # 例外の説明を残すと「では他のホッパーは止まるのか」と読めてしまうので消した。
                "notes": [
                    "<b>ホッパーに電気は要りません。</b>燃料を運ぶものも、そうでないものも、"
                    "いままでどおり動きます。",
                    "<b>v1.8.3 まではホッパーにも電気が要りました。</b>"
                    "そのせいで「燃料が届かない → 発電できない → ホッパーが動かない」という"
                    "抜け出せない状態になることがあったので、<b>やめました。</b>"
                    "止まっていたホッパーは、更新すると自分で動きだします。",
                ],
            },
            {
                "title": "⑦ 燃料の要らない発電({renewable_count} 種類)",
                "goal": "タダで発電できますが、<b>それぞれ条件があります</b>。"
                        "1 台では足りないので、並べて増やします。",
                "diagram": {
                    "caption": "条件を満たしていないと出力が落ちます / 止まります",
                    "rows": [
                        [
                            ("i", "sorakaze_power:solar_panel", "太陽光パネル"),
                            ("i", "sorakaze_power:wind_turbine", "風力発電機"),
                            ("i", "sorakaze_power:hydro_generator", "水流発電機"),
                        ],
                        [
                            ("n", "{solar_units} 単位(機器 {solar_devices} 台)"),
                            ("n", "{wind_units} 単位(機器 {wind_devices} 台)"),
                            ("n", "{hydro_units} 単位(機器 {hydro_devices} 台)"),
                        ],
                        [
                            ("n", "空が見えて、昼であること。夜は 0"),
                            ("n", "高いところ + 羽根の周りが開いていること"),
                            ("n", "流れている水に {hydro_faces} 面ふれていること"),
                        ],
                    ],
                },
                "io": {
                    "in": [("minecraft:water_bucket", "流れる水(水流発電機)")],
                    "out": [("sorakaze_power:cable", "燃料ゼロの電気")],
                },
                "steps": [
                    "どれも<b>ケーブルで分電盤につなぐ</b>だけです。燃料は要りません。",
                    "<b>太陽光パネル</b>は屋根の上に。空が見えないと発電しません。"
                    "<b>夜と雨は止まります。</b>",
                    "<b>風力発電機</b>は高い塔の上に。高さ Y{wind_base_y} 以下ではほとんど回らず、"
                    "Y{wind_full_y} で全力になります。羽根の周りをふさがないでください。"
                    "<b>夜も回ります。</b>",
                    "<b>水流発電機</b>は川の中に。<b>止まっている水では動きません</b>(流れている水が要ります)。"
                    "{hydro_faces} 面ふれていると全力です。昼も夜も一定です。",
                    "足りないときは<b>並べて増やしてください。</b>出力はそのまま足し算になります。",
                ],
                "notes": [
                    "<b>どれも石炭の発電機より弱いか、条件が厳しいかのどちらかです。</b>"
                    "太陽光は石炭の半分しか出ず、しかも 1 日の半分は 0 です。",
                    "素手で右クリックすると、いま何 % で発電しているか・止まっている理由が出ます。",
                ],
            },
            {
                "title": "⑧ ⚠ 発電機は部屋を暑くします(暖炉とエアコン)",
                "goal": "<b>動いている発電機は、その部屋を暑くします。</b>"
                        "台数が増えるほど暑くなり、放っておくと<b>体力が減ります。</b>"
                        "冷やす道具はエアコンだけです。",
                "diagram": {
                    "caption": "動いている機械 1 台ぶんの効果(止まっている機械は 0 °C です)",
                    "rows": [
                        [
                            ("i", "sorakaze_power:generator_controller", "発電機"),
                            ("i", "sorakaze_power:reactor_controller", "原子力発電所"),
                            ("i", "sorakaze_power:solar_panel", "太陽光・風力・水流"),
                            ("i", "sorakaze_power:air_conditioner", "エアコン"),
                        ],
                        [
                            ("n", "+{machine_heat_c}°C"),
                            ("n", "+{reactor_heat_c}°C"),
                            ("n", "+{renewable_heat_c}°C(出しません)"),
                            ("n", "−{aircon_c}°C"),
                        ],
                        [
                            ("n", "2 台で +{heat_2}°C"),
                            ("n", "4 台で +{heat_4}°C"),
                            ("n", "8 台で +{heat_8}°C"),
                            ("n", "エアコン 1 台 = 発電機 {machines_per_ac} 台ぶん"),
                        ],
                        [
                            ("i", "sorakaze_power:fireplace", "暖炉"),
                            ("n", "+{fireplace_c}°C"),
                            ("n", "寒さ対策 / 電気は要りません"),
                            ("n", "半径 {temp_radius} ブロック"),
                        ],
                    ],
                },
                "io": {
                    "in": [("sorakaze_power:generator_controller", "動かすと熱が出ます")],
                    "out": [("sorakaze_power:air_conditioner", "同じ部屋に置けば消えます")],
                },
                "steps": [
                    "<b>「その部屋」の空気がつながっている範囲で数えます。</b>"
                    "壁と閉じたドアで区切られていれば、向こう側の熱も冷房も届きません。"
                    "<b>だから機械室を分けて閉めるのがいちばん簡単な対策です。</b>",
                    "<b>エアコンは同じ部屋のどこに置いても同じだけ効きます</b>(距離は関係ありません)。"
                    "発電機のとなりに置く必要はありません。",
                    "必要なエアコンの数は<b>発電機 {machines_per_ac} 台につき 1 台</b>です。"
                    "発電機 4 台なら {ac_for_four} 台、8 台なら {ac_for_eight} 台に増やしてください。",
                    "<b>屋外では熱は {open_air_pct}% まで弱まります。</b>"
                    "どうしても冷やしきれないときは、屋根を外して露天にするのも手です。",
                    "<b>暖かくしたいときは暖炉です。</b>石炭を持って右クリックで入れるだけで"
                    "(上にホッパーでも入ります)、まわり半径 {temp_radius} ブロックが +{fireplace_c}°C になります。"
                    "電気は要りません。石炭 1 個で <b>{fireplace_seconds} 秒</b>もつので、"
                    "火が消えると暖まらなくなります。",
                ],
                "notes": [
                    "<b>{comfort_max_c}°C を超えると警告、{scorching_c}°C 以上で体力が減りはじめます。</b>"
                    "画面の温度計が赤くなったら、エアコンを増やすか発電機を止めてください。",
                    "<b>エアコンは冷やしすぎません。</b>{comfort_max_c}°C より下へは下げないので、"
                    "雪原に置いても凍えることはありません。",
                    "<b>エアコンには電気が要ります</b>(暖炉は要りません)。"
                    "ケーブルで分電盤につないでください。置くと {aircon_size} の大きさになります。"
                    "<b>スニーク + 右クリック</b>で入り切り、素手で右クリックすると状態が出ます。",
                    "熱は発電機 {machine_cap_count} 台(+{machine_cap_c}°C)で頭打ちになります。"
                    "それ以上増やしても暑くはなりませんが、<b>エアコンは 1 台ずつきちんと効きます。</b>",
                    "<b>暑くて困る心当たりがあるなら、</b>"
                    "<code>config/sorakaze_survival.json</code> の "
                    "<code>temperatureMachineHeatEnabled</code> を <code>false</code> にすれば"
                    "機械の熱だけを止められます(エアコンは止まりません)。",
                ],
            },
            {
                "title": "⑨ ⚠ 電気が要るようになったもの",
                "goal": "この MOD を入れると、<b>いままで動いていたものが止まります。</b>"
                        "配線すれば元どおり動きます。",
                "diagram": {
                    "caption": "この一覧の機器は、ケーブルで分電盤につながっていないと動きません",
                    "rows": [
                        [
                            ("i", "sorakaze_guns:auto_turret", "自動タレット"),
                            ("i", "sorakaze_guns:spider_turret", "クモ除けタレット"),
                            ("i", "sorakaze_guns:vex_turret", "ヴェックス除けタレット"),
                            ("i", "sorakaze_deco:atm", "ATM"),
                        ],
                        [
                            ("i", "sorakaze_deco:special_atm", "特別 ATM"),
                            ("i", "sorakaze_deco:security_camera", "防犯カメラ"),
                            ("i", "sorakaze_deco:teleport_elevator", "エレベーター"),
                            ("i", "sorakaze_deco:escalator", "エスカレーター"),
                        ],
                        [
                            ("i", "sorakaze_boss:enhanced_beacon", "強化ビーコン"),
                            ("i", "sorakaze_power:air_conditioner", "エアコン"),
                        ],
                    ],
                },
                "io": {
                    "in": [("sorakaze_power:cable", "ケーブルをつなぐ")],
                    "out": [("sorakaze_deco:teleport_elevator", "また動くようになります")],
                },
                "steps": [
                    "動かなくなった機器の場所まで、分電盤から<b>ケーブル</b>を引いてください。",
                    "<b>ケーブルが光れば通電しています。</b>光っていなければ、"
                    "分電盤・発電機・燃料のどれかを確かめてください。",
                    "機器 1 台が使う電気は {device_watts}W です。"
                    "{branch_watts}W(= {devices_per_branch} 台)ごとに、必要な発電が 1 単位ずつ増えます。",
                ],
                "notes": [
                    "<b>強化ビーコン</b>だけは少し違い、となりのケーブルが光っているかどうかを見ます。",
                    "建材 MOD の機器(カメラ・エレベーター・エスカレーター・ATM)は、"
                    "<b>建材 MOD 側の設定で個別に電気を要らなくできます</b>"
                    "(<code>config/sorakaze_deco.json</code> の <code>…RequiresPower</code>)。",
                ],
            },
            {
                "title": "⑩ ⚠⚠ レッドストーンにも電気が要ります(いちばん大事)",
                "goal": "<b>ワールド中のレッドストーン回路が、電気の来ていない場所では止まります。</b>"
                        "いま動いている農場・駅・自動ドアも止まります。",
                "diagram": {
                    "caption": "左: 電気が要るもの({gated_count} 種) / "
                               "右: 電気が無くても必ず動くもの({exempt_count} 種)",
                    "rows": [
                        [
                            ("i", "minecraft:redstone", "粉"),
                            ("i", "minecraft:repeater", "反復装置"),
                            ("i", "minecraft:comparator", "比較装置"),
                            ("n", "　"),
                            ("i", "minecraft:lever", "レバー"),
                            ("i", "minecraft:tripwire_hook", "フック"),
                        ],
                        [
                            ("i", "minecraft:redstone_torch", "トーチ"),
                            ("i", "minecraft:redstone_block", "ブロック"),
                            ("n", "↑ 止まります"),
                            ("n", "　"),
                            ("i", "minecraft:daylight_detector", "日照センサー"),
                            ("i", "minecraft:observer", "オブザーバー"),
                        ],
                    ],
                },
                "io": {
                    "in": [("sorakaze_power:cable", "その場所にケーブルを引く")],
                    "out": [("minecraft:redstone", "また信号が出ます")],
                },
                "steps": [
                    "<b>直しかたは 1 つだけです。</b>その回路のある場所まで、"
                    "分電盤から<b>ケーブルを引いてください。</b>それだけで元どおり動きます。",
                    "<b>レバー・ボタン・感圧板・オブザーバー・日照センサーなどの「感知するもの」は、"
                    "電気が無くても必ず動きます</b>({exempt_count} 種類)。"
                    "電気が止まった拠点をゲームの中から直せなくなるのを防ぐためです。",
                    "<b>レッドストーンブロックは、電気の来ていない場所に置くと約 {decay_minutes} 分で崩れます。</b>"
                    "崩れたぶんは{decay_drops}(なくなりません)。"
                    "置くだけで電気がタダになってしまうのを防ぐためです。"
                    "<b>電気の来ている場所では崩れません</b>ので、配線済みの拠点では飾りに使えます。",
                    # ⚠ v1.8.4: 対象が 17 → {inverted_count} になった。数だけでなく
                    # **名前**も実装(タグ + 各 MOD の ja_jp.json)から読む。
                    "<b>「通電すると止まる」タイプの装置は、電気の無い場所では"
                    "止まったままになります。</b>ただし対象は "
                    "<b>{inverted_names}</b> の {inverted_count} つだけです。"
                    "廃棄装置が中身を消したり、レーザーやタレットが勝手に点いて"
                    "動物や村人を殺したりするのは<b>取り返しがつかない</b>ためです。",
                    # ⚠ 「{freed_count} 種類あった」とは書かない —— v1.8.3 の総数は 17 で、
                    #   14 はそのうち**外したぶん**である。総数は実装から読めない
                    #   (外した先のタグにしか残っていない)ので、**総数を主張しない**書き方にする。
                    "<b>v1.8.3 では、これにさらに {freed_count} 種類が入っていました。</b>"
                    "仕分け機・コンベア・信号機・列車自動停止ブロックなどが"
                    "「電気が無いと動かない」状態になっていたので、"
                    "<b>ぜんぶ対象から外しました。</b>いまは電気が無くても動きます"
                    "(止まっていたものは、更新すると自分で動きだします)。",
                ],
                "notes": [
                    "<b>全部いままでどおりに戻す方法があります。</b>"
                    "<code>config/sorakaze_power.json</code> の "
                    "<code>redstoneRequiresPower</code> を <code>false</code> にしてください。"
                    "レッドストーンはこの MOD が無かったときと同じに戻ります"
                    "(切りかえたあとサーバーを再起動してください)。",
                    "<b>電気のしくみそのものを全部止めたいとき</b>は、同じファイルの "
                    "<code>powerEnabled</code> を <code>false</code> にします。"
                    "機器もレッドストーンも電気を要らなくなり、置いたブロックは消えません。",
                    # ⚠ v1.8.4: ここには「ホッパーも止まります(hoppersRequirePower で切れます)」
                    # と書いてあった。**どちらも嘘になった** —— ホッパーは対象から外れ、
                    # そのつまみは config ごと消えた。消えたつまみを案内すると、
                    # 所有者は `sorakaze_power.json` に無い行を探すことになる。
                    "<b>ホッパー(バニラのもの)は対象ではありません。</b>"
                    "電気が無くても、いままでどおり動きます。",
                ],
            },
            {
                "title": "⑪ LED パネル照明 — 電気で光る、いちばん明るい灯り",
                "goal": "光量は <b>{led_light}</b>(バニラで出せる最大)。"
                        "<b>薄い板</b>なので天井に貼っても頭がつかえません。",
                "diagram": {
                    "caption": "厚さは {led_thickness_px}/16 ブロック。"
                               "面ならどこにでも貼れます(床・壁・天井)",
                    "rows": [
                        [
                            ("i", "sorakaze_power:cable", "電気が来ている"),
                            ("n", "→"),
                            ("i", "sorakaze_power:led_panel", "光量 {led_light}"),
                            ("n", "→"),
                            ("i", "minecraft:torch", "たいまつより広く明るい"),
                        ],
                    ],
                },
                "io": {
                    "in": [("sorakaze_power:cable", "ケーブルをつなぐ")],
                    "out": [("sorakaze_power:led_panel", "光量 {led_light} で点きます")],
                },
                "steps": [
                    "貼りたい面を右クリックで置いてください。<b>向きは貼った面で決まります。</b>",
                    "<b>ケーブルで分電盤につないでください。</b>電気が来ていないと点きません"
                    "(暗いままなのは壊れているのではなく、電気が来ていないからです)。",
                    "<b>すき間なく並べると、明るい範囲がさらに広がります。</b>"
                    "どれだけ広がるかは<b>アイテムの説明(持ったときに出る文)</b>に"
                    "実測値が書いてあります(3×3・5×5・7×7 のぶん)。",
                ],
                "notes": [
                    "<b>停電すると消えます。</b>湧きつぶしをこれだけに頼っていると、"
                    "燃料が切れた夜に拠点の中で湧きます。"
                    "<b>大事な場所にはたいまつも残しておいてください。</b>",
                    "水に沈めても使えます(水没させても消えません)。",
                ],
            },
            {
                # V2 §9.2/§10(2026-08-17 に出荷)。**空気清浄機を足したら、
                # ここに書かないと生成が止まる**(検査⑤「電力 MOD のカードが全部
                # どれかの図に出ていること」)。実際 2026-08-17 の再生成はここで止まった。
                "title": "⑫ ⚠ 原子力発電所は空気を汚します(空気清浄機)",
                "goal": "<b>動いている原子力発電所は、まわりの空気を汚します。</b>"
                        "汚れた空気の中に立っていると、遅くなり・弱くなり・最後は毒を受けます。"
                        "消す道具は<b>空気清浄機</b>だけです。",
                "diagram": {
                    "caption": "汚染度は 0 〜 {pollution_max}。{pollution_light} 未満なら何も起きません"
                               "(原子力発電所を止めれば、時間とともに自分で下がります)",
                    "rows": [
                        [
                            ("i", "sorakaze_power:reactor_controller", "原子力発電所"),
                            ("a", "→"),
                            ("n", "半径 {pollution_radius} ブロックが汚れる"),
                            ("a", "→"),
                            ("i", "sorakaze_power:air_purifier", "空気清浄機"),
                            ("a", "→"),
                            ("n", "半径 {purifier_radius} ブロックが {purifier_seconds} 秒で安全に"),
                        ],
                        [
                            ("n", "{pollution_light} 以上"),
                            ("n", "{pollution_heavy} 以上"),
                            ("n", "{pollution_severe} 以上"),
                            None, None, None, None,
                        ],
                        [
                            ("n", "移動速度低下 I"),
                            ("n", "+ 弱体化 I"),
                            ("n", "+ 毒 I"),
                            None, None, None, None,
                        ],
                    ],
                },
                "io": {
                    "in": [("sorakaze_power:reactor_controller", "動かすと空気が汚れます")],
                    "out": [("sorakaze_power:air_purifier", "通電しているあいだ消し続けます")],
                },
                "steps": [
                    "<b>汚れるのは原子力発電所だけです。</b>石炭の発電機・太陽光・風力・水流は"
                    "空気を汚しません(<b>暑くはします</b> —— ⑧を見てください)。",
                    "<b>空気清浄機を置いて、ケーブルで分電盤につないでください。</b>"
                    "ふつうの機器と同じで、<b>電気が来ていないと何もしません。</b>",
                    "1 台で<b>半径 {purifier_radius} ブロック</b>を"
                    "<b>{purifier_seconds} 秒</b>で安全なところまで下げます。"
                    "広い拠点は<b>並べて増やしてください</b> —— 重なった所は効き目が足し算になります。",
                    "素手で右クリックすると、<b>いまここの汚染度</b>と、"
                    "電気が来ているかどうかが出ます。数字が {pollution_light} 未満なら安全です。",
                ],
                "notes": [
                    "<b>いちばん重い段でも毒までです。</b>毒は体力を 1 未満にしないので、"
                    "どれだけ濃くても<b>歩いて出れば必ず助かります</b>。"
                    "効果は域外に出れば数秒で切れます(画面のアイコンで分かります)。",
                    "<b>清浄機が無くても、原子力発電所を止めれば汚染は時間で 0 に戻ります。</b>"
                    "上がりっぱなしにはなりません。清浄機はその減りを局所的に速くする道具です。",
                    "<b>屋内・屋外の区別はありません</b>(気温と違うところです)。"
                    "壁で囲っても汚れは入ってきます —— 距離だけが効きます。",
                    "<b>丸ごと止めたいときは</b> <code>config/sorakaze_power.json</code> の "
                    "<code>pollution.enabled</code> を <code>false</code> にしてください。"
                    "半径や秒数も同じところで変えられます(変えると上の数字も一緒に変わります)。",
                ],
            },
        ],
    },
    # =======================================================================
    # V4(V4.0.1 で追加)。所有者の実機報告「時間停止などの新要素 20 項目で起動方法がよく
    # わからなかった」への答え。1 モジュール 1 節、**まず何を置いて何をすれば動くか**を絵で。
    # ⚠ 数字は {v4_*} で、各 MOD の config / 定数から読む(read_v4_facts)。手で書かない。
    # =======================================================================
    {
        "id": "v4",
        "icon": "sorakaze_sky:chronos_anchor",
        "tab": "使い方",
        "title": "V4 の新要素 20 種の使い方",
        "lede": "V4 で入った 20 のモジュールを、<b>「置く → 起動する → 何が起きるか」</b>の順に 1 つずつ。"
                "どれも<b>素手で右クリックすると、いま何をしているか(何が足りないか)を答えます</b>。"
                "電気が要るのは 4 つだけ(空間導管・自動製作機・生体織機、そして設定で有効にした場合の地殻掘削機)。",
        "sections": [
            {
                "title": "① 時間停止碇 — レッドストーン信号で起動",
                "goal": "信号を受けている間だけ、周り {v4_chronos_side}×{v4_chronos_side}×{v4_chronos_side} の"
                        "ブロックの動作(かまど・ホッパーなど)と生き物の動きが止まります。",
                "diagram": {
                    "caption": "碇の隣にレバー(またはレッドストーンブロック)。入れると止まり、切ると戻る",
                    "rows": [[("i", "minecraft:lever", "レバー(信号)"), ("a", "→"),
                              ("i", "sorakaze_sky:chronos_anchor", "時間停止碇"), ("a", "→"),
                              ("i", "minecraft:furnace", "止まる")]],
                },
                "io": {"in": [("minecraft:redstone_block", "レッドストーン信号")],
                       "out": [("sorakaze_sky:chronos_anchor", "光って、うなる")]},
                "steps": [
                    "碇を置きます。<b>置いただけでは何も起きません。</b>",
                    "隣にレバーを置いて入れる(またはレッドストーンブロックを接する)と起動し、碇が明るく光ります。",
                    "信号を切るか碇を壊すと、止めていた物は元どおり動きます。",
                ],
                "notes": ["素手で右クリック: 「起動中」か「待機中 — 信号を隣接させると…」を答えます。"],
            },
            {
                "title": "② 虚空ポーチ — 右クリックで開く",
                "goal": "持ち歩ける {v4_pocket_slots} マスの倉庫。中身はワールドに保存されるので、ポーチ自体は軽いままです。",
                "diagram": {
                    "caption": "手に持って右クリック。初めて開いた時にそのポーチだけの個体になる",
                    "rows": [[("i", "sorakaze_survival:void_stitched_pocket", "ポーチ"), ("a", "→"),
                              ("i", "minecraft:chest", "{v4_pocket_slots} マスの画面")]],
                },
                "io": {"in": [("sorakaze_survival:void_stitched_pocket", "右クリック")],
                       "out": [("minecraft:chest", "倉庫が開く")]},
                "steps": [
                    "ポーチを手に持って<b>右クリック</b>すると、{v4_pocket_slots} マスの画面が開きます。",
                    "溶岩で燃えたときだけ、燃えた場所に中身を吐き出して忘れます。それ以外では中身は失われません。",
                ],
            },
            {
                "title": "③ エコー探知機 — 手に持つだけ",
                "goal": "{v4_echo_range} ブロック以内の生き物(敵対・中立)とプレイヤーが立てた音を、{v4_echo_linger_s} 秒のあいだ枠で示します。",
                "diagram": {
                    "caption": "どちらかの手に持っている間だけ働く。専用の操作は無い",
                    "rows": [[("i", "sorakaze_survival:echolic_locator", "探知機を持つ"), ("a", "→"),
                              ("i", "minecraft:rotten_flesh", "足音・攻撃音の主に枠")]],
                },
                "io": {"in": [("sorakaze_survival:echolic_locator", "持つ")],
                       "out": [("minecraft:rotten_flesh", "音の主が見える")]},
                "steps": [
                    "利き手か左手に持ちます。<b>それだけです。</b>",
                    "生き物が音を立てる(歩く・攻撃する)と、その方向に枠が出て {v4_echo_linger_s} 秒で消えます。",
                    "環境音・ブロックの音・レコードは生き物ではないので拾いません。",
                ],
            },
            {
                "title": "④ 熱機関発電機 — バイオームの境目に置く",
                "goal": "各方向 {v4_thermo_probe} ブロック先のバイオームの温度差で発電します。燃料は要りません。",
                "diagram": {
                    "caption": "暑いバイオームと寒いバイオームの境目に置き、蓄電池へケーブルをつなぐ",
                    "rows": [[("n", "砂漠 ←"), ("i", "sorakaze_power:thermodynamic_engine", "熱機関発電機"),
                              ("n", "→ 雪原"), ("a", "→"), ("i", "sorakaze_power:cable", "ケーブル"), ("a", "→"),
                              ("i", "sorakaze_power:battery", "蓄電池")]],
                },
                "io": {"in": [("minecraft:snowball", "温度差")],
                       "out": [("sorakaze_power:battery", "電気(最大 {v4_thermo_max} 単位/tick)")]},
                "steps": [
                    "<b>同じバイオームの中では出力 0</b> です。{v4_thermo_probe} ブロック先の 4 方位のどれかが違う温度のバイオームになる場所(境目)に置きます。",
                    "ふつうの発電機と同じく、<b>蓄電池</b>までケーブルをつなぎます。出力は温度差に比例し、{v4_thermo_max} で頭打ちです。",
                    "素手で右クリックすると、いまの温度差と出力を答えます。",
                ],
            },
            {
                "title": "⑤ エントロピー吸引 — 武器のエンチャント",
                "goal": "倒した相手の最大体力 × {v4_siphon_percent}% × レベルぶん、傷んだ装備の耐久を回復します。",
                "diagram": {
                    "caption": "エンチャントテーブルか金床で武器に付ける(最大 III)。ブロックではない",
                    "rows": [[("i", "minecraft:enchanted_book", "エンチャント"), ("a", "→"),
                              ("i", "minecraft:diamond_sword", "武器に付く"), ("a", "→"),
                              ("i", "minecraft:iron_chestplate", "倒すと装備が直る")]],
                },
                "io": {"in": [("minecraft:lapis_lazuli", "エンチャント")],
                       "out": [("minecraft:iron_chestplate", "耐久回復")]},
                "steps": [
                    "エンチャントテーブルで武器に付けます(本と金床でも可)。",
                    "倒すたびに、傷んだ装備へ等分に耐久が戻ります。傷んでいない装備には配りません。",
                ],
            },
            {
                "title": "⑥ 共鳴レール — 通電で速くなる",
                "goal": "通電中のレールの上だけ、トロッコの上限が {v4_rail_bpt} ブロック/tick(= {v4_rail_mps} m/s)になります。",
                "diagram": {
                    "caption": "パワードレールと同じ通電のしかた。信号は通電したレールから 8 ブロック先まで伝わる",
                    "rows": [[("i", "minecraft:redstone_torch", "信号"), ("a", "→"),
                              ("i", "sorakaze_rail:resonance_rail", "共鳴レール(光る)"), ("a", "→"),
                              ("i", "minecraft:minecart", "トロッコが加速")]],
                },
                "io": {"in": [("minecraft:redstone_torch", "レッドストーン信号")],
                       "out": [("minecraft:minecart", "{v4_rail_mps} m/s")]},
                "steps": [
                    "直線のレールとして敷きます(カーブ・坂はバニラのレールで)。",
                    "レッドストーントーチやレバーで通電します。<b>光っていれば通電中</b>です。",
                    "共鳴レールを離れた次の tick から、バニラの上限(0.4 ブロック/tick)に戻ります。",
                ],
                "notes": ["高速で走ると進行方向のチャンクを先読みします。サーバーが重ければ config で上限を下げてください。"],
            },
            {
                "title": "⑦ 空間導管 + 空間チューナー — 送り先を「写す」",
                "goal": "取り付けた先のコンテナから、{v4_conduit_range} ブロック以内の好きなコンテナへアイテムと液体を送ります。電気 1 台ぶん。",
                "diagram": {
                    "caption": "①送り先のチェストをチューナーで右クリック ②導管をチューナーで右クリック ③導管はチェストに向けて置く",
                    "rows": [[("i", "sorakaze_power:aetherial_tuner", "チューナーで送り先を記憶"), ("a", "→"),
                              ("i", "sorakaze_power:aetherial_conduit", "導管に写す"), ("a", "→"),
                              ("i", "minecraft:chest", "送り先へ流れる")],
                             [("i", "minecraft:chest", "送り元(導管の向く先)"), None,
                              ("i", "sorakaze_power:cable", "電気(接する)"), None, None]],
                },
                "io": {"in": [("sorakaze_power:aetherial_tuner", "送り先の指定"), ("sorakaze_guns:energy_cell", "分電盤の電気")],
                       "out": [("minecraft:chest", "アイテム・液体が届く")]},
                "steps": [
                    "<b>送り先</b>のチェストを空間チューナーで右クリックして覚えさせます。",
                    "導管を<b>送り元のチェストに向けて</b>置き(観察者と同じ置き方)、その導管をチューナーで右クリックして送り先を写します。",
                    "分電盤の系統のケーブルを導管に接します。以後、毎ティック 1 スタック(液体は大釜から 1 バケツ)が流れます。",
                    "スニーク + 右クリックで結線を切ります。別ディメンションと {v4_conduit_range} ブロック超は断られます。",
                ],
            },
            {
                "title": "⑧ 運動減衰ブーツ — 履いて落ちる",
                "goal": "落下ダメージが消え、着地の衝撃波(落下距離 × {v4_kinetic_per_block}、最大 {v4_kinetic_max})になります。",
                "diagram": {
                    "caption": "履くだけ。既定ではブロックを壊さない(config kineticBootsBreakBlocks)",
                    "rows": [[("i", "sorakaze_survival:kinetic_boots", "履く"), ("a", "→"),
                              ("i", "minecraft:feather", "落ちてもダメージ 0"), ("a", "→"),
                              ("i", "minecraft:tnt", "着地で衝撃波")]],
                },
                "io": {"in": [("sorakaze_survival:kinetic_boots", "装備")],
                       "out": [("minecraft:tnt", "周囲にダメージ(自分は無傷)")]},
                "steps": ["足に装備します。着地のたびに耐久を {v4_kinetic_durability} 使います。"],
            },
            {
                "title": "⑨ 光合成灯 — 染料で色を合わせる",
                "goal": "赤・緑・青の 3 チャンネルを染料で調整する光源。{v4_photic_r}:{v4_photic_g}:{v4_photic_b} のときだけ真下の作物を促成します。",
                "diagram": {
                    "caption": "染料を持って右クリック = その色 +1。スニークで −1。染料は減らない",
                    "rows": [[("i", "minecraft:red_dye", "赤 {v4_photic_r}"), ("i", "minecraft:green_dye", "緑 {v4_photic_g}"),
                              ("i", "minecraft:blue_dye", "青 {v4_photic_b}"), ("a", "→"),
                              ("i", "sorakaze_deco:photic_synthesiser", "育成光"), ("a", "↓"),
                              ("i", "minecraft:wheat", "下の作物が早く育つ")]],
                },
                "io": {"in": [("minecraft:red_dye", "染料(減らない)")],
                       "out": [("minecraft:wheat", "円錐 1×1→3×3→5×5 が促成")]},
                "steps": [
                    "灯を置きます(置いた時点では 3 色とも 15 = 白い光)。",
                    "赤の染料で右クリックすると赤が 1 上がり(15 の次は 0)、スニークしながらで 1 下がります。緑・青も同じ。",
                    "赤 {v4_photic_r}・緑 {v4_photic_g}・青 {v4_photic_b} に合わせると「育成光」の表示が出て、真下の円錐の作物が早く育ちます。",
                ],
            },
            {
                "title": "⑩ 地殻掘削機 — 鉄ブロックで囲うだけ(電気は要らない)",
                "goal": "3×3×3 の筐体で囲い、筐体の外側にチェストを接すると、真下へ 3×3 の縦坑を {v4_drill_ticks} tick に 1 マスずつ岩盤まで掘ります。",
                "diagram": {
                    "caption": "中央に掘削機、周り 26 個を鉄ブロック(または機械の筐体)。チェストは筐体の外側に接する",
                    "rows": [[("i", "minecraft:iron_block", "鉄ブロック ×26"), ("a", "→"),
                              ("i", "sorakaze_power:geofracture_drill", "地殻掘削機(中央)"), ("a", "→"),
                              ("i", "minecraft:chest", "筐体に接するチェスト")],
                             [("i", "minecraft:stone", "石は"), ("a", "→"), ("i", "sorakaze_power:slag", "スラグ(4 個で砂利 1)"),
                              None, None]],
                },
                "io": {"in": [("minecraft:iron_block", "筐体 26 個"), ("minecraft:chest", "出口")],
                       "out": [("sorakaze_power:slag", "石はスラグ"), ("minecraft:dirt", "石以外はそのまま")]},
                "steps": [
                    "掘削機を置き、<b>上下前後左右の 26 マス全部</b>を鉄ブロックか機械の筐体で埋めます(隙間 1 つでも「筐体が未完成」)。",
                    "筐体のどれかに接する位置にチェストを置きます。<b>これで動きます。電気は要りません。</b>",
                    "チェストが満杯なら待ち、床には撒きません。岩盤に着いたら止まり、スニーク + 右クリックでやり直せます。",
                ],
                "notes": [
                    "V4.0.0 は電気を要求していましたが、筐体を隙間なく囲う決まりとケーブルを接する配線が両立しないため、"
                    "V4.0.1 で<b>電気不要</b>にしました(config drill.wattsFactor を 0 より大きくすると以前どおり要求します)。",
                    "素手で右クリック: 「筐体の不足 N」「コンテナがない」「掘削中」などを答えます。",
                ],
            },
            {
                "title": "⑪ 生体織機 + DNA 注射器 — 2 匹の親から交雑の卵",
                "goal": "空の注射器を生き物に使って種類を採り、2 本と電気で {v4_weaver_s} 秒後に交雑スポーンエッグができます。",
                "diagram": {
                    "caption": "①空の注射器で親 A を右クリック ②別の注射器で親 B ③織機に 2 本入れて電気 → 卵",
                    "rows": [[("i", "sorakaze_power:dna_syringe", "注射器 ×2(採取済み)"), ("a", "→"),
                              ("i", "sorakaze_power:biological_weaver", "生体織機 + 電気 2 台ぶん"), ("a", "→"),
                              ("i", "sorakaze_power:hybrid_spawn_egg", "交雑スポーンエッグ")]],
                },
                "io": {"in": [("sorakaze_power:dna_syringe", "親 A と親 B"), ("sorakaze_guns:energy_cell", "分電盤の電気")],
                       "out": [("sorakaze_power:hybrid_spawn_egg", "親 A の種類、速度と攻撃力は親 B")]},
                "steps": [
                    "空の DNA 注射器を持って生き物を右クリックすると、その種類を採ります(傷つけません)。",
                    "織機を右クリックして画面を開き、注射器を 2 本入れます。分電盤の系統のケーブルを織機に接します。",
                    "{v4_weaver_s} 秒で卵が 1 個できます。卵を使うと親 A の種類として湧き、移動速度と攻撃力だけが親 B の値になります。",
                ],
            },
            {
                "title": "⑫ 空間転位器 — 生き物と入れ替わる",
                "goal": "視線の先 {v4_transpositor_range} ブロック以内の生き物と、自分の位置を入れ替えます。再使用 {v4_transpositor_cooldown_s} 秒。",
                "diagram": {
                    "caption": "手に持って、生き物に向けて右クリック",
                    "rows": [[("i", "sorakaze_sky:spatial_transpositor", "右クリック"), ("a", "→"),
                              ("i", "minecraft:gunpowder", "相手の位置へ、相手は自分の位置へ")]],
                },
                "io": {"in": [("sorakaze_sky:spatial_transpositor", "右クリック")],
                       "out": [("minecraft:ender_pearl", "位置の交換")]},
                "steps": ["生き物を見て右クリック。{v4_transpositor_range} ブロック以内に相手がいなければ何も起きません。"],
            },
            {
                "title": "⑬ 重力反転機 — 置くだけ",
                "goal": "真上 {v4_gravity_w}×{v4_gravity_h}×{v4_gravity_w} の中の生き物と物を毎ティック押し上げます。信号も電気も要りません。",
                "diagram": {
                    "caption": "床に置くと、その真上の柱状の領域が反重力になる。上端を抜けた者は低速落下",
                    "rows": [[("i", "sorakaze_sky:gravity_inverter", "重力反転機"), ("a", "↑"),
                              ("i", "minecraft:feather", "上へ漂う"), ("a", "↑"),
                              ("i", "minecraft:phantom_membrane", "上端で低速落下")]],
                },
                "io": {"in": [("sorakaze_sky:gravity_inverter", "置く")],
                       "out": [("minecraft:feather", "{v4_gravity_h} 段の上昇気流")]},
                "steps": ["置くだけで動きます。壊せば止まります。素手で右クリックすると領域の大きさを答えます。"],
            },
            {
                "title": "⑭ グリッチ・ストライダー — 4 部位そろえて G",
                "goal": "フルセットで瞬移キー(既定 G)を押すと、視線の先 {v4_glitch_blocks} ブロックへ壁越しに移動します。",
                "diagram": {
                    "caption": "4 部位全部を装備。行き先の足元と頭が空気なら壁の向こうへも",
                    "rows": [[("i", "sorakaze_survival:glitch_strider_helmet", "バイザー"),
                              ("i", "sorakaze_survival:glitch_strider_chestplate", "スーツ"),
                              ("i", "sorakaze_survival:glitch_strider_leggings", "レギンス"),
                              ("i", "sorakaze_survival:glitch_strider_boots", "ブーツ"), ("a", "→"),
                              ("n", "G キー"), ("a", "→"), ("i", "minecraft:ender_pearl", "{v4_glitch_blocks} ブロック先へ")]],
                },
                "io": {"in": [("sorakaze_survival:glitch_strider_chestplate", "フルセット + G")],
                       "out": [("minecraft:ender_pearl", "無敵 {v4_glitch_invuln_s} 秒、再使用 {v4_glitch_cooldown_s} 秒")]},
                "steps": [
                    "4 部位全部を装備します(1 つ欠けても効きません)。",
                    "行きたい方向を見て <b>G</b> を押します。行き先が塞がっていれば何も起きません。",
                    "G は鉄道のドア・乗り物のギアと共有です。<b>搭乗中は瞬移しません。</b>",
                ],
            },
            {
                "title": "⑮ 音響タレット — 置くだけ、音に反応",
                "goal": "{v4_turret_range} ブロック以内の音(足音・着地・ブロック操作)を聞き、音の主へ音波弾(魔法ダメージ {v4_turret_damage})を撃ちます。",
                "diagram": {
                    "caption": "置くだけ。プレイヤーの音は無視。既定ではプレイヤーに当たらない",
                    "rows": [[("i", "minecraft:rotten_flesh", "Mob の足音"), ("a", "→"),
                              ("i", "sorakaze_guns:acoustic_turret", "音響タレット"), ("a", "→"),
                              ("i", "minecraft:echo_shard", "音波弾(魔法 {v4_turret_damage})")]],
                },
                "io": {"in": [("minecraft:sculk_sensor", "音(振動)")],
                       "out": [("minecraft:echo_shard", "{v4_turret_cooldown_s} 秒に 1 発")]},
                "steps": [
                    "置くだけです。電気も信号も要りません。",
                    "Mob が近くで歩く・攻撃すると撃ちます。プレイヤー自身の音とプレイヤーの発射体は無視します。",
                    "プレイヤーにも当てたいサーバーは config の hitsPlayers を有効にします。",
                ],
            },
            {
                "title": "⑯ 次元鏡 — ロードストーンコンパスで結ぶ",
                "goal": "結んだ場所の次元・バイオーム・昼夜を 11 種の絵で映します(実際の景色ではありません)。{v4_mirror_refresh_s} 秒ごとに更新。",
                "diagram": {
                    "caption": "①ロードストーンにコンパスを使う ②そのコンパスで鏡を右クリック ③絵が変わる",
                    "rows": [[("i", "minecraft:lodestone", "ロードストーン"), ("a", "→"),
                              ("i", "minecraft:compass", "ロードストーンコンパス"), ("a", "→"),
                              ("i", "sorakaze_sky:dimensional_mirror", "鏡に右クリック"), ("a", "→"),
                              ("i", "minecraft:painting", "その場所の絵")]],
                },
                "io": {"in": [("minecraft:compass", "ロードストーンコンパス")],
                       "out": [("minecraft:painting", "11 種の絵の 1 つ")]},
                "steps": [
                    "映したい場所にロードストーンを置き、コンパスを使ってロードストーンコンパスにします。",
                    "そのコンパスを持って鏡を右クリックすると結ばれます。素手で右クリックすると状態を答えます。",
                    "スニークしながら右クリックで結びを解きます。未読込の場所は読み込まず、絵は前回のままです。",
                ],
            },
            {
                "title": "⑰ 自動製作機 — 雛形に 1 個ずつ置く",
                "goal": "3×3 の雛形にレシピを並べると、接しているコンテナの材料で {v4_fabricator_s} 秒に 1 回作ります。電気 1 台ぶん。",
                "diagram": {
                    "caption": "画面の 3×3 に実物を 1 個ずつ置く(減らない)。材料は隣のチェストから引く",
                    "rows": [[("i", "minecraft:chest", "材料のチェスト(接する)"), ("a", "→"),
                              ("i", "sorakaze_power:automated_fabricator", "自動製作機(雛形 3×3)"), ("a", "→"),
                              ("i", "minecraft:hopper", "出力トレイからホッパーで")],
                             [None, None, ("i", "sorakaze_power:cable", "電気(接する)"), None, None]],
                },
                "io": {"in": [("minecraft:chest", "材料"), ("sorakaze_guns:energy_cell", "分電盤の電気")],
                       "out": [("minecraft:hopper", "完成品(取り出しのみ)")]},
                "steps": [
                    "製作機を右クリックして画面を開き、作りたいレシピのとおりに<b>実物を 1 個ずつ</b>雛形に置きます。雛形の物は減りません。",
                    "材料を入れたチェストを製作機に接して置き、分電盤の系統のケーブルも接します。",
                    "{v4_fabricator_s} 秒に 1 回、材料が全部そろっている時だけ作ります(1 個も消えません)。出力トレイはホッパーで取れます。",
                ],
            },
            {
                "title": "⑱ クライオキャノン — 当てて凍らせる",
                "goal": "命中ごとに凍傷(1 段につき移動速度 −{v4_cryo_slow_percent}%、{v4_cryo_frost_s} 秒)。{v4_cryo_stacks} 段目で {v4_cryo_encase_s} 秒間氷に封じます。",
                "diagram": {
                    "caption": "エネルギーセルを弾として使う銃。ビームを当て続ける",
                    "rows": [[("i", "sorakaze_guns:energy_cell", "エネルギーセル(弾)"), ("a", "→"),
                              ("i", "sorakaze_guns:cryo_cannon", "クライオキャノン"), ("a", "→"),
                              ("i", "minecraft:packed_ice", "{v4_cryo_stacks} 発で氷漬け")]],
                },
                "io": {"in": [("sorakaze_guns:energy_cell", "弾")],
                       "out": [("minecraft:packed_ice", "封じられた相手は動けず窒息する")]},
                "steps": ["ほかの銃と同じ操作です。弾はエネルギーセル。封じた氷は壁や床を置き換えません。"],
            },
            {
                "title": "⑲ 無効化領域発生器 — 置くだけ",
                "goal": "半径 {v4_nullzone_radius} の球の中で、レッドストーン信号の更新と状態効果の付与が止まります。信号も電気も要りません。",
                "diagram": {
                    "caption": "置いた瞬間から効く。壊せば戻る",
                    "rows": [[("i", "sorakaze_sky:null_zone_generator", "発生器"), ("a", "→"),
                              ("i", "minecraft:redstone", "信号が変わらない"), ("i", "minecraft:potion", "効果が付かない")]],
                },
                "io": {"in": [("sorakaze_sky:null_zone_generator", "置く")],
                       "out": [("minecraft:barrier", "半径 {v4_nullzone_radius} の球")]},
                "steps": [
                    "置くだけです。素手で右クリックすると半径と、何を止めているかを答えます。",
                    "ポーション・ビーコン・エンチャントを問わず新しい効果は付きません。<b>すでに掛かっている効果は消えません。</b>",
                    "水や松明などの形状の更新は止めません。例外にしたい効果はタグ #sorakaze_sky:null_zone_passes に書きます。",
                ],
            },
            {
                "title": "⑳ 大気採集機 — 空の下に置くだけ",
                "goal": "真上が空に開いていれば、その場所の温度と高さに応じた物を {v4_harvester_cycle_s} 秒に 1 個集めます。電気は要りません。",
                "diagram": {
                    "caption": "寒冷バイオーム、または Y150 より上。屋根があると止まる",
                    "rows": [[("i", "minecraft:snow_block", "寒冷バイオーム / 高所"), ("a", "→"),
                              ("i", "sorakaze_power:atmospheric_harvester", "大気採集機(空が見える)"), ("a", "→"),
                              ("i", "minecraft:hopper", "右クリックか下のホッパーで取り出す")]],
                },
                "io": {"in": [("minecraft:snow_block", "寒さ・高さ")],
                       "out": [("minecraft:glass_bottle", "液体窒素・高空の気体など")]},
                "steps": [
                    "真上に何も無い場所に置きます。ふつうの平地では「ここでは何も採れない」と答えます —— 寒いバイオームか Y150 より上へ。",
                    "溜まったら右クリックで受け取ります。下にホッパーを置けば自動で抜けます。",
                ],
            },
        ],
    },
]

# V4.2.2: 工場の手引き。V4.1 の産業化ブロック 40 種は 3 版のあいだ「使い方」の図に 1 つも出ておらず、
# `extract_recipes.py` が 40 ブロックを名指しで止めていた(= 早見表が V4.0.1 で止まっていた理由)。
# 本文は scratchpad の fg_ja.py から生成(13 言語の howto も同じ構造から出る)。
FACTORY_GUIDE = {
    "id": "factory",
    "icon": "sorakaze_power:steam_turbine",
    "tab": "使い方",
    "title": "工場のつくりかた(V4.1 産業化の 40 ブロック)",
    "lede": "回転・蒸気・炉・液体・水道・コンベア・加工・燃料・組立の 9 つに分けて、電力 MOD の産業化ブロック 40 種の使い方をまとめます。どれも<b>素手で右クリックすると自分の状態を答えます</b>。迷ったらまずそれを。",
    "sections": [
        {
            "title": "① 回転を作って運ぶ(手回しクランク・水車・動力軸・電動機)",
            "goal": "回転(SU)を作り、動力軸で運びます。",
            "diagram": {
                "caption": "回転は動力軸を通って、同じ向きにだけ伝わります(横から見た図)",
                "rows": [
                    [
                        [
                            "i",
                            "sorakaze_power:kinetic_crank",
                            "手回しクランク: 右クリックで 8 SU"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:power_axle",
                            "動力軸(最大 16 ブロック)"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:power_axle",
                            "同じ向きの軸だけ"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "n",
                            "回転を受ける機械(この版にはまだ無い)"
                        ]
                    ],
                    [
                        [
                            "i",
                            "sorakaze_power:water_wheel",
                            "水車: 流れる水の上"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:power_axle",
                            "動力軸"
                        ],
                        None,
                        [
                            "i",
                            "sorakaze_power:electric_motor",
                            "電動機: 電気 → 回転"
                        ],
                        [
                            "a",
                            "←"
                        ],
                        [
                            "i",
                            "sorakaze_power:cable",
                            "電気"
                        ]
                    ]
                ]
            },
            "io": {
                "in": [
                    [
                        "minecraft:water_bucket",
                        "流れる水(水車)"
                    ],
                    [
                        "sorakaze_power:cable",
                        "電気(電動機)"
                    ]
                ],
                "out": [
                    [
                        "sorakaze_power:power_axle",
                        "回転(SU)"
                    ]
                ]
            },
            "steps": [
                "手回しクランクを置いて<b>右クリック</b>します。約 3 秒回りつづけ、そのあいだ 8 SU を出します。止まる前にもう一度回すと延びます。",
                "水車は<b>「流れている水」</b>に置きます。止まった水源では回らず 0 SU です。流れが速いほど強く、軸の向きに 3 台並べると真ん中の 1 台だけが回り、単独よりずっと強く回ります。",
                "動力軸は当てた面の向きに寝て、同じ向きの軸が続くかぎり<b>最大 16 ブロック先</b>まで回転を渡します。8 ブロックごとに 1 SU を摩擦で失います。",
                "電動機は分電盤の系統の電気を回転に変えます。<b>逆(回転 → 電気)はできません</b>。電気が来ていないと何も出しません。"
            ],
            "notes": [
                "この版には、<b>回転を受け取って仕事をする機械はまだありません</b>。軸の網は検査で測っていますが、回転は次の機械のための下地です。",
                "途中の軸を 1 本壊すと、その先には届きません(網が割れます)。"
            ]
        },
        {
            "title": "② 蒸気で発電する(蒸気ボイラー・蒸気タービン)",
            "goal": "固形燃料と水から電気を作ります。",
            "diagram": {
                "caption": "燃料は上から、水はバケツで、蒸気は隣のタービンへ(横から見た図)",
                "rows": [
                    [
                        None,
                        None,
                        [
                            "i",
                            "minecraft:hopper",
                            "上のホッパーに固形燃料"
                        ]
                    ],
                    [
                        None,
                        None,
                        [
                            "a",
                            "↓"
                        ]
                    ],
                    [
                        [
                            "i",
                            "minecraft:water_bucket",
                            "水入りバケツで右クリック"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:steam_boiler",
                            "蒸気ボイラー"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:steam_turbine",
                            "蒸気タービン(6 面どこでも)"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:cable",
                            "ケーブル"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:breaker",
                            "分電盤"
                        ]
                    ],
                    [
                        None,
                        None,
                        [
                            "a",
                            "↓"
                        ]
                    ],
                    [
                        None,
                        None,
                        [
                            "n",
                            "灰は真下のホッパーへ"
                        ]
                    ]
                ]
            },
            "io": {
                "in": [
                    [
                        "minecraft:coal",
                        "石炭・木炭・板材など"
                    ],
                    [
                        "minecraft:water_bucket",
                        "水"
                    ]
                ],
                "out": [
                    [
                        "sorakaze_power:cable",
                        "電気"
                    ]
                ]
            },
            "steps": [
                "ボイラーの上にホッパーを載せ、固形燃料(石炭・木炭・板材など)を入れます。",
                "<b>水入りバケツでボイラーを右クリック</b>して水を張ります。",
                "ボイラーに接して(どの面でも)蒸気タービンを置き、分電盤の系統までケーブルを引きます。蒸気は隣へそのまま渡ります。",
                "どちらも画面はありません。素手で右クリックすると、熱・水・蒸気の量や、足りないのがどちらかを答えます。"
            ],
            "notes": [
                "<b>熱いまま水を切らさないでください。</b>水が無くなると熱が一気に上がって過熱し、冷めるまで止まります。",
                "灰は下の枠に溜まるので、真下にホッパーを置くと回収できます。タービンにコンパレーターを当てると蒸気の量が読めます。"
            ]
        },
        {
            "title": "③ 耐火煉瓦で炉を組む(コークス炉・高炉・工業用燻製塔)",
            "goal": "3 つの炉はどれも「正面ブロック 1 個 + 耐火煉瓦の殻」です。",
            "diagram": {
                "caption": "正面ブロックを壁の中央・地面から 1 段上に置き、残りを耐火煉瓦で埋めます",
                "rows": [
                    [
                        [
                            "i",
                            "sorakaze_power:firebrick",
                            "耐火煉瓦: コークス炉 33 個・高炉 31 個"
                        ]
                    ],
                    [
                        [
                            "i",
                            "sorakaze_power:coke_oven",
                            "コークス炉 3x3x4: 石炭 → コークスとクレオソート"
                        ],
                        [
                            "i",
                            "sorakaze_power:blast_furnace_stack",
                            "高炉 3x3x4: 鉄 + コークス + 方解石 → 鋼"
                        ],
                        [
                            "i",
                            "sorakaze_power:industrial_smoker",
                            "工業用燻製塔 3x3x3: 食べ物 4 品同時"
                        ]
                    ]
                ]
            },
            "io": {
                "in": [
                    [
                        "minecraft:coal",
                        "石炭(コークス炉)"
                    ],
                    [
                        "minecraft:iron_ingot",
                        "鉄インゴット(高炉)"
                    ],
                    [
                        "minecraft:calcite",
                        "方解石 = 融剤(高炉)"
                    ]
                ],
                "out": [
                    [
                        "sorakaze_power:steel_ingot",
                        "鋼インゴット"
                    ]
                ]
            },
            "steps": [
                "正面ブロック(コークス炉・高炉・燻製塔)を<b>正面の壁の中央、地面から 1 段上</b>に置きます。",
                "残りを耐火煉瓦で埋めます。コークス炉は正面ブロックの<b>真後ろとそのすぐ上の 2 マス</b>を空け(炉室)、高炉は<b>真後ろの列を 4 マスとも</b>空け(風道)、燻製塔は真ん中を空けます。",
                "素手で右クリックすると、組み上がっていなければ<b>足りない数と最初の 1 か所の座標</b>を答えます。",
                "画面はありません。上のホッパーから入れ、下のホッパーで取り出します(燻製塔の燃料は横から)。"
            ],
            "notes": [
                "燻製塔だけは<b>電気が要りません</b>。かまどと同じようにコークスか石炭を焚き、燻製器で焼ける食べ物はすべて焼けます。",
                "耐火煉瓦は建てる前に多めに(コークス炉 33 個、高炉 31 個)。単体ではただの建材です。"
            ]
        },
        {
            "title": "④ 液体を運ぶ(電動ポンプ・加圧流体パイプ・流体弁・貯水槽)",
            "goal": "液体を動かせるのはポンプだけ。パイプは繋ぐだけです。",
            "diagram": {
                "caption": "吸込フランジを汲みたいものに向け、他の面からパイプを引きます(横から見た図)",
                "rows": [
                    [
                        [
                            "i",
                            "minecraft:water_bucket",
                            "水源・溶岩源・大釜"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:electric_pump",
                            "電動ポンプ(正面の吸込フランジ)"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:fluid_pipe",
                            "加圧流体パイプ"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:fluid_valve",
                            "流体弁: 信号で閉じる"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:reservoir_tank",
                            "貯水槽 32,000 mB"
                        ]
                    ]
                ]
            },
            "io": {
                "in": [
                    [
                        "sorakaze_power:cable",
                        "電気(ポンプだけ)"
                    ]
                ],
                "out": [
                    [
                        "sorakaze_power:reservoir_tank",
                        "残量はコンパレーターで"
                    ]
                ]
            },
            "steps": [
                "電動ポンプの<b>正面の吸込フランジ</b>を汲みたいもの(水源・溶岩源・大釜・パイプ)に向けて置き、分電盤の系統から電気を送ります。",
                "送り先へは他の面から加圧流体パイプを引きます。パイプは同じパイプ・弁・タンクを持つ機械に自分から繋がります。",
                "流体弁はレッドストーン信号が来ると<b>閉じ、1 mB も通しません</b>。ポンプの行き先を切り替えたり、抜いている最中のタンクへ注ぐのを止めたりできます。",
                "貯水槽は 32,000 mB 溜まります。電気は不要で、コンパレーターで残量が読めます。"
            ],
            "notes": [
                "<b>1 本の系統で運べる液体は 1 種類だけ</b>です。最初に入った液体で固定され、空になるまで変わりません。",
                "パイプも弁もタンクも電気を使いません。素手で右クリックすると、何で固定されているか・弁で閉じられていないかを答えます。"
            ]
        },
        {
            "title": "⑤ 水道を引く(取水口・井戸・加圧ポンプ・給水塔・導水渠・浄水器・水量計・給水口)",
            "goal": "圧力のある水道を作り、給水口から機械に汲ませます。",
            "diagram": {
                "caption": "水を汲み、圧力を足し、高い所から配って、給水口で受けます",
                "rows": [
                    [
                        [
                            "i",
                            "sorakaze_power:water_intake",
                            "取水口: 静かな水源の上、200 mB/tick"
                        ],
                        [
                            "i",
                            "sorakaze_power:wellhead",
                            "井戸: 真下 8 ブロックの縦坑、100 mB/tick"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:pump_station",
                            "加圧ポンプ: 圧力 +32(上限 64)"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:water_tower",
                            "給水塔: 高い所から圧力を配る"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:consumer_port",
                            "給水口: 隣の機械が汲む"
                        ]
                    ],
                    [
                        [
                            "i",
                            "sorakaze_power:aqueduct_slab",
                            "導水渠: 重力だけで 50 mB/tick"
                        ],
                        [
                            "i",
                            "sorakaze_power:treatment_filter",
                            "浄水器: 系統を浄水済みに"
                        ],
                        [
                            "i",
                            "sorakaze_power:water_meter",
                            "水量計: コンパレーターに 0〜15"
                        ]
                    ]
                ]
            },
            "io": {
                "in": [
                    [
                        "sorakaze_power:cable",
                        "電気(取水口・浄水器)"
                    ]
                ],
                "out": [
                    [
                        "sorakaze_power:consumer_port",
                        "圧力 1 以上で汲める"
                    ]
                ]
            },
            "steps": [
                "取水口を<b>静かな水源の上</b>に置きます(通電中 200 mB/tick)。海が無ければ井戸を: 真下へ 8 ブロックの縦坑を掘って底の水を汲みます(100 mB/tick)。",
                "管 32 本ごとに加圧ポンプを 1 台。圧力を 32 回復します(上限 64)。",
                "給水塔を高い所に置くと、<b>8 ブロック以上下の 48 ブロック以内</b>へポンプ無しで圧力を配ります。",
                "給水口を機械の隣に置きます。圧力 1 以上で隣の機械が水道から汲みます(右クリックで圧力が読めます)。"
            ],
            "notes": [
                "導水渠は電気を一切使わず、重力だけで下流へ 50 mB/tick 流します。",
                "浄水器は水を素通しして系統を「浄水済み」にします(2 IU/t)。水量計は隣のコンパレーターに流量を 0〜15 で出します。"
            ]
        },
        {
            "title": "⑥ コンベアで運んで仕分ける(アイテムコンベア・上り坂・仕分け門)",
            "goal": "ホッパーの塔を建てずに、床の上で物を運んで振り分けます。",
            "diagram": {
                "caption": "上に落とした物が正面の向きへ流れ、仕分け門で横へ分かれます(上から見た図)",
                "rows": [
                    [
                        [
                            "i",
                            "minecraft:hopper",
                            "ホッパーから 1 枚目へ"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:item_conveyor",
                            "アイテムコンベア"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:item_conveyor_ramp",
                            "上り坂: 1 段持ち上げる"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:item_conveyor",
                            "アイテムコンベア"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:sorter_gate",
                            "仕分け門"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "minecraft:chest",
                            "それ以外はまっすぐ"
                        ]
                    ],
                    [
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        [
                            "a",
                            "↓"
                        ]
                    ],
                    [
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        [
                            "i",
                            "minecraft:chest",
                            "見本と同じものは横へ"
                        ]
                    ]
                ]
            },
            "io": {
                "in": [
                    [
                        "sorakaze_power:cable",
                        "ごく僅かな電気(8 枚でランプ 1 個ぶん)"
                    ]
                ],
                "out": [
                    [
                        "minecraft:chest",
                        "仕分けた箱"
                    ]
                ]
            },
            "steps": [
                "コンベアを正面の向きに並べ、上にアイテムを落とすかホッパーから 1 枚目に流し込みます。<b>人にも Mob にも触れません</b>。",
                "段差は上り坂で越えます。登りたい向きに置き、前後に平らなコンベアを並べます。要る電気は平らな 1 枚と同じです。",
                "仕分け門を列の途中に立て、<b>手に持って右クリック</b>で見本に加えます(5 個まで)。見本と同じものは横へ押し出され、それ以外は前へ進みます。",
                "しゃがんで右クリックで見本を全部忘れます。素手で右クリックすると向きと電気の状態を答えます。"
            ],
            "notes": [
                "レッドストーン信号は<b>動かす合図ではなく止める合図</b>です。仕分け門は信号で裏返り、見本が黒名簿になります(レンズが白名簿で緑・黒名簿で赤)。",
                "仕分け門は何も消しません。押し出す先が無ければ床に落ちるだけで、電気も要りません。"
            ]
        },
        {
            "title": "⑦ 鉱石を 2 倍にする(粉砕機・洗鉱機・電気炉・圧延機・旋盤・スラグ再処理機)",
            "goal": "鉱石 1 個をインゴット 2 個ぶんにし、板・棒・ねじ・歯車まで加工します。",
            "diagram": {
                "caption": "上のホッパーから入れ、下のホッパーで取り出して次へ(横から見た図)",
                "rows": [
                    [
                        [
                            "i",
                            "minecraft:iron_ore",
                            "鉄鉱石 1 個"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:crusher",
                            "粉砕機: 砕けた鉱石 2 個"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:ore_washer",
                            "洗鉱機: 粉に(水 250 mB)"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:arc_furnace",
                            "電気炉: インゴット・板"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:rolling_mill",
                            "圧延機: 棒・線"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:lathe",
                            "旋盤: ねじ・歯車"
                        ]
                    ],
                    [
                        [
                            "n",
                            "石の泥(洗鉱機)"
                        ],
                        [
                            "i",
                            "sorakaze_power:slag",
                            "スラグ"
                        ],
                        [
                            "n",
                            "灰(ボイラー)"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:slag_recycler",
                            "スラグ再処理機: 粘土玉・安山岩・粗い土に"
                        ]
                    ]
                ]
            },
            "io": {
                "in": [
                    [
                        "sorakaze_power:cable",
                        "電気(全部)"
                    ],
                    [
                        "minecraft:water_bucket",
                        "水(洗鉱機だけ)"
                    ]
                ],
                "out": [
                    [
                        "minecraft:iron_ingot",
                        "鉄インゴット 2 個ぶん"
                    ],
                    [
                        "sorakaze_power:steel_gear",
                        "鋼の歯車"
                    ]
                ]
            },
            "steps": [
                "粉砕機: 鉄鉱石・深層鉄鉱石・粗鉄 1 個から<b>砕けた鉄鉱石 2 個</b>(銅も同じ)。丸石は砂利になります。",
                "洗鉱機: 砕けた鉱石を洗って粉にします。<b>電気と水の両方</b>が要ります(1 回 250 mB)。石の泥も 2 つめの枠に出ます。",
                "電気炉: 粉をインゴットに、インゴットを板にします(鉄・銅・鋼)。6 台のなかでいちばん電気を食います。",
                "圧延機: 鋼板 1 → 鋼の棒 2、鉄板 1 → 棒 1、銅板 1 → 銅線 3。旋盤: 鋼の棒 1 → ねじ 4、鉄板 1 → 鋼の歯車 1。"
            ],
            "notes": [
                "どの機械も上のホッパーから入れて下のホッパーで取り出します。粉砕機と電気炉は<b>熱が溜まり、冷めるまで止まります</b>(素手で右クリックすると熱の量)。",
                "スラグ再処理機は屑を戻します: 灰 → 粗い土、スラグ → 安山岩、石の泥 → 粘土玉。6 台のなかでいちばん電気を食いません。"
            ]
        },
        {
            "title": "⑧ 燃料を精製して発電する(工業用蒸留器・燃料発電機)",
            "goal": "コークス炉のクレオソートを精製燃料にして、いちばん強い発電機を回します。",
            "diagram": {
                "caption": "クレオソートはパイプで蒸留器へ、精製燃料はパイプで発電機へ(横から見た図)",
                "rows": [
                    [
                        [
                            "i",
                            "sorakaze_power:coke_oven",
                            "コークス炉: クレオソート"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:fluid_pipe",
                            "パイプで入れる"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:industrial_distillery",
                            "工業用蒸留器"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:fluid_pipe",
                            "右手側の凝縮器から精製燃料"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:refinery_generator",
                            "燃料発電機"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:cable",
                            "分電盤へ"
                        ]
                    ],
                    [
                        None,
                        None,
                        None,
                        None,
                        [
                            "a",
                            "↓"
                        ],
                        None,
                        None,
                        None,
                        [
                            "n",
                            "排気筒の真上は空ける"
                        ]
                    ],
                    [
                        None,
                        None,
                        None,
                        None,
                        [
                            "n",
                            "残渣もパイプで捨てる"
                        ]
                    ]
                ]
            },
            "io": {
                "in": [
                    [
                        "sorakaze_power:cable",
                        "電気(蒸留器)"
                    ]
                ],
                "out": [
                    [
                        "sorakaze_power:cable",
                        "このパックでいちばん強い定常発電"
                    ]
                ]
            },
            "steps": [
                "コークス炉が出すクレオソートを<b>パイプで</b>蒸留器に入れ、分電盤の系統から電気を送ります。",
                "右手側の凝縮器から精製燃料をパイプで抜き、燃料発電機へ送ります。",
                "燃料発電機からケーブルを分電盤の系統まで引きます。<b>固形燃料は一切受けつけません</b>。",
                "素手で右クリックすると、蒸留器は 3 つのタンクの中身(mB)、発電機は動いている/いない理由・IU/t・残り燃料・煙突の状態を答えます。"
            ],
            "notes": [
                "蒸留器は 1 回ごとに<b>残渣</b>も出します。パイプで捨てないと塔が詰まって止まります。",
                "発電機の<b>排気筒の真上のブロックは空けておいてください</b>。煙突が塞がると息が詰まり、出力がぐっと落ちます。"
            ]
        },
        {
            "title": "⑨ 組み立て・見張り・足場(組立腕・設計図カード・工場制御盤・作業安全警報・工場足場・歩廊・工業用レンチ)",
            "goal": "3x3 レシピを自動で作り、工場を見張り、機械のあいだを安全に歩きます。",
            "diagram": {
                "caption": "自動製作機で写した設計図を組立腕に渡し、材料は隣の箱から(横から見た図)",
                "rows": [
                    [
                        [
                            "i",
                            "minecraft:crafter",
                            "自動製作機に 3x3 を並べる"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:blueprint_card",
                            "設計図カードで右クリック(写す)"
                        ],
                        [
                            "a",
                            "→"
                        ],
                        [
                            "i",
                            "sorakaze_power:assembler_arm",
                            "組立腕の上の枠へ"
                        ],
                        [
                            "a",
                            "←"
                        ],
                        [
                            "i",
                            "minecraft:chest",
                            "材料の箱(腕の隣)"
                        ]
                    ],
                    [
                        [
                            "i",
                            "sorakaze_power:factory_hub",
                            "工場制御盤: 8 台まで見張る"
                        ],
                        [
                            "i",
                            "sorakaze_power:safety_siren",
                            "作業安全警報: 熱い機械で鳴る"
                        ],
                        [
                            "i",
                            "sorakaze_power:factory_scaffold",
                            "工場足場: 登れる"
                        ],
                        [
                            "i",
                            "sorakaze_power:catwalk",
                            "歩廊: 手すり付き"
                        ],
                        [
                            "i",
                            "sorakaze_power:industrial_wrench",
                            "工業用レンチ: 回す・外す"
                        ]
                    ]
                ]
            },
            "io": {
                "in": [
                    [
                        "sorakaze_power:cable",
                        "電気(組立腕・制御盤)"
                    ]
                ],
                "out": [
                    [
                        "minecraft:redstone",
                        "止まった台があれば信号"
                    ]
                ]
            },
            "steps": [
                "設計図カード: 自動製作機に 3x3 の並びを置き、<b>カードでその自動製作機を右クリック</b>すると写します。しゃがんで右クリックで白紙に戻ります。",
                "組立腕: カードを上の枠に入れ(上のホッパーでも可)、材料の箱を腕の<b>隣</b>に置きます。9 枠ぶん全部見つかってから 1 個ずつ引くので、半端に食べません。できた物は下の枠から。",
                "工場制御盤は半径 16 の機械を最大 8 台見て、<b>1 台でも止まっていればレッドストーン信号</b>を出します。作業安全警報は熱くなった機械があると鳴り、回転灯が赤く光り、信号も出します。",
                "工場足場は梯子のように登れます(鋼の棒だけで 8 個)。歩廊は手すりに当たり判定があり縁から落ちません(6 枚)。工業用レンチは右クリックで 90 度回し、しゃがんで右クリックで丁寧に外します(400 回)。"
            ],
            "notes": [
                "制御盤も警報も<b>見るだけ</b>で、物も液体も動かしません。警報は電気不要、制御盤は少しだけ要ります。",
                "バニラの作業台は閉じると中身が消えるので写せません。雛形は自動製作機です。レンチは Alpha Power のブロックにだけ効きます。"
            ]
        }
    ]
}
GUIDES.append(FACTORY_GUIDE)


# ===========================================================================
# ページの雛形(Minecraft レシピブック風 UI)
# ===========================================================================
# f-string ではなく @@TOKEN@@ 置換で埋める(CSS/JS の { } を全部二重化する事故を防ぐ)。
# 置換漏れは main() 末尾の残存トークン検査で必ず落ちる。
TEMPLATE = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Glimpse Alpha レシピ早見表</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0;}
  [hidden]{display:none !important;}
  html{height:100%;}
  body{
    height:100vh;height:100dvh;display:flex;flex-direction:column;overflow:hidden;
    font-family:"Hiragino Kaku Gothic ProN","Hiragino Sans","Yu Gothic","Meiryo",sans-serif;
    @@BODY_BG@@
    color:#fff;
  }
  img{image-rendering:pixelated;}
  /* ---- 見出し(暗い背景に MC 風の影付き白文字)---- */
  .top{flex:none;text-align:center;padding:10px 12px 7px;text-shadow:2px 2px 0 rgba(0,0,0,.65);}
  .top h1{font-size:clamp(17px,2.6vw,23px);letter-spacing:.05em;}
  .top .sub{font-size:12px;color:#e0e0e0;margin-top:3px;text-shadow:1px 1px 0 rgba(0,0,0,.65);}
  /* ---- 本(パネル)---- */
  .bookwrap{flex:1 1 auto;min-height:0;display:flex;justify-content:center;padding:0 10px;}
  .book{width:100%;max-width:1150px;min-height:0;display:flex;flex-direction:column;}
  .tabs{flex:none;display:flex;flex-wrap:wrap;gap:3px;align-items:flex-end;padding:0 8px;position:relative;z-index:2;}
  .tab{
    appearance:none;-webkit-appearance:none;font:inherit;cursor:pointer;
    display:flex;align-items:center;gap:6px;padding:6px 9px;
    background:#8f8f8f;color:#2f2f2f;
    border:3px solid;border-color:#dcdcdc #4a4a4a #4a4a4a #dcdcdc;border-bottom:0;
  }
  .tab img{width:22px;height:22px;display:block;}
  .tab-label{font-size:13px;font-weight:bold;}
  .tab-count{font-size:11px;color:#3d3d3d;background:rgba(0,0,0,.13);padding:0 5px;border-radius:7px;}
  .tab[aria-selected="true"]{
    background:#C6C6C6;position:relative;z-index:3;margin-bottom:-4px;padding-bottom:12px;
    border-color:#fdfdfd #3e3e3e transparent #fdfdfd;
  }
  .tab.dim{opacity:.4;}
  .tab:focus-visible{outline:2px solid #fff;}
  .panel{
    flex:1 1 auto;min-height:0;display:flex;flex-direction:column;
    background:#C6C6C6;
    border:4px solid;border-color:#fdfdfd #3e3e3e #3e3e3e #fdfdfd;
    box-shadow:0 0 0 2px rgba(0,0,0,.55),0 14px 34px rgba(0,0,0,.55);
    position:relative;z-index:1;
  }
  .phead{flex:none;padding:10px 12px 8px;border-bottom:2px solid #adadad;}
  .field{display:flex;align-items:center;gap:8px;background:#000;
    border:2px solid;border-color:#373737 #fff #fff #373737;padding:5px 10px;}
  .field svg{flex:0 0 auto;}
  .field input{flex:1 1 auto;min-width:0;background:transparent;border:0;outline:0;
    color:#fff;font:inherit;font-size:16px;}
  .field input::placeholder{color:#7c7c7c;}
  .field input::-webkit-search-cancel-button{display:none;}
  #clear{flex:none;width:28px;height:28px;padding:0;line-height:1;font-size:15px;visibility:hidden;}
  .searchrow{display:flex;gap:8px;align-items:stretch;}
  .searchrow .field{flex:1 1 auto;min-width:0;}
  #mute{flex:none;display:flex;align-items:center;gap:6px;padding:0 9px;line-height:1;}
  #mute-ico{font-size:16px;}
  .mute-label{font-size:12px;font-weight:bold;white-space:nowrap;}
  #mute[aria-pressed="true"]{opacity:.8;}
  .status{margin-top:7px;font-size:12.5px;color:#3F3F3F;min-height:1.3em;}
  .status b{color:#17307f;}
  .hint{color:#6a6a6a;font-size:11.5px;}
  /* ---- スロットグリッド ---- */
  .bookbody{flex:1 1 auto;min-height:0;overflow-y:auto;overflow-x:hidden;padding:0 8px 12px;}
  .bookbody::-webkit-scrollbar{width:14px;}
  .bookbody::-webkit-scrollbar-track{background:#000;border:1px solid #3e3e3e;}
  .bookbody::-webkit-scrollbar-thumb{background:#8b8b8b;border:2px solid #000;
    box-shadow:inset 2px 2px 0 #c5c5c5,inset -2px -2px 0 #555;}
  .cat-head{position:sticky;top:0;z-index:4;display:flex;align-items:center;gap:8px;
    padding:9px 4px 7px;background:#C6C6C6;color:#3F3F3F;font-weight:bold;font-size:14.5px;
    box-shadow:0 2px 0 rgba(0,0,0,.08);}
  .cat-head img{width:20px;height:20px;}
  .cat-count{font-weight:normal;font-size:12px;color:#5b5b5b;}
  .slotgrid{display:flex;flex-wrap:wrap;gap:2px;padding:2px 2px 10px;}
  .slot{width:40px;height:40px;flex:none;position:relative;cursor:pointer;padding:0;
    appearance:none;-webkit-appearance:none;border:2px solid;border-color:#373737 #fff #fff #373737;
    background:#8B8B8B;}
  .slot img{display:block;width:32px;height:32px;margin:2px;pointer-events:none;}
  .slot:hover::after,.slot:focus-visible::after{content:"";position:absolute;inset:0;
    background:rgba(255,255,255,.45);pointer-events:none;}
  .slot:focus-visible{outline:2px solid #fff;z-index:1;}
  .missing{color:#ff6a5e;font-weight:bold;display:flex;align-items:center;justify-content:center;
    width:100%;height:100%;font-size:14px;}
  #noresult{margin:26px auto;max-width:430px;text-align:center;padding:16px 18px;
    color:#ff8d80;font-size:13.5px;line-height:1.8;border:2px solid transparent;
    background:linear-gradient(rgba(16,0,16,.94),rgba(16,0,16,.94)) padding-box,
               linear-gradient(rgba(255,85,85,.6),rgba(127,20,20,.6)) border-box;}
  #noresult b{color:#fff;}
  /* ---- 「使い方」タブ(v1.8.1)----
     カードの一覧とは別の中身なので、#sections と入れかえて表示する。
     図は画像を焼かず、一覧と同じテクスチャ(TEX)を並べて組み立てる
     = 何枚並べてもファイルは太らない。 */
  /* ⚠ この面(.panel)の地色は <b>rgb(198,198,198) の明るい灰色</b>である。
     最初これを暗い面だと思って白い文字を置いたところ、実測コントラストが
     1.4:1(判読限界の 4.5:1 を大きく下回る)で、目標文にいたっては 1.15:1 だった。
     地の上に置く文字は暗く、絵を並べる箱は本当に暗くして中の文字を明るくする。 */
  #guide{padding:4px 2px 18px;color:#2b2b2b;font-size:13.5px;line-height:1.85;}
  .g-lede{max-width:760px;margin:6px 4px 18px;padding:11px 14px;font-size:13.5px;
    color:#232323;background:rgba(255,255,255,.52);
    border-left:4px solid #3f8c3f;border-radius:3px;}
  .g-sec{margin:0 0 26px;padding:0 0 20px;border-bottom:1px solid rgba(0,0,0,.18);}
  .g-sec:last-child{border-bottom:none;}
  .g-h{font-size:16px;font-weight:bold;color:#141414;margin:14px 2px 4px;}
  .g-goal{margin:0 2px 12px;color:#4d4d4d;}
  /* 置きかた図 — 中は暗い面。ドット絵は暗い地の上のほうが見分けやすい。 */
  .g-fig{display:inline-block;max-width:100%;overflow-x:auto;padding:12px 14px 10px;
    background:rgba(0,0,0,.72);border:2px solid rgba(0,0,0,.45);border-radius:4px;}
  .g-figcap{color:#cfcfcf;font-size:11.5px;margin:0 0 9px;}
  .g-row{display:flex;align-items:flex-start;gap:2px;}
  .g-cell{width:82px;min-height:64px;flex:none;display:flex;flex-direction:column;
    align-items:center;justify-content:flex-start;text-align:center;}
  .g-cell img{width:38px;height:38px;image-rendering:pixelated;}
  .g-cap{font-size:10.5px;line-height:1.35;color:#ececec;margin-top:3px;word-break:break-word;}
  .g-arrow{color:#7ee87e;font-size:22px;font-weight:bold;line-height:1;padding-top:9px;}
  .g-note-cell{font-size:10.5px;color:#cfcfcf;padding-top:12px;}
  /* 入る / 出る */
  .g-io{display:flex;flex-wrap:wrap;gap:10px;margin:14px 2px 0;}
  .g-iobox{flex:1 1 240px;min-width:0;padding:9px 12px;border-radius:4px;
    background:rgba(0,0,0,.70);border:1px solid rgba(0,0,0,.45);}
  .g-iohead{font-size:11.5px;font-weight:bold;letter-spacing:.04em;margin-bottom:6px;}
  .g-in .g-iohead{color:#8fc7ff;}
  .g-out .g-iohead{color:#9ee89e;}
  .g-chip{display:inline-flex;align-items:center;gap:5px;margin:3px 8px 3px 0;
    font-size:11.5px;color:#ececec;}
  .g-chip img{width:22px;height:22px;image-rendering:pixelated;}
  /* 手順 */
  .g-steps{margin:14px 0 0;padding-left:0;list-style:none;counter-reset:gstep;}
  .g-steps li{position:relative;margin:0 0 9px;padding-left:34px;counter-increment:gstep;}
  .g-steps li::before{content:counter(gstep);position:absolute;left:0;top:1px;
    width:22px;height:22px;border-radius:50%;background:#2f6b2f;color:#fff;
    font-size:12px;font-weight:bold;display:flex;align-items:center;justify-content:center;}
  /* ⚠ 手順の中の太字。地色 rgb(198,198,198) の上で **実測 4.5:1 以上** であること。
     v1.8.1 の #7a4a00 は実測 4.38:1 で、AA(4.5:1)をわずかに下回っていた
     (13.5px の太字は WCAG の「大きな文字」に当たらないので、4.5:1 が基準である)。
     #6b4000 は同じ色みのまま 5.21:1。**目分量で決めず、必ず測ってから変えること。** */
  .g-steps b{color:#6b4000;}
  .g-notes{margin:12px 0 0;padding:9px 12px;border-radius:4px;font-size:12.5px;
    color:#3d2f08;background:rgba(255,238,190,.80);border-left:4px solid #a8781a;}
  .g-notes div{margin:2px 0;}
  .g-notes b{color:#7a4a00;}
  @media (max-width:620px){
    .g-cell{width:64px;}
    .g-cell img{width:30px;height:30px;}
    .g-cap{font-size:9.5px;}
  }
  /* ---- ツールチップ(MC 風: 暗紫のふち)---- */
  .tip{position:fixed;left:0;top:0;z-index:90;pointer-events:none;max-width:330px;
    padding:6px 9px;font-size:13px;line-height:1.45;
    border:2px solid transparent;
    background:linear-gradient(rgba(16,0,16,.94),rgba(16,0,16,.94)) padding-box,
               linear-gradient(to bottom,rgba(80,0,255,.55),rgba(40,0,127,.55)) border-box;
    box-shadow:0 3px 10px rgba(0,0,0,.5);}
  .tip-ja{color:#fff;font-weight:bold;text-shadow:1px 1px 0 rgba(0,0,0,.8);}
  .tip-en{color:#a8a8a8;font-size:11.5px;}
  .tip-hint{font-size:11.5px;margin-top:2px;}
  /* ---- レシピのモーダル(クラフト台)---- */
  #ov{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.6);
    display:flex;align-items:center;justify-content:center;padding:14px;}
  .modal{width:min(470px,100%);max-height:92vh;max-height:92dvh;overflow-y:auto;background:#C6C6C6;
    border:4px solid;border-color:#fdfdfd #3e3e3e #3e3e3e #fdfdfd;
    box-shadow:0 0 0 2px rgba(0,0,0,.6),0 18px 44px rgba(0,0,0,.7);
    padding:13px 15px;color:#3F3F3F;}
  .m-head{display:flex;align-items:flex-start;gap:10px;}
  .m-icon{flex:none;width:44px;height:44px;background:#8B8B8B;border:2px solid;
    border-color:#373737 #fff #fff #373737;}
  .m-icon img{width:32px;height:32px;margin:4px;display:block;}
  .m-names{flex:1 1 auto;min-width:0;}
  .m-ja{font-size:16.5px;font-weight:bold;color:#2f2f2f;line-height:1.35;}
  .m-en{font-size:12px;color:#6a6a6a;margin-top:1px;}
  .m-cat{font-size:11px;color:#6a6a6a;margin-top:2px;}
  .m-close{flex:none;width:34px;height:34px;padding:0;font-size:16px;}
  .m-craftrow{display:flex;align-items:center;justify-content:center;gap:12px;margin:16px 0 8px;}
  .m-grid{display:grid;grid-template-columns:repeat(3,44px);grid-auto-rows:44px;gap:2px;flex:none;}
  .m-cell{width:44px;height:44px;background:#8B8B8B;border:2px solid;
    border-color:#373737 #fff #fff #373737;padding:0;position:relative;
    appearance:none;-webkit-appearance:none;font:inherit;}
  .m-cell img{display:block;width:32px;height:32px;margin:4px;pointer-events:none;}
  button.m-cell.link{cursor:pointer;}
  button.m-cell.link:hover::after,button.m-cell.link:focus-visible::after{
    content:"";position:absolute;inset:0;background:rgba(255,255,255,.4);pointer-events:none;}
  .m-arrow{flex:none;}
  .m-arrow img{display:block;width:52px;height:34px;}
  .m-result{flex:none;width:56px;height:56px;background:#8B8B8B;border:2px solid;
    border-color:#373737 #fff #fff #373737;position:relative;}
  .m-result img{display:block;width:48px;height:48px;margin:2px;}
  .m-count{position:absolute;right:2px;bottom:0;color:#fff;font-weight:bold;font-size:15px;
    text-shadow:1px 1px 0 #000;pointer-events:none;}
  .m-out{text-align:center;font-size:13px;color:#3F3F3F;margin-bottom:4px;}
  .m-how{margin:14px 2px 10px;padding:10px 12px;font-size:13px;line-height:1.75;color:#ffd75e;
    border:2px solid transparent;
    background:linear-gradient(rgba(16,0,16,.94),rgba(16,0,16,.94)) padding-box,
               linear-gradient(to bottom,rgba(255,170,0,.6),rgba(140,90,0,.6)) border-box;}
  .m-ings{margin-top:10px;border-top:2px solid #adadad;padding-top:8px;}
  .m-ings-h{font-size:12px;color:#5b5b5b;margin-bottom:4px;font-weight:bold;}
  .m-ing{display:flex;align-items:center;gap:8px;width:100%;padding:3px 2px;font:inherit;
    font-size:13px;color:#3F3F3F;background:none;border:0;text-align:left;}
  .m-ing img{width:24px;height:24px;flex:none;}
  button.m-ing.link{cursor:pointer;color:#17307f;}
  button.m-ing.link:hover span,button.m-ing.link:focus-visible span{text-decoration:underline;}
  .m-alts{margin-top:10px;font-size:12.5px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;}
  .m-nav{margin-top:12px;display:flex;}
  .mcbtn{appearance:none;-webkit-appearance:none;font:inherit;cursor:pointer;color:#fff;
    background:#8b8b8b;border:2px solid;border-color:#cfcfcf #414141 #414141 #cfcfcf;
    text-shadow:1px 1px 0 rgba(0,0,0,.7);padding:4px 10px;font-size:13px;}
  .mcbtn:hover,.mcbtn:focus-visible{background:#8b95d8;border-color:#dfe3ff #2f3a70 #2f3a70 #dfe3ff;}
  .foot{flex:none;text-align:center;color:#c9c9c9;font-size:10.5px;padding:6px 10px 9px;
    text-shadow:1px 1px 0 rgba(0,0,0,.7);line-height:1.5;}
  @media (max-width:620px){
    .tab{padding:5px 7px;}
    .tab-label{display:none;}
    .mute-label{display:none;}
    #mute{padding:0;width:40px;justify-content:center;}
    .m-craftrow{gap:8px;}
    .m-grid{grid-template-columns:repeat(3,40px);grid-auto-rows:40px;}
    .m-cell{width:40px;height:40px;}
    .m-cell img{margin:2px;}
    .m-arrow img{width:26px;height:17px;}
    .m-result{width:48px;height:48px;}
    .m-result img{width:40px;height:40px;margin:2px;}
  }
  /* 印刷は補助扱い: いま表示中のスロット一覧だけでも切れずに出す。 */
  @media print{
    body{overflow:visible;height:auto;background:#fff;}
    .bookbody{overflow:visible;}
  }
</style>
</head>
<body>
<noscript><div style="background:#fff;color:#222;padding:20px;margin:20px;border-radius:8px;">
この早見表の表示には JavaScript が必要です(ファイルをそのままブラウザで開けば動きます。通信はいっさい行いません)。
</div></noscript>

<header class="top">
  <h1>Glimpse Alpha レシピ早見表</h1>
  <div class="sub">全 @@TOTAL@@ 種 - アイテムを<b>クリック</b>するとレシピ/入手方法がひらきます。カーソルを合わせると名前が出ます。</div>
</header>

<div class="bookwrap">
 <div class="book">
  <div class="tabs" id="tabs" role="tablist" aria-label="ジャンル"></div>
  <div class="panel">
    <div class="phead">
      <div class="searchrow">
        <label class="field" for="q">
          <svg viewBox="0 0 24 24" aria-hidden="true" width="16" height="16" fill="#8f8f8f"><path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
          <input type="search" id="q" autocomplete="off" autocapitalize="off" spellcheck="false"
                 placeholder="なまえ・材料で検索(ひらがなでもOK 例: てつ / 電車 / どあ / iron)">
          <button type="button" id="clear" class="mcbtn" title="検索をやめる(Esc)" aria-label="検索をやめる">×</button>
        </label>
        <button type="button" id="mute" class="mcbtn"><span id="mute-ico">🔊</span><span class="mute-label" id="mute-label"></span></button>
      </div>
      <div class="status" id="status" aria-live="polite" role="status"></div>
    </div>
    <div class="bookbody" id="bookbody">
      <div id="sections"></div>
      <div id="guide" hidden></div>
      <div id="noresult" hidden><b>見つかりませんでした。</b><br>
      ちがう言葉で探してみてください(ひらがな・カタカナ・漢字・英語のどれでも探せます)。</div>
    </div>
  </div>
 </div>
</div>

<footer class="foot">Glimpse Alpha レシピ早見表 - tools/gen_recipe_sheet.py により自動生成(手動編集しないでください。レシピやテクスチャを変更したら、このスクリプトを再実行してください)。</footer>

<div class="tip" id="tip" hidden></div>
<div id="ov" hidden><div class="modal" id="modal" role="dialog" aria-modal="true" aria-labelledby="m-title"></div></div>

<script>
/* レシピブック UI。外部ライブラリ・通信は使わない(ファイルを直接ひらいても動く)。
   データはすべて下の 4 定数(生成時に埋め込み)。テクスチャは TEX に 1 回ずつだけ入り、
   何百回使われても参照は key 1 つ = ファイルが太らない。 */
var TEX=@@TEX@@;
var IT=@@IT@@;
var CARDS=@@CARDS@@;
var CATS=@@CATS@@;
var ALL_ICON=@@ALLICON@@;
var GUIDES=@@GUIDES@@;   /* 「使い方」タブ。空配列ならタブ自体を出さない */
(function () {
'use strict';
var ARROW_SRC='data:image/png;base64,@@ARROW@@';
function $(id){return document.getElementById(id);}
function jaOf(id){var e=IT[id];return e?e[0]:id;}
function enOf(id){var e=IT[id];return e?e[1]:'';}
function srcOf(id){var e=IT[id];return (e&&e[2])?('data:image/png;base64,'+TEX[e[2]]):null;}
function el(tag,cls,parent){var n=document.createElement(tag);if(cls)n.className=cls;
  if(parent)parent.appendChild(n);return n;}
function iconNode(id,size,withAlt){
  var s=srcOf(id);
  if(!s){var sp=document.createElement('span');sp.className='missing';sp.textContent='?';return sp;}
  var img=document.createElement('img');
  img.src=s;img.width=size;img.height=size;img.alt=withAlt?jaOf(id):'';
  img.loading='lazy';img.decoding='async';
  return img;
}
function escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;');}

/* ---------- クリック音(バニラの random/click.ogg 由来の WAV を同梱)----------
   ブラウザは操作(クリック)があるまで音を止めるので、AudioContext は最初の
   クリックの中で作り、suspended なら resume する。連打は毎回新しい
   BufferSource を作って鳴らす(1 つの要素を巻き戻さない)ので濁らない。
   40ms の最小間隔は同一操作の二重発火よけで、人間の連打(>80ms)は全部鳴る。 */
var SND='@@SND@@';                 /* base64 WAV。空文字なら生成時に取れなかった合図 */
var SND_IS_MC=@@SND_IS_MC@@;       /* true = 本物のマインクラフトのクリック音 */
var audio={ctx:null,buf:null,decoding:false,fallback:!SND,muted:false,plays:0,last:0};
try{audio.muted=(localStorage.getItem('recipeSheetSound')==='off');}catch(e){}
function audioCtx(){
  if(!audio.ctx){
    var AC=window.AudioContext||window.webkitAudioContext;
    if(!AC)return null;
    try{audio.ctx=new AC();}catch(e){return null;}
  }
  if(audio.ctx.state==='suspended'){try{audio.ctx.resume();}catch(e){}}
  return audio.ctx;
}
function sndBytes(){
  var s=atob(SND),a=new Uint8Array(s.length);
  for(var i=0;i<s.length;i++)a[i]=s.charCodeAt(i);
  return a.buffer;
}
function playBuf(){
  try{
    var src=audio.ctx.createBufferSource();
    src.buffer=audio.buf;
    var g=audio.ctx.createGain();
    g.gain.value=0.55;
    src.connect(g);g.connect(audio.ctx.destination);
    src.start(0);
    audio.plays++;
  }catch(e){}
}
function synthBlip(){
  /* click.ogg を使えない環境向けの短いブリップ(WebAudio 合成、0 バイト) */
  try{
    var t=audio.ctx.currentTime;
    var o=audio.ctx.createOscillator(),g=audio.ctx.createGain();
    o.type='square';
    o.frequency.setValueAtTime(2200,t);
    o.frequency.exponentialRampToValueAtTime(700,t+0.05);
    g.gain.setValueAtTime(0.16,t);
    g.gain.exponentialRampToValueAtTime(0.001,t+0.06);
    o.connect(g);g.connect(audio.ctx.destination);
    o.start(t);o.stop(t+0.07);
    audio.plays++;
  }catch(e){}
}
function clickSound(){
  if(audio.muted)return;
  var now=(window.performance&&performance.now)?performance.now():Date.now();
  if(now-audio.last<40)return;
  audio.last=now;
  if(!audioCtx())return;
  if(audio.buf){playBuf();return;}
  if(audio.fallback){synthBlip();return;}
  if(audio.decoding)return;        /* 初回デコード中の 2 発目だけは落とす(数 ms の窓) */
  audio.decoding=true;
  try{
    audio.ctx.decodeAudioData(sndBytes(),
      function(b){audio.buf=b;playBuf();},
      function(){audio.fallback=true;synthBlip();});
  }catch(e){audio.fallback=true;synthBlip();}
}
/* 鳴らす場所は 1 か所に集約: スロット・タブ・MC 風ボタン・材料リンクのどれかを
   押したら鳴る(本物のインベントリと同じく「押せる物は全部カチッと鳴る」)。
   ミュートボタン自身は、切り替え後にミュートなら鳴らさない(消した瞬間は静か)。 */
document.addEventListener('click',function(e){
  var t=(e.target&&e.target.closest)?e.target.closest('.slot,.tab,.mcbtn,[data-link]'):null;
  if(!t)return;
  clickSound();
});

/* 逆引き: このアイテムを作るカード(材料クリックでそのレシピへ飛ぶのに使う)。 */
var recipeByResult={};
for(var r0=0;r0<CARDS.length;r0++){
  var rid=CARDS[r0][1];
  (recipeByResult[rid]||(recipeByResult[rid]=[])).push(r0);
}

/* ---------- ブラウズグリッド(ジャンルごとの見出し + スロット)---------- */
var sectionsHost=$('sections');
var sections=[];
var slotOf=new Array(CARDS.length);
var builtSlots=0;
(function build(){
  var frag=document.createDocumentFragment();
  var curCat=-1,curGrid=null,curSlots=null;
  for(var i=0;i<CARDS.length;i++){
    var c=CARDS[i];
    if(c[0]!==curCat){
      curCat=c[0];
      var sec=el('section','cat-section',frag);
      sec.id='cat-'+CATS[curCat][0];
      var head=el('div','cat-head',sec);
      head.appendChild(iconNode(CATS[curCat][1],20,false));
      el('span','cat-name',head).textContent=CATS[curCat][0];
      var badge=el('span','cat-count',head);
      badge.textContent=CATS[curCat][2]+'件';
      curGrid=el('div','slotgrid',sec);
      curSlots=[];
      sections.push({cat:curCat,sec:sec,badge:badge,slots:curSlots,total:CATS[curCat][2]});
    }
    var b=document.createElement('button');
    b.type='button';b.className='slot';
    b.setAttribute('data-i',i);
    b.setAttribute('data-ti',c[1]);
    b.setAttribute('data-tk',c[4]?'h':'r');
    b.setAttribute('aria-label',jaOf(c[1]));
    b.appendChild(iconNode(c[1],32,false));
    curGrid.appendChild(b);
    curSlots.push({el:b,i:i});
    slotOf[i]=b;
    builtSlots++;
  }
  sectionsHost.appendChild(frag);
  if(builtSlots!==CARDS.length)console.error('slot/card count mismatch:',builtSlots,'vs',CARDS.length);
  window.__SHEET__={cards:CARDS.length,slots:builtSlots,tex:Object.keys(TEX).length,cats:CATS.length};
})();

/* ---------- ジャンルタブ ---------- */
var tabsHost=$('tabs');
var tabs=[];
var curTab=-1;
function makeTab(idx,iconId,label,total){
  var b=document.createElement('button');
  b.type='button';b.className='tab';b.setAttribute('role','tab');
  b.setAttribute('aria-selected',idx===curTab?'true':'false');
  b.title=label;
  b.appendChild(iconNode(iconId,22,false));
  el('span','tab-label',b).textContent=label;
  var ct=el('span','tab-count',b);
  ct.textContent=total;
  b.addEventListener('click',function(){setTab(idx);});
  tabsHost.appendChild(b);
  tabs.push({el:b,idx:idx,count:ct,total:total});
}
makeTab(-1,ALL_ICON,'すべて',CARDS.length);
for(var ci=0;ci<CATS.length;ci++)makeTab(ci,CATS[ci][1],CATS[ci][0],CATS[ci][2]);
/* 「使い方」タブ(idx=-2)。カードではなく手引きを出すので、ジャンルの並びの外側=最後に置く。 */
var GUIDE_TAB=-2;
if(GUIDES.length){
  var gsecs=0;
  for(var gi0=0;gi0<GUIDES.length;gi0++)gsecs+=GUIDES[gi0].sections.length;
  makeTab(GUIDE_TAB,GUIDES[0].icon,GUIDES[0].tab,gsecs);
}
function setTab(idx){
  curTab=idx;
  for(var i=0;i<tabs.length;i++)
    tabs[i].el.setAttribute('aria-selected',tabs[i].idx===idx?'true':'false');
  apply();
  $('bookbody').scrollTop=0;
}

/* ---------- 「使い方」タブの中身 ----------
   図は画像を焼かず、カード一覧と同じ TEX を並べて組み立てる。 */
var guideHost=$('guide');
function guideCell(c){
  var d=el('div','g-cell');
  if(!c)return d;                                   /* 空白 */
  if(c[0]==='a'){d.className='g-cell g-arrow';d.textContent=c[1];return d;}
  if(c[0]==='n'){d.className='g-cell g-note-cell';d.textContent=c[1];return d;}
  d.appendChild(iconNode(c[1],38,true));
  if(c[2])el('div','g-cap',d).textContent=c[2];
  return d;
}
function guideChip(parent,pair){
  var s=el('span','g-chip',parent);
  s.appendChild(iconNode(pair[0],22,true));
  var t=document.createElement('span');t.textContent=pair[1];s.appendChild(t);
}
function buildGuides(){
  var frag=document.createDocumentFragment();
  for(var g=0;g<GUIDES.length;g++){
    var G=GUIDES[g];
    var h=el('div','g-h',frag);h.style.fontSize='19px';h.textContent=G.title;
    if(G.lede)el('div','g-lede',frag).innerHTML=G.lede;
    for(var s=0;s<G.sections.length;s++){
      var S=G.sections[s],sec=el('div','g-sec',frag);
      el('div','g-h',sec).textContent=S.title;
      /* goal は節でいちばん大事な 1 行なので <b> を効かせる(lede・steps・notes と同じ)。
         図の caption / セルの文字は textContent のまま —— 生成側の検査がそこに
         タグを書かせない(main() の「HTML が素通しできない場所」の検査)。 */
      if(S.goal)el('div','g-goal',sec).innerHTML=S.goal;
      if(S.diagram){
        var fig=el('div','g-fig',sec);
        if(S.diagram.caption)el('div','g-figcap',fig).textContent=S.diagram.caption;
        for(var r=0;r<S.diagram.rows.length;r++){
          var row=el('div','g-row',fig),cells=S.diagram.rows[r];
          for(var c=0;c<cells.length;c++)row.appendChild(guideCell(cells[c]));
        }
      }
      if(S.io&&((S.io['in']&&S.io['in'].length)||(S.io.out&&S.io.out.length))){
        var io=el('div','g-io',sec);
        if(S.io['in']&&S.io['in'].length){
          var bi=el('div','g-iobox g-in',io);
          el('div','g-iohead',bi).textContent='入れるもの(例)';
          for(var i2=0;i2<S.io['in'].length;i2++)guideChip(bi,S.io['in'][i2]);
        }
        if(S.io.out&&S.io.out.length){
          var bo=el('div','g-iobox g-out',io);
          el('div','g-iohead',bo).textContent='出てくるもの';
          for(var o2=0;o2<S.io.out.length;o2++)guideChip(bo,S.io.out[o2]);
        }
      }
      if(S.steps&&S.steps.length){
        var ol=document.createElement('ol');ol.className='g-steps';
        for(var st=0;st<S.steps.length;st++){
          var li=document.createElement('li');li.innerHTML=S.steps[st];ol.appendChild(li);
        }
        sec.appendChild(ol);
      }
      if(S.notes&&S.notes.length){
        var nb=el('div','g-notes',sec);
        for(var n2=0;n2<S.notes.length;n2++){
          var nd=document.createElement('div');nd.innerHTML='※ '+S.notes[n2];nb.appendChild(nd);
        }
      }
    }
  }
  guideHost.appendChild(frag);
  window.__GUIDE__={topics:GUIDES.length,
                    imgs:guideHost.getElementsByTagName('img').length,
                    missing:guideHost.getElementsByClassName('missing').length};
}
if(GUIDES.length)buildGuides();

/* ---------- 検索 ---------- */
var input=$('q'),clearBtn=$('clear'),statusEl=$('status'),nores=$('noresult');
/* Python 側の search_norm() と同じ規則。ずれると検索が当たらなくなる。 */
function norm(s){
  s=s.toLowerCase();
  var out='';
  for(var i=0;i<s.length;i++){
    var c=s.charCodeAt(i);
    if(c>=0xFF01&&c<=0xFF5E)out+=String.fromCharCode(c-0xFEE0);
    else if(c===0x3000)out+=' ';
    else if(c>=0x30A1&&c<=0x30F6)out+=String.fromCharCode(c-0x60);
    else out+=s.charAt(i);
  }
  return out;
}
var hitFlags=new Array(CARDS.length);
function apply(){
  /* 「使い方」タブはカードではないので、検索の対象にならない。
     一覧と入れかえて出し、タブの件数表示は素の数に戻す。 */
  if(curTab===GUIDE_TAB){
    sectionsHost.hidden=true;guideHost.hidden=false;nores.hidden=true;
    clearBtn.style.visibility=input.value?'visible':'hidden';
    for(var gt=0;gt<tabs.length;gt++){
      tabs[gt].el.classList.remove('dim');
      if(tabs[gt].count.textContent!==''+tabs[gt].total)tabs[gt].count.textContent=''+tabs[gt].total;
    }
    statusEl.innerHTML='<b>使い方</b>: 絵のとおりに置けば動きます '
      +'<span class="hint">(検索したいときは他のジャンルをえらんでください)</span>';
    return;
  }
  guideHost.hidden=true;sectionsHost.hidden=false;
  var raw=input.value;
  var q=norm(raw).replace(/^\s+|\s+$/g,'');
  var terms=q?q.split(/\s+/):[];
  var filtering=terms.length>0;
  clearBtn.style.visibility=filtering?'visible':'hidden';
  var perCat=[];
  for(var pi=0;pi<CATS.length;pi++)perCat[pi]=0;
  var overall=0;
  for(var i=0;i<CARDS.length;i++){
    var ok=true,s=CARDS[i][5];
    for(var t=0;t<terms.length;t++){
      if(s.indexOf(terms[t])===-1){ok=false;break;}
    }
    hitFlags[i]=ok;
    if(ok){perCat[CARDS[i][0]]++;overall++;}
  }
  var shown=0;
  for(var gi=0;gi<sections.length;gi++){
    var g=sections[gi];
    var tabOk=(curTab===-1||curTab===g.cat);
    var vis=0;
    for(var si=0;si<g.slots.length;si++){
      var sl=g.slots[si];
      var v=tabOk&&hitFlags[sl.i];
      if(sl.el.hidden===v)sl.el.hidden=!v;
      if(v)vis++;
    }
    shown+=vis;
    if(g.sec.hidden!==(vis===0))g.sec.hidden=(vis===0);
    var label=(filtering&&perCat[g.cat]!==g.total)?(perCat[g.cat]+'/'+g.total+'件'):(g.total+'件');
    if(g.badge.textContent!==label)g.badge.textContent=label;
  }
  for(var ti=0;ti<tabs.length;ti++){
    var tb=tabs[ti];
    var n=(tb.idx===-1)?overall:perCat[tb.idx];
    var lbl=filtering?(n+'/'+tb.total):(''+tb.total);
    if(tb.count.textContent!==lbl)tb.count.textContent=lbl;
    if(filtering&&n===0)tb.el.classList.add('dim');else tb.el.classList.remove('dim');
  }
  nores.hidden=!(filtering&&shown===0);
  if(!filtering){
    statusEl.innerHTML=(curTab===-1)
      ?('全 <b>'+CARDS.length+'</b> 件を表示中 <span class="hint">(ジャンルの中はあいうえお順)</span>')
      :('<b>'+escHtml(CATS[curTab][0])+'</b>: '+CATS[curTab][2]+' 件を表示中');
  }else{
    var extra=(curTab!==-1&&overall>shown)
      ?(' <span class="hint">(他のジャンルに '+(overall-shown)+' 件 → 「すべて」タブ)</span>'):'';
    statusEl.innerHTML='「'+escHtml(raw)+'」 → <b>'+shown+'</b> 件 / 全 '+CARDS.length+' 件'+extra;
  }
}
/* 「使い方」を見ているときに検索を打ちはじめたら、黙って無視せず一覧へ戻す。 */
input.addEventListener('input',function(){
  if(curTab===GUIDE_TAB&&input.value){setTab(-1);return;}
  apply();
});
clearBtn.addEventListener('click',function(){input.value='';apply();input.focus();});

/* ---------- レシピのモーダル ---------- */
var ov=$('ov'),modal=$('modal');
var histStack=[],curCard=null,lastTrigger=null;
sectionsHost.addEventListener('click',function(e){
  var b=(e.target&&e.target.closest)?e.target.closest('.slot'):null;
  if(!b||!sectionsHost.contains(b))return;
  lastTrigger=b;
  openCard(parseInt(b.getAttribute('data-i'),10),false);
});
function openCard(i,push){
  hideTip();
  if(push&&curCard!==null)histStack.push(curCard);
  if(!push)histStack=[];
  curCard=i;
  renderModal(i);
  ov.hidden=false;
  var cb=$('m-close');
  if(cb)cb.focus();
}
function closeModal(){
  ov.hidden=true;histStack=[];curCard=null;hideTip();
  if(lastTrigger&&lastTrigger.focus)lastTrigger.focus();
}
ov.addEventListener('click',function(e){if(e.target===ov)closeModal();});
document.addEventListener('keydown',function(e){
  var k=e.key||e.keyCode;
  if(k==='Escape'||k===27){
    if(!ov.hidden)closeModal();
    else if(input.value){input.value='';apply();}
  }
});
function linkTo(node,cardIdx){
  node.setAttribute('data-link',cardIdx);
}
function renderModal(i){
  hideTip();
  var c=CARDS[i],id=c[1];
  modal.innerHTML='';
  var head=el('div','m-head',modal);
  el('div','m-icon',head).appendChild(iconNode(id,32,true));
  var names=el('div','m-names',head);
  var ja=el('div','m-ja',names);ja.id='m-title';ja.textContent=jaOf(id);
  var enn=enOf(id);
  if(enn&&enn!==jaOf(id))el('div','m-en',names).textContent=enn;
  el('div','m-cat',names).textContent='ジャンル: '+CATS[c[0]][0];
  var close=document.createElement('button');
  close.type='button';close.id='m-close';close.className='mcbtn m-close';
  close.textContent='×';close.setAttribute('aria-label','とじる');
  close.addEventListener('click',closeModal);
  head.appendChild(close);

  if(c[4]){ /* クラフト不可(入手方法カード) */
    var row0=el('div','m-craftrow',modal);
    var res0=el('div','m-result',row0);
    res0.setAttribute('data-ti',id);res0.setAttribute('data-tk','n');
    res0.appendChild(iconNode(id,48,false));
    el('div','m-how',modal).textContent='入手方法: '+c[4];
  }else{
    var row=el('div','m-craftrow',modal);
    var grid=el('div','m-grid',row);
    for(var k=0;k<9;k++){
      var cid=c[2][k];
      if(!cid){el('div','m-cell empty',grid);continue;}
      var linkable=!!recipeByResult[cid];
      var cell=document.createElement(linkable?'button':'div');
      if(linkable){cell.type='button';linkTo(cell,recipeByResult[cid][0]);}
      cell.className='m-cell'+(linkable?' link':'');
      cell.setAttribute('data-ti',cid);
      cell.setAttribute('data-tk',linkable?'l':'i');
      if(linkable)cell.setAttribute('aria-label',jaOf(cid)+' のレシピを表示');
      cell.appendChild(iconNode(cid,32,!linkable));
      grid.appendChild(cell);
    }
    var ar=el('div','m-arrow',row);
    var aimg=document.createElement('img');
    aimg.src=ARROW_SRC;aimg.alt='→';
    ar.appendChild(aimg);
    var res=el('div','m-result',row);
    res.setAttribute('data-ti',id);res.setAttribute('data-tk','n');
    res.appendChild(iconNode(id,48,false));
    if(c[3]>1)el('span','m-count',res).textContent=c[3];
    el('div','m-out',modal).textContent='できあがり: '+jaOf(id)+(c[3]>1?(' ×'+c[3]):'');
    /* 材料一覧(同じ材料はまとめて数える) */
    var counts={},order=[];
    for(var k2=0;k2<9;k2++){
      var cid2=c[2][k2];
      if(!cid2)continue;
      if(!(cid2 in counts)){counts[cid2]=0;order.push(cid2);}
      counts[cid2]++;
    }
    if(order.length){
      var box=el('div','m-ings',modal);
      el('div','m-ings-h',box).textContent='必要な材料';
      for(var oi=0;oi<order.length;oi++){
        var iid=order[oi];
        var lk=!!recipeByResult[iid];
        var rowb=document.createElement(lk?'button':'div');
        if(lk){rowb.type='button';linkTo(rowb,recipeByResult[iid][0]);}
        rowb.className='m-ing'+(lk?' link':'');
        rowb.setAttribute('data-ti',iid);rowb.setAttribute('data-tk',lk?'l':'i');
        rowb.appendChild(iconNode(iid,24,false));
        el('span','',rowb).textContent=jaOf(iid)+' ×'+counts[iid];
        box.appendChild(rowb);
      }
    }
  }
  /* 同じアイテムを作る別レシピ(現データでは 1 アイテム 1 レシピだが、増えても隠れない) */
  var alts=recipeByResult[id]||[];
  if(alts.length>1){
    var altbox=el('div','m-alts',modal);
    el('span','',altbox).textContent='別レシピ:';
    for(var ai=0;ai<alts.length;ai++){
      if(alts[ai]===i)continue;
      (function(target,no){
        var ab=document.createElement('button');
        ab.type='button';ab.className='mcbtn';ab.textContent='レシピ'+no;
        ab.addEventListener('click',function(){openCard(target,true);});
        altbox.appendChild(ab);
      })(alts[ai],ai+1);
    }
  }
  if(histStack.length){
    var nav=el('div','m-nav',modal);
    var back=document.createElement('button');
    back.type='button';back.className='mcbtn';back.textContent='← 戻る';
    back.addEventListener('click',function(){
      var prev=histStack.pop();
      curCard=prev;
      renderModal(prev);
    });
    nav.appendChild(back);
  }
}
modal.addEventListener('click',function(e){
  var lk=(e.target&&e.target.closest)?e.target.closest('[data-link]'):null;
  if(lk&&modal.contains(lk))openCard(parseInt(lk.getAttribute('data-link'),10),true);
});

/* ---------- ツールチップ ---------- */
var tip=$('tip');
var tipFor=null;
function hintFor(kind){
  if(kind==='r')return['クリックでレシピを表示','#9aa5ff'];
  if(kind==='h')return['クリックで入手方法を表示','#ffc34d'];
  if(kind==='l')return['クリックでこの材料のレシピを表示','#9aa5ff'];
  return null;
}
function showTip(t,x,y){
  var id=t.getAttribute('data-ti');
  var kind=t.getAttribute('data-tk');
  tip.innerHTML='';
  el('div','tip-ja',tip).textContent=jaOf(id);
  var enn=enOf(id);
  if(enn&&enn!==jaOf(id))el('div','tip-en',tip).textContent=enn;
  var h=hintFor(kind);
  if(h){
    var l3=el('div','tip-hint',tip);
    l3.textContent=h[0];l3.style.color=h[1];
  }
  tip.hidden=false;
  moveTipXY(x,y);
}
function moveTipXY(x,y){
  var w=tip.offsetWidth,hh=tip.offsetHeight;
  var vw=window.innerWidth,vh=window.innerHeight;
  var nx=x+14,ny=y-hh-8;
  if(nx+w>vw-4)nx=x-w-14;
  if(nx<4)nx=4;
  if(ny<4)ny=y+18;
  if(ny+hh>vh-4)ny=vh-hh-4;
  tip.style.left=nx+'px';
  tip.style.top=ny+'px';
}
function hideTip(){tip.hidden=true;tipFor=null;}
document.addEventListener('mouseover',function(e){
  var t=(e.target&&e.target.closest)?e.target.closest('[data-ti]'):null;
  if(t!==tipFor){
    tipFor=t;
    if(t)showTip(t,e.clientX,e.clientY);else hideTip();
  }
});
document.addEventListener('mousemove',function(e){
  if(tipFor)moveTipXY(e.clientX,e.clientY);
});
window.addEventListener('blur',hideTip);
document.documentElement.addEventListener('mouseleave',hideTip);

/* ---------- クリック音のオン/オフ(choice は localStorage に保存)---------- */
var muteBtn=$('mute');
function syncMute(){
  /* 状態が読めるトグル: アイコン(🔊/🔇)+日本語の状態ラベル。
     title / aria-label は日本語+英語の併記(スクリーンリーダー・英語話者向け)。 */
  $('mute-ico').textContent=audio.muted?'🔇':'🔊';
  $('mute-label').textContent=audio.muted?'音:オフ':'音:オン';
  muteBtn.setAttribute('aria-pressed',audio.muted?'true':'false');
  var label=audio.muted
    ?'クリック音はオフです。押すとオンになります / Click sound is OFF - press to turn it on'
    :'クリック音はオンです。押すとオフになります / Click sound is ON - press to turn it off';
  muteBtn.title=label;
  muteBtn.setAttribute('aria-label',label);
}
muteBtn.addEventListener('click',function(){
  /* この要素のリスナーは document のリスナーより先に走るので、
     ここで反転しておけば「消した瞬間は静か・点けた瞬間はカチッ」になる。 */
  audio.muted=!audio.muted;
  try{localStorage.setItem('recipeSheetSound',audio.muted?'off':'on');}catch(e){}
  syncMute();
});
syncMute();
if(window.__SHEET__)window.__SHEET__.audio=function(){
  return {state:audio.ctx?audio.ctx.state:null,decoded:!!audio.buf,
          fallback:audio.fallback,plays:audio.plays,muted:audio.muted,isMc:SND_IS_MC};
};

apply();
})();
</script>
</body>
</html>
"""


def main():
    # ⚠ いちばん先に走らせる。ここを通らないと「1 つのモジュールが丸ごと無い」ことに
    #    誰も気づけない —— 出力は正常に見え、終了コードは 0 のままだからである。
    if RETIRED:
        # Alpha's 13 modules are not part of the sheet: nothing to count and nothing to stage.
        MODS.clear()
    else:
        check_mods_roster()
    # 別ブランド(Cherry / OUKA)は配布済み zip から取り出して MODS に足す。
    # MODS を歩くものより先に置く —— 後ろに置くと、テクスチャ解決やレシピの走査が
    # 「まだ MODS に無いもの」を静かに読み飛ばす。
    with tempfile.TemporaryDirectory(prefix="wiki-brands-") as tmp:
        # Alpha も別ブランドも、レシピ・テクスチャ・表示名は**配布物**から読む。
        # Java の実装から読む数値(電力ガイド等)だけは mods-src のソースのまま。
        MODS.extend(stage_published_brands(Path(tmp)))
        if not RETIRED:
            stage_published_pack(Path(tmp))
        return _main_body()


def _main_body():
    zf = vanilla_zip()
    lang_by_modid = {modid: load_lang(mod_dir, modid) for mod_dir, modid, _ in MODS}
    lang_en_by_modid = {modid: load_lang(mod_dir, modid, "en_us") for mod_dir, modid, _ in MODS}
    van_ja = load_vanilla_ja()
    van_en = load_vanilla_en(zf)
    reg = ItemRegistry(van_ja, van_en, lang_by_modid, lang_en_by_modid)

    cards = []       # dict: cat / id / cells(9 個の id or None) / count / how / s
    no_yomi = []     # 読みを組み立てられなかったカード名(黙って捨てずに報告する)
    published = {} if RETIRED else published_recipe_names()
    withheld = []    # 作業木にしか無いレシピ(配られていないので載せない)
    seen_published = set()   # 実際に読んだ配布済みレシピ(取りこぼしを後で数える)
    cards_per_mod = {}       # mod_dir -> このループで作ったカード数(EVERY_RECIPE_SHOWN の照合用)
    halia_counts = (0, 0, 0, 0)  # (json that can never be crafted, cards on top of one per json, recolouring json, set aside 1.4.0)
    for mod_dir, modid, mod_cat in MODS:
        recipe_dir = mod_resources(mod_dir) / "data" / modid / "recipe"
        if mod_dir == "halia":
            made, not_crafts, on_top, recolour = halia_cards(recipe_dir, mod_cat, reg, cards, no_yomi,
                                                             seen_published, published)
            cards_per_mod[mod_dir] = made
            set_aside_n = len(HALIA_SET_ASIDE_NAMES["playwright"]) + len(HALIA_SET_ASIDE_NAMES["brew_potion_contents"])
            halia_counts = (not_crafts, on_top, recolour, set_aside_n)
            print(f"halia: {len(HALIA_SET_ASIDE_NAMES['playwright'])} playwright book-cloning marker(s) set aside "
                  f"(no inputs and no result; not cards): {', '.join(HALIA_SET_ASIDE_NAMES['playwright']) or 'none'}")
            print(f"halia: {len(HALIA_SET_ASIDE_NAMES['brew_potion_contents'])} brewing recipes with potion contents "
                  f"set aside (a known gap on the recipe sheet; not cards): "
                  f"{', '.join(HALIA_SET_ASIDE_NAMES['brew_potion_contents']) or 'none'}")
            print(f"halia: {made} card(s); {not_crafts} recipe json are not crafts (their only ingredient is a tag "
                  f"holding nothing but air); {on_top} card(s) are the anvil half of a material box; "
                  f"{recolour} recolouring recipe(s) of the Aerie are set aside (not cards)")
            continue
        if mod_dir in MOD_RESOURCE_ROOT:
            # 別ブランドは配布済み jar そのものを展開したものなので、ここに在る = 配られている。
            # (jar の sha256 はマニフェストと突き合わせ済み。stage_published_brands を見よ)
            known = {q.name for q in recipe_dir.glob("*.json")}
            published[modid] = known
        else:
            known = published.get(modid)
        if not known:
            raise SystemExit(
                f"ERROR: {modid} is in MODS but no published archive carries a recipe for it. "
                f"Either the module is not shipped, or this check is reading the wrong archive; "
                f"both are worse than the sheet being out of date.")
        for path in sorted(recipe_dir.glob("*.json")):
            if path.name not in known:
                # 作業木のほうが先に進んでいる。配布済みの版では作れないので載せない。
                withheld.append(f"{modid}/{path.name}")
                continue
            seen_published.add(f"{modid}/{path.name}")
            parsed = parse_recipe(path)
            if parsed is None:
                cooked = parse_campfire_recipe(path, reg)
                if cooked is not None:
                    # 焚き火の調理: 作業台の 3x3 ではないので「入手方法」カード(how)で出す。
                    cooked_id, cooked_how, cooked_ids = cooked
                    _ns, cooked_name = cooked_id.split(":", 1)
                    ja, en, _tex = reg.register(cooked_id)
                    cat = category_of(mod_cat, cooked_name)
                    _, unknown = reading_of(ja)
                    if unknown:
                        no_yomi.append((cat, ja, "".join(sorted(set(unknown)))))
                    tokens = cat_tokens(cat) + item_tokens(cooked_id, ja) + [en, cooked_how]
                    for cid in cooked_ids:
                        cja, cen, _ = reg.register(cid)
                        tokens += item_tokens(cid, cja)
                        tokens.append(cen)
                    cards.append({"cat": cat, "id": cooked_id, "cells": None, "count": None,
                                  "how": cooked_how, "s": search_blob(tokens)})
                    cards_per_mod[mod_dir] = cards_per_mod.get(mod_dir, 0) + 1
                elif (cut := parse_stonecutting_recipe(path, reg)) is not None:
                    # 石切台: 3x3 ではないので「入手方法」カード。駅(station)・材料・文(ja, en)は
                    # recipes_how.json に書く(Halia の溶鉱炉と同じ形。ポータルが「石切台で作る」と出す)。
                    cut_id, cut_count, cut_how, cut_how_en, cut_ids = cut
                    ja, en, _tex = reg.register(cut_id)
                    cat = category_of(mod_cat, cut_id.split(":", 1)[1])
                    _, unknown = reading_of(ja)
                    if unknown:
                        no_yomi.append((cat, ja, "".join(sorted(set(unknown)))))
                    tokens = cat_tokens(cat) + item_tokens(cut_id, ja) + [en, cut_how]
                    for cid in cut_ids + ["minecraft:stonecutter"]:
                        cja, cen, _ = reg.register(cid)
                        tokens += item_tokens(cid, cja)
                        tokens.append(cen)
                    cards.append({"cat": cat, "id": cut_id, "cells": None, "count": cut_count,
                                  "how": cut_how, "s": search_blob(tokens)})
                    if cut_id in HALIA_HOW:
                        raise SystemExit(f"ERROR: two how-to cards are keyed {cut_id!r}; one would show the other's text.")
                    HALIA_HOW[cut_id] = {"station": "stonecutter", "inputs": cut_ids, "ja": cut_how, "en": cut_how_en}
                    cards_per_mod[mod_dir] = cards_per_mod.get(mod_dir, 0) + 1
                elif mod_dir in EVERY_RECIPE_SHOWN:
                    raise SystemExit(
                        f"ERROR: {modid}/{path.name} (type {json.loads(path.read_text(encoding='utf-8')).get('type')}) "
                        f"produces no card, but {mod_dir} is in EVERY_RECIPE_SHOWN: its recipes must all appear on "
                        f"the sheet. Teach parse_recipe/parse_campfire_recipe the type instead of skipping it.")
                continue
            cards_per_mod[mod_dir] = cards_per_mod.get(mod_dir, 0) + 1
            result_id = parsed["result_id"]
            _result_ns, result_name = result_id.split(":", 1)
            ja, en, _tex = reg.register(result_id)
            cat = category_of(mod_cat, result_name)
            _, unknown = reading_of(ja)
            if unknown:
                no_yomi.append((cat, ja, "".join(sorted(set(unknown)))))
            tokens = cat_tokens(cat) + item_tokens(result_id, ja)
            for cell_id in parsed["cells"]:
                if not cell_id:
                    continue
                cja, cen, _ = reg.register(cell_id)
                tokens += item_tokens(cell_id, cja)
                tokens.append(cen)
            tokens.append(en)
            cards.append({"cat": cat, "id": result_id, "cells": parsed["cells"],
                          "count": parsed["count"], "how": None,
                          "s": search_blob(tokens)})

    # クラフト不可の特別入手アイテム(強化ビーコン等)+食料品 300 種は「入手方法」カード。
    alpha_specials = [] if RETIRED else SPECIAL_ITEMS + load_food_specials()
    for modid, item_name, how_to_get, cat in (alpha_specials + read_code_only_recipes(reg)):
        item_id = f"{modid}:{item_name}"
        ja, en, _tex = reg.register(item_id)
        _, unknown = reading_of(ja)
        if unknown:
            no_yomi.append((cat, ja, "".join(sorted(set(unknown)))))
        blob = search_blob(cat_tokens(cat) + item_tokens(item_id, ja) + [en, how_to_get])
        cards.append({"cat": cat, "id": item_id, "cells": None, "count": None,
                      "how": how_to_get, "s": blob})

    # V1.4.1: 「天空」を追加。<b>この一覧に無いカテゴリのカードは黙って捨てられる。</b>
    # MODS に足すだけでは早見表に出ない(実際に天空 MOD が丸ごと欠落した)ので、
    # MOD を増やしたら必ずここにも足すこと。
    # ---- 配布物との突き合わせ(両方向)--------------------------------------
    # こちら向き: 配られているのに読めなかったもの。早見表が**少なく**なる側の失敗で、
    # 黙って通ると「そのアイテムは作れない」と書いたことになる。
    expected = {f"{modid}/{name}"
                for _d, modid, _c in MODS
                for name in published.get(modid, ())}
    unread = sorted(expected - seen_published)
    if unread:
        raise SystemExit(
            "ERROR: %d recipe(s) are in the published archives but were not read from the source "
            "tree, so the sheet would say they cannot be crafted: %s"
            % (len(unread), ", ".join(unread[:12]) + (" ..." if len(unread) > 12 else "")))
    if withheld:
        # 2026-09-20 の後半以降、レシピの出典は配布物そのものなので、ここは
        # **本来ぜったいに通らない**。通ったということは、どれかのモジュールが
        # 作業木から読まれている(= 並べ直しが効いていない)ということ。
        raise SystemExit(
            "ERROR: %d recipe(s) were read from a source the published archives do not carry: "
            "%s. Since the pack and the brands are both staged from what players download, "
            "this can only mean a module fell back to the working tree - which is the thing "
            "the staging exists to prevent."
            % (len(withheld), ", ".join(withheld)))
    print("published cross-check: %d recipe(s) read, all of them present in the shipped jars"
          % len(seen_published))
    for mod_dir in sorted(EVERY_RECIPE_SHOWN):
        n_json = sum(1 for _d, modid, _c in MODS if _d == mod_dir
                     for name in published.get(modid, ()))
        n_cards = cards_per_mod.get(mod_dir, 0)
        if mod_dir == "halia":
            n_json = n_json - halia_counts[0] - halia_counts[2] - halia_counts[3] + halia_counts[1]
        if n_json != n_cards or n_json == 0:
            raise SystemExit(f"ERROR: {mod_dir}: {n_json} recipe json in the published jar but {n_cards} card(s) "
                             f"made from them - EVERY_RECIPE_SHOWN says there must be one each (and at least one).")
        if mod_dir == "halia":
            print(f"halia: {n_cards} card(s) for the published jar's craftable recipes, none missing "
                  f"({halia_counts[0]} uncraftable json set aside, {halia_counts[2]} recolouring json set aside, "
                  f"{halia_counts[3]} playwright or potion-input json set aside, "
                  f"{halia_counts[1]} anvil card(s) on top)")
        else:
            print(f"{mod_dir}: all {n_json} recipe json in the published jar became a card")

    cat_order = ["銃", "電車", "建材", "ドア", "乗り物", "ボス", "天空", "サバイバル", "電力",
                 "二相楽園", "灰街圏",
                 # 別ブランドは Alpha のジャンルの後ろに、サイトの並び(OUKA→Cherry)で置く。
                 # Tsubomi(2026-10-05)は ASTRAEA の後ろ(同じ理由: 既存のタブ番号 #0〜#2 を動かさない)。
                 # ASTRAEA(2026-09-30)は Cherry の後ろ: 既存のタブの番号(OUKA 0・Cherry 1)と札の並びを
                 # 一つも動かさない(ポータルのレシピ頁は #0/#1 の深いリンクと t<N> を使う)。
                 *[LIVE_BRAND_CATEGORY[b] for b in ("ouka", "cherry", "astraea", "tsubomi", "halia")
                   if b in LIVE_BRAND_CATEGORY]]
    missing = {c["cat"] for c in cards} - set(cat_order)
    if missing:
        raise SystemExit(
            f"ERROR: these categories would be silently dropped from the sheet: {sorted(missing)}. "
            f"Add them to cat_order.")

    # 並びは **あいうえお順(五十音順)**。ジャンル(カテゴリ)とその順番は cat_order のまま。
    # 生の文字列で sorted() するとコードポイント順(=漢字がでたらめな順)になるので、
    # 必ず gojuon_key() を通すこと。読めなかった文字はかなより後ろに回り、
    # さらに実行時に WARNING で名指しされる(黙って間違った順に混ざることはない)。
    ordered = []
    for cat in cat_order:
        ordered += sorted((c for c in cards if c["cat"] == cat),
                          key=lambda c: gojuon_key(reg.items[c["id"]][0]))

    # ジャンルタブ(アイコンは実在カードから。無ければ WARNING + 先頭カードで代用)。
    ids_by_cat = {}
    for c in ordered:
        ids_by_cat.setdefault(c["cat"], []).append(c["id"])
    cats_meta = []
    for cat in cat_order:
        if cat not in ids_by_cat:
            continue
        icon = CATEGORY_TAB_ICON.get(cat)
        if icon not in ids_by_cat[cat]:
            print(f"WARNING: tab icon {icon!r} is not a card of ジャンル「{cat}」 - "
                  f"falling back to the first card of that ジャンル")
            icon = ids_by_cat[cat][0]
        cats_meta.append([cat, icon, len(ids_by_cat[cat])])
    reg.register(ALL_TAB_ICON)   # 「すべて」タブの作業台アイコン

    # 整合性の自己点検(構築上ここで落ちることは無いはずだが、黙って欠けさせない)。
    for c in ordered:
        assert c["id"] in reg.items, c["id"]
        for cell_id in (c["cells"] or []):
            assert cell_id is None or cell_id in reg.items, cell_id

    # ---- 名前が解決できているか(v1.8.4 で新設)---------------------------
    #
    # lang に鍵が無いと `display_name()` は **生の id をそのまま名前にする**。
    # 読みの検査は ASCII をローマ字として読めてしまうので通り、
    # テクスチャも在るので ①〜④ も通る —— **どこにも引っかからずに
    # `missile_launcher` と書かれたカードが出る**。実際に 17 枚出ていた。
    # 詳しくは KNOWN_UNNAMED の注記を参照。
    unnamed = set()
    for item_id, (ja, en, _tex) in reg.items.items():
        ns, raw = item_id.split(":", 1)
        if ns == "minecraft":
            continue                      # バニラは公式 lang から引くので対象外
        if ja == raw or en == raw:        # display_name() の素通し = 名前が無い
            unnamed.add(item_id)
    regressions = sorted(unnamed - KNOWN_UNNAMED)
    if regressions:
        raise SystemExit(
            "ERROR: %d item(s) have no display name in ja_jp.json / en_us.json, so the sheet "
            "would show a raw id where a name belongs (and the game shows the raw translation "
            "key in hand): %s\n"
            "       Add the lang entries and rebuild that module, or - only if this is "
            "deliberate - add the id to KNOWN_UNNAMED with a note saying why."
            % (len(regressions), ", ".join(regressions)))
    fixed = [] if RETIRED else sorted(KNOWN_UNNAMED - unnamed)   # the list is Alpha's; nothing of it is read now
    if fixed:
        raise SystemExit(
            "ERROR: %d id(s) in KNOWN_UNNAMED now have a proper name - remove them from that "
            "list so it keeps telling the truth about what is still broken: %s"
            % (len(fixed), ", ".join(fixed)))
    if unnamed:
        print(f"unnamed items: {len(unnamed)} still show a raw id "
              f"(known gap, listed in KNOWN_UNNAMED - fix lang + rebuild to clear)")

    # ---- 「使い方」タブ(v1.8.1)------------------------------------------
    #
    # ⚠ ここの 3 つの検査は「黙って劣化しない」ためにある。
    # 手引きが参照する id が 1 つでも解決できないと、ページ上は「?」の四角が
    # 出るだけで生成は成功してしまう(§31.4 で 309 個のアイテムが黙って表から
    # 落ちていたのと、§37 で「?」カード 1 枚として現れたのと同じ形)。
    # 2026-09-28: Alpha is retired (data/retirement.json) and the sheet is Cherry + OUKA only. The 使い方 tab
    # is Alpha's wiring / power / sorting guide, and every check below asserts something about Alpha's
    # cards, so none of it can hold; the tab is empty rather than half-checked.
    if RETIRED:
        guides_filled, guide_ids, guides_json, n_examples = [], [], [], 0
    else:
        # ⓪ 先に `{fact}` を実装から読んだ値へ置きかえる。**以降はこの GUIDES_FILLED を使う。**
        #    未知の名前があればここで生成が止まる(fill_facts)。
        guides_filled = fill_facts(GUIDES)
        unused = sorted(set(POWER_FACTS) - USED_FACTS)
        if unused:
            raise SystemExit(
                "ERROR: %d value(s) are read out of the implementation for the 使い方 tab but are "
                "used by no guide - a dead reading looks maintained while it is not. Either use "
                "them or stop reading them: %s" % (len(unused), ", ".join(unused)))

        guide_ids = []
        for g in guides_filled:
            guide_ids.append(g["icon"])
            for sec in g["sections"]:
                for row in (sec.get("diagram") or {}).get("rows", []):
                    for cell in row:
                        if cell and cell[0] == "i":
                            guide_ids.append(cell[1])
                for side in ("in", "out"):
                    for pair in (sec.get("io") or {}).get(side, []):
                        guide_ids.append(pair[0])

        # ① 手引きが触れる id は、全部テクスチャつきで解決できること。
        broken = []
        for iid in dict.fromkeys(guide_ids):
            ja, en, tex = reg.register(iid)
            if not tex:
                broken.append(iid)
        if broken:
            raise SystemExit(
                "ERROR: the 使い方 tab references %d item(s) with no texture - they would render "
                "as a '?' box while the build still 'succeeded': %s" % (len(broken), ", ".join(broken)))

        # ② 自動仕分け一式が、早見表のカードとして実在すること(改名・綴り違いの検出)。
        card_ids = {c["id"] for c in ordered}
        missing_cards = [i for i in SORTING_KIT if i not in card_ids]
        if missing_cards:
            raise SystemExit(
                "ERROR: SORTING_KIT lists %d id(s) that are not cards in this sheet (renamed or "
                "misspelled?): %s" % (len(missing_cards), ", ".join(missing_cards)))

        # ③ 一式の全部が、どれかの図に出ていること(= 説明されていない部品が無い)。
        #    部品を増やして手引きに足し忘れたら、ここで生成が止まる。
        shown = set(guide_ids)
        undocumented = [i for i in SORTING_KIT if i not in shown]
        if undocumented:
            raise SystemExit(
                "ERROR: %d sorting part(s) never appear in any 使い方 diagram - the owner would have "
                "no way to learn what they do: %s" % (len(undocumented), ", ".join(undocumented)))

        # ④ 一式の 10 枚が、**互いに違う絵**で出ていること。
        #
        # これは v1.8.0 で実際に起きた失敗そのものを二度と通さないための検査である。
        # あのとき 9 枚のカードは同じ texture key(t140 = 共有の天面)を指していて、
        # 早見表の上では見分けが付かなかった。カードは 9 枚あるので枚数の検査は通り、
        # WARNING も出ず、**誰も気付けなかった**。
        kit_tex = {}
        for iid in SORTING_KIT:
            tex = reg.items[iid][2]
            kit_tex.setdefault(tex, []).append(iid)
        dupes = {t: ids for t, ids in kit_tex.items() if len(ids) > 1}
        if dupes:
            raise SystemExit(
                "ERROR: sorting parts share a picture in this sheet - the owner could not tell them "
                "apart on the page (this is the v1.8.0 defect): "
                + "; ".join("%s <- %s" % (t, ", ".join(ids)) for t, ids in dupes.items()))

        # ④.5 **HTML が素通しできない場所にタグを書いていないこと。**
        #
        # 描画側は場所によって innerHTML と textContent を使い分けている:
        #   innerHTML  … lede / goal / steps / notes(強調を効かせたい文章)
        #   textContent … 図の caption / セルの下の説明 / 文字だけのセル
        # 後者に <b> を書くと、**画面に「<b>」という 3 文字がそのまま出る**。
        # 生成は成功し、警告も出ず、ブラウザで見るまで分からない —— 実際に一度そうなった。
        text_only = []
        for g in guides_filled:
            for sec in g["sections"]:
                dia = sec.get("diagram") or {}
                if dia.get("caption"):
                    text_only.append(("diagram caption", dia["caption"]))
                for row in dia.get("rows", []):
                    for cell in row:
                        if cell and cell[0] == "n":
                            text_only.append(("text cell", cell[1]))
                        elif cell and cell[0] == "i" and len(cell) > 2 and cell[2]:
                            text_only.append(("icon caption", cell[2]))
                for side in ("in", "out"):
                    for pair in (sec.get("io") or {}).get(side, []):
                        text_only.append(("io chip", pair[1]))
        tagged = [(where, s) for where, s in text_only if re.search(r"<[a-zA-Z/]", s)]
        if tagged:
            raise SystemExit(
                "ERROR: %d 使い方 string(s) contain HTML in a place the page renders as plain text - "
                "the markup would be shown to the owner as literal characters: %s"
                % (len(tagged), "; ".join("%s %r" % (w, s[:60]) for w, s in tagged)))

        # ⑤ 電力 MOD のカードが全部どれかの図に出ていること。
        #    **ブロックを増やして手引きに足し忘れたら、ここで生成が止まる。**
        #    (§39 で「MODS に足し忘れて 10 レシピが丸ごと落ちた」のと同じ穴を、手引き側で塞ぐ。)
        power_cards = sorted(i for i in card_ids if i.startswith("sorakaze_power:"))
        if not power_cards:
            raise SystemExit(
                "ERROR: this sheet has no sorakaze_power cards at all - the 電力 guide would be "
                "describing blocks that do not exist (an empty set makes every check below "
                "vacuously true, which is exactly the CLAUDE.md section 30.4 failure)")
        undoc_power = [i for i in power_cards if i not in shown]
        if undoc_power:
            raise SystemExit(
                "ERROR: %d 電力 block(s) never appear in any 使い方 diagram - the owner would have "
                "no way to learn what they do: %s" % (len(undoc_power), ", ".join(undoc_power)))

        # ⑥ 「電気が要る機器」の一覧が、タグと 1 個ずれても止まること。
        #    出典は data の block タグなので、相手の MOD に機器が増えれば自動で効く。
        if not POWERED_DEVICE_IDS:
            raise SystemExit("ERROR: the power_devices block tag resolved to nothing - the "
                             "「電気が要る機器」 list would be vacuously complete")
        undoc_dev = [i for i in (POWERED_DEVICE_IDS + POWERED_EXTRA_IDS)
                     if i not in shown and not i.endswith("_part")]
        if undoc_dev:
            raise SystemExit(
                "ERROR: %d device(s) now need electricity but are not shown in the 使い方 tab - "
                "the owner would find them dead with no explanation: %s"
                % (len(undoc_dev), ", ".join(undoc_dev)))

        guides_json = guides_filled
        n_examples = sum(len(g["sections"]) for g in guides_filled)
        print(f"sorting kit: {len(SORTING_KIT)} parts -> {len(kit_tex)} distinct pictures")
        print(f"使い方 tab: {len(guides_filled)} topic(s), {n_examples} worked example(s), "
              f"{len(set(guide_ids))} distinct icons - all resolved")
        print(f"電力 guide: {len(POWER_FACTS)} value(s) read live out of the implementation "
              f"(none hand-typed); {len(power_cards)} 電力 block(s) and "
              f"{len(POWERED_DEVICE_IDS) + len(POWERED_EXTRA_IDS)} powered device(s) all documented")

    cat_index = {cat: i for i, (cat, _icon, _n) in enumerate(cats_meta)}
    cards_json = []
    for c in ordered:
        grid = None
        if c["cells"] is not None:
            grid = [(cid if cid else 0) for cid in c["cells"]]
        cards_json.append([cat_index[c["cat"]], c["id"], grid,
                           c["count"] if c["count"] else 0,
                           c["how"] if c["how"] else 0,
                           c["s"]])
    items_map = {iid: [ja, en, tex] for iid, (ja, en, tex) in reg.items.items()}
    total = len(ordered)

    # ---- Corvus adaptation ------------------------------------------
    # Everything above this point (data assembly, every validation check) is
    # byte-identical to the original generator's main(). From here down,
    # instead of splicing everything into one self-contained HTML page
    # (TEMPLATE, unused in this copy), we write the same data as JSON +
    # individual PNGs for this wiki's own multi-page, natively-styled
    # recipes/ section to fetch and render.
    if HALIA_MISSING_ICONS:
        # Nothing is written past this point: the sheet would carry placeholder pictures.
        print(f"MISSING HALIA ICONS: {len(HALIA_MISSING_ICONS)} item/block picture(s) with no entry in "
              f"data/halia_icons/index.json (the run stopped before writing anything):")
        for section, key in sorted(set(HALIA_MISSING_ICONS)):
            print(f"  {section}  {key}")
        raise SystemExit(1)
    OUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    recipes_data = {
        "total": total,
        # この早見表がどの配布物から作られたか。サイトが新しい版を配り始めたのに
        # 作り直していなければ、check_recipe_sources.py がここを見て赤くする。
        "sources": recipe_sources(),
        "cats": cats_meta,       # [[name, icon_item_id, count], ...]
        "all_tab_icon": ALL_TAB_ICON,
        "items": items_map,      # id -> [ja, en, tex_key_or_null]
        "cards": cards_json,     # [cat_index, id, grid_or_null, count, how_or_0, search_blob]
        "guides": guides_json,
    }
    OUT_IMG_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_IMG_DIR.glob("t*.png"):
        old.unlink()
    # Only the pictures the new sheet names are written. A picture only a retired product used (ASTRAEA, 2026-10-17)
    # is not written, so it is not in the folder any more; every other picture keeps its number and its bytes.
    referenced = set(re.findall(r'"(t\d+)"', json.dumps(recipes_data, ensure_ascii=False) + json.dumps(HALIA_HOW, ensure_ascii=False)))
    published_old = json.loads(_git_bytes("show", f"{PUBLISHED_REF}:data/recipes.json"))
    drop = retired_only_textures(published_old)[0] - referenced
    for payload in reg.tex_order:
        key = reg.tex_payloads[payload]
        if key not in drop:
            (OUT_IMG_DIR / f"{key}.png").write_bytes(base64.b64decode(payload))

    # The portal's half of the how-to cards that are not grids (Halia): written only when there is one, sorted.
    (OUT_DATA_DIR / "recipes_how.json").write_text(
        json.dumps({"_comment": "station, inputs and the sentence (ja, en) of how-to cards; written by "
                                "scripts/extract_recipes.py, read by web/scripts/extract_wiki.py",
                    "cards": dict(sorted(HALIA_HOW.items()))}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    out_json = OUT_DATA_DIR / "recipes.json"
    out_json.write_text(
        json.dumps(recipes_data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    if no_yomi:
        print(f"WARNING: {len(no_yomi)} item name(s) have no reading in YOMI - "
              f"they will NOT be in correct あいうえお order:")
        for cat, name, chars in no_yomi:
            print(f"  WARNING: [{cat}] {name}  (未登録の文字: {chars})")
    print(f"reading coverage: {total - len(no_yomi)}/{total} card titles have a full yomi")
    packed_bytes = sum(len(base64.b64decode(p)) for p in reg.tex_order if reg.tex_payloads[p] not in drop)
    print(f"textures: {len(reg.tex_order)} unique payloads "
          f"({reg.raw_bytes / 1048576:.2f} MiB source -> {packed_bytes / 1048576:.2f} MiB "
          f"written as individual PNGs, verified-lossless)")
    print(f"wrote {out_json} ({total} recipes, {out_json.stat().st_size / 1048576:.2f} MiB) "
          f"+ {len(reg.tex_order)} PNGs in {OUT_IMG_DIR}")
    guard = guard_published_textures()
    if guard:
        for problem in guard[:20]:
            print("  GUARD: " + problem)
        raise SystemExit(f"ERROR: {len(guard)} published texture(s) moved or changed - the portal's t<N> links would point "
                         f"at other pictures. Nothing published may be renumbered.")
    print(f"published textures guard: every item of the published sheet keeps its texture and its bytes: GREEN")


if __name__ == "__main__":
    import sys as _sys
    if "--guard-self-test" in _sys.argv[1:]:
        _bad = icon_guard_self_test()
        for _b in _bad:
            print("  SELF-TEST RED: " + _b)
        print("icon guard self-test:", "GREEN" if not _bad else f"RED ({len(_bad)})")
        _sys.exit(1 if _bad else 0)
    if "--guard-only" in _sys.argv[1:]:
        _problems = guard_published_textures()
        for _p in _problems[:20]:
            print("  GUARD: " + _p)
        print("published textures guard:", "GREEN" if not _problems else f"RED ({len(_problems)} problem(s))")
        _sys.exit(1 if _problems else 0)
    main()
