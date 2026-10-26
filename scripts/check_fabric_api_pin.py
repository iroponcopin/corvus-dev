#!/usr/bin/env python3
"""門（オフライン）: Fabric API (Modrinth P7dR8mSH) is pinned, never hosted, and the manifest says so.

Fabric API is a third-party Fabric mod (Apache-2.0, per Modrinth). This site does not host it: the Corvus Store
downloads it from the Modrinth CDN when a mod that needs it is installed and Fabric API is missing. This gate
proves, with no network, that:

  1. data/fabric_api.json has every field of the pin, sha256 is 64 lowercase hex, sha512 is 128, file_size is a
     positive integer.
  2. download_url is https on cdn.modrinth.com, its path names the pinned Modrinth version id, and once
     percent-decoding is accounted for (the API writes "+" as %2B) it ends with the pinned file name.
  3. hosted_by_corvus is false; mod id is "fabric-api"; licence is "Apache-2.0"; project_url is https on modrinth.com.
  4. NO Fabric API jar is anywhere under the repository tree (outside .git and node_modules): none named
     fabric-api*.jar, none whose TOP-LEVEL fabric.mod.json declares id "fabric-api" (nested jars are not opened),
     and no file whose size equals the pinned size and whose SHA-256 equals the pinned one (a renamed copy is a copy).
  5. glimpse_manifest.json has a top-level "fabric_api" block that equals the pin's block fields exactly, and the
     builder's own function (build_glimpse_manifest.fabric_api_block_from_pin) produces that same block.

What this gate does NOT do: it does not download anything (scripts/pin_fabric_api.py --check asks Modrinth, by
hand), and it does not check that the Modrinth CDN still serves the file (check_published_artefacts.py does that,
live, and hashes the bytes in memory).

使い方:
    python3 scripts/check_fabric_api_pin.py
    python3 scripts/check_fabric_api_pin.py --self-test   # plants each defect; every one must turn it RED
"""
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

BLOCK_KEYS = ("mod_id", "latest", "download_url", "file_name", "file_size", "sha256", "sha512",
              "source", "project_url", "license", "hosted_by_corvus")
PIN_KEYS = BLOCK_KEYS + ("name", "schema", "minecraft", "loader", "side", "requires",
                         "modrinth_project_id", "modrinth_version_id", "redistribution")
PRUNE = {".git", "node_modules", ".next"}
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX128 = re.compile(r"[0-9a-f]{128}")
MOD_ID = "fabric-api"
LICENCE = "Apache-2.0"


def _load_pin(root):
    path = Path(root) / "data" / "fabric_api.json"
    if not path.is_file():
        raise ValueError("data/fabric_api.json is missing")
    return json.loads(path.read_text(encoding="utf-8"))


def pin_problems(pin):
    problems = []
    for key in PIN_KEYS:
        if key not in pin or pin[key] in (None, ""):
            problems.append(f"data/fabric_api.json: '{key}' is missing or empty")
    if problems:
        return problems
    if not HEX64.fullmatch(str(pin["sha256"])):
        problems.append(f"data/fabric_api.json: sha256 {pin['sha256']!r} is not 64 lowercase hex digits")
    if not HEX128.fullmatch(str(pin["sha512"])):
        problems.append("data/fabric_api.json: sha512 is not 128 lowercase hex digits")
    size = pin["file_size"]
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        problems.append(f"data/fabric_api.json: file_size {size!r} is not a positive integer")
    url = pin["download_url"]
    parts = urlsplit(url) if isinstance(url, str) else None
    if parts is None or parts.scheme != "https":
        problems.append(f"data/fabric_api.json: download_url {url!r} is not https")
    elif parts.hostname != "cdn.modrinth.com":
        problems.append(f"data/fabric_api.json: download_url host is {parts.hostname!r}, must be cdn.modrinth.com")
    else:
        decoded_path = unquote(parts.path)
        if f"/versions/{pin['modrinth_version_id']}/" not in decoded_path:
            problems.append(f"data/fabric_api.json: download_url path does not name Modrinth version {pin['modrinth_version_id']}")
        if not decoded_path.endswith("/" + pin["file_name"]):
            problems.append(f"data/fabric_api.json: download_url does not end with the file name {pin['file_name']} "
                            f"(percent-decoded)")
        if f"/data/{pin['modrinth_project_id']}/" not in decoded_path:
            problems.append("data/fabric_api.json: download_url does not name the Modrinth project id")
    if pin.get("hosted_by_corvus") is not False:
        problems.append("data/fabric_api.json: hosted_by_corvus must be false")
    if pin.get("mod_id") != MOD_ID:
        problems.append(f"data/fabric_api.json: mod_id is {pin.get('mod_id')!r}, not '{MOD_ID}'")
    if pin.get("license") != LICENCE:
        problems.append(f"data/fabric_api.json: license is {pin.get('license')!r}; Modrinth reports {LICENCE}")
    purl = urlsplit(str(pin.get("project_url", "")))
    if purl.scheme != "https" or purl.hostname != "modrinth.com":
        problems.append(f"data/fabric_api.json: project_url {pin.get('project_url')!r} is not https on modrinth.com")
    return problems


