#!/usr/bin/env python3
"""Gate: the ASTRAEA release the site publishes is the zip really in downloads/, the manifest describes that zip, and
the zip is ASTRAEA alone.

ASTRAEA V1.0.0 (2026-09-30) is the first brand released after the 3D portal became the site, so the page half of the
Cherry and OUKA gates (a link, a size and a hash printed on /cherry/ and /ouka/) is the portal's own gates' job now, and
those two gates are retired at the portal (check_site.RETIRED_AT_PORTAL). What stays true in the portal era, and what no
other checker here reads for ASTRAEA, is checked here — a live gate, not a retired one:

  1. exactly one downloads/ASTRAEA_MODs_v<ver>+mc<mc>.zip, and it is TRACKED by git: an untracked zip builds a manifest
     and a Store card whose download 404s on the live site (three sessions nearly shipped that on 2026-09-15);
  2. its mods/ holds exactly one jar, and that jar's own fabric.mod.json says id "astraea" and the zip name's version;
  3. that jar depends on nothing but fabricloader, minecraft, java, fabric-api and (since V1.5.2) ouka, and names no other mod in
     recommends / suggests / breaks / conflicts (since V1.1.0 it may suggest "ouka", its optional power partner, and
     only that): ASTRAEA bundles nothing and has no compatibility with Alpha (the
     owner's decision D-1). No entry of the zip or of the jar is named after Alpha's modules ("sorakaze");
  4. glimpse_manifest.json carries an "astraea" block for that zip: mod_id "astraea", latest <ver>, the zip's file name,
     address, size and SHA-256, and "jars" exactly {astraea: {path, version, file_size, sha256}} read from the zip. The
     Discord release bot announces from this block, and the Store installs from it;
  5. changelog_feed/brands.json lists ASTRAEA with its feed, and each of the 13 languages' changelog_feed/astraea feed
     leads with V<ver>: the site does not publish a release its changelog has not reached.
  6. Since 2026-10-16 (ASTRAEA's service ended, owner's instruction) data/retirement.json's "astraea" block says so, and
     the manifest's astraea block carries exactly one more key, "retired" = {date, remove_after, notice_url}, derived
     from that block (notice_url is the site's /astraea/ page). Its "last_version" must be the ZIP's version. The ZIP
     itself is still described exactly as in rule 4: the notice changes what the site offers, never what the zip is.

Independent by construction: it imports nothing from the builders (not site_common, not build_glimpse_manifest, not
build_changelog_feed). The language list, the site address and the file-name rule are written out again here, so a
mistake in a builder cannot make this gate agree with it.

  python3 scripts/check_astraea_release.py              # the gate
  python3 scripts/check_astraea_release.py --self-test  # the pristine tree green, every planted defect red

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
ZIP_RE = re.compile(r"^ASTRAEA_MODs_v(\d+(?:\.\d+)*)\+mc(\d+(?:\.\d+)*)\.zip$")
SITE = "https://iroponcopin.github.io/aurora-corvus"
# Since V1.5.2 (2026-10-13) ASTRAEA needs OUKA 1.4.0: its rebuilt machines run on OUKA's grid and nowhere else (the owner,
# 2026-10-11: native to OUKA's power system). Depending on a mod is not bundling it: the zip must still hold ASTRAEA's jar
# alone (rule 2), and it may depend on nothing else.
ALLOWED_DEPENDS = {"fabricloader", "minecraft", "java", "fabric-api", "ouka"}
ALLOWED_SUGGESTS = {"ouka"}
RETIREMENT_FILE = ("data", "retirement.json")


def git_tracked(root: Path, rel: str) -> bool:
    result = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root, capture_output=True, text=True)
    return result.returncode == 0


def check(root: Path, tracked=git_tracked):
    """(problems, facts). A problem is a string; an empty list is green."""
    problems = []
    downloads = root / "downloads"
    zips = sorted(p for p in downloads.glob("ASTRAEA_MODs_v*.zip") if ZIP_RE.match(p.name))
    if not zips:
        return ["no downloads/ASTRAEA_MODs_v<ver>+mc<mc>.zip: nothing to check (the gate cannot pass on absence)"], {}
    if len(zips) > 1:
        return [f"more than one ASTRAEA zip in downloads/ ({', '.join(z.name for z in zips)}); the manifest describes one"], {}
    zpath = zips[0]
    version = ZIP_RE.match(zpath.name).group(1)
    rel = f"downloads/{zpath.name}"
    if not tracked(root, rel):
        problems.append(f"{rel} is not tracked by git: the live site would serve a 404 for it")
    data = zpath.read_bytes()
    jars = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if "sorakaze" in info.filename.lower():
                    problems.append(f"{zpath.name} carries {info.filename}, named after Alpha's modules (D-1)")
                if not info.filename.lower().endswith(".jar"):
                    continue
                if not info.filename.startswith("mods/") or info.filename.count("/") != 1:
                    problems.append(f"{zpath.name} carries a jar outside mods/: {info.filename}")
                    continue
                blob = zf.read(info)
                with zipfile.ZipFile(io.BytesIO(blob)) as jar:
                    for inner in jar.namelist():
                        if "sorakaze" in inner.lower():
                            problems.append(f"{info.filename} carries {inner}, named after Alpha's modules (D-1)")
                    meta = json.loads(jar.read("fabric.mod.json").decode("utf-8"))
                jars[meta.get("id")] = {"path": info.filename, "version": meta.get("version"), "file_size": info.file_size,
                                        "sha256": hashlib.sha256(blob).hexdigest(), "_meta": meta}
    except (zipfile.BadZipFile, KeyError, ValueError) as exc:
        return problems + [f"{zpath.name} cannot be read as a release ({exc})"], {}
    if sorted(jars) != ["astraea"]:
        problems.append(f"{zpath.name}'s mods/ holds {sorted(jars) or 'no jar'}; ASTRAEA ships exactly one jar, its own")
    own = jars.get("astraea")
    if own:
        if own["version"] != version:
            problems.append(f"{zpath.name} is named for {version}, but its jar declares {own['version']}")
        meta = own["_meta"]
        extra = sorted(set(meta.get("depends") or {}) - ALLOWED_DEPENDS)
        if extra:
            problems.append(f"the astraea jar depends on {extra}: it may depend only on {sorted(ALLOWED_DEPENDS)} (D-1, no bundled mod)")
        for field in ("recommends", "suggests", "breaks", "conflicts"):
            # V1.1.0 (2026-10-04): OUKA is an optional partner — it powers the security devices when installed, and
            # ASTRAEA runs without it — so the jar may suggest "ouka" and nothing else (and never depend on it).
            named = {k: v for k, v in (meta.get(field) or {}).items() if not (field == "suggests" and k in ALLOWED_SUGGESTS)}
            if named:
                problems.append(f"the astraea jar's fabric.mod.json names other mods under {field}: {named}")
    manifest_path = root / "glimpse_manifest.json"
    try:
        block = json.loads(manifest_path.read_text(encoding="utf-8")).get("astraea")
    except (OSError, ValueError) as exc:
        return problems + [f"glimpse_manifest.json cannot be read ({exc})"], {}
    expected_jars = {k: {x: v[x] for x in ("path", "version", "file_size", "sha256")} for k, v in jars.items()}
    expected = {
        "mod_id": "astraea",
        "latest": version,
        "download_url": f"{SITE}/downloads/{zpath.name}",
        "file_name": zpath.name,
        "file_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "jars": expected_jars,
    }
    try:
        ended = (json.loads((root.joinpath(*RETIREMENT_FILE)).read_text(encoding="utf-8")).get("astraea") or {})
    except (OSError, ValueError) as exc:
        return problems + [f"data/retirement.json cannot be read ({exc})"], {}
    if ended.get("retired"):
        if ended.get("last_version") != version:
            problems.append(f"data/retirement.json says ASTRAEA ended at {ended.get('last_version')!r}, the ZIP is {version}")
        expected["retired"] = {"date": ended.get("date"), "remove_after": ended.get("remove_after"),
                               "notice_url": f"{SITE}/astraea/"}
    if block is None:
        problems.append("glimpse_manifest.json has no 'astraea' block: the bot would announce nothing and the Store offer nothing")
    elif block != expected:
        for key in expected:
            if block.get(key) != expected[key]:
                problems.append(f"glimpse_manifest.json astraea.{key} is {block.get(key)!r}, the zip says {expected[key]!r}")
        for key in sorted(set(block) - set(expected)):
            problems.append(f"glimpse_manifest.json astraea carries an unexpected key {key!r}")
    try:
        brands = json.loads((root / "changelog_feed" / "brands.json").read_text(encoding="utf-8"))["brands"]
        entry = [b for b in brands if b.get("id") == "astraea"]
        if not entry or entry[0].get("feed") != "changelog_feed/astraea/{lang}.json":
            problems.append("changelog_feed/brands.json does not list ASTRAEA with changelog_feed/astraea/{lang}.json")
    except (OSError, ValueError, KeyError) as exc:
        problems.append(f"changelog_feed/brands.json cannot be read ({exc})")
    for lang in LANGS:
        path = root / "changelog_feed" / "astraea" / f"{lang}.json"
        try:
            feed = json.loads(path.read_text(encoding="utf-8"))
            newest = feed["groups"][0]["releases"][0]["version"]
        except (OSError, ValueError, KeyError, IndexError) as exc:
            problems.append(f"changelog_feed/astraea/{lang}.json cannot be read for its newest release ({exc})")
            continue
        if newest != f"V{version}":
            problems.append(f"changelog_feed/astraea/{lang}.json leads with {newest}, but the site publishes V{version}")
    return problems, {"zip": zpath.name, "version": version, "size": len(data), "sha256": expected["sha256"]}


# --- self-test ----------------------------------------------------------------------------------

def self_test() -> int:
    """The pristine tree must be green; then each plant, in its own copy, must turn it red."""
    base, _ = check(ROOT)
    if base:
        print("SELF-TEST CANNOT JUDGE: the pristine tree is not green, so a red plant would prove nothing:")
        for p in base:
            print("  " + p)
        return 2
    zips = sorted((ROOT / "downloads").glob("ASTRAEA_MODs_v*.zip"))
    zname = zips[0].name

    def copy_tree(dst: Path):
        (dst / "downloads").mkdir(parents=True)
        shutil.copy2(ROOT / "downloads" / zname, dst / "downloads" / zname)
        shutil.copy2(ROOT / "glimpse_manifest.json", dst / "glimpse_manifest.json")
        shutil.copytree(ROOT / "changelog_feed", dst / "changelog_feed")
        (dst / "data").mkdir()
        shutil.copy2(ROOT / "data" / "retirement.json", dst / "data" / "retirement.json")

    def rewrite_zip(path: Path, change):
        """Rebuild the zip with change(entries) applied to {name: bytes}; entries of the jar under '<jar>!<inner>'."""
        with zipfile.ZipFile(path) as zf:
            entries = {n: zf.read(n) for n in zf.namelist()}
        change(entries)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for n, b in entries.items():
                zf.writestr(n, b)
        path.write_bytes(buf.getvalue())

    def jar_with(meta_change=None, extra_inner=None):
        def change(entries):
            jar_name = next(n for n in entries if n.endswith(".jar"))
            with zipfile.ZipFile(io.BytesIO(entries[jar_name])) as jar:
                inner = {n: jar.read(n) for n in jar.namelist()}
            if meta_change:
                meta = json.loads(inner["fabric.mod.json"])
                meta_change(meta)
                inner["fabric.mod.json"] = json.dumps(meta).encode()
            if extra_inner:
                inner.update(extra_inner)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as jar:
                for n, b in inner.items():
                    jar.writestr(n, b)
            entries[jar_name] = buf.getvalue()
        return change

    def edit_manifest(dst: Path, change):
        p = dst / "glimpse_manifest.json"
        m = json.loads(p.read_text(encoding="utf-8"))
        change(m)
        p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def edit_feed(dst: Path, lang: str, version: str):
        p = dst / "changelog_feed" / "astraea" / f"{lang}.json"
        f = json.loads(p.read_text(encoding="utf-8"))
        f["groups"][0]["releases"][0]["version"] = version
        p.write_text(json.dumps(f, ensure_ascii=False), encoding="utf-8")

    plants = [
        ("clean copy", lambda d: None, True, False),
        ("the zip is untracked (the live 404)", lambda d: None, False, True),
        ("the manifest has no astraea block", lambda d: edit_manifest(d, lambda m: m.pop("astraea")), True, True),
        ("the manifest's sha256 is stale", lambda d: edit_manifest(d, lambda m: m["astraea"].update(sha256="0" * 64)), True, True),
        ("the manifest's jars miss a field", lambda d: edit_manifest(d, lambda m: m["astraea"]["jars"]["astraea"].pop("sha256")), True, True),
        ("the zip is replaced after the manifest was built",
         lambda d: rewrite_zip(d / "downloads" / zname, lambda e: e.update({"README.txt": e["README.txt"] + b" "})), True, True),
        ("a second jar is bundled", lambda d: rewrite_zip(d / "downloads" / zname, lambda e: e.update({"mods/other.jar": _tiny_jar("other")})), True, True),
        ("an Alpha dependency (D-1)",
         lambda d: rewrite_zip(d / "downloads" / zname, jar_with(lambda m: m["depends"].update(sorakaze_guns="*"))), True, True),
        ("an Alpha-named entry in the jar (D-1)",
         lambda d: rewrite_zip(d / "downloads" / zname, jar_with(extra_inner={"assets/sorakaze_guns/x.json": b"{}"})), True, True),
        ("a declared compatibility (suggests)",
         lambda d: rewrite_zip(d / "downloads" / zname, jar_with(lambda m: m.update(suggests={"cherry": "*"}))), True, True),
        ("the jar's version differs from the zip's name",
         lambda d: rewrite_zip(d / "downloads" / zname, jar_with(lambda m: m.update(version="0.9.9"))), True, True),
        ("one language's feed lags the release", lambda d: edit_feed(d, "ar", "V0.9.0"), True, True),
        ("the retirement is announced but the manifest lost its retired block (the notice does not reach the Store)",
         lambda d: edit_manifest(d, lambda m: m["astraea"].pop("retired")), True, True),
        ("the manifest's retired.remove_after differs from data/retirement.json",
         lambda d: edit_manifest(d, lambda m: m["astraea"]["retired"].update(remove_after="2026-10-30")), True, True),
        ("the retirement names another last version than the ZIP",
         lambda d: _edit_json(d / "data" / "retirement.json", lambda r: r["astraea"].update(last_version="1.5.3")), True, True),
    ]
    ok = True
    for label, plant, is_tracked, should_fail in plants:
        with tempfile.TemporaryDirectory() as temp:
            dst = Path(temp)
            copy_tree(dst)
            plant(dst)
            failed = bool(check(dst, tracked=lambda _r, _p, t=is_tracked: t)[0])
        right = failed == should_fail
        ok &= right
        print(f"  self-test [{'ok' if right else 'WRONG'}] {label}: {'red' if failed else 'green'}")
    print("SELF-TEST VERDICT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def _edit_json(path: Path, change):
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _tiny_jar(mod_id: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as jar:
        jar.writestr("fabric.mod.json", json.dumps({"id": mod_id, "version": "1.0.0"}))
    return buf.getvalue()


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    problems, facts = check(ROOT)
    for p in problems:
        print("  RED: " + p)
    if problems:
        print(f"astraea release: RED ({len(problems)} problem(s))")
        return 1
    print(f"astraea release: {facts['zip']} ({facts['size']:,} bytes, sha256 {facts['sha256'][:16]}…) is tracked, one jar, "
          f"no Alpha, described exactly by the manifest's astraea block, and led by V{facts['version']} in all 13 feeds: GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
