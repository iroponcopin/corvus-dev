#!/usr/bin/env python3
"""Builds the site-wide 404.html.

GitHub Pages serves this file's *content* at whatever URL the visitor actually
hit (any path, any depth) while leaving the browser's resolved base URL as that
broken path -- so this page cannot use normal depth-relative asset/nav paths
like every other page does. It passes absolute_base to page() to force every
link to an absolute path instead. It also gets neither hreflang nor the entry
language detector, because its "section" is a fiction (see the comment in
site_common.page()).

⚠ WHY THIS PAGE IS BUILT IN THIRTEEN LANGUAGES AT ONCE
  It used to be rendered in Japanese only, with one English line underneath,
  and its three buttons pointed at the Japanese top page, the Japanese recipe
  list and the Japanese changelog -- for every visitor, from every language.
  Twelve of the thirteen audiences hit a wall in a language they may not read,
  and the way back was a language they may not read either.

  The path cannot tell us the visitor's language: GitHub Pages serves this
  content at the broken URL, which is by definition not a URL this site
  publishes, so /ru/typo and /typo are indistinguishable to us. But the
  BROWSER knows. So:

    * all thirteen messages are in the HTML, each in its own <section> with
      the right lang= and dir=. With scripting off, every one of them is
      visible and every visitor can read their own and click through to their
      own language's pages. That is the floor, and it is already better than
      Japanese-only.
    * a tiny inline script reads navigator.languages, resolves it against the
      thirteen we publish (same tag rules as scripts/lang_detect.py: pt-* ->
      pt-br, zh-* -> zh, in -> id, everything else by base subtag), and sets
      data-nf on <html>. The stylesheet rule below then shows that one section
      and hides the rest, and <html lang>/<html dir> are corrected so the page
      chrome flips to RTL for an Arabic visitor.
    * it does NOT redirect. lang_detect.py is deliberately absent from this
      page: bouncing someone off an error page to a language home would lose
      the one piece of information they came here with, which is that a URL
      they had is broken.

  Both the <style> and the <script> are inline and sit in <head>, so the
  resolution has happened before the sections are parsed -- no flash of all
  thirteen, and no dependency on assets/js/main.js, which this page's own
  chrome already loads separately.

  The <h1> is the digits "404" on purpose. It is the one part of the message
  that needs no language, which lets every translated line live inside its own
  correctly-tagged section instead of under a Japanese heading.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import (  # noqa: E402
    ROOT, LANGUAGES, esc, page, load_bundle, available_langs,
)

ABS_BASE = "/corvus-dev/"

# The two sentences this page says, per language. They live here rather than in
# data/i18n/*.json for the same reason site_common.NAV_LABEL_FALLBACK does: this
# is the one page that must still render correctly when a bundle is missing or
# half-written, since it is what a visitor sees when everything else has already
# gone wrong. The link LABELS below do come from the bundles (ui.nav), so the
# buttons always read exactly like the site's own navigation.
MESSAGES = {
    "ja": ("ページが見つかりません",
           "お探しのページは移動または削除された可能性があります。下のリンクからお進みください。"),
    "en": ("Page not found",
           "The page you are looking for may have moved or been removed. Try one of the links below."),
    "es": ("Página no encontrada",
           "Es posible que la página que buscas se haya movido o eliminado. Prueba con uno de estos enlaces."),
    "fr": ("Page introuvable",
           "La page que vous cherchez a peut-être été déplacée ou supprimée. Essayez l'un des liens ci-dessous."),
    "zh": ("找不到页面",
           "您要找的页面可能已被移动或删除。请尝试下面的链接。"),
    "ko": ("페이지를 찾을 수 없습니다",
           "찾으시는 페이지가 이동되었거나 삭제되었을 수 있습니다. 아래 링크를 이용해 주십시오."),
    "pt-br": ("Página não encontrada",
              "A página que você procura pode ter sido movida ou removida. Tente um dos links abaixo."),
    "it": ("Pagina non trovata",
           "La pagina che cerchi potrebbe essere stata spostata o rimossa. Prova uno dei link qui sotto."),
    "ar": ("الصفحة غير موجودة",
           "قد تكون الصفحة التي تبحث عنها قد نُقلت أو حُذفت. جرّب أحد الروابط أدناه."),
    "ru": ("Страница не найдена",
           "Возможно, страница, которую вы ищете, была перемещена или удалена. Попробуйте одну из ссылок ниже."),
    "id": ("Halaman tidak ditemukan",
           "Halaman yang kamu cari mungkin sudah dipindahkan atau dihapus. Coba salah satu tautan di bawah ini."),
    "de": ("Seite nicht gefunden",
           "Die gesuchte Seite wurde womöglich verschoben oder entfernt. Probier einen der Links unten."),
    "tr": ("Sayfa bulunamadı",
           "Aradığınız sayfa taşınmış veya kaldırılmış olabilir. Aşağıdaki bağlantılardan birini deneyin."),
}

# Where each button goes, and which ui.nav key names it.
TARGETS = (("home", ""), ("recipes", "recipes/"), ("changelog", "changelog/"))

_DIR = {c: d for c, _n, d in LANGUAGES}


def _lang_base(lang):
    return ABS_BASE if lang == "ja" else f"{ABS_BASE}{lang}/"


def _section(lang):
    bundle = load_bundle(lang)
    nav = bundle["ui"]["nav"]
    heading, lede = MESSAGES[lang]
    base = _lang_base(lang)
    buttons = "".join(
        f'<a class="btn{"" if i == 0 else " btn--ghost"}" href="{esc(base + slug)}">'
        f'{esc(nav.get(key, key))}</a>'
        for i, (key, slug) in enumerate(TARGETS)
    )
    return f"""<section class="nf nf--{esc(lang)}" lang="{esc(lang)}" dir="{_DIR.get(lang, 'ltr')}">
    <h2 style="margin-top:0">{esc(heading)}</h2>
    <p class="lede">{esc(lede)}</p>
    <div class="tag-row" style="margin-top:20px;">{buttons}</div>
  </section>"""


def build():
    langs = [c for c in available_langs() if c in MESSAGES]
    missing = [c for c in MESSAGES if c not in langs]
    if missing:
        # Not fatal: a language with no bundle yet simply is not offered. But
        # it must be said out loud, because the failure it hides -- a visitor
        # sent to a language that is not published -- is invisible on the page.
        print(f"  NOTE: no bundle yet for {', '.join(missing)}; those sections are omitted.")

    sections = "\n  ".join(_section(c) for c in langs)
    dirs = json.dumps({c: _DIR.get(c, "ltr") for c in langs}, separators=(",", ":"))
    codes = json.dumps(langs, separators=(",", ":"))

    # data-nf is set BEFORE the sections are parsed, so nothing flashes; with no
    # scripting the attribute never appears and every section stays visible.
    head = f"""<style>