def _is_fabric_api_jar(path):
    """Reads only the TOP-LEVEL fabric.mod.json. Fabric API nests other jars; those are not opened here."""
    try:
        with zipfile.ZipFile(path) as zf:
            meta = json.loads(zf.read("fabric.mod.json").decode("utf-8"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        return False
    return meta.get("id") == MOD_ID


def tree_problems(root, pin):
    """No Fabric API jar anywhere in the tree. Walks everything; hashes only files of exactly the pinned size."""
    problems = []
    want_size, want_sha = pin.get("file_size"), str(pin.get("sha256", ""))
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in PRUNE]
        for name in files:
            path = Path(base) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                continue
            low = name.lower()
            if low.startswith("fabric-api") and low.endswith(".jar"):
                problems.append(f"{rel}: a Fabric API jar is in the repository. It is pinned, never hosted.")
                continue
            if low.endswith(".jar") and _is_fabric_api_jar(path):
                problems.append(f"{rel}: this jar declares the mod id 'fabric-api'. It must not be in the repository.")
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size == want_size and want_size:
                if hashlib.sha256(path.read_bytes()).hexdigest() == want_sha:
                    problems.append(f"{rel}: a copy of the pinned Fabric API jar (same SHA-256), whatever its name.")
    return problems


def manifest_problems(root, pin):
    path = Path(root) / "glimpse_manifest.json"
    if not path.is_file():
        return ["glimpse_manifest.json is missing"]
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"glimpse_manifest.json is not JSON ({exc})"]
    if "fabric_api" not in manifest:
        return ["glimpse_manifest.json has no 'fabric_api' block, so the Store cannot fetch Fabric API (run build.py --feeds)"]
    block = manifest["fabric_api"]
    want = {k: pin.get(k) for k in BLOCK_KEYS}
    problems = []
    if not isinstance(block, dict) or set(block) != set(BLOCK_KEYS):
        problems.append(f"glimpse_manifest.json: 'fabric_api' must hold exactly {sorted(BLOCK_KEYS)}, has {sorted(block) if isinstance(block, dict) else block!r}")
    for key in BLOCK_KEYS:
        if isinstance(block, dict) and block.get(key) != want[key]:
            problems.append(f"glimpse_manifest.json: fabric_api.{key} is {block.get(key)!r}, the pin says {want[key]!r}")
    return problems


def builder_problems(pin):
    """The builder's own function must produce the same block from the same pin (imported, not re-typed here)."""
    try:
        import build_glimpse_manifest as bgm
    except SystemExit as exc:
        return [f"could not import the builder: {exc}"]
    try:
        built = bgm.fabric_api_block_from_pin(pin)
    except SystemExit as exc:
        return [f"the builder refuses the pin: {exc}"]
    want = {k: pin.get(k) for k in BLOCK_KEYS}
    return [] if built == want else [f"fabric_api_block_from_pin() gives {built!r}, not the pin's block fields"]


def run_all(root):
    """Returns (checks, fatal): each check is (label, [problems])."""
    root = Path(root)
    try:
        pin = _load_pin(root)
    except (OSError, ValueError) as exc:
        return [("pin", [f"data/fabric_api.json: {exc}"])], True
    checks = [
        ("1-3 pin fields, hosting, licence and URL", pin_problems(pin)),
        ("4 no Fabric API jar in the tree", tree_problems(root, pin)),
        ("5 manifest block equals the pin", manifest_problems(root, pin)),
        ("5 builder reproduces the block", builder_problems(pin)),
    ]
    return checks, False


