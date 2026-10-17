#!/usr/bin/env python3
"""Builds the legacy mirror: the folder served at the site's OLD address, for the software already installed.

The site moved from https://iroponcopin.github.io/aurora-corvus/ to https://iroponcopin.github.io/corvus-dev/.
The Corvus Store and Agent (glimpse-launcher-eos) and the Discord release bot (discord-release-bot) read these from the
old address, so the old address keeps serving exactly those files, copied byte-for-byte from the new build:

  glimpse_manifest.json, releases.json, upcoming.json, changelog_feed/ (the whole tree)

(the launcher reads the manifest and changelog_feed/; the bot reads releases.json, upcoming.json and the manifest; the
Agent reads the manifest). The manifest's download URLs already point to the new site, so nothing downloaded from
the old address is needed. Also written: an index.html and a 404.html that send every path under /aurora-corvus/ (and
any other path) to the same path under the new site (meta refresh and a script, noindex), and an empty .nojekyll.

Nothing here is pushed or committed: the folder is built, and its file list is printed.

Usage: python3 scripts/build_legacy_mirror.py [--source DIR] [--out DIR]
  --source  the new build (default: this repository's root, after `npm run apply`)
  --out     the mirror folder (default: ../aurora-corvus-mirror, beside this repository)
"""

from __future__ import annotations

import argparse
import filecmp
import hashlib
import html
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: The OLD address: the only place this repository names the old path. Everything else points at the new site.
LEGACY_SITE_URL = "https://iroponcopin.github.io/aurora-corvus/"
NEW_SITE_URL = "https://iroponcopin.github.io/corvus-dev/"
OLD_BASE_PATH = "/aurora-corvus"
NEW_BASE_PATH = "/corvus-dev"

#: The files the installed software reads from the old address, relative to the new build's root.
FILES = ["glimpse_manifest.json", "releases.json", "upcoming.json"]
TREES = ["changelog_feed"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_exact(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    if not filecmp.cmp(src, dst, shallow=False):
        raise SystemExit(f"legacy mirror: {dst} is not byte-identical to {src}")


def manifest_points_to_new_site(path: Path) -> None:
    """The mirrored manifest must not send anyone to the old address for a download."""
    text = path.read_text(encoding="utf-8")
    json.loads(text)
    if LEGACY_SITE_URL in text:
        raise SystemExit(f"legacy mirror: {path.name} still names the old address; rebuild the new site first")


REDIRECT_JS = (
    "(function(){var n=" + json.dumps(NEW_SITE_URL.rstrip("/")) + ",o=" + json.dumps(OLD_BASE_PATH) + ";"
    "var p=location.pathname;if(p.indexOf(o)===0)p=p.slice(o.length);if(p===\"\")p=\"/\";"
    "location.replace(n+p+location.search+location.hash);})();"
)


def redirect_page(title: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="canonical" href="{html.escape(NEW_SITE_URL)}">
<meta http-equiv="refresh" content="0; url={html.escape(NEW_SITE_URL)}">
<script>{REDIRECT_JS}</script>
</head>
<body>
<p>This address has moved: <a href="{html.escape(NEW_SITE_URL)}">{html.escape(NEW_SITE_URL)}</a></p>
</body>
</html>
"""


def build(source: Path, out: Path) -> list[str]:
    if not source.is_dir():
        raise SystemExit(f"legacy mirror: source {source} is not a directory")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    written: list[str] = []
    for name in FILES:
        src = source / name
        if not src.is_file():
            raise SystemExit(f"legacy mirror: {name} is missing from the new build at {source}")
        copy_exact(src, out / name)
        if name.endswith(".json"):
            manifest_points_to_new_site(out / name)
        written.append(name)
    for tree in TREES:
        base = source / tree
        if not base.is_dir():
            raise SystemExit(f"legacy mirror: {tree}/ is missing from the new build at {source}")
        for src in sorted(base.rglob("*")):
            if src.is_file():
                rel = src.relative_to(source).as_posix()
                copy_exact(src, out / rel)
                written.append(rel)
    (out / "index.html").write_text(redirect_page("Corvus has moved"), encoding="utf-8")
    (out / "404.html").write_text(redirect_page("Corvus has moved"), encoding="utf-8")
    (out / ".nojekyll").write_bytes(b"")
    written += ["index.html", "404.html", ".nojekyll"]
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", type=Path, default=REPO)
    ap.add_argument("--out", type=Path, default=REPO.parent / "aurora-corvus-mirror")
    args = ap.parse_args()
    files = build(args.source.resolve(), args.out.resolve())
    print(f"legacy mirror: {len(files)} files in {args.out.resolve()}")
    for rel in files:
        print(f"  {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
