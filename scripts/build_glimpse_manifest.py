#!/usr/bin/env python3
"""Builds glimpse_manifest.json at the repo root — the contract the Glimpse
Launcher desktop app (a separate project, built independently) polls to
check for pack/launcher updates.

This is a DIFFERENT file from releases.json (see build_releases_feed.py):
releases.json already has a tested consumer (the Discord release bot) with
a fixed schema, and must not be repurposed. glimpse_manifest.json is a new,
separate contract for the launcher.

Design note: same discipline as build_releases_feed.py / build_download.py —
every fact here is computed from the real shipped ZIP and data/*.json at
build time, never typed as a literal. If a fact is missing (no matching
changelog entry, no ZIP on disk), the build stops loudly rather than
inventing one.

The "launcher" block is OMITTED only when downloads/ has never held a
launcher jar at all. We do not invent placeholder launcher facts just to
keep the schema "complete" — an absent key is honest; a fabricated sha256 is
not. But an absent key is only honest when the launcher really has not
shipped: once data/launcher_notes.json lists released versions, a downloads/
folder with no jar in it means the *lookup* broke, not that the product
vanished, and build() now stops loudly instead of publishing a manifest that
would switch off self-update for every installed launcher.

Jar discovery and version ordering live in site_common (find_launcher_jars /
newest_launcher_jar) so this script and build_download.py cannot drift apart
about which file is "current" — see the comment there for the two bugs the
old private copies shared.

The "aureum" block (2026-08-31) follows the same rule for the same reason.
Aureum is a SEPARATE mod with its own repo and its own version line, and until
now it had no path through Corvus at all — it was a website download only. The
owner asked for three things: that it be installable FROM Corvus without
visiting the site, that people who already have it get new versions
automatically, and — the constraint that shapes everything — that it is NEVER
introduced automatically unless they put the jar in their mods folder
themselves or pressed Install in Corvus. This block is what makes the first two
possible; the third is enforced on the launcher side (see AureumConsent there).

Two things about this block are deliberate:

  * jar discovery reuses build_download.py's _aureum_facts(), so the Download
    page, the /aureum/ landing page and this manifest can never disagree about
    which build is current. build_aureum.py already imports it for exactly this
    reason.

  * "mod_id" is read out of the jar's own fabric.mod.json rather than typed.
    Corvus identifies an installed Aureum by mod id, never by file name --
    because the file name is the thing that has already broken a cross-repo
    contract in this project once (the launcher jar glob). Typing "aureum" here
    would reintroduce exactly that class of drift, one layer down.

The "cherry" block (2026-09-13, Corvus 2.1.0) is the same idea for a PACKAGE.
The owner asked: 「Corvus からのダウンロードと自動アップデートに対応してください。」
Cherry ships as a ZIP — its jar, the GeckoLib jar it needs, licence texts — so
the block describes the ZIP and, in "jars", every jar Corvus is to install from
it, keyed by the Fabric mod id each jar declares. Everything is read from the
ZIP: the jars' ids, versions, sizes and hashes from the jars themselves; which
jar is Cherry itself from the dependency graph (the one jar no other jar in the
ZIP depends on), never from a typed name; and that jar's version must be the one
in the ZIP's file name. Corvus 2.1.0 refuses a package whose mods/ holds a jar
the block does not list, so "jars" lists every one. Installed 2.0.0 launchers
ignore the block (their parser ignores unknown top-level keys on purpose).

The "ouka" block (OUKA V1.0.0, staged 2026-09-15) is the same package block for
the second brand that ships as a ZIP -- its own jar and the GeckoLib jar it
needs -- read from the ZIP by the same rules: "jars" keyed by the Fabric mod id
each jar declares, OUKA's own jar found from the dependency graph, and that
jar's version equal to the one in the ZIP's file name. _ouka_block() is a
separate copy of _cherry_block() on purpose, so adding OUKA cannot change a byte
of the published cherry block. Corvus 2.1.0 and 2.2.0 have no field for it and
ignore it, as 2.0.0 ignored "cherry" -- which has to be shown with both shipped
jars (ManifestCompat) before the block is published. From the first build that
writes it, the never-drop rule applies to it as well.

The "astraea" block (ASTRAEA V1.0.0, 2026-09-30) is the same package block for
the third brand that ships as a ZIP. ASTRAEA bundles no other mod, so its ZIP
holds one jar; the rules are OUKA's all the same (jars keyed by the mod id each
jar declares, the brand's own jar found from the dependency graph, its version
equal to the ZIP's). _astraea_block() is a separate copy of _ouka_block() on
purpose, so adding ASTRAEA cannot change a byte of the published cherry or ouka
blocks. ASTRAEA has no compatibility with Alpha (the owner's decision D-1). From
the first build that writes it, the never-drop rule applies to it as well.

The "tsubomi" block (Tsubomi V1.0.0, 2026-09-30) is Aureum's shape, not a package's:
Tsubomi ships as a bare jar, so there is no "jars" and no notes. _tsubomi_block() reads
everything from the jar -- the mod id from its fabric.mod.json (it must be "tsubomi", the
name the Store and the Discord bot key the brand by) and its version, which must equal the
one in the file name. Exactly one Tsubomi jar is published at a time, as for ASTRAEA's ZIP
(check_tsubomi_release.py holds the same rule). It is a separate function, so adding Tsubomi cannot change a
byte of any other block. Tsubomi is not compatible with Alpha (the owner, 2026-09-30; the jar
declares it). From the first build that writes it, the never-drop rule applies to it as well.
"""
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import (  # noqa: E402
    ROOT, LAUNCHER_APP_NAME, newest_launcher_jar, launcher_native_files,
    PACK_NAME, pack_zip_path, retirement,
)
from build_download import _aureum_facts  # noqa: E402  (single source of truth
# for which Aureum jar is current -- same import build_aureum.py already makes)