def self_test():
    real = _load_pin(ROOT)
    results = []

    def make_root(tmp, pin, manifest_block="ok", extra=None):
        root = Path(tmp)
        (root / "data").mkdir(parents=True, exist_ok=True)
        (root / "downloads").mkdir(parents=True, exist_ok=True)
        (root / "data" / "fabric_api.json").write_text(json.dumps(pin), encoding="utf-8")
        block = {k: pin.get(k) for k in BLOCK_KEYS}
        if manifest_block == "ok":
            manifest = {"pack": {}, "fabric_api": block}
        elif manifest_block == "none":
            manifest = {"pack": {}}
        else:
            manifest = {"pack": {}, "fabric_api": dict(block, **manifest_block)}
        (root / "glimpse_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        for rel, data in (extra or {}).items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(data)
        return root

    def plant(label, want_red, pin_mut=None, manifest_block="ok", extra=None):
        with tempfile.TemporaryDirectory(prefix="fabric-gate-") as tmp:
            pin = copy.deepcopy(real)
            if pin_mut:
                pin_mut(pin)
            root = make_root(tmp, pin, manifest_block, extra)
            checks, fatal = run_all(root)
            red = fatal or any(p for _, p in checks)
            ok = red == want_red
            results.append((label, ok, sum(len(p) for _, p in checks)))

    plant("control: a faithful pin in a clean tree is GREEN", False)
    plant("missing sha512", True, lambda p: p.pop("sha512"))
    plant("sha256 not 64 hex", True, lambda p: p.update(sha256="ABC"))
    plant("file_size zero", True, lambda p: p.update(file_size=0))
    plant("download host is not the Modrinth CDN", True,
          lambda p: p.update(download_url=p["download_url"].replace("cdn.modrinth.com", "example.com")))
    plant("download over http", True, lambda p: p.update(download_url=p["download_url"].replace("https://", "http://")))
    plant("download path lacks the pinned version id", True,
          lambda p: p.update(download_url=p["download_url"].replace("EQKgpeKu", "OTHERID1")))
    plant("download URL names another file (after decoding)", True,
          lambda p: p.update(download_url=p["download_url"].replace("fabric-api-0.165.0%2B26.3.jar", "fabric-api-9.9%2B26.3.jar")))
    plant("raw '+' in the URL is still the same file (control: %2B and + both decode)", False,
          lambda p: p.update(download_url=p["download_url"].replace("%2B", "+")))
    plant("hosted_by_corvus true", True, lambda p: p.update(hosted_by_corvus=True))
    plant("licence changed to another one", True, lambda p: p.update(license="MIT"))
    plant("mod id changed", True, lambda p: p.update(mod_id="fabric"))
    plant("manifest block is missing", True, manifest_block="none")
    plant("manifest block names another latest", True, manifest_block={"latest": "9.9"})
    plant("manifest block carries an extra key", True, manifest_block={"download_url_extra": "x"})
    plant("a fabric-api jar planted in downloads/", True,
          extra={"downloads/fabric-api-0.165.0+26.3.jar": b"not really a jar"})

    def jar_with_id(path_rel, mod_id):
        with tempfile.TemporaryDirectory(prefix="fabric-jar-") as jt:
            jp = Path(jt) / "x.jar"
            with zipfile.ZipFile(jp, "w") as zf:
                zf.writestr("fabric.mod.json", json.dumps({"id": mod_id, "version": "0.165.0+26.3"}))
            return {path_rel: jp.read_bytes()}
    plant("a jar with another name but top-level mod id fabric-api", True,
          extra=jar_with_id("downloads/renamed-bundle.jar", MOD_ID))
    plant("a bundle jar that only NESTS fabric-api is not a Fabric API jar (control)", False,
          extra=jar_with_id("downloads/corvus-stand-in.jar", "some-other-mod"))

    content = b"stand-in payload, same size and hash as the pin in this control"

    def pin_matches_copy(p):
        p.update(file_size=len(content), sha256=hashlib.sha256(content).hexdigest())
    plant("a renamed copy of the pinned bytes", True, pin_matches_copy,
          extra={"downloads/notes.bin": content})

    passed = sum(1 for _, ok, _ in results if ok)
    for label, ok, n in results:
        print(f"  {'OK ' if ok else 'BAD'}  {label}  (problems found: {n})")
    if passed != len(results):
        print(f"check_fabric_api_pin self-test = RED ({len(results) - passed} case(s) did not behave as planted)")
        return 1
    print(f"check_fabric_api_pin self-test = GREEN ({len(results)} cases, every planted defect turns the gate red)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    checks, fatal = run_all(ROOT)
    failed = 0
    for label, problems in checks:
        print(f"  {'PASS' if not problems else 'FAIL'}  {label}")
        for p in problems:
            print(f"        - {p}")
        failed += bool(problems)
    if fatal or failed:
        print("FABRIC API PIN = RED")
        return 1
    print("FABRIC API PIN = GREEN (pinned, not hosted, manifest equals the pin, no Fabric API jar in the tree)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
