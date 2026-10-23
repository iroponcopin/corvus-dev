#!/usr/bin/env python3
"""Gate: the Halia release the site publishes is the jar really in downloads/, the manifest describes that jar, and
the jar says what Halia is.

Halia V1.0.0 (2026-10-11) ships as a BARE JAR, like Aureum, not as a package ZIP like Cherry, OUKA and ASTRAEA, so
its manifest block has Aureum's shape (no "jars", no notes). The page half of a release (the Download section, the
changelog tab, the Store card) is the portal's own gates' job. What no other checker here reads for Halia is checked
here:

  1. exactly one downloads/halia-<ver>.jar, and it is TRACKED by git: an untracked jar builds a manifest and a
     Discord post whose download 404s on the live site;
  2. its fabric.mod.json says id "halia" and the file name's version;
  3. it depends on nothing but fabricloader, minecraft, java and fabric-api, and recommends / suggests nothing;
  4. it declares no breaks and no conflicts: Halia 1.0.0 refuses no other mod, and Corvus Store (3.0.2 and later)
     turns an unconditional "breaks" in a brand's jar into a refused install;
  5. glimpse_manifest.json carries a "halia" block for that jar and nothing else: mod_id "halia", latest <ver>, the
     jar's file name, address, size and SHA-256 — and no "jars" key (Halia 1.0.0 has no crafting recipes, so it is not a recipe-sheet source). The Discord release bot announces from this block;
  6. changelog_feed/brands.json lists Halia with its feed, and each of the 13 languages' changelog_feed/halia feed
     leads with the release that the jar is: "V" + <ver> (V1.4.0.37), or, for a jar version with exactly three numeric
     parts a.b.c, the owner's notation "V<a>.<b> <c>" (V1.4 1140: the same numbers, one space, no other variant). The
     site does not publish a release its changelog has not reached;
  7. (Halia 1.4.0, 2026-10-22) the manifest's top-level "spawn_lock" is exactly {model: "halia", from, until} with
     YYYY-MM-DD dates and from before until, and halia.creatures is exactly seven entries: each {id, name: {en, ja},
     dimension}, the id matching the Store's pattern [a-z][a-z0-9_]* with no "halia:" prefix, no duplicate ids, and
     non-empty names and dimension. The Store refuses a list it cannot read and falls back to its bundled one.

Independent by construction: it imports nothing from the builders (not site_common, not build_glimpse_manifest, not
build_changelog_feed). The language list, the site address and the file-name rule are written out again here, so a
mistake in a builder cannot make this gate agree with it.

  python3 scripts/check_halia_release.py              # the gate
  python3 scripts/check_halia_release.py --self-test  # the pristine tree green, every planted defect red

Exit code: 0 green, 1 red, 2 cannot judge (never green).
"""
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["ja", "en", "es", "fr", "zh", "ko", "pt-br", "it", "ar", "ru", "id", "de", "tr"]
JAR_RE = re.compile(r"^halia-(\d+(?:\.\d+)*)\.jar$")
SITE = "https://iroponcopin.github.io/corvus-dev"
ALLOWED_DEPENDS = {"fabricloader", "minecraft", "java", "fabric-api"}
ALLOWED_SOFT = set()               # Halia recommends and suggests nothing
CREATURE_ID_RE = re.compile(r"[a-z][a-z0-9_]*")       # the Store's pattern (HaliaCreature.ID)
CREATURE_COUNT = 7                 # the natural-spawn creatures of V1.4 (CREATURES_FOR_CORVUS.json "creatures")
THREE_PART_RE = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)")


def release_string_ok(newest, version: str) -> bool:
    """Rule 6's test, pure: the feed's newest release string names the jar's version. Two forms and nothing looser:
    "V" + the jar version (V1.4.0.37), and, when the jar version has exactly three numeric parts a.b.c, the owner's
    "V<a>.<b> <c>" (V1.4 1140). No other variant: not two spaces, not a lowercase v, not trailing text."""
    if not isinstance(newest, str):
        return False
    if newest == f"V{version}":
        return True
    three = THREE_PART_RE.fullmatch(version)
    return three is not None and newest == f"V{three.group(1)}.{three.group(2)} {three.group(3)}"


