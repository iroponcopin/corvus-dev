#!/usr/bin/env python3
"""Pin for the third-party Fabric mod "Fabric API" (Modrinth project P7dR8mSH, slug fabric-api).

Fabric API is NOT Corvus's. Its licence is Apache-2.0 (Modrinth reports it; this script reads it, it does not
guess it). The Corvus site still never hosts the jar: no copy goes into the repository, downloads/ or the site.
data/fabric_api.json only POINTS at the official Modrinth CDN; the Corvus Store downloads the jar from there,
only when a mod that needs it is installed and Fabric API is missing.

Run by hand at publish time (it needs the network; nothing else does):

    python3 scripts/pin_fabric_api.py              # --check (default): is data/fabric_api.json the newest 26.3 release?
    python3 scripts/pin_fabric_api.py --write      # download to a temp dir OUTSIDE the repo, verify, rewrite the pin
    python3 scripts/pin_fabric_api.py --self-test  # offline: stand-in responses; planted defects must be refused

--check never writes and never downloads the jar. It asks the Modrinth API only (versions and the project's
licence). Exit 0 = the pin is the newest release and the licence matches, exit 1 = a newer 26.3 release exists
(or the pin disagrees with the API), exit 2 = could not ask.

--write: takes the newest 26.3 fabric release from the API, downloads its primary file to a temp dir, refuses
unless the sha512 matches the API's, reads fabric.mod.json from the TOP LEVEL of the jar (id must be "fabric-api";
the jar is only parsed as a zip, never executed; nested jars are not opened), computes sha256 and size, and
rewrites data/fabric_api.json. The temp dir is deleted at the end.
"""
import hashlib
import json
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN_FILE = ROOT / "data" / "fabric_api.json"

PROJECT_ID = "P7dR8mSH"
MC_VERSION = "26.3"
LOADER = "fabric"
MOD_ID = "fabric-api"
CDN_HOST = "cdn.modrinth.com"
USER_AGENT = "Corvus-Site-Pin/1 (iroponcopin.github.io/corvus-dev)"
API_URL = ("https://api.modrinth.com/v2/project/%s/version?%s" % (
    PROJECT_ID,
    urllib.parse.urlencode({"game_versions": json.dumps([MC_VERSION]), "loaders": json.dumps([LOADER])})))
PROJECT_API_URL = "https://api.modrinth.com/v2/project/%s" % PROJECT_ID
MAX_JAR_BYTES = 64 * 1024 * 1024
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX128 = re.compile(r"^[0-9a-f]{128}$")


def http_get(url, max_bytes=None):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        final = resp.geturl()
        if max_bytes is None:
            return final, resp.read()
        body = resp.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise SystemExit("ERROR: the download is larger than %d bytes; refusing." % max_bytes)
        return final, body


def newest_release(versions):
    """The newest release of 26.3 for fabric, by date_published. Beta and alpha builds are not pinned."""
    usable = [v for v in versions
              if v.get("version_type") == "release"
              and MC_VERSION in (v.get("game_versions") or [])
              and LOADER in (v.get("loaders") or [])]
    if not usable:
        raise SystemExit("ERROR: Modrinth lists no release of Fabric API for Minecraft %s on %s." % (MC_VERSION, LOADER))
    usable.sort(key=lambda v: str(v.get("date_published", "")))
    return usable[-1]


def primary_file(version):
    files = version.get("files") or []
    primary = [f for f in files if f.get("primary")]
    if len(primary) != 1:
        raise SystemExit("ERROR: version %s has %d primary files; expected exactly one." % (version.get("id"), len(primary)))
    f = primary[0]
    url = f.get("url", "")
    expected_prefix = "https://%s/data/%s/versions/%s/" % (CDN_HOST, PROJECT_ID, version.get("id"))
    # The API publishes the URL percent-encoded ("+" as %2B); the file name is compared once decoded.
    decoded = urllib.parse.unquote(url) if isinstance(url, str) else ""
    if not url.startswith(expected_prefix) or not decoded.endswith("/" + f.get("filename", "\0")):
        raise SystemExit("ERROR: the file URL %r is not the Modrinth CDN path for version %s (%s). Refusing."
                         % (url, version.get("id"), f.get("filename")))
    sha512 = str((f.get("hashes") or {}).get("sha512", "")).lower()
    if not HEX128.match(sha512):
        raise SystemExit("ERROR: the API gives no usable sha512 for %s." % f.get("filename"))
    size = f.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise SystemExit("ERROR: the API gives no usable size for %s." % f.get("filename"))
    return {"file_name": f["filename"], "url": url, "sha512": sha512, "size": size}


