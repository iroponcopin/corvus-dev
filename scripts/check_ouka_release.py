#!/usr/bin/env python3
"""Gate: /ouka/ hands out the OUKA release that is really in downloads/, in all 13 languages,
and Corvus's manifest describes that same release.

OUKA V1.0.0 (staged 2026-09-15) put a download on the brand page, as Cherry V1.0.0 did on its own
page on 2026-09-13. Nothing else on this site reads an OUKA file, so without this gate a stale hash,
a link that 404s from one language's depth, or a page still pointing at an older zip would all
publish with every other checker green. This is check_cherry_release.py's gate, written again for OUKA.

Independent by construction: it imports nothing from the builders (not site_common, not build_ouka,
not build_glimpse_manifest) and nothing from the Cherry gate. The language list, the page paths, the
site address and the size rule are written out again here, so a mistake in a builder cannot make this
gate agree with it.

Per page, in every language:
  1. the page exists and <html lang> names its language;
  2. exactly one link inside <section class="ou-release">, and its href, resolved from THIS page's
     directory, is the newest downloads/OUKA_MODs_v<ver>+mc<mc>.zip (numeric version order);
  3. the SHA-256 printed is that file's own, and so is the size (data-bytes == st_size, and the text
     follows the Download page's rule: one decimal in MB, KB below 1 MB);
  4. the version printed (V<ver>) is the file name's, and the ouka jar inside the zip says the same
     in its fabric.mod.json;
  5. no pre-release line (class "ou-soon") survives beside a release;
  6. the release line is this language's own, not the English one (the builder has no fallback;
     this catches one being added);
  7. the version, every spec value and the hash carry dir="ltr". On the Arabic page, bidi
     mirroring would otherwise print "≥" as "≤";
  8. the name, <h1 class="ou-name">, carries dir="ltr". Its letters are separate inline blocks (the
     entrance raises them one at a time), and a right-to-left page lays inline blocks out from the
     right: the Arabic page printed the name as "AKUO" until that was seen on the rendered page
     on 2026-09-15.
And once for the site:
  9. glimpse_manifest.json carries an "ouka" block for that zip: mod_id "ouka", latest <ver>, the
     zip's file name, address, size and SHA-256, and "jars" listing exactly the jars in the zip's
     mods/ — each keyed by the id its own fabric.mod.json declares, with its path, version, size and
     SHA-256. No released Corvus reads this block (2.1.0 and 2.2.0 have no field for it), but
     whatever reads it first will act on it, so a manifest built before the zip was replaced must
     not publish.

  python3 scripts/check_ouka_release.py              # the gate
  python3 scripts/check_ouka_release.py --self-test  # pristine copy green, every planted defect red

Exit code: 0 green, 1 red, 2 cannot judge (never green).
"""
import hashlib
import html
import io
import json
import re
import shutil
import sys
import tempfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["ja", "en", "es", "fr", "zh", "ko", "pt-br", "it", "ar", "ru", "id", "de", "tr"]
ZIP_RE = re.compile(r"^OUKA_MODs_v(\d+(?:\.\d+)*)\+mc(\d+(?:\.\d+)*)\.zip$")
SITE = "https://iroponcopin.github.io/corvus-dev"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
        "track", "wbr"}


def page_path(root: Path, lang: str) -> Path:
    return (root if lang == "ja" else root / lang) / "ouka" / "index.html"


def fmt_size(num_bytes: int) -> str:
    """The Download page's rule (scripts/build_download.py _fmt_size), written out again on purpose."""
    mb = num_bytes / (1024 * 1024)
    if mb >= 1:
        return f"{mb:.1f} MB"
    return f"{num_bytes / 1024:.1f} KB"


