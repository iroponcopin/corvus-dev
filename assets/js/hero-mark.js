/* Corvus — the home page's opening beat, glyph half.
 *
 * Loaded by build_home.py only (extra_head), deferred, after main.js's own
 * contract. Read hero-mark.css first: it explains the whole opening. This
 * file is responsible for exactly ONE thing, and it is not "playing the
 * animation" — the mark's entire arrival is declarative CSS that needs no
 * script at all.
 *
 * WHAT THIS FILE IS FOR
 * style.css paints the wordmark by putting a gradient on the <h1> and
 * clipping it to the text (`background-clip: text`, `color: transparent`).
 * Under that model the ink belongs to the <h1>, not to the glyphs — and the
 * moment a glyph is TRANSFORMED, the parent's text clip and the glyph's own
 * position disagree about where that letter is, so it paints twice, offset,
 * and the two copies union into a solid dilated slab. That is not a
 * prediction: it shipped that way for one round and the "A" rendered as a
 * white blob for the whole 0.8s of its animation, in headless Chrome 151 at
 * both device scale factors and with and without GPU raster. Hiding the
 * glyphs made the blob vanish; clearing the <h1>'s own background-image with
 * the glyphs left alone fixed it outright.
 *
 * So each glyph has to carry its own background, and hero-mark.css has to
 * take the <h1>'s away (`.is-lit { background-image: none }`). If each glyph
 * then simply repeated the gradient, the word would read as twelve little
 * gradients instead of one long one, which is worse than not animating at
 * all. So every glyph gets the SAME gradient, sized to the whole word and
 * offset by that glyph's own position — one continuous ramp, twelve
 * independently animatable boxes.
 *
 * Two properties are load-bearing here:
 *   1. The gradient is COPIED off the <h1>'s computed style rather than
 *      restated. style.css stays the single source of truth for the
 *      wordmark's colour, and the copy is re-taken when the theme changes.
 *   2. Positions are read with offsetLeft/offsetTop, never
 *      getBoundingClientRect(). The glyphs are already carrying the `from`
 *      keyframe's transform by the time this runs (animation-fill-mode:
 *      both), so their client rects are the ANIMATED rects; offset* is the
 *      layout position and is transform-free. Reading rects here produces a
 *      gradient that is subtly wrong for exactly as long as the animation
 *      runs, and right afterwards — which is the kind of bug that survives a
 *      screenshot taken at the end.
 *
 * PERFORMANCE
 * Nothing in this file runs per frame, and nothing here touches scroll.
 * There is one layout read, at startup, and one more per resize/theme change
 * — all outside any scroll or animation path. It adds no listener that can
 * fire during a scroll or a touch.
 *
 * FAILURE MODE
 * If anything here throws or never runs, `is-lit` is never added; every
 * per-glyph rule in hero-mark.css is gated on it, so the wordmark falls
 * straight back to style.css's own `film-in` fade. The mark is unaffected
 * either way.
 */
