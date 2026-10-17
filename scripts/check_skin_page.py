#!/usr/bin/env python3
"""Gate: the sealed skin page is present, wired and NOT stale — without the PIN.

This is the half of the skin gate that needs no secret, so it can live in
scripts/check_site.py and run on every audit:

  * every language has a /skin/ page, and each one points at the blob with a
    path that actually resolves from that page's depth (the ja/non-ja prefix
    trap that has broken this site's scripts before);
  * the blob exists, starts with the ACSK1 magic, and its declared plaintext
    length matches its payload;
  * data/skin_gate.json's plaintext sha256 IS the sha256 of the skin the game
    ships — i.e. the page is handing out the current picture;
  * no page contains a four-or-more digit run inside the gate markup, so a
    future edit cannot quietly write the PIN into the HTML.

The claims that DO need the PIN (it decrypts; a wrong PIN is refused; the PIN
is in no committed file) live in scripts/check_skin_gate.py, which is run by
hand at release time with CORVUS_SKIN_PIN set.
"""
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "skin_gate.json"
SKIN_SOURCE = (ROOT.parent / "mods-src" / "sorakaze-planarcadia" / "src" / "main"
               / "resources" / "assets" / "sorakaze_planarcadia" / "textures"
               / "entity" / "sparxie.png")
MAGIC = b"ACSK1"

LANGS = ["ja", "en", "de", "es", "fr", "it", "pt-br", "ru", "tr", "ar", "id", "ko", "zh"]

DIGITS = re.compile(r'data-(?:salt|iterations|sha256)="[^"]*"')


def page_path(lang: str) -> Path:
    return (ROOT if lang == "ja" else ROOT / lang) / "skin" / "index.html"


def main() -> int:
    problems = []
    if not MANIFEST.exists():
        print("SKIN PAGE = FAIL (1)")
        print(f"  - {MANIFEST.relative_to(ROOT)} is missing; run scripts/build_skin_gate.py")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    blob_path = ROOT / manifest["blob"]

    if not blob_path.exists():
        problems.append(f"the sealed blob is missing: {manifest['blob']}")
    else:
        blob = blob_path.read_bytes()
        if not blob.startswith(MAGIC):
            problems.append(f"{manifest['blob']} does not start with {MAGIC!r}")
        else:
            at = len(MAGIC) + 16 + 4
            declared = struct.unpack(">I", blob[at:at + 4])[0]
            payload = len(blob) - (at + 4 + 32)
            if declared != payload:
                problems.append(f"the blob says {declared} plaintext bytes but carries "
                                f"{payload} bytes of ciphertext")
            if declared != manifest["plain_bytes"]:
                problems.append(f"the blob says {declared} plaintext bytes, the manifest says "
                                f"{manifest['plain_bytes']}")

    if not SKIN_SOURCE.exists():
        problems.append(f"the in-game skin is missing, so staleness cannot be judged: "
                        f"{SKIN_SOURCE}")
    else:
        live = hashlib.sha256(SKIN_SOURCE.read_bytes()).hexdigest()
        if live != manifest["plain_sha256"]:
            problems.append(
                f"STALE: the game ships a skin of {live} but the site's sealed blob is of "
                f"{manifest['plain_sha256']}. Re-seal with "
                f"CORVUS_SKIN_PIN=**** python3 scripts/build_skin_gate.py")

    pages = 0
    for lang in LANGS:
        path = page_path(lang)
        if not path.exists():
            problems.append(f"{lang}: no /skin/ page at {path.relative_to(ROOT)}")
            continue
        pages += 1
        html = path.read_text(encoding="utf-8")
        marker = f'data-blob="'
        if marker not in html:
            problems.append(f"{lang}: the skin page carries no data-blob attribute")
            continue
        href = html.split(marker, 1)[1].split('"', 1)[0]
        # Resolve it the way a browser would, from the page's own directory.
        resolved = (path.parent / href).resolve()
        if not resolved.exists():
            problems.append(f"{lang}: data-blob={href!r} resolves to {resolved}, which does "
                            f"not exist (the ja/non-ja depth prefix is wrong)")
        # The PIN must never be written into the markup. The only digit runs
        # allowed in the gate block are the declared salt/iterations/sha256.
        block = html.split('id="skin-gate"', 1)[1].split("</section>", 1)[0]
        stripped = DIGITS.sub("", block)
        stray = re.findall(r"\b\d{4,}\b", stripped)
        if stray:
            problems.append(f"{lang}: the skin gate markup contains bare digit run(s) {stray} — "
                            f"the PIN must never be written into the page")

    if pages == 0:
        problems.append("no /skin/ page was found in any language — this check is vacuous")

    if problems:
        print("SKIN PAGE = FAIL (%d)" % len(problems))
        for problem in problems:
            print("  - " + problem)
        return 1
    print(f"SKIN PAGE = PASS ({pages} language(s), blob {blob_path.stat().st_size:,} B is the "
          f"skin the game ships, no digit run in the gate markup)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