:root[data-nf] .nf {{ display: none; }}
{chr(10).join(f':root[data-nf="{c}"] .nf--{c} {{ display: block; }}' for c in langs)}
.nf + .nf {{ margin-top: 32px; padding-top: 32px; border-top: 1px solid var(--border, rgba(128,128,128,.3)); }}
:root[data-nf] .nf + .nf {{ margin-top: 0; padding-top: 0; border-top: 0; }}
</style>
<script>
(function () {{
  var CODES = {codes}, DIRS = {dirs};
  function known(c) {{ return c && CODES.indexOf(c) >= 0 ? c : null; }}
  function fromTag(t) {{
    t = String(t || "").toLowerCase().replace(/_/g, "-");
    if (!t) return null;
    if (known(t)) return t;
    var base = t.split("-")[0];
    /* Same three special cases as scripts/lang_detect.py, and for the same
       reasons: Brazilian is the only Portuguese and Simplified the only
       Chinese we publish, and "in" is the pre-1989 code some clients still
       send for Indonesian. */
    if (base === "pt") return known("pt-br");
    if (base === "zh") return known("zh");
    if (base === "in") return known("id");
    return known(base);
  }}
  try {{
    var tags = (navigator.languages && navigator.languages.length)
      ? navigator.languages : [navigator.language];
    for (var i = 0; i < tags.length; i++) {{
      var hit = fromTag(tags[i]);
      if (hit) {{
        var el = document.documentElement;
        el.setAttribute("data-nf", hit);
        el.setAttribute("lang", hit);
        el.setAttribute("dir", DIRS[hit] || "ltr");
        return;
      }}
    }}
  }} catch (e) {{ /* leave every section visible -- that is the safe state */ }}
}})();
</script>
"""

    body = f"""
<div class="hero">
  <h1 style="margin-bottom:8px">404</h1>
  {sections}
</div>
"""
    ja = MESSAGES["ja"]
    html = page(
        lang="ja",
        section="",
        title=ja[0],
        description="404 Not Found",
        active="",
        body=body,
        extra_head=head,
        absolute_base=ABS_BASE,
    )
    (ROOT / "404.html").write_text(html, encoding="utf-8")
    print(f"wrote 404.html ({len(html):,} bytes, {len(langs)} languages)")


if __name__ == "__main__":
    build()