(function () {
  "use strict";

  var root = document.documentElement;

  // Same check main.js makes. Under reduced motion hero-mark.css contributes
  // nothing, so lighting the glyphs would only change the paint path for a
  // picture that is meant to be identical to the no-JS one.
  var reducedMotion = false;
  try {
    reducedMotion = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (e) {
    reducedMotion = false;
  }
  if (reducedMotion) return;

  var word = document.getElementById("filmWord");
  if (!word) return;
  var glyphs = Array.prototype.slice.call(word.querySelectorAll(".hm-g"));
  if (!glyphs.length) return;

  var mark = document.querySelector(".film__scene--title .film__mark.hm");

  var lastW = -1;
  var lastH = -1;

  // The <h1>'s own gradient, with var() resolved to real colours. It can only
  // be read while `is-lit` is off, because `is-lit` sets background-image to
  // none on the <h1> — hence the remove/read/add dance on re-capture. That is
  // synchronous, so no frame is ever committed in between and nothing
  // flickers; it costs one forced style recalc on an event that happens at
  // most a handful of times in a session.
  //
  // Known, accepted side effect: the glyph rules are keyed on the same class,
  // so a theme toggle during the ~2s the opening is still running restarts the
  // letter stagger (it re-resolves, in the new theme's colours). After that
  // the `is-done` rule has already stopped those animations, so the toggle
  // costs nothing. The first call happens before `is-lit` exists and therefore
  // never toggles anything.
  function readGradient() {
    var lit = word.classList.contains("is-lit");
    if (lit) word.classList.remove("is-lit");
    var g = "";
    try { g = window.getComputedStyle(word).backgroundImage; } catch (e) { g = ""; }
    if (lit) word.classList.add("is-lit");
    return (g && g !== "none") ? g : "";
  }

  // Hand every glyph its slice. Ordering matters: `is-lit` makes the glyphs
  // inline-block, which changes their layout positions, so the class has to
  // be on BEFORE anything is measured. All of it happens inside one task, so
  // the browser resolves style once and paints once, at the end.
  function light() {
    var grad = readGradient();
    if (!grad) return false;            // style.css missing: leave it alone

    word.style.setProperty("--wm-grad", grad);
    word.classList.add("is-lit");
    position();
    return true;
  }

  // Absolute layout offset, summed up the offsetParent chain to the root.
  //
  // Summing rather than taking a single offsetLeft is not defensiveness, it
  // is a bug fix: Chromium reports the <h1> ITSELF as the offsetParent of the
  // glyphs, so `glyph.offsetLeft - word.offsetLeft` double-counts the word's
  // own position and every slice lands in the wrong place. Summing both to
  // the root and subtracting cancels whatever the shared chain above the
  // wordmark happens to be, and is correct whether or not the <h1> is the
  // offsetParent — which is exactly the kind of thing that quietly differs
  // between engines and between the pinned and static layouts.
  function chain(el) {
    var x = 0, y = 0, n = el;
    while (n) { x += n.offsetLeft; y += n.offsetTop; n = n.offsetParent; }
    return [x, y];
  }

  function position() {
    // Layout positions, not client rects — see the header comment.
    var w = word.offsetWidth;
    var h = word.offsetHeight;
    if (!w || !h) return;

    var base = chain(word);

    lastW = w;
    lastH = h;
    word.style.setProperty("--wm-w", w + "px");
    word.style.setProperty("--wm-h", h + "px");

    for (var i = 0; i < glyphs.length; i++) {
      var g = glyphs[i];
      var at = chain(g);
      // The glyph's offset inside the wordmark's own box — including which
      // line it is on, once the name wraps to two lines on a narrow phone.
      g.style.setProperty("--gx", (at[0] - base[0]) + "px");
      g.style.setProperty("--gy", (at[1] - base[1]) + "px");
    }
  }

  if (!light()) return;

  // --- re-measure, off every hot path -----------------------------------
  var pending = false;
  function remeasure() {
    pending = false;
    if (word.offsetWidth === lastW && word.offsetHeight === lastH) return;
    position();
  }
  function queue() {
    if (pending) return;
    pending = true;
    window.requestAnimationFrame(remeasure);
  }
  window.addEventListener("resize", queue, { passive: true });
  window.addEventListener("orientationchange", queue, { passive: true });

  // Web-font metrics can still move the glyphs after first paint. On Apple
  // hardware the display stack resolves to SF before Inter is ever fetched,
  // so this usually resolves immediately and changes nothing.
  if (document.fonts && document.fonts.ready && document.fonts.ready.then) {
    document.fonts.ready.then(queue).catch(function () {});
  }

  // The theme toggle rewrites data-theme on <html>, which changes --text and
  // --accent-strong and therefore the gradient itself. Re-copy it; positions
  // are unaffected.
  if (window.MutationObserver) {
    var mo = new MutationObserver(function () {
      var grad = readGradient();
      if (grad) word.style.setProperty("--wm-grad", grad);
    });
    mo.observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  }

  // --- release the promoted layers when the opening has landed -----------
  // hero-mark.css promotes six layers plus the glyphs for the ~2s the
  // opening runs. Leaving will-change on afterwards is the blanket-promotion
  // antipattern main.js's own comments call out, so it is dropped as soon as
  // the longest beat (the bloom, 2.1s) has finished. animationend bubbles;
  // the timer is the backstop for the case where it does not arrive at all
  // (a theme switch mid-opening restarts the bloom under a new name).
  var done = false;
  function markDone() {
    if (done) return;
    done = true;
    if (mark) mark.classList.add("is-done");
    word.classList.add("is-done");
  }
  if (mark) {
    mark.addEventListener("animationend", function (e) {
      if (e.animationName === "hm-bloom" || e.animationName === "hm-bloom-light") {
        markDone();
      }
    });
  }
  window.setTimeout(markDone, 4200);
}());