MC_VERSION = "26.3"
DOWNLOAD_DIR = ROOT / "downloads"
SITE_BASE_URL = "https://iroponcopin.github.io/aurora-corvus"
CHERRY_ZIP_PREFIX = "Cherry_MODs_v"
CHERRY_ZIP_SUFFIX = f"+mc{MC_VERSION}.zip"
OUKA_ZIP_PREFIX = "OUKA_MODs_v"
OUKA_ZIP_SUFFIX = f"+mc{MC_VERSION}.zip"
ASTRAEA_ZIP_PREFIX = "ASTRAEA_MODs_v"
ASTRAEA_ZIP_SUFFIX = f"+mc{MC_VERSION}.zip"
TSUBOMI_JAR_PREFIX = "tsubomi-"
TSUBOMI_JAR_SUFFIX = ".jar"
TSUBOMI_MOD_ID = "tsubomi"
HALIA_JAR_PREFIX = "halia-"
HALIA_JAR_SUFFIX = ".jar"
HALIA_MOD_ID = "halia"
NOCTUA_ZIP_PREFIX = "Noctua_v"
NOCTUA_ZIP_SUFFIX = ".zip"


def _mod_version():
    mods = json.loads((ROOT / "data" / "versions.json").read_text(encoding="utf-8"))["mods"]
    versions = set(mods.values())
    if len(versions) != 1:
        raise SystemExit(
            f"ERROR: data/versions.json lists more than one distinct version {sorted(versions)} "
            f"- glimpse_manifest.json cannot describe a single pack release when the table "
            f"itself disagrees."
        )
    return versions.pop()


def _zip_path(version):
    # Filename from site_common.pack_zip_name() — see the note there about the
    # V2.5.0 Glimpse_Alpha_MODs_* -> Alpha_MODs_* rename. This one matters
    # most of the three: Corvus downloads exactly the `file_name` this block
    # publishes, so a name invented here is a 404 for every installed app.
    return pack_zip_path(version, MC_VERSION, why="glimpse_manifest.json")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _changelog_entry(version):
    entries = json.loads((ROOT / "data" / "changelog.json").read_text(encoding="utf-8"))
    for e in entries:
        rel = str(e.get("release", "")).lstrip("vV")
        if rel == version:
            return e
    raise SystemExit(
        f"ERROR: data/changelog.json has no entry with release == V{version}. "
        f"glimpse_manifest.json needs a real title/summary/date, not an invented one."
    )


def _english_summary(entry):
    """Same derivation as build_releases_feed.py's _english_summary: a
    plain, honest English restatement of release type + highlight count,
    not a translation of the Japanese summary field."""
    # 2026-09-28: an entry may carry its own honest English text (`english_summary`). The
    # retirement release needs it: "Release v4.4.0.2. 3 change(s)" would announce, to every Discord
    # server and in the manifest, an update that switches Alpha off as if it were a new feature drop.
    own = str(entry.get("english_summary", "")).strip()
    if own:
        return own
    kind = "Hotfix" if entry.get("type") == "hotfix" else "Release"
    highlight_count = len(entry.get("highlights", []))
    if highlight_count:
        return (f"{kind} {entry['release']}. {highlight_count} change(s) in this update - "
                f"see the full changelog on the Wiki for details.")
    return f"{kind} {entry['release']}. See the full changelog on the Wiki for details."


def _launcher_notes_table():
    notes_path = ROOT / "data" / "launcher_notes.json"
    if not notes_path.exists():
        return notes_path, {}
    return notes_path, json.loads(notes_path.read_text(encoding="utf-8"))


def _launcher_block(release):
    """release is a dict from site_common.newest_launcher_jar()."""
    jar_path = release["path"]
    version = release["version"]
    size_bytes = jar_path.stat().st_size
    sha256_hex = _sha256(jar_path)

    notes_path, notes_table = _launcher_notes_table()
    if version not in notes_table:
        raise SystemExit(
            f"ERROR: {notes_path} has no entry for launcher version {version!r} - add real release "
            f"notes there before publishing this build (see the existing entries for the style: "
            f"plain, honest, no invented features)."
        )

    block = {
        "latest": version,
        "download_url": f"{SITE_BASE_URL}/downloads/{jar_path.name}",
        "file_name": jar_path.name,
        "file_size": size_bytes,
        "sha256": sha256_hex,
        "notes": notes_table[version],
    }

    # Native builds: produced by the launcher project's own GitHub Actions CI
    # (real macOS/Windows/Linux runners), copied here by hand from the CI
    # run's artifacts. Included only for platforms that actually have a
    # published file -- read straight from disk, never assumed.
    native = {}
    for n in launcher_native_files(version, DOWNLOAD_DIR):
        native[n["platform_id"]] = {
            "download_url": f"{SITE_BASE_URL}/downloads/{n['file_name']}",
            "file_name": n["file_name"],
            "file_size": n["size_bytes"],
            "sha256": _sha256(n["path"]),
        }
    if native:
        block["native"] = native
    return block


def _aureum_mod_id(jar_path):
    """The Fabric mod id the published jar actually declares.

    Read from the artefact, never typed. Corvus matches an installed Aureum by
    mod id (see AureumJar over there), so this value is what lets a future
    rename reach copies that are already installed. A literal here would be a
    second place for the truth to live, and the wrong one would silently switch
    install detection off for everybody -- the launcher would then report
    "not installed" for a folder that has it, and offer to install a second
    copy, which Fabric refuses to load.
    """
    try:
        with zipfile.ZipFile(jar_path) as zf:
            meta = json.loads(zf.read("fabric.mod.json").decode("utf-8"))
    except (OSError, KeyError, ValueError) as exc:
        raise SystemExit(
            f"ERROR: could not read fabric.mod.json out of {jar_path} ({exc}). The manifest's "
            f"aureum.mod_id must come from the jar itself -- do not type it."
        )
    mod_id = meta.get("id")
    if not isinstance(mod_id, str) or not mod_id.strip():
        raise SystemExit(
            f"ERROR: {jar_path} declares no usable \"id\" in its fabric.mod.json, so Corvus would "
            f"have nothing to match an installed copy against."
        )
    return mod_id.strip()