def git_tracked(root: Path, rel: str) -> bool:
    result = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root, capture_output=True, text=True)
    return result.returncode == 0


def spawn_and_creature_problems(manifest: dict, halia_block) -> list:
    """Item 7: the spawn_lock setting and the halia.creatures list are well formed. Pure: takes the parsed manifest."""
    from datetime import date
    problems = []
    lock = manifest.get("spawn_lock")
    if lock is None:
        problems.append("glimpse_manifest.json has no top-level 'spawn_lock': the Store would not lock the creature switches")
    elif not isinstance(lock, dict) or set(lock) != {"model", "from", "until"}:
        problems.append(f"glimpse_manifest.json spawn_lock must be exactly {{model, from, until}} (was {lock!r})")
    else:
        if lock["model"] != "halia":
            problems.append(f"spawn_lock.model is {lock['model']!r}, not 'halia'")
        try:
            start, end = date.fromisoformat(lock["from"]), date.fromisoformat(lock["until"])
        except (TypeError, ValueError):
            problems.append(f"spawn_lock from/until must be YYYY-MM-DD (was {lock['from']!r}, {lock['until']!r})")
        else:
            if not start < end:
                problems.append(f"spawn_lock from {lock['from']} is not before until {lock['until']}")
    if halia_block is None:
        return problems          # the missing halia block is already a problem above
    creatures = halia_block.get("creatures")
    if not isinstance(creatures, list):
        return problems + ["glimpse_manifest.json halia.creatures is missing or not a list (the Store shows its bundled list)"]
    if len(creatures) != CREATURE_COUNT:
        problems.append(f"halia.creatures has {len(creatures)} entries, the V1.4 natural-spawn creatures are {CREATURE_COUNT}")
    seen = set()
    for i, c in enumerate(creatures):
        if not isinstance(c, dict) or set(c) != {"id", "name", "dimension"}:
            problems.append(f"halia.creatures[{i}] must be exactly {{id, name, dimension}} (was {c!r})")
            continue
        cid = c["id"]
        if not isinstance(cid, str) or not CREATURE_ID_RE.fullmatch(cid) or cid.startswith("halia:"):
            problems.append(f"halia.creatures[{i}] id {cid!r} does not match [a-z][a-z0-9_]* without a namespace")
        elif cid in seen:
            problems.append(f"halia.creatures id {cid!r} appears twice")
        seen.add(cid)
        name = c["name"]
        if not isinstance(name, dict) or set(name) != {"en", "ja"} or not all(
                isinstance(v, str) and v.strip() for v in name.values()):
            problems.append(f"halia.creatures[{i}] ({cid}) needs non-empty name en and ja")
        if not isinstance(c["dimension"], str) or not c["dimension"].strip():
            problems.append(f"halia.creatures[{i}] ({cid}) needs a non-empty dimension")
    return problems


def nested_mod_ids(data: bytes) -> set:
    """The mod ids declared by the jars nested under META-INF/jars/ of the Halia jar (read from each nested
    fabric.mod.json). Unreadable nested jars contribute nothing, so they cannot excuse a dependency."""
    ids = set()
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as outer:
            for name in outer.namelist():
                if name.startswith("META-INF/jars/") and name.endswith(".jar"):
                    try:
                        with zipfile.ZipFile(io.BytesIO(outer.read(name))) as inner:
                            mod = json.loads(inner.read("fabric.mod.json").decode("utf-8"))
                        if isinstance(mod.get("id"), str):
                            ids.add(mod["id"])
                    except (zipfile.BadZipFile, KeyError, ValueError):
                        continue
    except zipfile.BadZipFile:
        return set()
    return ids


