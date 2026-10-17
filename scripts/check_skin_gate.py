#!/usr/bin/env python3
"""Gate: the sealed skin really is the shipped skin, and the PIN is nowhere in the repo.

Three claims, each of which can fail on its own:

  1. The blob in downloads/ decrypts, with the PIN from $CORVUS_SKIN_PIN, to a
     png whose sha256 matches data/skin_gate.json AND matches the skin the
     game actually ships. A stale blob (skin changed, seal not re-run) fails
     here — that is the whole reason the manifest carries the plaintext hash.
  2. A wrong PIN is refused. Without this, a broken tag check would pass (1)
     and hand the file to anyone.
  3. The PIN appears in no committed file. This is the claim the owner asked
     for in as many words: 「PIN CODEはウェブサイト等には一切記載せず」.

Without $CORVUS_SKIN_PIN this check is RED, not skipped. A gate nobody can run
is not a gate — and this one guards the one thing in the repository that must
never be committed.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skin_crypt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "skin_gate.json"
SKIN_SOURCE = (ROOT.parent / "mods-src" / "sorakaze-planarcadia" / "src" / "main"
               / "resources" / "assets" / "sorakaze_planarcadia" / "textures"
               / "entity" / "sparxie.png")
ENV_PIN = "CORVUS_SKIN_PIN"


def main() -> int:
    problems = []
    pin = os.environ.get(ENV_PIN, "")
    if not pin:
        print("SKIN GATE = FAIL (1)")
        print(f"  - {ENV_PIN} is not set, so none of this check's three claims can be made.")
        print(f"    Run it as:  {ENV_PIN}=**** python3 scripts/check_skin_gate.py")
        print("    The PIN is held by the owner and is never committed.")
        return 1
    if not MANIFEST.exists():
        print("SKIN GATE = FAIL (1)")
        print(f"  - {MANIFEST} is missing; run scripts/build_skin_gate.py")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    blob_path = ROOT / manifest["blob"]
    if not blob_path.exists():
        print("SKIN GATE = FAIL (1)")
        print(f"  - the sealed blob is missing: {blob_path}")
        return 1

    blob = blob_path.read_bytes()

    # 1. decrypts to the shipped skin
    try:
        plain = skin_crypt.open_sealed(blob, pin)
    except ValueError as error:
        plain = b""
        problems.append(f"the blob does not open with {ENV_PIN}: {error}")
    if plain:
        got = hashlib.sha256(plain).hexdigest()
        if got != manifest["plain_sha256"]:
            problems.append(f"the blob decrypts to {got} but the manifest says "
                            f"{manifest['plain_sha256']}")
        if SKIN_SOURCE.exists():
            live = hashlib.sha256(SKIN_SOURCE.read_bytes()).hexdigest()
            if live != got:
                problems.append(
                    f"the sealed skin ({got}) is NOT the skin the game ships ({live}). "
                    f"Re-seal it: {ENV_PIN}=**** python3 scripts/build_skin_gate.py")
        else:
            problems.append(f"the in-game skin is missing, so 'same file' cannot be checked: "
                            f"{SKIN_SOURCE}")

    # 2. a wrong PIN is refused
    wrong = "0" * len(pin) if pin != "0" * len(pin) else "1" * len(pin)
    try:
        skin_crypt.open_sealed(blob, wrong)
        problems.append("a WRONG pin opened the blob — the tag check is not working")
    except ValueError:
        pass

    # 3. the PIN is in no committed TEXT file.
    #
    # `-I` skips binaries. Without it this claim is drowned by false positives:
    # the four bytes of a PIN occur by chance inside every shipped ZIP and MSI
    # in downloads/ (measured: 9 of them on the first run). Those are not the
    # PIN being written down — they are compressed bytes. A check that cries
    # wolf on every release artefact is a check nobody will read.
    try:
        hit = subprocess.run(["git", "grep", "-I", "-l", "--", pin], cwd=ROOT,
                             capture_output=True, text=True)
        if hit.returncode == 0 and hit.stdout.strip():
            for line in hit.stdout.strip().splitlines():
                problems.append(f"the PIN appears in a committed text file: {line}")
        # Non-empty guard: the search must be able to find something, or the
        # zero above means "grep is broken", not "the PIN is absent".
        probe = subprocess.run(["git", "grep", "-I", "-l", "--", "CORVUS_SKIN_PIN"], cwd=ROOT,
                               capture_output=True, text=True)
        if probe.returncode != 0 or not probe.stdout.strip():
            problems.append("git grep found no file containing 'CORVUS_SKIN_PIN' — the search "
                            "itself is not working, so 'the PIN is absent' proves nothing")
    except OSError as error:
        problems.append(f"could not run git grep to look for the PIN: {error}")

    if problems:
        print("SKIN GATE = FAIL (%d)" % len(problems))
        for problem in problems:
            print("  - " + problem)
        return 1
    print(f"SKIN GATE = PASS (blob {len(blob):,} B opens to the shipped {len(plain):,} B skin, "
          f"a wrong PIN is refused, the PIN is in 0 committed files, "
          f"{manifest['iterations']:,} PBKDF2 iterations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