def _aureum_block():
    """The `aureum` block, or None when no Aureum build has been published.

    None is honest before the first Aureum release, exactly as an absent
    `launcher` block was before the first launcher shipped. It is NOT honest
    once one has shipped: a manifest that silently drops the block would tell
    every installed Corvus that Aureum no longer exists, which switches its
    auto-update off. build() checks the already-published manifest for that
    case and stops loudly.
    """
    facts = _aureum_facts()
    if facts is None:
        return None
    jar_path = DOWNLOAD_DIR / facts["file_name"]
    return {
        "mod_id": _aureum_mod_id(jar_path),
        "latest": facts["version"],
        "download_url": f"{SITE_BASE_URL}/downloads/{facts['file_name']}",
        "file_name": facts["file_name"],
        "file_size": facts["size_bytes"],
        "sha256": facts["sha256"],
    }


def _release_version_key(name, prefix, suffix):
    """The numeric version in ``<prefix><version><suffix>``, for ordering releases.

    Numeric, never lexicographic: as strings "1.10.0" sorts before "1.9.0".
    Trailing zeros are dropped so that "1.0.1" and "1.0.1.0" compare equal, which is
    how Corvus's VersionComparator treats them (missing parts count as 0) — two such
    files would be the same release to every installed launcher.
    """
    middle = name[len(prefix):-len(suffix)]
    parts = middle.split(".")
    if not middle or not all(part.isdigit() for part in parts):
        raise SystemExit(
            f"ERROR: {name} does not parse as {prefix}<version>{suffix}. "
            f"Rename or remove it - an unparseable name cannot be ordered against the others.")
    key = [int(part) for part in parts]
    while len(key) > 1 and key[-1] == 0:
        key.pop()
    return tuple(key)


def _newest_release_zip(zips, prefix, suffix):
    """The newest release among ``zips`` by numeric version.

    **Older releases stay in downloads/ and stay downloadable.** The manifest names
    only the current build, but a published file is never deleted to make room for the
    next one: Discord links and bookmarks keep working, and the history stays
    reproducible. Alpha's pack has always worked this way (48 releases side by side);
    this is the same rule for a brand whose builder used to refuse a second file, which
    forced every release to delete the previous one (2026-09-21, Cherry 1.1.0 was about
    to delete 1.0.1 for that reason alone). build_cherry.py and check_cherry_release.py
    already choose the newest by numeric version, so the manifest and the page now agree
    by construction.

    Two files that are the same version to the launcher are refused rather than guessed.
    """
    ranked = sorted(zips, key=lambda p: _release_version_key(p.name, prefix, suffix))
    if len(ranked) > 1:
        top = _release_version_key(ranked[-1].name, prefix, suffix)
        runner_up = _release_version_key(ranked[-2].name, prefix, suffix)
        if top == runner_up:
            raise SystemExit(
                f"ERROR: {ranked[-2].name} and {ranked[-1].name} are the same version to Corvus "
                f"(missing parts count as 0), so neither can be called the current build. Remove one.")
    return ranked[-1]


