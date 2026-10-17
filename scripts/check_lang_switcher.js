/* Behavioural gate for the entry-time language detector.
 *
 * Drives the REAL shipped assets/js/lang.js with the REAL per-page config
 * extracted from the REAL built HTML, under mocked browser globals. Nothing
 * here re-implements the resolution logic, so if the generator stops emitting
 * the config, or lang.js stops defining the global, or a decision changes,
 * this goes red rather than quietly agreeing with itself.
 *
 *   node scripts/check_lang_switcher.js          # after a build
 *
 * Shown to go RED against deliberate breaks: region checked before device
 * language (2 failures), the same-origin-referrer guard removed (5), the
 * redirect target off by one language (3, including WRONG DESTINATION), the
 * one-shot session marker removed (1), both anti-loop legs removed at once
 * (chain length 4 = a real loop), the flag-emoji threshold inverted (2).
 */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const REPO = process.argv[2] || path.resolve(__dirname, "..");

const LANG_JS = fs.readFileSync(path.join(REPO, "assets/js/lang.js"), "utf8");

// ---------------------------------------------------------------- page config
function pageFile(urlPath, mount) {
  let rel = urlPath;
  if (!rel.startsWith(mount)) throw new Error(`path ${urlPath} outside mount ${mount}`);
  rel = rel.slice(mount.length);
  return path.join(REPO, rel, "index.html");
}
const cfgCache = new Map();
function configFor(urlPath, mount) {
  const f = pageFile(urlPath, mount);
  if (!cfgCache.has(f)) {
    const html = fs.readFileSync(f, "utf8");
    const m = html.match(/__corvusLangInit\((\{[\s\S]*?\})\);<\/script>/);
    if (!m) throw new Error(`no __corvusLangInit config in ${f}`);
    cfgCache.set(f, JSON.parse(m[1]));
  }
  return cfgCache.get(f);
}

// ------------------------------------------------------------------- sandbox
function makeStore(initial, broken) {
  const data = Object.assign({}, initial || {});
  const die = () => { throw new Error("storage disabled"); };
  return {
    getItem: k => broken ? die() : (k in data ? data[k] : null),
    setItem: (k, v) => broken ? die() : (data[k] = String(v)),
    removeItem: k => broken ? die() : delete data[k],
    _data: data,
  };
}

/* opts: {url, mount, referrer, languages, timeZone, local, session,
 *        localBroken, sessionBroken, canvasWidths} */
function run(opts) {
  const mount = opts.mount || "/";
  const cfg = configFor(opts.url, mount);
  const calls = [];
  const classes = new Set(["js"]);

  const canvas = opts.canvasWidths
    ? { getContext: () => ({ set font(v) { }, measureText: t => ({ width: opts.canvasWidths(t) }) }) }
    : { getContext: () => null };   // -> composesFlags() false

  const win = {};
  const sandbox = {
    window: win,
    document: {
      referrer: opts.referrer || "",
      createElement: n => (n === "canvas" ? canvas : {}),
      documentElement: { classList: { add: c => classes.add(c) } },
    },
    location: {
      pathname: opts.url,
      origin: opts.origin || "https://example.test",
      search: opts.search || "",
      hash: opts.hash || "",
      replace: u => calls.push(u),
    },
    navigator: { languages: opts.languages || [], language: (opts.languages || [])[0] },
    localStorage: makeStore(opts.local, opts.localBroken),
    sessionStorage: makeStore(opts.session, opts.sessionBroken),
    Intl: {
      DateTimeFormat: function () {
        return { resolvedOptions: () => ({ timeZone: opts.timeZone }) };
      },
    },
    console,
  };
  sandbox.globalThis = sandbox;
  win.navigator = sandbox.navigator;
  win.sessionStorage = sandbox.sessionStorage;
  win.localStorage = sandbox.localStorage;
  vm.createContext(sandbox);
  vm.runInContext(LANG_JS, sandbox, { filename: "lang.js" });
  if (typeof win.__corvusLangInit !== "function")
    throw new Error("lang.js did not define window.__corvusLangInit");
  win.__corvusLangInit(cfg);

  return {
    decision: win.__corvusLang.decision,
    diag: win.__corvusLang,
    redirects: calls,
    classes: [...classes],
    local: sandbox.localStorage._data,
    session: sandbox.sessionStorage._data,
  };
}

