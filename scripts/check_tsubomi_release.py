#!/usr/bin/env python3
"""Gate: the Tsubomi release the site publishes is the jar really in downloads/, the manifest describes that jar, and
the jar says what Tsubomi is.

Tsubomi V1.0.0 (2026-09-30) ships as a BARE JAR, like Aureum, not as a package ZIP like Cherry, OUKA and ASTRAEA, so
its manifest block has Aureum's shape (no "jars", no notes). The page half of a release (the Download section, the
changelog tab, the Store card) is the portal's own gates' job. What no other checker here reads for Tsubomi is checked
here:

  1. exactly one downloads/tsubomi-<ver>.jar, and it is TRACKED by git: an untracked jar builds a manifest and a
     Discord post whose download 404s on the live site;
  2. its fabric.mod.json says id "tsubomi" and the file name's version;
  3. it depends on nothing but fabricloader, minecraft, java and fabric-api. Cherry may appear only as a soft link
     (recommends / suggests): Tsubomi works beside Cherry and needs nothing. breaks / conflicts may name only Alpha's
     modules (sorakaze_*): a declared incompatibility with anything else would refuse a brand Tsubomi works with;
  4. the OPPOSITE of ASTRAEA's D-1 rule: the jar must DECLARE custom.tsubomi.brand.incompatible_with == ["Alpha"]
     (Tsubomi is not compatible with Alpha — the owner, 2026-09-30), since the Store reads that declaration;
  5. glimpse_manifest.json carries a "tsubomi" block for that jar and nothing else: mod_id "tsubomi", latest <ver>, the
     jar's file name, address, size and SHA-256 — and no "jars" key (check_recipe_sources keys on blocks with mod_id +
     jars, and Tsubomi's recipes are not part of this release). The Discord release bot announces from this block;
  6. changelog_feed/brands.json lists Tsubomi with its feed, and each of the 13 languages' changelog_feed/tsubomi feed
     leads with the release that the jar is: "V" + <ver> (V2.3.1024), or, for a jar version with exactly three numeric
     parts a.b.c, the owner's notation "V<a>.<b> <c>" (V2.3 1024: the same numbers, one space, no other variant). The
     site does not publish a release its changelog has not reached.

Independent by construction: it imports nothing from the builders (not site_common, not build_glimpse_manifest, not
build_changelog_feed). The language list, the site address and the file-name rule are written out again here, so a
mistake in a builder cannot make this gate agree with it.

  python3 scripts/check_tsubomi_release.py              # the gate
  python3 scripts/check_tsubomi_release.py --self-test  # the pristine tree green, every planted defect red

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
JAR_RE = re.compile(r"^tsubomi-(\d+(?:\.\d+)*)\.jar$")
SITE = "https://iroponcopin.github.io/corvus-dev"
ALLOWED_DEPENDS = {"fabricloader", "minecraft", "java", "fabric-api"}
ALLOWED_SOFT = {"cherry"}          # recommends / suggests may name Cherry, and nothing else
ALPHA_PREFIX = "sorakaze_"         # breaks / conflicts may name Alpha's modules, and nothing else
INCOMPATIBLE_WITH = ["Alpha"]
THREE_PART_RE = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)")


def release_string_ok(newest, version: str) -> bool:
    """Rule 6's test, pure: the feed's newest release string names the jar's version. Two forms and nothing looser:
    "V" + the jar version (V2.3.1024), and, when the jar version has exactly three numeric parts a.b.c, the owner's
    "V<a>.<b> <c>" (V2.3 1024). No other variant: not two spaces, not a lowercase v, not trailing text."""
    if not isinstance(newest, str):
        return False
    if newest == f"V{version}":
        return True
    three = THREE_PART_RE.fullmatch(version)
    return three is not None and newest == f"V{three.group(1)}.{three.group(2)} {three.group(3)}"


def git_tracked(root: Path, rel: str) -> bool:
    result = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root, capture_output=True, text=True)
    return result.returncode == 0


def check(root: Path, tracked=git_tracked):
    """(problems, facts). A problem is a string; an empty list is green."""
    problems = []
    downloads = root / "downloads"
    jars = sorted(p for p in downloads.glob("tsubomi-*.jar") if p.is_file())
    if not jars:
        return ["no downloads/tsubomi-<ver>.jar: nothing to check (the gate cannot pass on absence)"], {}
    if len(jars) > 1:
        return [f"more than one Tsubomi jar in downloads/ ({', '.join(j.name for j in jars)}); the manifest describes one"], {}
    jpath = jars[0]
    m = JAR_RE.match(jpath.name)
    if not m:
        return [f"downloads/{jpath.name} does not parse as tsubomi-<numeric.version>.jar"], {}
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
    if meta.get("id") != "tsubomi":
        problems.append(f"{jpath.name} declares the mod id {meta.get('id')!r}, not 'tsubomi'")
    if meta.get("version") != version:
        problems.append(f"{jpath.name} is named for {version}, but its fabric.mod.json declares {meta.get('version')!r}")
    extra = sorted(set(meta.get("depends") or {}) - ALLOWED_DEPENDS)
    if extra:
        problems.append(f"the tsubomi jar depends on {extra}: it may depend only on {sorted(ALLOWED_DEPENDS)}")
    for field in ("recommends", "suggests"):
        soft = sorted(set(meta.get(field) or {}) - ALLOWED_SOFT)
        if soft:
            problems.append(f"the tsubomi jar names {soft} under {field}: only {sorted(ALLOWED_SOFT)} may appear there")
    for field in ("breaks", "conflicts"):
        wrong = sorted(k for k in (meta.get(field) or {}) if not k.startswith(ALPHA_PREFIX))
        if wrong:
            problems.append(f"the tsubomi jar declares {field} against {wrong}: only Alpha's modules ({ALPHA_PREFIX}*) may be refused")
    declared = (((meta.get("custom") or {}).get("tsubomi") or {}).get("brand") or {}).get("incompatible_with")
    if declared != INCOMPATIBLE_WITH:
        problems.append(f"the tsubomi jar declares custom.tsubomi.brand.incompatible_with = {declared!r}, "
                        f"not {INCOMPATIBLE_WITH!r} (Tsubomi is not compatible with Alpha; the Store reads this)")
    try:
        block = json.loads((root / "glimpse_manifest.json").read_text(encoding="utf-8")).get("tsubomi")
    except (OSError, ValueError) as exc:
        return problems + [f"glimpse_manifest.json cannot be read ({exc})"], {}
    expected = {
        "mod_id": "tsubomi",
        "latest": version,
        "download_url": f"{SITE}/downloads/{jpath.name}",
        "file_name": jpath.name,
        "file_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if block is None:
        problems.append("glimpse_manifest.json has no 'tsubomi' block: the bot would announce nothing")
    elif block != expected:
        for key in expected:
            if block.get(key) != expected[key]:
                problems.append(f"glimpse_manifest.json tsubomi.{key} is {block.get(key)!r}, the jar says {expected[key]!r}")
        for key in sorted(set(block) - set(expected)):
            problems.append(f"glimpse_manifest.json tsubomi carries an unexpected key {key!r} (a bare jar's block is Aureum's shape)")
    try:
        brands = json.loads((root / "changelog_feed" / "brands.json").read_text(encoding="utf-8"))["brands"]
        entry = [b for b in brands if b.get("id") == "tsubomi"]
        if not entry or entry[0].get("feed") != "changelog_feed/tsubomi/{lang}.json":
            problems.append("changelog_feed/brands.json does not list Tsubomi with changelog_feed/tsubomi/{lang}.json")
    except (OSError, ValueError, KeyError) as exc:
        problems.append(f"changelog_feed/brands.json cannot be read ({exc})")
    for lang in LANGS:
        path = root / "changelog_feed" / "tsubomi" / f"{lang}.json"
        try:
            feed = json.loads(path.read_text(encoding="utf-8"))
            newest = feed["groups"][0]["releases"][0]["version"]
        except (OSError, ValueError, KeyError, IndexError) as exc:
            problems.append(f"changelog_feed/tsubomi/{lang}.json cannot be read for its newest release ({exc})")
            continue
        if not release_string_ok(newest, version):
            hint = ""
            three = THREE_PART_RE.fullmatch(version)
            if three:
                hint = f" or V{three.group(1)}.{three.group(2)} {three.group(3)}"
            problems.append(f"changelog_feed/tsubomi/{lang}.json leads with {newest!r}, but the site publishes V{version}{hint}")
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
    jname = sorted((ROOT / "downloads").glob("tsubomi-*.jar"))[0].name

    def copy_tree(dst: Path):
        (dst / "downloads").mkdir(parents=True)
        shutil.copy2(ROOT / "downloads" / jname, dst / "downloads" / jname)
        shutil.copy2(ROOT / "glimpse_manifest.json", dst / "glimpse_manifest.json")
        shutil.copytree(ROOT / "changelog_feed", dst / "changelog_feed")

    def rewrite_jar(dst: Path, meta_change=None, extra_inner=None, sync_manifest=True):
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
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as jar:
            for n, b in inner.items():
                jar.writestr(n, b)
        path.write_bytes(buf.getvalue())
        if sync_manifest:
            edit_manifest(dst, lambda m: m["tsubomi"].update(file_size=len(buf.getvalue()),
                                                            sha256=hashlib.sha256(buf.getvalue()).hexdigest()))

    def edit_manifest(dst: Path, change):
        p = dst / "glimpse_manifest.json"
        m = json.loads(p.read_text(encoding="utf-8"))
        change(m)
        p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def edit_feed(dst: Path, lang: str, version: str):
        p = dst / "changelog_feed" / "tsubomi" / f"{lang}.json"
        f = json.loads(p.read_text(encoding="utf-8"))
        f["groups"][0]["releases"][0]["version"] = version
        p.write_text(json.dumps(f, ensure_ascii=False), encoding="utf-8")

    def brand(meta, **kv):
        meta.setdefault("custom", {}).setdefault("tsubomi", {}).setdefault("brand", {}).update(kv)

    def second_jar(dst: Path):
        shutil.copy2(dst / "downloads" / jname, dst / "downloads" / "tsubomi-0.9.0.jar")

    plants = [
        # label, plant, tracked, should_fail
        ("clean copy", lambda d: None, True, False),
        ("Cherry as a suggestion is allowed (control)", lambda d: rewrite_jar(d, lambda m: m.update(suggests={"cherry": "*"})), True, False),
        ("the jar is untracked (the live 404)", lambda d: None, False, True),
        ("a second Tsubomi jar in downloads/", second_jar, True, True),
        ("the manifest has no tsubomi block", lambda d: edit_manifest(d, lambda m: m.pop("tsubomi")), True, True),
        ("the manifest's sha256 is stale", lambda d: edit_manifest(d, lambda m: m["tsubomi"].update(sha256="0" * 64)), True, True),
        ("the manifest's block carries 'jars' (a package's shape)",
         lambda d: edit_manifest(d, lambda m: m["tsubomi"].update(jars={"tsubomi": {"version": "1.0.0"}})), True, True),
        ("the jar is replaced after the manifest was built",
         lambda d: rewrite_jar(d, extra_inner={"extra.txt": b"x"}, sync_manifest=False), True, True),
        ("the jar declares another mod id", lambda d: rewrite_jar(d, lambda m: m.update(id="tsubomi_x")), True, True),
        ("the jar's version differs from its name", lambda d: rewrite_jar(d, lambda m: m.update(version="0.9.9")), True, True),
        ("Cherry as a hard dependency", lambda d: rewrite_jar(d, lambda m: m["depends"].update(cherry="*")), True, True),
        ("an Alpha module as a dependency", lambda d: rewrite_jar(d, lambda m: m["depends"].update(sorakaze_guns="*")), True, True),
        ("another mod suggested", lambda d: rewrite_jar(d, lambda m: m.update(suggests={"ouka": "*"})), True, True),
        ("breaks names Cherry (a false incompatibility)",
         lambda d: rewrite_jar(d, lambda m: m.setdefault("breaks", {}).update(cherry="*")), True, True),
        ("incompatible_with is missing", lambda d: rewrite_jar(d, lambda m: m["custom"]["tsubomi"]["brand"].pop("incompatible_with")), True, True),
        ("incompatible_with names the wrong brand", lambda d: rewrite_jar(d, lambda m: brand(m, incompatible_with=["Cherry"])), True, True),
        ("one language's feed lags the release", lambda d: edit_feed(d, "ar", "V0.9.0"), True, True),
        ("the owner's notation V2.3 1024 in one feed (control)", lambda d: edit_feed(d, "ja", "V2.3 1024"), True, False),
        ("the dotted form V2.3.1024 in one feed (control)", lambda d: edit_feed(d, "de", "V2.3.1024"), True, False),
        ("a wrong build in the new notation: V2.3 1023", lambda d: edit_feed(d, "en", "V2.3 1023"), True, True),
        ("the new notation with two spaces: V2.3  1024", lambda d: edit_feed(d, "fr", "V2.3  1024"), True, True),
        ("the new notation with a lowercase v: v2.3 1024", lambda d: edit_feed(d, "ko", "v2.3 1024"), True, True),
        ("the new notation with trailing text: V2.3 1024 beta", lambda d: edit_feed(d, "zh", "V2.3 1024 beta"), True, True),
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
        print(f"tsubomi release: RED ({len(problems)} problem(s))")
        return 1
    print(f"tsubomi release: {facts['jar']} ({facts['size']:,} bytes, sha256 {facts['sha256'][:16]}…) is tracked, the one "
          f"Tsubomi jar, depends on Fabric only, declares itself incompatible with Alpha, is described exactly by the "
          f"manifest's tsubomi block, and led by V{facts['version']} in all 13 feeds: GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