def _cherry_block():
    """The `cherry` block, or None when no Cherry ZIP has been published.

    Every value is read from the ZIP in downloads/ (see the module docstring). The
    same never-drop rule as the other optional blocks applies in build().

    When several Cherry ZIPs for this Minecraft version are present, the block
    describes the newest; the older ones remain published (see _newest_release_zip).
    """
    zips = sorted(p for p in DOWNLOAD_DIR.glob(f"{CHERRY_ZIP_PREFIX}*{CHERRY_ZIP_SUFFIX}") if p.is_file())
    if not zips:
        return None
    zpath = _newest_release_zip(zips, CHERRY_ZIP_PREFIX, CHERRY_ZIP_SUFFIX)
    zip_version = zpath.name[len(CHERRY_ZIP_PREFIX):-len(CHERRY_ZIP_SUFFIX)]
    jars = {}
    depends = {}
    try:
        with zipfile.ZipFile(zpath) as zf:
            for info in zf.infolist():
                name = info.filename
                if not name.lower().endswith(".jar"):
                    continue
                if not name.startswith("mods/") or name.count("/") != 1:
                    raise SystemExit(
                        f"ERROR: {zpath.name} carries a jar outside mods/ ({name}). Corvus installs only "
                        f"mods/<name>.jar, so a jar anywhere else would never be installed.")
                data = zf.read(info)
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as jar:
                        meta = json.loads(jar.read("fabric.mod.json").decode("utf-8"))
                except (KeyError, ValueError, zipfile.BadZipFile) as exc:
                    raise SystemExit(
                        f"ERROR: could not read fabric.mod.json out of {name} in {zpath.name} ({exc}). "
                        f"cherry.jars must come from the jars themselves - do not type it.")
                mod_id, version = meta.get("id"), meta.get("version")
                if not isinstance(mod_id, str) or not mod_id.strip() or not isinstance(version, str) or not version.strip():
                    raise SystemExit(
                        f"ERROR: {name} in {zpath.name} declares no usable id and version in its fabric.mod.json, "
                        f"so Corvus would have nothing to match an installed copy against.")
                mod_id = mod_id.strip()
                if mod_id in jars:
                    raise SystemExit(f"ERROR: {zpath.name} carries two jars declaring the mod id {mod_id!r}.")
                jars[mod_id] = {
                    "path": name,
                    "version": version.strip(),
                    "file_size": info.file_size,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                depends[mod_id] = set((meta.get("depends") or {}).keys())
    except (OSError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"ERROR: could not read {zpath} ({exc}).")
    if not jars:
        raise SystemExit(f"ERROR: {zpath.name} carries no jar in mods/, so there is nothing for Corvus to install.")
    roots = [m for m in jars if not any(m in needs for other, needs in depends.items() if other != m)]
    if len(roots) != 1:
        raise SystemExit(
            f"ERROR: cannot tell which jar in {zpath.name} is Cherry itself: the jars no other jar depends on are "
            f"{roots or 'none'}. The package's own mod must be the one jar nothing else in the ZIP depends on.")
    own = roots[0]
    if jars[own]["version"] != zip_version:
        raise SystemExit(
            f"ERROR: {zpath.name} is named for version {zip_version}, but its own jar {jars[own]['path']} declares "
            f"{jars[own]['version']}. An installed Cherry would compare itself against the wrong number.")
    return {
        "mod_id": own,
        "latest": jars[own]["version"],
        "download_url": f"{SITE_BASE_URL}/downloads/{zpath.name}",
        "file_name": zpath.name,
        "file_size": zpath.stat().st_size,
        "sha256": _sha256(zpath),
        "jars": jars,
    }


def _ouka_block():
    """The `ouka` block, or None when no OUKA ZIP has been published.

    The same rules as _cherry_block(), in a separate copy so that adding OUKA can
    never change a byte of the published cherry block (see the module docstring).
    The same never-drop rule applies in build().
    """
    zips = sorted(p for p in DOWNLOAD_DIR.glob(f"{OUKA_ZIP_PREFIX}*{OUKA_ZIP_SUFFIX}") if p.is_file())
    if not zips:
        return None
    if len(zips) > 1:
        raise SystemExit(
            f"ERROR: more than one OUKA ZIP in {DOWNLOAD_DIR} ({', '.join(z.name for z in zips)}). "
            f"The manifest describes the current build only - publish exactly one."
        )
    zpath = zips[0]
    zip_version = zpath.name[len(OUKA_ZIP_PREFIX):-len(OUKA_ZIP_SUFFIX)]
    jars = {}
    depends = {}
    try:
        with zipfile.ZipFile(zpath) as zf:
            for info in zf.infolist():
                name = info.filename
                if not name.lower().endswith(".jar"):
                    continue
                if not name.startswith("mods/") or name.count("/") != 1:
                    raise SystemExit(
                        f"ERROR: {zpath.name} carries a jar outside mods/ ({name}). A package is installed from "
                        f"mods/<name>.jar only, so a jar anywhere else would never be installed.")
                data = zf.read(info)
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as jar:
                        meta = json.loads(jar.read("fabric.mod.json").decode("utf-8"))
                except (KeyError, ValueError, zipfile.BadZipFile) as exc:
                    raise SystemExit(
                        f"ERROR: could not read fabric.mod.json out of {name} in {zpath.name} ({exc}). "
                        f"ouka.jars must come from the jars themselves - do not type it.")
                mod_id, version = meta.get("id"), meta.get("version")
                if not isinstance(mod_id, str) or not mod_id.strip() or not isinstance(version, str) or not version.strip():
                    raise SystemExit(
                        f"ERROR: {name} in {zpath.name} declares no usable id and version in its fabric.mod.json, "
                        f"so nothing could match an installed copy against it.")
                mod_id = mod_id.strip()
                if mod_id in jars:
                    raise SystemExit(f"ERROR: {zpath.name} carries two jars declaring the mod id {mod_id!r}.")
                jars[mod_id] = {
                    "path": name,
                    "version": version.strip(),
                    "file_size": info.file_size,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                depends[mod_id] = set((meta.get("depends") or {}).keys())
    except (OSError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"ERROR: could not read {zpath} ({exc}).")
    if not jars:
        raise SystemExit(f"ERROR: {zpath.name} carries no jar in mods/, so there is nothing to install.")
    roots = [m for m in jars if not any(m in needs for other, needs in depends.items() if other != m)]
    if len(roots) != 1:
        raise SystemExit(
            f"ERROR: cannot tell which jar in {zpath.name} is OUKA itself: the jars no other jar depends on are "
            f"{roots or 'none'}. The package's own mod must be the one jar nothing else in the ZIP depends on.")
    own = roots[0]
    if jars[own]["version"] != zip_version:
        raise SystemExit(
            f"ERROR: {zpath.name} is named for version {zip_version}, but its own jar {jars[own]['path']} declares "
            f"{jars[own]['version']}. An installed OUKA would compare itself against the wrong number.")
    return {
        "mod_id": own,
        "latest": jars[own]["version"],
        "download_url": f"{SITE_BASE_URL}/downloads/{zpath.name}",
        "file_name": zpath.name,
        "file_size": zpath.stat().st_size,
        "sha256": _sha256(zpath),
        "jars": jars,
    }


def _astraea_block():
    """The `astraea` block, or None when no ASTRAEA ZIP has been published.

    The same rules as _ouka_block(), in a separate copy so that adding ASTRAEA can
    never change a byte of the published cherry or ouka blocks (see the module
    docstring). The same never-drop rule applies in build().
    """
    zips = sorted(p for p in DOWNLOAD_DIR.glob(f"{ASTRAEA_ZIP_PREFIX}*{ASTRAEA_ZIP_SUFFIX}") if p.is_file())
    if not zips:
        return None
    if len(zips) > 1:
        raise SystemExit(
            f"ERROR: more than one ASTRAEA ZIP in {DOWNLOAD_DIR} ({', '.join(z.name for z in zips)}). "
            f"The manifest describes the current build only - publish exactly one."
        )
    zpath = zips[0]
    zip_version = zpath.name[len(ASTRAEA_ZIP_PREFIX):-len(ASTRAEA_ZIP_SUFFIX)]
    jars = {}
    depends = {}
    try:
        with zipfile.ZipFile(zpath) as zf:
            for info in zf.infolist():
                name = info.filename
                if not name.lower().endswith(".jar"):
                    continue
                if not name.startswith("mods/") or name.count("/") != 1:
                    raise SystemExit(
                        f"ERROR: {zpath.name} carries a jar outside mods/ ({name}). A package is installed from "
                        f"mods/<name>.jar only, so a jar anywhere else would never be installed.")
                data = zf.read(info)
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as jar:
                        meta = json.loads(jar.read("fabric.mod.json").decode("utf-8"))
                except (KeyError, ValueError, zipfile.BadZipFile) as exc:
                    raise SystemExit(
                        f"ERROR: could not read fabric.mod.json out of {name} in {zpath.name} ({exc}). "
                        f"astraea.jars must come from the jars themselves - do not type it.")
                mod_id, version = meta.get("id"), meta.get("version")
                if not isinstance(mod_id, str) or not mod_id.strip() or not isinstance(version, str) or not version.strip():
                    raise SystemExit(
                        f"ERROR: {name} in {zpath.name} declares no usable id and version in its fabric.mod.json, "
                        f"so nothing could match an installed copy against it.")
                mod_id = mod_id.strip()
                if mod_id in jars:
                    raise SystemExit(f"ERROR: {zpath.name} carries two jars declaring the mod id {mod_id!r}.")
                jars[mod_id] = {
                    "path": name,
                    "version": version.strip(),
                    "file_size": info.file_size,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                depends[mod_id] = set((meta.get("depends") or {}).keys())
    except (OSError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"ERROR: could not read {zpath} ({exc}).")
    if not jars:
        raise SystemExit(f"ERROR: {zpath.name} carries no jar in mods/, so there is nothing to install.")
    roots = [m for m in jars if not any(m in needs for other, needs in depends.items() if other != m)]
    if len(roots) != 1:
        raise SystemExit(
            f"ERROR: cannot tell which jar in {zpath.name} is ASTRAEA itself: the jars no other jar depends on are "
            f"{roots or 'none'}. The package's own mod must be the one jar nothing else in the ZIP depends on.")
    own = roots[0]
    if jars[own]["version"] != zip_version:
        raise SystemExit(
            f"ERROR: {zpath.name} is named for version {zip_version}, but its own jar {jars[own]['path']} declares "
            f"{jars[own]['version']}. An installed ASTRAEA would compare itself against the wrong number.")
    block = {
        "mod_id": own,
        "latest": jars[own]["version"],
        "download_url": f"{SITE_BASE_URL}/downloads/{zpath.name}",
        "file_name": zpath.name,
        "file_size": zpath.stat().st_size,
        "sha256": _sha256(zpath),
        "jars": jars,
    }
    # 2026-10-16: ASTRAEA's service has ended (data/retirement.json). The ZIP stays here, because the Store and
    # Corvus Agent read this block; `retired` tells them the model is ended, when Agent removes it, and where the
    # notice is. Added last, so every other key keeps its position and bytes.
    ended = retirement("astraea")
    if ended.get("retired"):
        if ended.get("last_version") != block["latest"]:
            raise SystemExit(
                f"ERROR: data/retirement.json says ASTRAEA ended at {ended.get('last_version')!r}, but the ZIP {zpath.name} "
                f"is {block['latest']}. The retirement must name the last version that is published.")
        block["retired"] = {
            "date": ended["date"],
            "remove_after": ended["remove_after"],
            "notice_url": f"{SITE_BASE_URL}/astraea/",
        }
    return block


def _tsubomi_block():
    """The `tsubomi` block, or None when no Tsubomi jar has been published.

    Aureum's shape (a bare jar: no `jars`, no notes), in a function of its own so that
    adding Tsubomi can never change a byte of another block (see the module docstring).
    The mod id and the version are read out of the jar, never typed: the id must be
    "tsubomi" and the version must equal the file name's, or an installed Tsubomi would
    be matched or compared against the wrong thing. The same never-drop rule applies in
    build().
    """
    jars = sorted(p for p in DOWNLOAD_DIR.glob(f"{TSUBOMI_JAR_PREFIX}*{TSUBOMI_JAR_SUFFIX}") if p.is_file())
    if not jars:
        return None
    if len(jars) > 1:
        raise SystemExit(
            f"ERROR: more than one Tsubomi jar in {DOWNLOAD_DIR} ({', '.join(j.name for j in jars)}). "
            f"The manifest describes the current build only - publish exactly one.")
    jpath = jars[0]
    name_version = jpath.name[len(TSUBOMI_JAR_PREFIX):-len(TSUBOMI_JAR_SUFFIX)]
    try:
        with zipfile.ZipFile(jpath) as zf:
            meta = json.loads(zf.read("fabric.mod.json").decode("utf-8"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        raise SystemExit(
            f"ERROR: could not read fabric.mod.json out of {jpath} ({exc}). The manifest's "
            f"tsubomi.mod_id and tsubomi.latest must come from the jar itself - do not type them.")
    mod_id, version = meta.get("id"), meta.get("version")
    if mod_id != TSUBOMI_MOD_ID:
        raise SystemExit(
            f"ERROR: {jpath.name} declares the mod id {mod_id!r}, not {TSUBOMI_MOD_ID!r}. The Store and the "
            f"Discord bot know the brand by that id, so an installed copy would never be matched.")
    if version != name_version:
        raise SystemExit(
            f"ERROR: {jpath.name} is named for version {name_version}, but its fabric.mod.json declares "
            f"{version!r}. An installed Tsubomi would compare itself against the wrong number.")
    return {
        "mod_id": mod_id,
        "latest": version,
        "download_url": f"{SITE_BASE_URL}/downloads/{jpath.name}",
        "file_name": jpath.name,
        "file_size": jpath.stat().st_size,
        "sha256": _sha256(jpath),
    }


def _halia_block():
    """The `halia` block, or None when no Halia jar has been published.

    Aureum's shape (a bare jar: no `jars`, no notes), in a function of its own so that
    adding Halia (2026-10-11) can never change a byte of another block. Tsubomi's function, copied on purpose.
    The mod id and the version are read out of the jar, never typed: the id must be
    "halia" and the version must equal the file name's, or an installed Halia would
    be matched or compared against the wrong thing. The same never-drop rule applies in
    build().
    """
    jars = sorted(p for p in DOWNLOAD_DIR.glob(f"{HALIA_JAR_PREFIX}*{HALIA_JAR_SUFFIX}") if p.is_file())
    if not jars:
        return None
    if len(jars) > 1:
        raise SystemExit(
            f"ERROR: more than one Halia jar in {DOWNLOAD_DIR} ({', '.join(j.name for j in jars)}). "
            f"The manifest describes the current build only - publish exactly one.")
    jpath = jars[0]
    name_version = jpath.name[len(HALIA_JAR_PREFIX):-len(HALIA_JAR_SUFFIX)]
    try:
        with zipfile.ZipFile(jpath) as zf:
            meta = json.loads(zf.read("fabric.mod.json").decode("utf-8"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        raise SystemExit(
            f"ERROR: could not read fabric.mod.json out of {jpath} ({exc}). The manifest's "
            f"halia.mod_id and halia.latest must come from the jar itself - do not type them.")
    mod_id, version = meta.get("id"), meta.get("version")
    if mod_id != HALIA_MOD_ID:
        raise SystemExit(
            f"ERROR: {jpath.name} declares the mod id {mod_id!r}, not {HALIA_MOD_ID!r}. The Store and the "
            f"Discord bot know the brand by that id, so an installed copy would never be matched.")
    if version != name_version:
        raise SystemExit(
            f"ERROR: {jpath.name} is named for version {name_version}, but its fabric.mod.json declares "
            f"{version!r}. An installed Halia would compare itself against the wrong number.")
    return {
        "mod_id": mod_id,
        "latest": version,
        "download_url": f"{SITE_BASE_URL}/downloads/{jpath.name}",
        "file_name": jpath.name,
        "file_size": jpath.stat().st_size,
        "sha256": _sha256(jpath),
    }


def _noctua_block():
    """The `noctua` block, or None when no Noctua package has been published.

    Noctua (2026-10-04) is a SERVER-side Palworld mod (UE4SS Lua), so there is no jar and no
    mod id: the block is the package's file name, size and SHA-256, and the Store lists the
    brand as available because it exists. The version is the file name's
    (Noctua_v<version>+pal<game>.zip) and must be the version CHANGELOG.md inside the package
    leads with, so a renamed older package cannot masquerade as a newer one. Exactly one
    package is published at a time; a separate function, so adding Noctua cannot change a
    byte of any other block. The never-drop rule applies in build().
    """
    zips = sorted(p for p in DOWNLOAD_DIR.glob(f"{NOCTUA_ZIP_PREFIX}*{NOCTUA_ZIP_SUFFIX}") if p.is_file())
    if not zips:
        return None
    if len(zips) > 1:
        raise SystemExit(
            f"ERROR: more than one Noctua package in {DOWNLOAD_DIR} ({', '.join(z.name for z in zips)}). "
            f"The manifest describes the current build only - publish exactly one.")
    zpath = zips[0]
    stem = zpath.name[len(NOCTUA_ZIP_PREFIX):-len(NOCTUA_ZIP_SUFFIX)]
    version = stem.split("+", 1)[0]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or "+pal" not in stem:
        raise SystemExit(f"ERROR: {zpath.name} is not named Noctua_v<major.minor.patch>+pal<game version>.zip.")
    try:
        with zipfile.ZipFile(zpath) as zf:
            names = set(zf.namelist())
            changelog = zf.read("CHANGELOG.md").decode("utf-8")
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"ERROR: could not read CHANGELOG.md out of {zpath} ({exc}).")
    if not any(n.endswith("NoctuaCore/scripts/main.lua") for n in names):
        raise SystemExit(f"ERROR: {zpath.name} holds no NoctuaCore/scripts/main.lua - it is not a Noctua package.")
    heading = re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.MULTILINE)
    if not heading or heading.group(1) != version:
        raise SystemExit(
            f"ERROR: {zpath.name} is named for version {version}, but its CHANGELOG.md leads with "
            f"{heading.group(1) if heading else 'no version'}.")
    return {
        "latest": version,
        "download_url": f"{SITE_BASE_URL}/downloads/{zpath.name}",
        "file_name": zpath.name,
        "file_size": zpath.stat().st_size,
        "sha256": _sha256(zpath),
    }


AGENT_ZIP_PREFIX = "corvus-agent-"
AGENT_ZIP_SUFFIX = ".zip"


def _agent_block():
    """The `agent` block (Corvus Agent, 2026-10-12), or None when no package has been published.

    Corvus Agent is the program beside a self-hosted server that keeps its mods in step with this manifest; nothing in
    the game loads it, so the block is a file: name, size, SHA-256. Its name starts with "corvus-agent-", which the
    launcher's own rule (corvus-<digits>.jar) cannot match. The version is the file name's and must be the
    Implementation-Version of the jar inside, so a renamed package cannot pass for another. Exactly one package; a
    function of its own, so it cannot change a byte of another block; never dropped once published.
    """
    zips = sorted(p for p in DOWNLOAD_DIR.glob(f"{AGENT_ZIP_PREFIX}*{AGENT_ZIP_SUFFIX}") if p.is_file())
    if not zips:
        return None
    if len(zips) > 1:
        raise SystemExit(f"ERROR: more than one Corvus Agent package in {DOWNLOAD_DIR} "
                         f"({', '.join(z.name for z in zips)}). Publish exactly one.")
    zpath = zips[0]
    version = zpath.name[len(AGENT_ZIP_PREFIX):-len(AGENT_ZIP_SUFFIX)]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"ERROR: {zpath.name} is not named corvus-agent-<major.minor.patch>.zip.")
    inner = f"corvus-agent-{version}/corvus-agent-{version}.jar"
    try:
        with zipfile.ZipFile(zpath) as zf:
            with zipfile.ZipFile(io.BytesIO(zf.read(inner))) as jar:
                meta = jar.read("META-INF/MANIFEST.MF").decode("utf-8")
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"ERROR: could not read {inner} out of {zpath} ({exc}).")
    declared = re.search(r"^Implementation-Version: (.+)$", meta, re.MULTILINE)
    if not declared or declared.group(1).strip() != version:
        raise SystemExit(f"ERROR: {zpath.name} is named for {version}, but the jar inside declares "
                         f"{declared.group(1).strip() if declared else 'no version'}.")
    return {
        "latest": version,
        "download_url": f"{SITE_BASE_URL}/downloads/{zpath.name}",
        "file_name": zpath.name,
        "file_size": zpath.stat().st_size,
        "sha256": _sha256(zpath),
    }


def _previously_published_manifest():
    """The manifest currently committed at the repo root, or {} if there is none."""
    path = ROOT / "glimpse_manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def build():
    version = _mod_version()
    zpath = _zip_path(version)
    entry = _changelog_entry(version)
    size_bytes = zpath.stat().st_size
    sha256_hex = _sha256(zpath)
    published_at = f"{entry['date']}T00:00:00+00:00"

    manifest = {
        "pack": {
            # `id` is a stable key, not a display name: Corvus keys its
            # installed-pack record off it, so the V2.5.0 brand rename
            # deliberately does NOT touch it. Renaming it would orphan every
            # existing install's record. `title` below carries the new name.
            "id": "glimpse-pack",
            "latest": version,
            "published_at": published_at,
            "title": f"{PACK_NAME} {entry['release']}",
            "summary": _english_summary(entry),
            "download_url": f"{SITE_BASE_URL}/downloads/{zpath.name}",
            "file_name": zpath.name,
            "file_size": size_bytes,
            "sha256": sha256_hex,
            "changelog_url": f"{SITE_BASE_URL}/en/changelog/",
        }
    }

    release = newest_launcher_jar(DOWNLOAD_DIR)
    if release is not None:
        manifest["launcher"] = _launcher_block(release)
        print(f"glimpse_manifest.py: {LAUNCHER_APP_NAME} build {release['file_name']} "
              f"(version {release['version']}) selected, including 'launcher' block")
    else:
        # An empty result is only acceptable before the first launcher ever
        # shipped. After that it means the discovery broke (a rename, a moved
        # folder) and shipping a manifest without a launcher block would
        # silently switch off self-update for everyone already running it.
        _notes_path, notes_table = _launcher_notes_table()
        if notes_table:
            raise SystemExit(
                "ERROR: no launcher jar found in %s, but %s already lists released versions "
                "(%s). A manifest with no 'launcher' block would silently disable self-update "
                "for every installed %s. Publish the jar, or fix the naming - do not ship this."
                % (DOWNLOAD_DIR, _notes_path,
                   ", ".join(sorted(notes_table)), LAUNCHER_APP_NAME))
        print("glimpse_manifest.py: no launcher jar found yet - writing manifest with 'pack' "
              "only (expected until the first launcher build ships)")

    aureum = _aureum_block()
    if aureum is not None:
        manifest["aureum"] = aureum
        print(f"glimpse_manifest.py: Aureum {aureum['latest']} ({aureum['file_name']}, mod id "
              f"{aureum['mod_id']!r}) selected, including 'aureum' block")
    elif "aureum" in _previously_published_manifest():
        # Same rule as the launcher block above, and the same failure it
        # prevents: an absent block is only honest before the first release.
        # After that it means discovery broke (a rename, a moved folder), and
        # publishing without it would tell every installed Corvus that Aureum
        # has no published version -- switching off the auto-update the owner
        # explicitly asked for, silently, for everyone who already has it.
        raise SystemExit(
            f"ERROR: no Aureum jar found in {DOWNLOAD_DIR}, but the published glimpse_manifest.json "
            f"already carries an 'aureum' block. Dropping it would silently disable Aureum "
            f"auto-update for every installed Corvus. Publish the jar, or fix the naming - do not "
            f"ship this."
        )
    else:
        print("glimpse_manifest.py: no Aureum jar found yet - writing manifest with no 'aureum' "
              "block (expected until the first Aureum build ships)")

    cherry = _cherry_block()
    if cherry is not None:
        manifest["cherry"] = cherry
        print(f"glimpse_manifest.py: Cherry {cherry['latest']} ({cherry['file_name']}, mod id "
              f"{cherry['mod_id']!r}, jars {', '.join(cherry['jars'])}) selected, including 'cherry' block")
    elif "cherry" in _previously_published_manifest():
        # The never-drop rule once more: after the first Cherry release an absent ZIP means
        # discovery broke, and dropping the block would switch off Cherry auto-update for
        # every installed Corvus.
        raise SystemExit(
            f"ERROR: no Cherry ZIP found in {DOWNLOAD_DIR}, but the published glimpse_manifest.json "
            f"already carries a 'cherry' block. Dropping it would silently disable Cherry "
            f"auto-update for every installed Corvus. Publish the ZIP, or fix the naming - do not "
            f"ship this."
        )
    else:
        print("glimpse_manifest.py: no Cherry ZIP found yet - writing manifest with no 'cherry' "
              "block (expected until the first Cherry build ships)")

    ouka = _ouka_block()
    if ouka is not None:
        manifest["ouka"] = ouka
        print(f"glimpse_manifest.py: OUKA {ouka['latest']} ({ouka['file_name']}, mod id "
              f"{ouka['mod_id']!r}, jars {', '.join(ouka['jars'])}) selected, including 'ouka' block")
    elif "ouka" in _previously_published_manifest():
        # The never-drop rule for OUKA: once its block is published, an absent ZIP means
        # discovery broke (a rename, a moved folder), and dropping the block would silently
        # withdraw the published OUKA release from everything that reads this manifest.
        raise SystemExit(
            f"ERROR: no OUKA ZIP found in {DOWNLOAD_DIR}, but the published glimpse_manifest.json "
            f"already carries an 'ouka' block. Dropping it would silently withdraw the OUKA release "
            f"from every reader of the manifest. Publish the ZIP, or fix the naming - do not ship this."
        )
    else:
        print("glimpse_manifest.py: no OUKA ZIP found yet - writing manifest with no 'ouka' "
              "block (expected until the first OUKA build ships)")

    astraea = _astraea_block()
    if astraea is not None:
        manifest["astraea"] = astraea
        print(f"glimpse_manifest.py: ASTRAEA {astraea['latest']} ({astraea['file_name']}, mod id "
              f"{astraea['mod_id']!r}, jars {', '.join(astraea['jars'])}) selected, including 'astraea' block")
    elif "astraea" in _previously_published_manifest():
        # The never-drop rule for ASTRAEA: once its block is published, an absent ZIP means
        # discovery broke (a rename, a moved folder), and dropping the block would silently
        # withdraw the published ASTRAEA release from everything that reads this manifest.
        raise SystemExit(
            f"ERROR: no ASTRAEA ZIP found in {DOWNLOAD_DIR}, but the published glimpse_manifest.json "
            f"already carries an 'astraea' block. Dropping it would silently withdraw the ASTRAEA release "
            f"from every reader of the manifest. Publish the ZIP, or fix the naming - do not ship this."
        )
    else:
        print("glimpse_manifest.py: no ASTRAEA ZIP found yet - writing manifest with no 'astraea' "
              "block (expected until the first ASTRAEA build ships)")

    tsubomi = _tsubomi_block()
    if tsubomi is not None:
        manifest["tsubomi"] = tsubomi
        print(f"glimpse_manifest.py: Tsubomi {tsubomi['latest']} ({tsubomi['file_name']}, mod id "
              f"{tsubomi['mod_id']!r}) selected, including 'tsubomi' block")
    elif "tsubomi" in _previously_published_manifest():
        # The never-drop rule for Tsubomi: once its block is published, an absent jar means
        # discovery broke (a rename, a moved folder), and dropping the block would silently
        # withdraw the published Tsubomi release from everything that reads this manifest.
        raise SystemExit(
            f"ERROR: no Tsubomi jar found in {DOWNLOAD_DIR}, but the published glimpse_manifest.json "
            f"already carries a 'tsubomi' block. Dropping it would silently withdraw the Tsubomi release "
            f"from every reader of the manifest. Publish the jar, or fix the naming - do not ship this.")
    else:
        print("glimpse_manifest.py: no Tsubomi jar found yet - writing manifest with no 'tsubomi' "
              "block (expected until the first Tsubomi build ships)")

    halia = _halia_block()
    if halia is not None:
        manifest["halia"] = halia
        print(f"glimpse_manifest.py: Halia {halia['latest']} ({halia['file_name']}, mod id {halia['mod_id']!r}) "
              f"selected, including 'halia' block")
    elif "halia" in _previously_published_manifest():
        raise SystemExit(
            f"ERROR: no Halia jar found in {DOWNLOAD_DIR}, but the published glimpse_manifest.json already carries a "
            f"'halia' block. Dropping it would silently withdraw the release. Publish the jar, or fix the naming.")
    else:
        print("glimpse_manifest.py: no Halia jar found yet - writing manifest with no 'halia' block")

    agent = _agent_block()
    if agent is not None:
        manifest["agent"] = agent
        print(f"glimpse_manifest.py: Corvus Agent {agent['latest']} ({agent['file_name']}) selected, including 'agent' block")
    elif "agent" in _previously_published_manifest():
        raise SystemExit(f"ERROR: no Corvus Agent package found in {DOWNLOAD_DIR}, but the published manifest carries an "
                         f"'agent' block. Dropping it would silently withdraw the release.")

    noctua = _noctua_block()
    if noctua is not None:
        manifest["noctua"] = noctua
        print(f"glimpse_manifest.py: Noctua {noctua['latest']} ({noctua['file_name']}) selected, "
              f"including 'noctua' block")
    elif "noctua" in _previously_published_manifest():
        raise SystemExit(
            f"ERROR: no Noctua package found in {DOWNLOAD_DIR}, but the published glimpse_manifest.json "
            f"already carries a 'noctua' block. Dropping it would silently withdraw the release. "
            f"Publish the package, or fix the naming - do not ship this.")
    else:
        print("glimpse_manifest.py: no Noctua package found yet - writing manifest with no 'noctua' block")

    out_path = ROOT / "glimpse_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out_path} (pack version {version}, sha256 {sha256_hex[:12]}...)")


if __name__ == "__main__":
    build()
