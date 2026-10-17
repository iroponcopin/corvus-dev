#!/usr/bin/env python3
"""Builds releases.json at the repo root — a small, stable, English-only
feed describing the current release. This is the "machine-readable feed"
the Discord release bot polls (see discord-release-bot/bot/poller.py) as
its fallback trigger, since this Wiki is a static site published by a
person running this build and pushing to GitHub Pages, not by a CI
pipeline that could call a webhook on its own.

Design note: same discipline as build_download.py — every fact here is
computed from the real shipped ZIP and data/*.json at build time, never
typed as a literal. This file's shape is a contract with a separate
project (discord-release-bot/bot/release.py's ReleasePayload) — do not
rename or drop fields without updating that project to match.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import ROOT, PACK_NAME, pack_zip_path  # noqa: E402

MC_VERSION = "26.3"
DOWNLOAD_DIR = ROOT / "downloads"
SITE_BASE_URL = "https://iroponcopin.github.io/corvus-dev"


def _mod_version():
    mods = json.loads((ROOT / "data" / "versions.json").read_text(encoding="utf-8"))["mods"]
    versions = set(mods.values())
    if len(versions) != 1:
        raise SystemExit(
            f"ERROR: data/versions.json lists more than one distinct version {sorted(versions)} "
            f"- releases.json cannot describe a single release when the table itself disagrees."
        )
    return versions.pop()


def _zip_path(version):
    # Filename from site_common.pack_zip_name() — see the note there about the
    # V2.5.0 Glimpse_Alpha_MODs_* -> Alpha_MODs_* rename being one fact, not
    # three copies. `file_name` below is this real file's name, so the feed
    # follows the rename without this script knowing about it.
    return pack_zip_path(version, MC_VERSION, why="releases.json")


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
        f"ERROR: data/changelog.json has no entry with release == V{version}. releases.json "
        f"needs a real title/summary/date, not an invented one."
    )


def _english_summary(entry):
    """The changelog is authored in Japanese with the highlights list as the
    real content; the Discord bot posts in English (spec: British English
    for bot messages), so this feed carries a short, honest English summary
    rather than forwarding untranslated Japanese into every Discord server.
    We do not have a machine translation pipeline here, so this is a plain
    English restatement of the release type + headline count, not a
    translation of the Japanese summary field - deliberately modest rather
    than inventing prose we can't stand behind."""
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


def build():
    version = _mod_version()
    zpath = _zip_path(version)
    entry = _changelog_entry(version)
    size_bytes = zpath.stat().st_size
    sha256_hex = _sha256(zpath)

    published_at = f"{entry['date']}T00:00:00+00:00"

    feed = {
        "version": version,
        "title": f"{PACK_NAME} {entry['release']}",
        "summary": _english_summary(entry),
        "download_url": f"{SITE_BASE_URL}/downloads/{zpath.name}",
        "file_name": zpath.name,
        "file_size": size_bytes,
        "sha256": sha256_hex,
        "published_at": published_at,
        "changelog_url": f"{SITE_BASE_URL}/en/changelog/",
    }

    out_path = ROOT / "releases.json"
    out_path.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out_path} (version {version}, sha256 {sha256_hex[:12]}...)")


if __name__ == "__main__":
    build()