class ReleaseParser(HTMLParser):
    """Collects what the release section says, and the name's attributes. Apart from the name, only
    elements inside section.ou-release count."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.html_lang = None
        self.releases = 0
        self.soon = 0
        self.stack = []          # (tag, classes, attrs, collector-or-None)
        self.links = []
        self.names = []          # attrs of every <h1 class="ou-name">, wherever it stands
        self.values = []         # {"what", "dir", "text", "attrs"}
        self.line = []

    def _inside_release(self) -> bool:
        return any("ou-release" in classes for _t, classes, _a, _c in self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        if tag == "html":
            self.html_lang = a.get("lang")
        if "ou-soon" in classes:
            self.soon += 1
        if "ou-release" in classes:
            self.releases += 1
        if tag == "h1" and "ou-name" in classes:
            self.names.append(a)
        collector = None
        if self._inside_release() or "ou-release" in classes:
            if tag == "a":
                self.links.append(a)
            if "ou-ver" in classes:
                collector = {"what": "version", "attrs": a, "text": []}
            elif tag == "dd":
                collector = {"what": "spec", "attrs": a, "text": []}
            elif tag == "code":
                collector = {"what": "sha256", "attrs": a, "text": []}
            elif "ou-line" in classes:
                collector = {"what": "line", "attrs": a, "text": []}
            if collector is not None:
                self.values.append(collector)
        if tag not in VOID:
            self.stack.append((tag, classes, a, collector))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        for _t, _c, _a, collector in self.stack:
            if collector is not None:
                collector["text"].append(data)


def zip_jars(data: bytes) -> dict:
    """{mod id: {path, version, file_size, sha256}} for every jar in the zip's mods/, read from the jars."""
    jars = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if not info.filename.lower().endswith(".jar"):
                continue
            payload = z.read(info.filename)
            with zipfile.ZipFile(io.BytesIO(payload)) as j:
                mod = json.loads(j.read("fabric.mod.json"))
            jars[mod.get("id")] = {"path": info.filename, "version": mod.get("version"),
                                   "file_size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    return jars


def judge_manifest(root: Path, zpath: Path, ver: str, size: int, sha: str, data: bytes) -> list[str]:
    problems = []
    path = root / "glimpse_manifest.json"
    if not path.is_file():
        return ["glimpse_manifest.json: missing, so nothing can see the OUKA release"]
    try:
        block = json.loads(path.read_text(encoding="utf-8")).get("ouka")
    except ValueError as e:
        return [f"glimpse_manifest.json: not JSON ({e})"]
    if not isinstance(block, dict):
        return [f"glimpse_manifest.json: no 'ouka' block, so the manifest does not describe downloads/{zpath.name}"]
    expected = {"mod_id": "ouka", "latest": ver, "file_name": zpath.name, "file_size": size, "sha256": sha,
                "download_url": f"{SITE}/downloads/{zpath.name}"}
    for key, value in expected.items():
        if block.get(key) != value:
            problems.append(f"glimpse_manifest.json: ouka.{key} is {block.get(key)!r}, but downloads/{zpath.name} "
                            f"says {value!r}")
    try:
        jars = zip_jars(data)
    except (KeyError, zipfile.BadZipFile, json.JSONDecodeError) as e:
        return problems + [f"downloads/{zpath.name}: cannot read the jars' fabric.mod.json ({e})"]
    if block.get("jars") != jars:
        problems.append(f"glimpse_manifest.json: ouka.jars is {block.get('jars')!r}, but the jars in "
                        f"downloads/{zpath.name} are {jars!r}")
    return problems


def judge(root: Path) -> tuple[list[str], str]:
    problems = []
    downloads = root / "downloads"
    zips = []
    for p in (sorted(downloads.glob("OUKA*")) if downloads.is_dir() else []):
        m = ZIP_RE.match(p.name)
        if not m:
            problems.append(f"downloads/{p.name} starts like an OUKA release but its name does not "
                            f"parse as OUKA_MODs_v<ver>+mc<mc>.zip")
            continue
        zips.append((tuple(int(x) for x in m.group(1).split(".")), m.group(1), m.group(2), p))
    if not zips:
        problems.append("downloads/ holds no OUKA_MODs_v<ver>+mc<mc>.zip, so no page can be handing "
                        "out a real release")
        return problems, "no release"
    _key, ver, mc, zpath = max(zips)
    data = zpath.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    size = len(data)
    jar_name = f"mods/ouka-{ver}+mc{mc}.jar"
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            jar = z.read(jar_name)
        with zipfile.ZipFile(io.BytesIO(jar)) as j:
            mod = json.loads(j.read("fabric.mod.json"))
        if mod.get("id") != "ouka" or mod.get("version") != ver:
            problems.append(f"downloads/{zpath.name}: its ouka jar says id={mod.get('id')!r} "
                            f"version={mod.get('version')!r}, but the file name says {ver}")
    except (KeyError, zipfile.BadZipFile, json.JSONDecodeError) as e:
        problems.append(f"downloads/{zpath.name}: cannot read {jar_name}!/fabric.mod.json ({e})")

    lines = {}
    for lang in LANGS:
        path = page_path(root, lang)
        rel = path.relative_to(root).as_posix()
        if not path.is_file():
            problems.append(f"{rel}: missing")
            continue
        p = ReleaseParser()
        p.feed(path.read_text(encoding="utf-8"))
        if p.html_lang != lang:
            problems.append(f"{rel}: <html lang={p.html_lang!r}>, expected {lang!r}")
        if p.soon:
            problems.append(f"{rel}: the pre-release line (class ou-soon) is still on a page that "
                            f"carries a release")
        if len(p.names) != 1:
            problems.append(f"{rel}: {len(p.names)} <h1 class=\"ou-name\"> element(s); the page has one name")
        elif p.names[0].get("dir") != "ltr":
            problems.append(f"{rel}: the name <h1 class=\"ou-name\"> is not dir=\"ltr\" (dir="
                            f"{p.names[0].get('dir')!r}); its letters are separate inline blocks, so a "
                            f"right-to-left page lays them out backwards (OUKA printed as AKUO)")
        if p.releases != 1:
            problems.append(f"{rel}: {p.releases} release section(s), expected exactly 1")
            continue
        if len(p.links) != 1:
            problems.append(f"{rel}: {len(p.links)} link(s) in the release section, expected exactly 1")
        else:
            href = p.links[0].get("href") or ""
            target = (path.parent / href).resolve()
            if target != zpath.resolve():
                problems.append(f"{rel}: the download link {href!r} resolves to {target}, not the "
                                f"newest release downloads/{zpath.name}")
        found = {"version": 0, "sha256": 0, "size": 0, "line": 0}
        for v in p.values:
            text = "".join(v["text"]).strip()
            what = v["what"]
            if what == "line":
                found["line"] += 1
                lines[lang] = text
                continue
            if v["attrs"].get("dir") != "ltr":
                problems.append(f"{rel}: the {what} value {text!r} has no dir=\"ltr\" (bidi would "
                                f"reorder or mirror it on a right-to-left page)")
            if what == "version":
                found["version"] += 1
                if text != f"V{ver}":
                    problems.append(f"{rel}: prints {text!r}, the release is V{ver}")
            elif what == "sha256":
                found["sha256"] += 1
                if text != sha:
                    problems.append(f"{rel}: prints SHA-256 {text!r}, the file's is {sha}")
            elif what == "spec" and "data-bytes" in v["attrs"]:
                found["size"] += 1
                printed_bytes = v["attrs"].get("data-bytes")
                if printed_bytes != str(size) or text != fmt_size(size):
                    problems.append(f"{rel}: prints size {text!r} (data-bytes {printed_bytes}), the "
                                    f"file is {size} bytes = {fmt_size(size)!r}")
        for what, count in found.items():
            if count != 1:
                problems.append(f"{rel}: {count} {what} value(s) in the release section, expected 1")
    english = lines.get("en")
    for lang, line in sorted(lines.items()):
        if not line:
            problems.append(f"{lang}: the release line is empty")
        elif lang != "en" and line == english:
            problems.append(f"{lang}: the release line is the English one ({line!r}); every language "
                            f"carries its own copy")
    problems.extend(judge_manifest(root, zpath, ver, size, sha, data))
    return problems, f"downloads/{zpath.name}, {size:,} bytes, sha256 {sha}"


def main() -> int:
    problems, what = judge(ROOT)
    if problems:
        print(f"OUKA RELEASE PAGE = FAIL ({len(problems)})")
        for line in problems:
            print(f"  - {line}")
        return 1
    print(f"OUKA RELEASE PAGE = PASS ({len(LANGS)} pages and the Corvus manifest hand out {what})")
    return 0


# --- self-test ----------------------------------------------------------------------------------
# Controls run against a copy of the REAL rendered pages, the REAL manifest and the REAL zip, so they
# exercise what the builders actually write. Each plant must turn the gate red with ITS OWN message; a
# red that comes from some other problem proves nothing about the assertion the plant aims at.

def _fresh_copy(zips: list[Path]) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="ouka-release-gate-"))
    for lang in LANGS:
        dst = page_path(tmp, lang)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(page_path(ROOT, lang), dst)
    (tmp / "downloads").mkdir()
    for z in zips:
        shutil.copy2(z, tmp / "downloads" / z.name)
    if (ROOT / "glimpse_manifest.json").is_file():
        shutil.copy2(ROOT / "glimpse_manifest.json", tmp / "glimpse_manifest.json")
    return tmp


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"SELF-TEST = INCONCLUSIVE: the plant could not find {old[:60]!r} in "
                         f"{path.name}; the control would not reach its assertion")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _edit_manifest(root: Path, change) -> None:
    path = root / "glimpse_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("ouka"), dict):
        raise SystemExit("SELF-TEST = INCONCLUSIVE: the manifest copy has no ouka block to plant in; "
                         "the control would not reach its assertion")
    change(manifest)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _rewrite_inner_version(zpath: Path, ver: str, mc: str, new_version: str) -> None:
    src = zpath.read_bytes()
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(src)) as z, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as w:
        for info in z.infolist():
            payload = z.read(info.filename)
            if info.filename == f"mods/ouka-{ver}+mc{mc}.jar":
                jar_out = io.BytesIO()
                with zipfile.ZipFile(io.BytesIO(payload)) as j, \
                        zipfile.ZipFile(jar_out, "w", zipfile.ZIP_DEFLATED) as jw:
                    for jinfo in j.infolist():
                        jpayload = j.read(jinfo.filename)
                        if jinfo.filename == "fabric.mod.json":
                            mod = json.loads(jpayload)
                            mod["version"] = new_version
                            jpayload = json.dumps(mod).encode("utf-8")
                        jw.writestr(jinfo.filename, jpayload)
                payload = jar_out.getvalue()
            w.writestr(info.filename, payload)
    zpath.write_bytes(out.getvalue())


