#!/usr/bin/env python3
"""Builds sitemap.xml by walking every generated index.html. Run this LAST,
after scripts/build.py, since it just reflects whatever pages exist on disk.

SITE_URL must be filled in once the GitHub Pages URL is known (see README).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://iroponcopin.github.io/corvus-dev"


def build():
    # The site's own pages only: not web/ (the portal's source, its build output and node_modules)
    # and nothing under a dot directory.
    pages = sorted(
        p for p in ROOT.rglob("index.html")
        if p.relative_to(ROOT).parts[0] != "web" and not any(x.startswith(".") for x in p.relative_to(ROOT).parts)
    )
    urls = []
    for p in pages:
        rel = p.relative_to(ROOT).parent
        rel_str = "" if str(rel) == "." else str(rel) + "/"
        urls.append(f"{SITE_URL}/{rel_str}")

    body = "\n".join(
        f"  <url><loc>{u}</loc></url>" for u in urls
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
"""
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"wrote sitemap.xml ({len(urls)} URLs)")

    # Exactly one Sitemap: line, pointing at this site. A line left by an earlier name of the site
    # (glimpse-alpha-wiki) is replaced, not kept: it sent crawlers to another site's sitemap.
    robots = ROOT / "robots.txt"
    text = robots.read_text(encoding="utf-8")
    line = f"Sitemap: {SITE_URL}/sitemap.xml"
    kept = [x for x in text.splitlines() if not x.lower().startswith("sitemap:")]
    fixed = "\n".join(kept).rstrip() + f"\n{line}\n"
    if fixed != text:
        robots.write_text(fixed, encoding="utf-8")
        print(f"robots.txt: {line}")


if __name__ == "__main__":
    build()
