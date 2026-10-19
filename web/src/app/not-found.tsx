import "./globals.css";
import { BASE_PATH, asset, LANGUAGES, pathOf } from "@/lib/site";
import { wiki } from "@/lib/wiki";

/**
 * 404.html, served by GitHub Pages for any missing path. One document in all 13 languages: an
 * inline script shows the visitor's own (navigator.languages) and hides the rest; without
 * JavaScript every language stays visible. No redirect, as before.
 */
export default function NotFound() {
  const w = wiki();
  const codes = LANGUAGES.map((l) => l.code);
  const css =
    ":root[data-nf] .ac-nf{display:none}" +
    codes.map((c) => `:root[data-nf="${c}"] .ac-nf--${c}{display:block}`).join("") +
    ":root[data-nf] .ac-nf+.ac-nf{margin:0;padding:0;border:0}";
  const pick =
    `(function(){var C=${JSON.stringify(codes)},D=${JSON.stringify(Object.fromEntries(LANGUAGES.map((l) => [l.code, l.dir])))};` +
    `function t(x){x=String(x||"").toLowerCase().replace(/_/g,"-");if(C.indexOf(x)>=0)return x;var b=x.split("-")[0];` +
    `if(b==="pt")return"pt-br";if(b==="in")b="id";return C.indexOf(b)>=0?b:null}` +
    `var n=navigator.languages&&navigator.languages.length?navigator.languages:[navigator.language];` +
    `for(var i=0;i<n.length;i++){var c=t(n[i]);if(c){var r=document.documentElement;r.setAttribute("data-nf",c);` +
    `r.setAttribute("lang",c);r.setAttribute("dir",D[c]);break}}})();`;
  return (
    <html lang="ja" dir="ltr">
      <head>
        <title>{w.site.notFoundTitle}</title>
        <meta name="robots" content="noindex" />
        <meta name="theme-color" content="#000000" />
        <link rel="icon" href={asset("wiki/corvus/favicon.ico")} sizes="any" />
        <style dangerouslySetInnerHTML={{ __html: css }} />
        <script dangerouslySetInnerHTML={{ __html: pick }} />
      </head>
      <body className="ac-nf-body">
        <a className="ac-nf-brand" href={`${BASE_PATH}/`}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={asset("logo.png")} alt="" width={22} height={22} />
          <span>{w.site.title}</span>
        </a>
        <main className="ac-wrap ac-nf-wrap">
          <h1 className="ac-display ac-gradient-text">404</h1>
          {LANGUAGES.map((l) => {
            const d = w.langs[l.code];
            return (
              <section key={l.code} className={`ac-nf ac-nf--${l.code}`} lang={l.code} dir={l.dir}>
                <h2 className="ac-h2">{d.notFound.heading}</h2>
                <p className="ac-lead">{d.notFound.body}</p>
                <p className="ac-nf-btns">
                  <a className="ac-btn" href={`${BASE_PATH}${pathOf(l.code, "")}`}>
                    {d.chrome.home}
                  </a>
                  <a className="ac-btn ac-btn--ghost" href={`${BASE_PATH}${pathOf(l.code, "recipes/")}`}>
                    {d.chrome.recipes}
                  </a>
                  <a className="ac-btn ac-btn--ghost" href={`${BASE_PATH}${pathOf(l.code, "changelog/")}`}>
                    {d.chrome.changelog}
                  </a>
                </p>
              </section>
            );
          })}
        </main>
      </body>
    </html>
  );
}