// -------------------------------------------------------------------- assert
let pass = 0, fail = 0;
const failures = [];
function check(name, got, want) {
  const g = JSON.stringify(got), w = JSON.stringify(want);
  if (g === w) { pass++; return true; }
  fail++; failures.push(`${name}\n     got  ${g}\n     want ${w}`);
  return false;
}
function note(s) { console.log(s); }

// resolve a relative redirect target against the page it came from
function resolveTarget(fromPath, rel) {
  const base = fromPath.endsWith("/") ? fromPath : fromPath + "/";
  let p = path.posix.normalize(path.posix.join(base, rel));
  if (!p.endsWith("/")) p += "/";
  return p;
}

module.exports = { run, check, resolveTarget, configFor };

// ============================================================ THE TEST MATRIX
if (require.main === module) {
  const MOUNTS = ["/", "/corvus-dev/"];

  note("=== A. resolution order, mocked devices ===");
  const M = "/";
  const CASES = [
    // name, page, env, expected decision
    ["JA device in Japan, lands on JA root",
      "/", { languages: ["ja-JP", "ja"], timeZone: "Asia/Tokyo" },
      { act: "stay", why: "already-correct" }],
    ["EN device in Japan, lands on JA root -> English (device beats region)",
      "/", { languages: ["en-US", "en"], timeZone: "Asia/Tokyo" },
      { act: "go", to: "en", why: "detected" }],
    ["JA device in Germany, lands on JA root -> stays (device beats region)",
      "/", { languages: ["ja-JP"], timeZone: "Europe/Berlin" },
      { act: "stay", why: "already-correct" }],
    ["DE device in Germany, lands on JA root -> German",
      "/", { languages: ["de-DE", "de"], timeZone: "Europe/Berlin" },
      { act: "go", to: "de", why: "detected" }],
    ["pt-PT device -> pt-br (only Portuguese available)",
      "/", { languages: ["pt-PT", "pt"], timeZone: "Europe/Lisbon" },
      { act: "go", to: "pt-br", why: "detected" }],
    ["zh-TW device -> zh (only Simplified available)",
      "/", { languages: ["zh-TW", "zh-Hant"], timeZone: "Asia/Taipei" },
      { act: "go", to: "zh", why: "detected" }],
    ["zh-Hant-HK device -> zh",
      "/", { languages: ["zh-Hant-HK"], timeZone: "Asia/Hong_Kong" },
      { act: "go", to: "zh", why: "detected" }],
    ["sv device (not in the 13) in Sweden -> region says en",
      "/", { languages: ["sv-SE", "sv"], timeZone: "Europe/Stockholm" },
      { act: "go", to: "en", why: "detected" }],
    ["mn device in Mongolia -> no signal at all, stays put",
      "/", { languages: ["mn-MN", "mn"], timeZone: "Asia/Ulaanbaatar" },
      { act: "stay", why: "no-signal" }],
    ["stored ES beats a JA device in Japan",
      "/", { languages: ["ja-JP"], timeZone: "Asia/Tokyo", local: { "corvus-dev-lang": "es" } },
      { act: "go", to: "es", why: "stored" }],
    ["stored JA on an English page beats device+region",
      "/en/", { languages: ["en-US"], timeZone: "America/New_York", local: { "corvus-dev-lang": "ja" } },
      { act: "go", to: "ja", why: "stored" }],
    ["stored EN on the English page: nothing happens",
      "/en/", { languages: ["ja-JP"], timeZone: "Asia/Tokyo", local: { "corvus-dev-lang": "en" } },
      { act: "stay", why: "stored-is-current" }],
    ["en-GB reaches en",
      "/", { languages: ["en-GB"], timeZone: "Europe/London" },
      { act: "go", to: "en", why: "detected" }],
    ["unknown device language, unknown tz, region subtag carries it",
      "/", { languages: ["sv-BR"], timeZone: "Etc/UTC" },
      { act: "go", to: "pt-br", why: "detected" }],
    ["Indonesian legacy code in-ID",
      "/", { languages: ["in-ID"], timeZone: "Asia/Jakarta" },
      { act: "go", to: "id", why: "detected" }],
    ["no Intl at all, no device match: falls to region subtag",
      "/", { languages: ["ko-KR"], timeZone: undefined },
      { act: "go", to: "ko", why: "detected" }],
    ["deep page keeps its section: DE device on /en/changelog/",
      "/en/changelog/", { languages: ["de-DE"], timeZone: "Europe/Berlin" },
      { act: "go", to: "de", why: "detected" }],
  ];
  for (const [name, url, env, want] of CASES) {
    const r = run(Object.assign({ url, mount: M }, env));
    const got = { act: r.decision.act, why: r.decision.why };
    if (r.decision.to) got.to = r.decision.to;
    const w = Object.assign({}, want);
    check("  " + name, got, { act: w.act, why: w.why, ...(w.to ? { to: w.to } : {}) });
  }

  note("=== B. never fight the visitor (same-origin referrer) ===");
  {
    // landed on /en/, clicked 日本語 -> now on /, referrer /en/
    const r = run({
      url: "/", mount: M, referrer: "https://example.test/en/",
      languages: ["en-US"], timeZone: "America/New_York",
    });
    check("  /en/ -> / via switcher: no redirect",
      { act: r.decision.act, redirects: r.redirects.length }, { act: "stay", redirects: 0 });
    check("  ...and the choice is adopted so it survives the visit",
      r.local["corvus-dev-lang"], "ja");
  }
  {
    // stored=en, but they deliberately navigated to the JA page in-site
    const r = run({
      url: "/", mount: M, referrer: "https://example.test/en/",
      languages: ["en-US"], timeZone: "America/New_York",
      local: { "corvus-dev-lang": "en" },
    });
    check("  stored EN + in-site nav to JA: still no redirect",
      { act: r.decision.act, redirects: r.redirects.length }, { act: "stay", redirects: 0 });
    check("  ...and stored flips to ja", r.local["corvus-dev-lang"], "ja");
  }
  {
    // ordinary in-site nav within one language must NOT rewrite the preference
    const r = run({
      url: "/changelog/", mount: M, referrer: "https://example.test/",
      languages: ["en-US"], timeZone: "America/New_York",
    });
    check("  in-site nav within JA: no redirect, no adoption",
      { act: r.decision.act, stored: r.local["corvus-dev-lang"] || null },
      { act: "stay", stored: null });
  }
  {
    // 404-style: referrer is a DIFFERENT section, so it is not the switcher
    const r = run({
      url: "/", mount: M, referrer: "https://example.test/en/changelog/",
      languages: ["en-US"], timeZone: "America/New_York",
    });
    check("  in-site nav across language AND section: no adoption",
      r.local["corvus-dev-lang"] || null, null);
  }
  {
    const r = run({
      url: "/", mount: M, referrer: "https://www.google.com/search?q=x",
      languages: ["de-DE"], timeZone: "Europe/Berlin",
    });
    check("  cross-origin referrer still counts as an entry",
      { act: r.decision.act, to: r.decision.to }, { act: "go", to: "de" });
  }

  note("=== C. one redirect per session, fail-closed storage ===");
  {
    const r = run({
      url: "/", mount: M, languages: ["de-DE"], timeZone: "Europe/Berlin",
      session: { "corvus-dev-lang-redirected": "1" },
    });
    check("  marker already set: decision is still go, but nothing navigates",
      { act: r.decision.act, redirects: r.redirects.length }, { act: "go", redirects: 0 });
  }
  {
    const r = run({
      url: "/", mount: M, languages: ["de-DE"], timeZone: "Europe/Berlin",
      sessionBroken: true,
    });
    check("  sessionStorage unusable: refuses to redirect at all",
      r.redirects.length, 0);
  }
  {
    const r = run({
      url: "/", mount: M, languages: ["de-DE"], timeZone: "Europe/Berlin",
      localBroken: true,
    });
    check("  localStorage unusable: still detects and redirects once",
      { n: r.redirects.length, to: r.redirects[0] }, { n: 1, to: "./de/" });
  }
  {
    const r = run({
      url: "/recipes/", mount: M, languages: ["de-DE"], timeZone: "Europe/Berlin",
      search: "?q=1", hash: "#cat3",
    });
    check("  query and fragment survive the redirect",
      r.redirects[0], "../de/recipes/?q=1#cat3");
  }

  note("=== D. loop proof: every language x every page x every device ===");
  {
    const SECTIONS = ["", "download/", "changelog/", "recipes/", "guide/",
      "launcher/", "gates/", "features/", "roadmap/", "known-issues/"];
    const LANGS = ["ja", "en", "es", "fr", "zh", "ko", "pt-br", "it", "ar", "ru", "id", "de", "tr"];
    const DEVICES = [
      { languages: ["ja-JP"], timeZone: "Asia/Tokyo" },
      { languages: ["en-US"], timeZone: "America/New_York" },
      { languages: ["de-DE"], timeZone: "Europe/Berlin" },
      { languages: ["pt-PT"], timeZone: "Europe/Lisbon" },
      { languages: ["zh-TW"], timeZone: "Asia/Taipei" },
      { languages: ["sv-SE"], timeZone: "Europe/Stockholm" },
      { languages: ["mn-MN"], timeZone: "Asia/Ulaanbaatar" },
      { languages: ["ar-SA"], timeZone: "Asia/Riyadh" },
      { languages: [], timeZone: undefined },
    ];
    const STORED = [null, "ja", "en", "tr"];
    let hops = 0, worst = 0, loops = 0, checked = 0, wrongDest = 0;
    const cfg0 = (u, m) => configFor(u, m);
    /* keepReferrer=false is the WORST CASE and the one that actually tests
       legs (a) and (b): a browser that strips the referrer (privacy mode, a
       future Referrer-Policy header) removes the "internal navigation" guard
       entirely, so the chain has to terminate on the fixed point and the
       one-shot marker alone. The first cut of this walk propagated the
       referrer, and every chain terminated on the referrer guard -- it was
       green for the wrong reason. */
    for (const keepReferrer of [false, true]) {
    for (const mount of MOUNTS) {
      for (const lang of LANGS) {
        for (const section of SECTIONS) {
          for (const dev of DEVICES) {
            for (const stored of STORED) {
              let url = mount + (lang === "ja" ? "" : lang + "/") + section;
              const session = {};
              const local = stored ? { "corvus-dev-lang": stored } : {};
              let referrer = "";           // an ENTRY: no referrer at all
              let n = 0;
              checked++;
              while (true) {
                const r = run({
                  url, mount, referrer, local, session,
                  languages: dev.languages, timeZone: dev.timeZone,
                  origin: "https://example.test",
                });
                Object.assign(local, r.local);
                Object.assign(session, r.session);
                if (!r.redirects.length) break;
                n++; hops++;
                if (n > 3) { loops++; failures.push(`  LOOP from ${url}`); break; }
                const next = resolveTarget(url, r.redirects[0]);
                // Leg (a) of the anti-loop argument, measured rather than
                // asserted: the page we land on really is the language we
                // asked for, and really is the same section.
                const dest = configFor(next, mount);
                if (dest.c !== r.decision.to || dest.s !== cfg0(url, mount).s) {
                  wrongDest++;
                  failures.push(`  WRONG DESTINATION ${url} -> ${next}` +
                    ` (wanted ${r.decision.to}/${cfg0(url, mount).s},` +
                    ` got ${dest.c}/${dest.s})`);
                }
                referrer = keepReferrer ? "https://example.test" + url : "";
                url = next;
              }
              worst = Math.max(worst, n);
            }
          }
        }
      }
    }
    }
    note(`  walked ${checked} entry states, ${hops} redirects, longest chain ${worst}`);
    check("  no chain ever exceeds ONE redirect", { worst, loops }, { worst: 1, loops: 0 });
    check("  every redirect lands on the language+section it asked for",
      wrongDest, 0);
  }

  note("=== E. flag-emoji capability probe ===");
  {
    // A platform that composes: the pair is one glyph, ~ the width of one
    // regional indicator.
    const composing = run({
      url: "/", mount: M, languages: ["ja-JP"], timeZone: "Asia/Tokyo",
      canvasWidths: t => (t.length === 4 ? 32 : 30),
    });
    check("  composing platform: no fallback class",
      composing.classes.includes("no-flag-emoji"), false);
    // Windows Chrome/Edge: two letter-boxes, twice as wide.
    const windows = run({
      url: "/", mount: M, languages: ["ja-JP"], timeZone: "Asia/Tokyo",
      canvasWidths: t => (t.length === 4 ? 60 : 30),
    });
    check("  non-composing platform: fallback class applied",
      windows.classes.includes("no-flag-emoji"), true);
    const nocanvas = run({ url: "/", mount: M, languages: ["ja-JP"], timeZone: "Asia/Tokyo" });
    check("  no 2d context at all: fails safe to the SVG flags",
      nocanvas.classes.includes("no-flag-emoji"), true);
  }

  note("");
  console.log(`${pass} passed, ${fail} failed`);
  if (fail) { console.log("\nFAILURES:"); failures.forEach(f => console.log("  - " + f)); }
  process.exit(fail ? 1 : 0);
}