def self_test() -> int:
    zips = sorted((ROOT / "downloads").glob("OUKA_MODs_v*.zip"))
    pages = [page_path(ROOT, lang) for lang in LANGS]
    if not zips or not all(p.is_file() for p in pages) or not (ROOT / "glimpse_manifest.json").is_file():
        print("SELF-TEST = INCONCLUSIVE: needs the built /ouka/ pages, glimpse_manifest.json and an OUKA zip in "
              "downloads/ (run scripts/build.py first)")
        return 2
    unparsed = [z.name for z in zips if not ZIP_RE.match(z.name)]
    if unparsed:
        print(f"SELF-TEST = INCONCLUSIVE: downloads/ holds OUKA file(s) whose names do not parse "
              f"({', '.join(unparsed)}); run the gate itself, which names them")
        return 2
    newest = max(zips, key=lambda z: tuple(int(x) for x in ZIP_RE.match(z.name).group(1).split(".")))
    m = ZIP_RE.match(newest.name)
    ver, mc = m.group(1), m.group(2)
    sha = hashlib.sha256(newest.read_bytes()).hexdigest()
    size = newest.stat().st_size

    def plant_sha(t):
        _edit(page_path(t, "de"), sha, sha[:-1] + ("0" if sha[-1] != "0" else "1"))

    def plant_size(t):
        _edit(page_path(t, "fr"), f'data-bytes="{size}"', f'data-bytes="{size + 1}"')

    def plant_depth(t):
        _edit(page_path(t, "en"), f'href="../../downloads/{newest.name}"', f'href="../downloads/{newest.name}"')

    def plant_newer(t):
        shutil.copy2(newest, t / "downloads" / f"OUKA_MODs_v{ver}.9+mc{mc}.zip")

    def plant_soon(t):
        _edit(page_path(t, "ko"), '<section class="ou-release', '<p class="ou-soon">x</p><section class="ou-release')

    def plant_fallback(t):
        en = ReleaseParser()
        en.feed(page_path(t, "en").read_text(encoding="utf-8"))
        it = ReleaseParser()
        it.feed(page_path(t, "it").read_text(encoding="utf-8"))
        en_line = "".join(next(v for v in en.values if v["what"] == "line")["text"]).strip()
        it_line = "".join(next(v for v in it.values if v["what"] == "line")["text"]).strip()
        # The parser hands back unescaped text, but the page holds the line escaped: the Italian line's
        # apostrophe is &#x27; on disk. Plant against the form the file actually carries.
        on_disk = page_path(t, "it").read_text(encoding="utf-8")
        old = next((form for form in (html.escape(it_line, quote=True), it_line) if form in on_disk), it_line)
        _edit(page_path(t, "it"), old, html.escape(en_line, quote=True))

    def plant_rtl(t):
        _edit(page_path(t, "ar"), f'<code dir="ltr">{sha}</code>', f"<code>{sha}</code>")

    def plant_name_rtl(t):
        _edit(page_path(t, "ar"), '<h1 class="ou-name" dir="ltr"', '<h1 class="ou-name"')

    def plant_missing(t):
        page_path(t, "tr").unlink()

    def plant_bad_name(t):
        shutil.copy2(newest, t / "downloads" / "OUKA_MODs_latest.zip")

    def plant_inner(t):
        _rewrite_inner_version(t / "downloads" / newest.name, ver, mc, "9.9.9")

    def plant_lang(t):
        _edit(page_path(t, "id"), '<html lang="id"', '<html lang="en"')

    def plant_no_zip(t):
        for z in (t / "downloads").iterdir():
            z.unlink()

    def plant_two_links(t):
        _edit(page_path(t, "zh"), "</dl>", '</dl><a href="#">x</a>')

    def plant_manifest_sha(t):
        _edit_manifest(t, lambda d: d["ouka"].update(sha256=sha[:-1] + ("0" if sha[-1] != "0" else "1")))

    def plant_manifest_missing(t):
        _edit_manifest(t, lambda d: d.pop("ouka"))

    def plant_manifest_jar(t):
        def drop_one(d):
            jars = d["ouka"]["jars"]
            jars.pop(next(k for k in jars if k != "ouka"))
        _edit_manifest(t, drop_one)

    plants = [
        ("hash of another file", plant_sha, "prints SHA-256"),
        ("size off by one byte", plant_size, "prints size"),
        ("link written for the wrong depth", plant_depth, "resolves to"),
        ("a newer zip the page does not link", plant_newer, "not the newest release"),
        ("pre-release line left beside the release", plant_soon, "pre-release line"),
        ("English line as a fallback", plant_fallback, "the English one"),
        ("hash without dir=ltr on the Arabic page", plant_rtl, 'no dir="ltr"'),
        ("name without dir=ltr on the Arabic page", plant_name_rtl, 'the name <h1 class="ou-name"> is not'),
        ("a language page missing", plant_missing, "tr/ouka/index.html: missing"),
        ("an unparseable OUKA file name", plant_bad_name, "does not parse"),
        ("zip whose jar names another version", plant_inner, "its ouka jar says"),
        ("wrong <html lang>", plant_lang, "<html lang="),
        ("no zip at all", plant_no_zip, "holds no OUKA"),
        ("a second link in the release section", plant_two_links, "expected exactly 1"),
        ("manifest hash of another file", plant_manifest_sha, "ouka.sha256 is"),
        ("manifest without the ouka block", plant_manifest_missing, "no 'ouka' block"),
        ("manifest jars missing the bundled dependency", plant_manifest_jar, "ouka.jars is"),
    ]

    ok = True
    pristine = _fresh_copy(zips)
    problems, what = judge(pristine)
    shutil.rmtree(pristine, ignore_errors=True)
    if problems:
        print("  self-test [FAIL] pristine copy is red:")
        for line in problems:
            print(f"      {line}")
        ok = False
    else:
        print(f"  self-test [ok] pristine copy green ({what})")
    for name, plant, needle in plants:
        t = _fresh_copy(zips)
        try:
            plant(t)
            problems, _ = judge(t)
        finally:
            shutil.rmtree(t, ignore_errors=True)
        hit = [line for line in problems if needle in line]
        if hit:
            print(f"  self-test [ok] {name}: red ({hit[0][:110]})")
        else:
            ok = False
            print(f"  self-test [FAIL] {name}: expected a red containing {needle!r}, got {problems!r}")
    print("SELF-TEST VERDICT: " + ("PASS (pristine copy green, every planted defect red with its own message)"
                                   if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        sys.exit(self_test())
    sys.exit(main())
