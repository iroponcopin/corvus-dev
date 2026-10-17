#!/usr/bin/env python3
"""Audits the rendered 404.html: one message section per language, correct
lang/dir, buttons that stay inside that language's own subtree, the inline
language resolver, and the CSS rules that reveal exactly one section.

  python3 scripts/check_404.py [repo]      # default: this file's repo

Instrument A only. It reads markup, so it can see that the resolver is PRESENT
but not that it BEHAVES; the behavioural half is a browser run against mocked
navigator.languages. Deliberately does not import site_common or build_404 —
every expectation is written out here by hand, so this cannot pass by agreeing
with the generator about a shared mistake.

⚠ The hreflang assertion at the bottom is written against <link rel="alternate">
  in <head> ONLY. The first version of it looked for the substring "hreflang"
  anywhere in the file and was red on the fixed page AND on the broken one — it
  was matching the language switcher's own <a hreflang="ja"> links, which are
  correct and have always been there. A red that fires in both states measures
  nothing.
"""
import re
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 \
    else Path(__file__).resolve().parent.parent

# Hand-written, not imported from site_common.
LANGS = ["ja", "en", "es", "fr", "zh", "ko", "pt-br", "it", "ar", "ru", "id", "de", "tr"]
RTL = {"ar"}
# The absolute path the site is published under (GitHub Pages project page).
ABS = "/corvus-dev/"


def main():
    h = (REPO / "404.html").read_text(encoding="utf-8")
    fails = []

    def fail(m):
        fails.append(m)
        print(f"  RED  {m}")

    secs = dict((m.group(1), m.group(0)) for m in re.finditer(
        r'<section class="nf nf--([a-z\-]+)".*?</section>', h, re.S))
    missing = [l for l in LANGS if l not in secs]
    if missing:
        fail(f"404.html has no message section for: {missing} "
             f"(a visitor in those languages gets someone else's language)")

    for lang, block in secs.items():
        want_dir = "rtl" if lang in RTL else "ltr"
        if f'lang="{lang}"' not in block or f'dir="{want_dir}"' not in block:
            fail(f"404.html section {lang}: wrong lang= or dir= (want dir={want_dir})")
        base = ABS if lang == "ja" else f"{ABS}{lang}/"
        hrefs = re.findall(r'<a class="btn[^"]*" href="([^"]+)"', block)
        if len(hrefs) != 3:
            fail(f"404.html section {lang}: {len(hrefs)} buttons, expected 3")
        wrong = [u for u in hrefs if not u.startswith(base)]
        if wrong:
            fail(f"404.html section {lang}: {len(wrong)} button(s) point outside {base}: {wrong}")

    if 'data-nf' not in h or 'navigator.languages' not in h:
        fail("404.html has no inline language resolver -- every visitor would see all "
             "13 sections stacked, or (worse) whichever one CSS happens to show")
    for lang in LANGS:
        if f':root[data-nf="{lang}"]' not in h:
            fail(f"404.html has no CSS rule to reveal the {lang} section")
    if re.search(r'<link[^>]+rel="alternate"[^>]+hreflang=', h):
        fail("404.html now advertises hreflang alternates -- its section is a fiction, "
             "see site_common.page()")

    print(f"{'RED' if fails else 'GREEN'}: {len(fails)} failure(s); "
          f"{len(secs)} language sections found")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