def check(root: Path, tracked=git_tracked):
    """(problems, facts). A problem is a string; an empty list is green."""
    problems = []
    downloads = root / "downloads"
    jars = sorted(p for p in downloads.glob("halia-*.jar") if p.is_file())
    if not jars:
        return ["no downloads/halia-<ver>.jar: nothing to check (the gate cannot pass on absence)"], {}
    if len(jars) > 1:
        return [f"more than one Halia jar in downloads/ ({', '.join(j.name for j in jars)}); the manifest describes one"], {}
    jpath = jars[0]
    m = JAR_RE.match(jpath.name)
    if not m:
        return [f"downloads/{jpath.name} does not parse as halia-<numeric.version>.jar"], {}
    version = m.group(1)
    rel = f"downloads/{jpath.name}"
    if not tracked(root, rel):
        problems.append(f"{rel} is not tracked by git: the live site would serve a 404 for it")
    data = jpath.read_bytes()
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as jar:
            meta = json.loads(jar.read("fabric.mod.json").decode("utf-8"))
    except (zipfile.BadZipFile, KeyError, ValueError) as exc:
        return problems + [f"{jpath.name} cannot be read as a Fabric jar ({exc})"], {}
    if meta.get("id") != "halia":
        problems.append(f"{jpath.name} declares the mod id {meta.get('id')!r}, not 'halia'")
    if meta.get("version") != version:
        problems.append(f"{jpath.name} is named for {version}, but its fabric.mod.json declares {meta.get('version')!r}")
    # Item 3 (decided 2026-10-22 by the parent, option B): besides the four base dependencies, a Halia jar may depend
    # on a mod only when one of the jars it NESTS (META-INF/jars/*.jar) declares that exact mod id in its own
    # fabric.mod.json. The nested copy is read from the jar, never typed here, so a dependency with nothing nested
    # behind it stays red.
    nested_ids = nested_mod_ids(data)
    extra = sorted(set(meta.get("depends") or {}) - ALLOWED_DEPENDS - nested_ids)
    if extra:
        problems.append(f"the halia jar depends on {extra}: it may depend only on {sorted(ALLOWED_DEPENDS)}, plus a mod "
                        f"whose jar it nests under META-INF/jars (nested ids here: {sorted(nested_ids)})")
    for field in ("recommends", "suggests"):
        soft = sorted(set(meta.get(field) or {}) - ALLOWED_SOFT)
        if soft:
            problems.append(f"the halia jar names {soft} under {field}: only {sorted(ALLOWED_SOFT)} may appear there")
    for field in ("breaks", "conflicts"):
        wrong = sorted(meta.get(field) or {})
        if wrong:
            problems.append(f"the halia jar declares {field} against {wrong}: Halia 1.0.0 refuses nothing, and the Store "
                            f"would turn an unconditional 'breaks' into a refused install")
    try:
        manifest = json.loads((root / "glimpse_manifest.json").read_text(encoding="utf-8"))
        block = manifest.get("halia")
    except (OSError, ValueError) as exc:
        return problems + [f"glimpse_manifest.json cannot be read ({exc})"], {}
    # item 7 reads creatures out of the block; the byte-for-byte comparison below covers the rest of the block.
    problems += spawn_and_creature_problems(manifest, block)
    if isinstance(block, dict) and "creatures" in block:
        block = {k: v for k, v in block.items() if k != "creatures"}
    expected = {
        "mod_id": "halia",
        "latest": version,
        "download_url": f"{SITE}/downloads/{jpath.name}",
        "file_name": jpath.name,
        "file_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if block is None:
        problems.append("glimpse_manifest.json has no 'halia' block: the bot would announce nothing")
    elif block != expected:
        for key in expected:
            if block.get(key) != expected[key]:
                problems.append(f"glimpse_manifest.json halia.{key} is {block.get(key)!r}, the jar says {expected[key]!r}")
        for key in sorted(set(block) - set(expected)):
            problems.append(f"glimpse_manifest.json halia carries an unexpected key {key!r} (a bare jar's block is Aureum's shape)")
    try:
        brands = json.loads((root / "changelog_feed" / "brands.json").read_text(encoding="utf-8"))["brands"]
        entry = [b for b in brands if b.get("id") == "halia"]
        if not entry or entry[0].get("feed") != "changelog_feed/halia/{lang}.json":
            problems.append("changelog_feed/brands.json does not list Halia with changelog_feed/halia/{lang}.json")
    except (OSError, ValueError, KeyError) as exc:
        problems.append(f"changelog_feed/brands.json cannot be read ({exc})")
    for lang in LANGS:
        path = root / "changelog_feed" / "halia" / f"{lang}.json"
        try:
            feed = json.loads(path.read_text(encoding="utf-8"))
            newest = feed["groups"][0]["releases"][0]["version"]
        except (OSError, ValueError, KeyError, IndexError) as exc:
            problems.append(f"changelog_feed/halia/{lang}.json cannot be read for its newest release ({exc})")
            continue
        if not release_string_ok(newest, version):
            hint = ""
            three = THREE_PART_RE.fullmatch(version)
            if three:
                hint = f" or V{three.group(1)}.{three.group(2)} {three.group(3)}"
            problems.append(f"changelog_feed/halia/{lang}.json leads with {newest!r}, but the site publishes V{version}{hint}")
    return problems, {"jar": jpath.name, "version": version, "size": len(data), "sha256": expected["sha256"]}


# --- self-test ----------------------------------------------------------------------------------

def self_test() -> int:
    """The pristine tree must be green; then each plant, in its own copy, must turn it red (and each allowed variant
    must stay green, so the rules are not simply refusing everything)."""
    base, _ = check(ROOT)
    if base:
        print("SELF-TEST CANNOT JUDGE: the pristine tree is not green, so a red plant would prove nothing:")
        for p in base:
            print("  " + p)
        return 2
    jname = sorted((ROOT / "downloads").glob("halia-*.jar"))[0].name

    def copy_tree(dst: Path):
        (dst / "downloads").mkdir(parents=True)
        shutil.copy2(ROOT / "downloads" / jname, dst / "downloads" / jname)
        shutil.copy2(ROOT / "glimpse_manifest.json", dst / "glimpse_manifest.json")
        shutil.copytree(ROOT / "changelog_feed", dst / "changelog_feed")

    def rewrite_jar(dst: Path, meta_change=None, extra_inner=None, sync_manifest=True, drop_nested=()):
        """Rebuild the jar with the change applied. With sync_manifest the manifest block is rewritten to the new
        jar's size and hash, so only the planted fault can be what turns the gate red."""
        path = dst / "downloads" / jname
        with zipfile.ZipFile(path) as jar:
            inner = {n: jar.read(n) for n in jar.namelist()}
        if meta_change:
            meta = json.loads(inner["fabric.mod.json"])
            meta_change(meta)
            inner["fabric.mod.json"] = json.dumps(meta).encode()
        if extra_inner:
            inner.update(extra_inner)
        for prefix in drop_nested:
            for name in [n for n in inner if n.startswith(prefix)]:
                del inner[name]
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as jar:
            for n, b in inner.items():
                jar.writestr(n, b)
        path.write_bytes(buf.getvalue())
        if sync_manifest:
            edit_manifest(dst, lambda m: m["halia"].update(file_size=len(buf.getvalue()),
                                                            sha256=hashlib.sha256(buf.getvalue()).hexdigest()))

    def edit_manifest(dst: Path, change):
        p = dst / "glimpse_manifest.json"
        m = json.loads(p.read_text(encoding="utf-8"))
        change(m)
        p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def edit_feed(dst: Path, lang: str, version: str):
        p = dst / "changelog_feed" / "halia" / f"{lang}.json"
        f = json.loads(p.read_text(encoding="utf-8"))
        f["groups"][0]["releases"][0]["version"] = version
        p.write_text(json.dumps(f, ensure_ascii=False), encoding="utf-8")

    def set_feeds(dst: Path, version: str):
        """Every one of the 13 feeds leads with `version` (the release string, not the jar version)."""
        for lang in LANGS:
            edit_feed(dst, lang, version)

    def retag(dst: Path, version: str):
        """Re-version the planted copy to a three-part `version`: the jar moves to halia-<version>.jar with its own
        fabric.mod.json, and the manifest's halia block (latest, file name, address, size, SHA-256) moves with it, so the
        only thing the plant changes is the version the feeds are checked against."""
        old = dst / "downloads" / jname
        with zipfile.ZipFile(old) as jar:
            inner = {n: jar.read(n) for n in jar.namelist()}
        meta = json.loads(inner["fabric.mod.json"])
        meta["version"] = version
        inner["fabric.mod.json"] = json.dumps(meta).encode()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as jar:
            for n, b in inner.items():
                jar.writestr(n, b)
        data = buf.getvalue()
        name = f"halia-{version}.jar"
        (dst / "downloads" / name).write_bytes(data)
        if old.name != name:      # the staged jar already has this name: unlinking it would delete the new one
            old.unlink()

        def move_block(m):
            m["halia"].update(latest=version, file_name=name, download_url=f"{SITE}/downloads/{name}",
                              file_size=len(data), sha256=hashlib.sha256(data).hexdigest())
        edit_manifest(dst, move_block)

    def brand(meta, **kv):
        meta.setdefault("custom", {}).setdefault("halia", {}).setdefault("brand", {}).update(kv)

    def second_jar(dst: Path):
        shutil.copy2(dst / "downloads" / jname, dst / "downloads" / "halia-0.9.0.jar")

    plants = [
        # label, plant, tracked, should_fail
        ("clean copy", lambda d: None, True, False),
        ("Cherry as a suggestion", lambda d: rewrite_jar(d, lambda m: m.update(suggests={"cherry": "*"})), True, True),
        ("the jar is untracked (the live 404)", lambda d: None, False, True),
        ("a second Halia jar in downloads/", second_jar, True, True),
        ("the manifest has no halia block", lambda d: edit_manifest(d, lambda m: m.pop("halia")), True, True),
        ("the manifest's sha256 is stale", lambda d: edit_manifest(d, lambda m: m["halia"].update(sha256="0" * 64)), True, True),
        ("the manifest's block carries 'jars' (a package's shape)",
         lambda d: edit_manifest(d, lambda m: m["halia"].update(jars={"halia": {"version": "1.0.0"}})), True, True),
        ("the jar is replaced after the manifest was built",
         lambda d: rewrite_jar(d, extra_inner={"extra.txt": b"x"}, sync_manifest=False), True, True),
        ("the jar declares another mod id", lambda d: rewrite_jar(d, lambda m: m.update(id="halia_x")), True, True),
        ("the jar's version differs from its name", lambda d: rewrite_jar(d, lambda m: m.update(version="0.9.9")), True, True),
        ("Cherry as a hard dependency", lambda d: rewrite_jar(d, lambda m: m["depends"].update(cherry="*")), True, True),
        ("geckolib depended on with no geckolib jar nested (the nested copy removed)",
         lambda d: rewrite_jar(d, lambda m: m["depends"].update(geckolib=">=5.5.6"),
                               extra_inner=None, sync_manifest=True, drop_nested=("META-INF/jars/geckolib-",)), True, True),
        ("an unlisted mod depended on with nothing nested behind it",
         lambda d: rewrite_jar(d, lambda m: m["depends"].update(cherry="*")), True, True),
        ("an Alpha module as a dependency", lambda d: rewrite_jar(d, lambda m: m["depends"].update(sorakaze_guns="*")), True, True),
        ("another mod suggested", lambda d: rewrite_jar(d, lambda m: m.update(suggests={"ouka": "*"})), True, True),
        ("breaks names Cherry (a false incompatibility)",
         lambda d: rewrite_jar(d, lambda m: m.setdefault("breaks", {}).update(cherry="*")), True, True),
        ("one language's feed lags the release", lambda d: edit_feed(d, "ar", "V0.9.0"), True, True),
        ("spawn_lock is missing (the switches would not lock)", lambda d: edit_manifest(d, lambda m: m.pop("spawn_lock")), True, True),
        ("spawn_lock from is after until", lambda d: edit_manifest(d, lambda m: m["spawn_lock"].update({"from": "2027-01-01"})), True, True),
        ("spawn_lock names another model", lambda d: edit_manifest(d, lambda m: m["spawn_lock"].update({"model": "ouka"})), True, True),
        ("a creature id carries the halia: prefix",
         lambda d: edit_manifest(d, lambda m: m["halia"]["creatures"][0].update({"id": "halia:glimmerwisp"})), True, True),
        ("a creature is missing (six, not seven)", lambda d: edit_manifest(d, lambda m: m["halia"]["creatures"].pop()), True, True),
        ("a creature has no Japanese name",
         lambda d: edit_manifest(d, lambda m: m["halia"]["creatures"][1]["name"].update({"ja": ""})), True, True),
        ("a creature id is duplicated",
         lambda d: edit_manifest(d, lambda m: m["halia"]["creatures"].__setitem__(1, dict(m["halia"]["creatures"][0]))), True, True),
        ("Halia 1.4.1140 with every feed in the owner's notation V1.4 1140 (control)",
         lambda d: (retag(d, "1.4.1140"), set_feeds(d, "V1.4 1140")), True, False),
        ("Halia 1.4.1140 with one feed at a wrong build: V1.4 1139",
         lambda d: (retag(d, "1.4.1140"), set_feeds(d, "V1.4 1140"), edit_feed(d, "ar", "V1.4 1139")), True, True),
        ("Halia 1.4.1140 with every feed in the dotted form V1.4.1140 (control)",
         lambda d: (retag(d, "1.4.1140"), set_feeds(d, "V1.4.1140")), True, False),
        ("Halia 1.4.1140 with two spaces in the notation: V1.4  1140",
         lambda d: (retag(d, "1.4.1140"), set_feeds(d, "V1.4  1140")), True, True),
        ("Halia 1.4.1140 with a lowercase v: v1.4 1140",
         lambda d: (retag(d, "1.4.1140"), set_feeds(d, "v1.4 1140")), True, True),
        ("Halia 1.4.1140 with trailing text: V1.4 1140 beta",
         lambda d: (retag(d, "1.4.1140"), set_feeds(d, "V1.4 1140 beta")), True, True),
    ]
    ok = True
    for label, plant, is_tracked, should_fail in plants:
        with tempfile.TemporaryDirectory() as temp:
            dst = Path(temp)
            copy_tree(dst)
            plant(dst)
            found = check(dst, tracked=lambda _r, _p, t=is_tracked: t)[0]
        failed = bool(found)
        right = failed == should_fail
        ok &= right
        detail = f" ({found[0]})" if found and right else (f" UNEXPECTED: {found}" if found else "")
        print(f"  self-test [{'ok' if right else 'WRONG'}] {label}: {'red' if failed else 'green'}{detail[:170]}")
    print("SELF-TEST VERDICT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    problems, facts = check(ROOT)
    for p in problems:
        print("  RED: " + p)
    if problems:
        print(f"halia release: RED ({len(problems)} problem(s))")
        return 1
    print(f"halia release: {facts['jar']} ({facts['size']:,} bytes, sha256 {facts['sha256'][:16]}…) is tracked, the one "
          f"Halia jar, depends only on Fabric and the mods it nests, refuses no other mod, is described exactly by the "
          f"manifest's halia block, and led by V{facts['version']} in all 13 feeds: GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