def read_jar_identity(path):
    """id and version from the jar's own TOP-LEVEL fabric.mod.json. Fabric API is a bundle: nested jars are not read."""
    try:
        with zipfile.ZipFile(path) as zf:
            meta = json.loads(zf.read("fabric.mod.json").decode("utf-8"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        raise SystemExit("ERROR: cannot read fabric.mod.json from the downloaded jar (%s)." % exc)
    if meta.get("id") != MOD_ID:
        raise SystemExit("ERROR: the jar declares id %r, not %r. Refusing to pin it." % (meta.get("id"), MOD_ID))
    return str(meta.get("version", "")).strip()


def pin_from_facts(static, version, file_info, sha256_hex, jar_version):
    """The full pin. Static fields (name, licence, requires, redistribution text) come from the current pin file.
    jar_version is read from the jar itself, so the pin's "latest" is the jar's own version, not a typed one."""
    pin = dict(static)
    pin.update({
        "latest": jar_version,
        "file_name": file_info["file_name"],
        "file_size": file_info["size"],
        "sha256": sha256_hex,
        "sha512": file_info["sha512"],
        "download_url": file_info["url"],
        "modrinth_version_id": version["id"],
    })
    return pin


def fetch_license(getter=http_get):
    """The project's licence id as Modrinth reports it (e.g. "Apache-2.0")."""
    _final, raw = getter(PROJECT_API_URL)
    lic = json.loads(raw.decode("utf-8")).get("license") or {}
    return str(lic.get("id", ""))


def check_against_api(pin, version, file_info, api_license):
    """Problems with the pin relative to the API's newest release. [] means the pin is current."""
    problems = []
    if api_license != pin.get("license"):
        problems.append("licence differs: Modrinth says %r, the pin says %r" % (api_license, pin.get("license")))
    if version["id"] != pin.get("modrinth_version_id"):
        problems.append("newer 26.3 release on Modrinth: %s (%s) -- the pin names %s"
                        % (version.get("version_number"), version["id"], pin.get("modrinth_version_id")))
        return problems
    if file_info["file_name"] != pin.get("file_name"):
        problems.append("file name differs: API %s, pin %s" % (file_info["file_name"], pin.get("file_name")))
    if file_info["sha512"] != pin.get("sha512"):
        problems.append("sha512 differs from the API's for the pinned version")
    if file_info["size"] != pin.get("file_size"):
        problems.append("file size differs: API %s, pin %s" % (file_info["size"], pin.get("file_size")))
    return problems


def fetch_versions(getter=http_get):
    _final, raw = getter(API_URL)
    return json.loads(raw.decode("utf-8"))


def write_pin(static, version, file_info, downloader):
    """Downloads via downloader(url) -> bytes into a temp dir outside the repo, verifies, returns the new pin dict."""
    with tempfile.TemporaryDirectory(prefix="fabric-api-pin-") as tmp:
        jar = Path(tmp) / file_info["file_name"]
        body = downloader(file_info["url"])
        if len(body) != file_info["size"]:
            raise SystemExit("ERROR: downloaded %d bytes, the API says %d." % (len(body), file_info["size"]))
        if hashlib.sha512(body).hexdigest() != file_info["sha512"]:
            raise SystemExit("ERROR: sha512 of the download does not match the API's. Refusing to pin it.")
        jar.write_bytes(body)
        jar_version = read_jar_identity(jar)
        sha256_hex = hashlib.sha256(body).hexdigest()
    return pin_from_facts(static, version, file_info, sha256_hex, jar_version)


def load_static():
    return json.loads(PIN_FILE.read_text(encoding="utf-8"))


def main(argv):
    if "--self-test" in argv:
        return self_test()
    write = "--write" in argv
    static = load_static()
    try:
        versions = fetch_versions()
        version = newest_release(versions)
        file_info = primary_file(version)
        api_license = fetch_license()
    except (OSError, ValueError, urllib.error.URLError) as exc:
        print("pin_fabric_api: could not ask Modrinth (%s)." % exc)
        return 2
    if write:
        if api_license != static.get("license"):
            raise SystemExit("ERROR: Modrinth says the licence is %r, the pin says %r. Fix the pin's licence by hand "
                             "after reading the licence, then re-run." % (api_license, static.get("license")))
        pin = write_pin(static, version, file_info, lambda u: http_get(u, MAX_JAR_BYTES)[1])
        if not HEX64.match(pin["sha256"]):
            raise SystemExit("ERROR: computed sha256 is malformed.")
        PIN_FILE.write_text(json.dumps(pin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("pin_fabric_api: wrote %s (version %s, file %s, %d bytes, sha256 %s...)"
              % (PIN_FILE, pin["latest"], pin["file_name"], pin["file_size"], pin["sha256"][:12]))
        return 0
    problems = check_against_api(static, version, file_info, api_license)
    if not problems:
        print("pin_fabric_api: CURRENT -- data/fabric_api.json pins Modrinth version %s (%s, %d bytes, sha512 %s...), licence %s."
              % (version["id"], file_info["file_name"], file_info["size"], file_info["sha512"][:12], api_license))
        return 0
    print("pin_fabric_api: NOT CURRENT")
    for p in problems:
        print("  - " + p)
    print("  run: python3 scripts/pin_fabric_api.py --write   (then the gates: check_fabric_api_pin.py, build.py --feeds)")
    return 1


# ---------------------------------------------------------------- self-test (offline, stand-in responses only)

def _fake_jar(tmp, mod_id=MOD_ID, version="0.165.0+26.3"):
    """A stand-in jar: a zip with a top-level fabric.mod.json. It is never executed, only read as a zip."""
    path = Path(tmp) / "stand-in.jar"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("fabric.mod.json", json.dumps({"schemaVersion": 1, "id": mod_id, "version": version}))
    return path.read_bytes()


def self_test():
    failures = []
    results = []

    with tempfile.TemporaryDirectory(prefix="fabric-api-selftest-") as tmp:
        body = _fake_jar(tmp)
        sha512 = hashlib.sha512(body).hexdigest()
        vid = "EQKgpeKu"
        fname = "fabric-api-0.165.0+26.3.jar"
        url = "https://%s/data/%s/versions/%s/fabric-api-0.165.0%%2B26.3.jar" % (CDN_HOST, PROJECT_ID, vid)

        def api(files=None, **over):
            this_id = over.pop("id", vid)
            v = {"id": this_id, "version_number": "0.165.0+26.3", "version_type": "release",
                 "game_versions": [MC_VERSION], "loaders": [LOADER], "date_published": "2026-10-23T08:35:46Z",
                 "files": files if files is not None else [
                     {"filename": fname, "primary": True, "size": len(body),
                      "hashes": {"sha512": sha512},
                      "url": "https://%s/data/%s/versions/%s/fabric-api-0.165.0%%2B26.3.jar" % (CDN_HOST, PROJECT_ID, this_id)}]}
            v.update(over)
            return v

        static = load_static()

        def expect(label, want_ok, fn):
            try:
                fn()
                ok = True
            except SystemExit as exc:
                ok = False
                reason = str(exc)
            else:
                reason = ""
            good = ok == want_ok
            results.append((label, good, "refused: " + reason[:90] if not ok else "accepted"))
            if not good:
                failures.append(label)

        # 1. the stand-in pipeline accepts a correct release (percent-encoded URL, decoded name)
        def green():
            v = newest_release([api()])
            f = primary_file(v)
            pin = write_pin(static, v, f, lambda u: body)
            assert pin["latest"] == "0.165.0+26.3" and pin["sha256"] == hashlib.sha256(body).hexdigest()
        expect("stand-in: correct release is pinned", True, green)

        # 2. planted wrong sha512 in the API -> the download is refused
        def wrong_hash():
            v = newest_release([api(files=[{"filename": fname, "primary": True, "size": len(body),
                                            "hashes": {"sha512": "0" * 128}, "url": url}])])
            f = primary_file(v)
            write_pin(static, v, f, lambda u: body)
        expect("planted: wrong sha512 is refused", False, wrong_hash)

        # 3. planted wrong mod id in the jar -> refused
        def wrong_id():
            other = _fake_jar(tmp, mod_id="not-fabric-api")
            files = [{"filename": fname, "primary": True, "size": len(other),
                      "hashes": {"sha512": hashlib.sha512(other).hexdigest()}, "url": url}]
            v = newest_release([api(files=files)])
            f = primary_file(v)
            write_pin(static, v, f, lambda u: other)
        expect("planted: jar with another mod id is refused", False, wrong_id)

        # 4. planted URL on another host -> refused
        def evil_host():
            v = newest_release([api(files=[{"filename": fname, "primary": True, "size": len(body),
                                            "hashes": {"sha512": sha512},
                                            "url": "https://example.com/data/%s/versions/%s/fabric-api-0.165.0%%2B26.3.jar" % (PROJECT_ID, vid)}])])
            primary_file(v)
        expect("planted: non-Modrinth CDN URL is refused", False, evil_host)

        # 5. planted beta-only -> no release, refused
        def beta_only():
            newest_release([api(version_type="beta")])
        expect("planted: beta-only versions are not pinned", False, beta_only)

        # 6. a planted licence change at Modrinth -> reported as NOT CURRENT
        v_now = newest_release([api()])
        if not check_against_api(static, v_now, primary_file(v_now), "MIT"):
            failures.append("planted: a licence change was not reported")
            results.append(("planted: a licence change is reported as NOT CURRENT", False, "not reported"))
        else:
            results.append(("planted: a licence change is reported as NOT CURRENT", True, "reported"))

        # 7. a newer release than the pin -> reported as not current
        v_newer = newest_release([api(id="NEWERID1")])
        if not check_against_api(static, v_newer, primary_file(v_newer), static.get("license")):
            failures.append("planted: a newer release was not reported")
            results.append(("planted: a newer release is reported as NOT CURRENT", False, "not reported"))
        else:
            results.append(("planted: a newer release is reported as NOT CURRENT", True, "reported"))

    for label, good, detail in results:
        print("  %s  %s  (%s)" % ("OK " if good else "BAD", label, detail))
    if failures:
        print("pin_fabric_api self-test = RED (%d)" % len(failures))
        return 1
    print("pin_fabric_api self-test = GREEN (%d cases)" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
