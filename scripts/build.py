#!/usr/bin/env python3
"""Rebuilds every static page in the site from data/*.json.
Does NOT re-run the data extraction scripts (extract_versions.py,
extract_recipes.py, merge_changelog.py) — those pull from the source mod
pack project and should be re-run explicitly when that project ships an
update. This script only re-renders HTML from whatever is currently in data/.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD_SCRIPTS = [
    # Writes assets/css/lang-flags.css and assets/js/lang.js, which every
    # page's <head> links to. First so a flag/language mismatch stops the
    # build before 143 pages are written against it.
    "build_lang_assets.py",
    # V4.3.8: writes assets/img/cherry/blossom.svg, blossom-mark.svg and
    # assets/css/cherry-tokens.css. Must precede build_cherry.py, which links
    # those tokens.
    # ⚠ 2026-09-12: the Cherry PAGE no longer inlines blossom.svg -- the owner
    #   supplied a real Cherry logo and the page now carries the mark cut from
    #   that photograph (assets/img/cherry/mark*.webp). The generated SVGs stay
    #   because they are committed brand artefacts with their own uses, but
    #   nothing on the site inlines them any more; only cherry-tokens.css is
    #   still read by a page.
    "gen_cherry_brand.py",
    "build_recipe_overlays.py",
    "build_home.py",
    "build_download.py",
    # Right after build_download.py: build_aureum.py imports _aureum_facts()
    # from it to discover the published jar (see build_aureum.py's header),
    # and this page's download CTA is a companion to that page's Aureum
    # section, not to anything below.
    "build_aureum.py",
    # V4.3.8: Cherry's brand page. It links assets/css/cherry-tokens.css, which
    # gen_cherry_brand.py (first in this list) writes, and carries the mark cut
    # from the owner's own Cherry logo.
    "build_cherry.py",
    # 2026-09-23 (owner: 「飛行機と戦闘機の操作方法と船の操作方法を教えてください」
    # 「Corvus Webに公開してください」): how to fly Cherry's aircraft and sail its
    # ships, a page of its own. After build_cherry.py: it checks that the brand
    # page's link to it resolves, which needs the brand page written first.
    "build_cherry_controls.py",
    # 2026-09-12: OUKA -- the top of the brand line (OUKA -> Cherry -> Alpha).
    # Beside the other two brand pages, and before build_alpha.py for the same
    # reason the nav lists them in that order: this is the ranking, top first.
    "build_ouka.py",
    # 2026-09-10: Alpha finally gets a brand page of its own, so the Store
    # mega-menu has three real destinations instead of two.
    "build_alpha.py",
    "build_changelog.py",
    "build_recipes.py",
    "build_launcher.py",
    # After the roadmap (same family of page) and before the feeds/sitemap,
    # because it writes upcoming.json at the site root for the Discord bot.
    "build_upcoming.py",
    # After build_upcoming.py and before the feeds/sitemap. It imports
    # _discord_invite() from build_download.py so the invite link on this page
    # and on the Download page cannot diverge, and it reads the command export
    # copied from the bot repo (data/discord_commands.json).
    "build_discord.py",
    # V4.3.0: the Sparxie skin behind its PIN. After the download page (it is a
    # companion to it) and before the feeds, which walk whatever pages exist.
    # Without CORVUS_SKIN_PIN in the environment this re-publishes the committed
    # blob and REFUSES if the skin has changed since it was sealed.
    "build_skin_gate.py",
    "build_changelog_feed.py",
    "build_releases_feed.py",
    "build_glimpse_manifest.py",
    "build_404.py",
    "build_sitemap.py",  # must run last -- walks whatever pages exist on disk
]


# What produces the files the launcher and the bot read (the CONTRACT files) and nothing else: no page. After the portal
# cutover this is what a release runs; the pages are the portal's (web/: `npm run build && npm run apply`).
FEED_SCRIPTS = [
    ("build_upcoming.py", ["--feed-only"]),
    ("build_changelog_feed.py", []),
    ("build_releases_feed.py", []),
    ("build_glimpse_manifest.py", []),
]


def portal_is_in_place():
    return (HERE.parent / "portal" / "build.json").exists()


def main():
    argv = sys.argv[1:]
    if "--feeds" in argv:
        for name, args in FEED_SCRIPTS:
            print(f"--- {name} {' '.join(args)} ---".replace("  ", " "))
            subprocess.run([sys.executable, str(HERE / name), *args], check=True)
        return
    if portal_is_in_place() and "--legacy-pages" not in argv:
        raise SystemExit(
            "build.py refuses to run: portal/build.json exists, so the pages of this site are the 3D portal's "
            "(web/: `npm run build && npm run apply`), and this script would WRITE THE OLD PAGES OVER THEM.\n"
            "  * to rebuild what the launcher and the bot read (manifest, feeds):   python3 scripts/build.py --feeds\n"
            "  * to rebuild the pages after a release: see README.md, 'Releasing' (data -> --feeds -> web: build -> apply)\n"
            "  * to really write the old pages anyway (a rollback rehearsal):        python3 scripts/build.py --legacy-pages")
    for name in BUILD_SCRIPTS:
        script = HERE / name
        if not script.exists():
            print(f"skip (not written yet): {name}")
            continue
        print(f"--- {name} ---")
        subprocess.run([sys.executable, str(script)], check=True)


if __name__ == "__main__":
    main()
