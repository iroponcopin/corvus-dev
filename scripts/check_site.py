#!/usr/bin/env python3
"""One entry point for every audit in this repo. Run it after scripts/build.py.

  python3 scripts/check_site.py               # everything
  python3 scripts/check_site.py --list        # what it would run
  python3 scripts/check_site.py defects 404   # just these

Each checker is a separate process with its own hand-written expectations, and
none of them imports the page builders' shared helpers except where noted, so a
mistake inside site_common.py cannot make them all agree with it.

Deliberately NOT wired into scripts/build.py: these audit the OUTPUT of that
build, and running them as part of producing it would be circular — a checker
that runs before the pages it reads have been written would be green on a stale
site. build.py stays the thing that produces; this stays the thing that judges.

Exit code is the number of checkers that went RED (0 = all green). The verdict
is the printed summary, not the exit code alone: read it.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# name -> (script, args, what it looks at)
CHECKS = [
    ("defects", "check_defects.py", [],
     "data/*.json + the rendered pages: the 5 defect groups this site has shipped"),
    ("figures", "check_figures.py", [],
     "data/i18n/*.json: safety-relevant figures surviving translation"),
    ("404", "check_404.py", [],
     "404.html: one message section per language, resolver, no hreflang"),
    ("lang", "check_lang_switcher.py", [],
     "every rendered page: switcher, flags, hreflang alternates, detector"),
    ("discord", "check_discord_page.py", [],
     "/discord/ vs the bot's own command export, in all 13 languages"),
    # V4.3.0. The half of the skin gate that needs no secret: the page exists in
    # every language, its blob path resolves, the blob is well formed, it is NOT
    # stale against the skin the game ships, and no digit run leaked into the
    # markup. The PIN-bearing half is scripts/check_skin_gate.py, run by hand at
    # release time with CORVUS_SKIN_PIN set — it cannot live here because this
    # entry point must stay runnable by anyone.
    ("skin", "check_skin_page.py", [],
     "/skin/ in 13 languages + downloads/sparxie-skin.acsk vs the in-game skin"),
    # Cherry V1.0.0 (2026-09-13). The brand page hands out the release: the link
    # must resolve from every language's depth to the newest Cherry zip, and the
    # version, size and SHA-256 it prints must be that file's own. Nothing else on
    # the site reads a Cherry file.
    ("cherry", "check_cherry_release.py", [],
     "/cherry/ in 13 languages vs downloads/Cherry_MODs_v*.zip (link, size, hash)"),
    # OUKA V1.0.0 (staged 2026-09-15). The same gate for the OUKA page: the link must resolve from
    # every language's depth to the newest OUKA zip, the version, size and SHA-256 it prints must be
    # that file's own, and the manifest's ouka block must describe the same file.
    ("ouka", "check_ouka_release.py", [],
     "/ouka/ in 13 languages vs downloads/OUKA_MODs_v*.zip (link, size, hash)"),
    # 2026-09-14 (owner): the changelog's brand tabs (OUKA -> Cherry -> Alpha, then Aureum) and the brand feeds Corvus
    # reads. Alpha's panel and Alpha's feed must stay Alpha's alone; the self-test plants one defect per check.
    ("changelog-brands", "check_changelog_brands.py", [],
     "/changelog/ brand panels in 13 languages + changelog_feed/brands.json and every brand feed"),
    ("changelog-brands-controls", "check_changelog_brands.py", ["--self-test"],
     "the brand-changelog gate turns every planted defect red"),
    # Portal only (runs when portal/build.json exists): the half of the brand-changelog gate that reads DATA and FEEDS
    # (data/changelog_brands.json, the i18n titles, changelog_feed/brands.json and every brand feed the launcher reads),
    # without the pages, whose markup is the portal's now.
    ("changelog-feeds", "check_changelog_brands.py", ["--feeds-only"],
     "data/changelog_brands.json + changelog_feed/brands.json and every brand feed (the pages are not read)"),
    # 2026-09-20: レシピ集は配布物(pack zip とブランド zip)から作られる。新しい版を
    # 配り始めたのに作り直していなければ、サイトは新しい zip を配りながら古い作り方を
    # 表示し続ける —— 出力は正常に見え、リンクも切れないので誰も気づかない。
    ("recipe-sources", "check_recipe_sources.py", [],
     "data/recipes.json was generated from the versions the site currently publishes"),
    # 2026-10-07 (owner): every recipe a published jar holds is on the recipe page, the machine ones too (OUKA's
    # assembly line, crusher, centrifuge, culture vat and bore, Cherry's fabricator, furnaces). The sheet above reads
    # crafting grids only; this one reads the rest from the same zips and must match them.
    ("machine-recipes", "extract_machine_recipes.py", ["--check"],
     "data/recipes_machines.json holds every machine recipe of the zips the site currently publishes"),
    # ASTRAEA V1.0.0 (2026-09-30), the first brand released after the portal cutover. Not a page gate (those are the
    # portal's now) but the DATA the Store and the Discord bot act on: the zip in downloads/ is tracked (an untracked one
    # 404s live), holds ASTRAEA's one jar with no foreign dependency and no Alpha trace (owner, D-1), the manifest's
    # astraea block describes exactly that zip, and all 13 changelog feeds lead with its version. Live at the portal.
    ("astraea", "check_astraea_release.py", [],
     "downloads/ASTRAEA_MODs_v*.zip (tracked, one jar, no Alpha) vs the manifest's astraea block and the 13 feeds"),
    ("astraea-controls", "check_astraea_release.py", ["--self-test"],
     "the ASTRAEA release gate turns every planted defect red"),
    # Tsubomi V1.0.0 (2026-09-30), a BARE JAR like Aureum: the jar in downloads/ is tracked and the only one, is id
    # "tsubomi" at its file name's version, depends on Fabric only (Cherry at most as a suggestion), DECLARES that it is
    # incompatible with Alpha (owner, 2026-09-30; the opposite of ASTRAEA's D-1 rule), the manifest's tsubomi block
    # (Aureum's shape, no "jars") describes exactly that jar, and all 13 changelog feeds lead with its version.
    ("tsubomi", "check_tsubomi_release.py", [],
     "downloads/tsubomi-*.jar (tracked, Fabric-only, declares Alpha incompatible) vs the manifest's tsubomi block and the 13 feeds"),
    ("tsubomi-controls", "check_tsubomi_release.py", ["--self-test"],
     "the Tsubomi release gate turns every planted defect red"),
    # Halia V1.0.0 (2026-10-11), a bare jar like Tsubomi: tracked and the only one, id "halia" at its file name's
    # version, Fabric-only, refuses no other mod, described exactly by the manifest's halia block, 13 feeds lead with it.
    ("halia", "check_halia_release.py", [],
     "downloads/halia-*.jar (tracked, Fabric-only, no breaks) vs the manifest's halia block and the 13 feeds"),
    ("halia-controls", "check_halia_release.py", ["--self-test"],
     "the Halia release gate turns every planted defect red"),
    # 2026-10-25 (Corvus Store 5.5.204): the local assistant's model mirror. The Store trusts the manifest's local_ai
    # block and verifies the download by hash, so the block must match the pinned model (file, bytes, SHA-256, the
    # Store's LocalAiSpec) and the documented part plan, offline. The network half (every listed part answers 200 with
    # its bytes) is check_published_artefacts.py, run after publish.
    ("local-ai", "check_local_ai.py", [],
     "data/local_ai.json vs the pinned model (LocalAiSpec copy) and data/local_ai_mirror_parts.json"),
    ("local-ai-controls", "check_local_ai.py", ["--self-test"],
     "the local AI gate turns every planted defect red"),
    # 2026-10-26: Punchy! is a THIRD-PARTY Fabric mod (Modrinth 8aoMKplv), All Rights Reserved, redistribution not
    # allowed. Nothing is hosted here: data/punchy.json pins the Modrinth CDN file, the manifest's punchy block
    # (hosted_by_corvus: false) describes it, and no Punchy! jar may exist anywhere in the tree. Offline.
    ("punchy", "check_punchy_pin.py", [],
     "data/punchy.json (pinned, Modrinth CDN only) vs the manifest's punchy block; no Punchy! jar in the tree"),
    ("punchy-controls", "check_punchy_pin.py", ["--self-test"],
     "the Punchy pin gate turns every planted defect red"),
    ("punchy-fetch-controls", "pin_punchy.py", ["--self-test"],
     "the Punchy pin script refuses a wrong hash, a wrong mod id, a non-CDN URL and a beta-only release (stand-in, offline)"),
]


# The checkers that read the OLD pages' markup. Once the portal is the site (portal/build.json exists) their expectations
# are about HTML that is no longer there, so they would go red for the right reason and prove nothing; they are retired
# here, and their jobs are done by the portal's own gates (`npm run check:all` in web/: typecheck, lint, the build,
# which refuses to export a contract file, and check:export — every page's head, every link and anchor, the 404 rule,
# and each printed SHA-256 against the file actually served). What stays is what reads DATA.
RETIRED_AT_PORTAL = {"defects", "404", "lang", "discord", "skin", "cherry", "ouka", "changelog-brands",
                     "changelog-brands-controls"}
PORTAL_ONLY = {"changelog-feeds"}


def portal_is_in_place():
    return (HERE.parent / "portal" / "build.json").exists()


def main():
    argv = sys.argv[1:]
    portal = portal_is_in_place()
    if "--list" in argv:
        for name, script, _a, what in CHECKS:
            mark = "  [retired: the portal is the site]" if portal and name in RETIRED_AT_PORTAL else (
                "  [only once the portal is the site]" if not portal and name in PORTAL_ONLY else "")
            print(f"  {name:9} {script:24} {what}{mark}")
        return 0
    want = [a for a in argv if not a.startswith("-")]
    todo = [c for c in CHECKS if not want or c[0] in want]
    if not portal:
        todo = [c for c in todo if c[0] not in PORTAL_ONLY]
    if portal:
        retired = [c[0] for c in todo if c[0] in RETIRED_AT_PORTAL]
        todo = [c for c in todo if c[0] not in RETIRED_AT_PORTAL]
        if retired:
            print("retired at the portal cutover (they read the old pages' markup): " + ", ".join(retired))
            print("  the portal's gates replace them: cd web && npm run check:all")
    unknown = [w for w in want if w not in {c[0] for c in CHECKS}]
    if unknown:
        raise SystemExit(f"ERROR: no such check: {', '.join(unknown)}. "
                         f"Known: {', '.join(c[0] for c in CHECKS)}")

    results = []
    for name, script, args, _what in todo:
        path = HERE / script
        print(f"\n{'=' * 72}\n== {name}  ({script})\n{'=' * 72}")
        if not path.exists():
            print(f"  RED  {script} is missing from scripts/")
            results.append((name, None))
            continue
        r = subprocess.run([sys.executable, str(path), *args])
        results.append((name, r.returncode))

    print(f"\n{'=' * 72}\nSUMMARY")
    red = 0
    for name, code in results:
        if code is None:
            verdict, red = "MISSING", red + 1
        elif code == 0:
            verdict = "GREEN"
        else:
            verdict, red = f"RED (exit {code})", red + 1
        print(f"  {name:9} {verdict}")
    print(f"\n{red} of {len(results)} checker(s) RED")
    return red


if __name__ == "__main__":
    sys.exit(main())
