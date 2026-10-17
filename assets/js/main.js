/* Corvus — shared behaviour layer.
 *
 * Performance contract for everything in this file (owner directive: the
 * site must feel right on a 120Hz ProMotion display, not merely on 60Hz):
 *
 *   1. There is exactly ONE scroll listener and ONE rAF loop. It reads every
 *      value it needs first, then writes — no interleaved read/write, so
 *      nothing forces a synchronous layout mid-frame.
 *   2. Nothing in the scroll path calls getBoundingClientRect(). The hero's
 *      document position is measured once and re-measured only on resize.
 *   3. Nothing here interpolates over time, so nothing is tied to a 16.67ms
 *      frame budget: the parallax is a pure function of scroll position, so
 *      it lands on the identical value whether the display refreshes 60 or
 *      120 times a second. Where a value *is* animated, it is animated by
 *      CSS on transform/opacity only, off the main thread.
 *   4. Every listener that can fire during a scroll or a touch is passive.
 *   5. will-change is set only while an element is actually animating and
 *      cleared on transitionend.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var body = document.body;

  var reducedMotion = false;
  try {
    reducedMotion = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (e) {
    reducedMotion = false;
  }

  // Desktop = the width at which the drawer stops and the mega menu starts;
  // must match the `@media (max-width: 899px)` block in style.css.
  var mqDesktop = window.matchMedia("(min-width: 900px)");
  var mqFinePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  function hoverMode() { return mqDesktop.matches && mqFinePointer.matches; }

  function isKeyboardFocus(el) {
    // :focus-visible is what separates "tabbed to" from "clicked on"; a
    // browser without it simply doesn't get focus-to-open (click still works).
    try { return el.matches(":focus-visible"); } catch (e) { return false; }
  }

  // =====================================================================
  // Mega menu (desktop hover-reveal / mobile accordion)
  // =====================================================================
  var siteNav = document.getElementById("siteNav");
  var megaItems = Array.prototype.slice.call(
    document.querySelectorAll(".nav-item--mega"));
  var openItem = null;
  var openTimer = 0;
  var closeTimer = 0;
  // Escape returns focus to the trigger; without this guard that programmatic
  // focus would satisfy :focus-visible and immediately reopen what the user
  // just dismissed.
  var suppressFocusOpen = false;

  // Hover intent. OPEN_DELAY stops the panel flashing open as the cursor
  // merely crosses the bar; CLOSE_DELAY is what lets a diagonal move from
  // the nav item down into the panel survive. Once a panel is already open,
  // moving to a sibling switches instantly — that is what makes Apple's bar
  // feel decisive rather than sticky.
  var OPEN_DELAY = 130;
  var CLOSE_DELAY = 220;

  function clearTimers() {
    if (openTimer) { clearTimeout(openTimer); openTimer = 0; }
    if (closeTimer) { clearTimeout(closeTimer); closeTimer = 0; }
  }

  function setItemOpen(item, open) {
    if (!item) return;
    var btn = item.querySelector(".nav-link--mega");
    item.classList.toggle("is-open", open);
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function openMega(item) {
    clearTimers();
    if (openItem && openItem !== item) setItemOpen(openItem, false);
    openItem = item;
    setItemOpen(item, true);
  }

  function closeMega(item) {
    clearTimers();
    setItemOpen(item, false);
    if (openItem === item) openItem = null;
  }

  function closeAllMega() {
    clearTimers();
    megaItems.forEach(function (it) { setItemOpen(it, false); });
    openItem = null;
  }

  megaItems.forEach(function (item) {
    var btn = item.querySelector(".nav-link--mega");
    if (!btn) return;

    btn.addEventListener("click", function (e) {
      e.preventDefault();
      if (item.classList.contains("is-open")) closeMega(item);
      else openMega(item);
    });

    // Keyboard: tabbing onto the trigger reveals its panel, so the grouped
    // links are reachable in DOM order without any extra key. (Closed panels
    // are visibility:hidden in CSS, which keeps them out of the tab order.)
    btn.addEventListener("focus", function () {
      if (suppressFocusOpen) return;
      if (isKeyboardFocus(btn)) openMega(item);
    });

    // Focus leaving the whole item (trigger + panel) closes it.
    item.addEventListener("focusout", function (e) {
      var to = e.relatedTarget;
      if (!to || !item.contains(to)) {
        if (item.classList.contains("is-open") && !item.matches(":hover")) {
          closeMega(item);
        }
      }
    });

    item.addEventListener("mouseenter", function () {
      if (!hoverMode()) return;
      clearTimers();
      if (openItem && openItem !== item) {
        openMega(item);            // already browsing the bar: switch at once
      } else if (!openItem) {
        openTimer = setTimeout(function () { openMega(item); }, OPEN_DELAY);
      }
    });

    item.addEventListener("mouseleave", function () {
      if (!hoverMode()) return;
      if (openTimer) { clearTimeout(openTimer); openTimer = 0; }
      if (!item.classList.contains("is-open")) return;
      closeTimer = setTimeout(function () { closeMega(item); }, CLOSE_DELAY);
    });

    // Following a link inside the panel should not leave it hanging open
    // when the browser restores this page from the back/forward cache.
    item.querySelectorAll(".mega-link").forEach(function (a) {
      a.addEventListener("click", function () { closeMega(item); });
    });
  });

  // =====================================================================
  // Mobile drawer
  // =====================================================================
  var navToggle = document.getElementById("navToggle");
  var navScrim = document.getElementById("navScrim");
  var drawerOpen = false;
  var lockedScrollY = 0;

  function lockScroll() {
    lockedScrollY = window.scrollY || window.pageYOffset || 0;
    body.style.position = "fixed";
    body.style.top = -lockedScrollY + "px";
    body.style.left = "0";
    body.style.right = "0";
    body.style.width = "100%";
  }

  function unlockScroll() {
    body.style.position = "";
    body.style.top = "";
    body.style.left = "";
    body.style.right = "";
    body.style.width = "";
    // html.js sets scroll-behavior:smooth; restoring the position must not
    // become a visible animated scroll back to where the user already was.
    var prev = root.style.scrollBehavior;
    root.style.scrollBehavior = "auto";
    window.scrollTo(0, lockedScrollY);
    root.style.scrollBehavior = prev;
  }

  function setDrawer(open) {
    if (open === drawerOpen) return;
    drawerOpen = open;
    root.classList.toggle("nav-open", open);
    if (navToggle) navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      lockScroll();
      // On mobile the panels are accordions; start with the section that
      // contains the current page already expanded.
      var current = siteNav && siteNav.querySelector(".mega-link.is-current");
      var host = current && current.closest(".nav-item--mega");
      if (host) setItemOpen(host, true);
    } else {
      unlockScroll();
      closeAllMega();
    }
  }

  if (navToggle && siteNav) {
    navToggle.addEventListener("click", function () { setDrawer(!drawerOpen); });
    if (navScrim) {
      navScrim.addEventListener("click", function () { setDrawer(false); });
    }
    // Any real navigation closes the drawer.
    siteNav.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () { setDrawer(false); });
    });
    // Growing past the drawer breakpoint must not leave the body locked.
    var onBreakpoint = function () { if (mqDesktop.matches) setDrawer(false); };
    if (mqDesktop.addEventListener) mqDesktop.addEventListener("change", onBreakpoint);
    else if (mqDesktop.addListener) mqDesktop.addListener(onBreakpoint);
  }

  // =====================================================================
  // Language switcher dropdown
  // =====================================================================
  var langToggle = document.getElementById("langToggle");
  var langSwitch = langToggle && langToggle.closest(".lang-switch");
  function closeLang() {
    if (!langSwitch) return;
    langSwitch.classList.remove("open");
    langToggle.setAttribute("aria-expanded", "false");
  }
  if (langToggle && langSwitch) {
    langToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = langSwitch.classList.toggle("open");
      langToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // ---- persist an explicit language choice ----------------------------
  // THE KEY NAME IS A CONTRACT with the language detector loaded in the
  // <head> (assets/js/lang.js, generated from scripts/lang_detect.py),
  // exactly like the theme key above. Change one side and you must change
  // the other; grep "corvus-dev-lang" to find them together.
  //
  // The detector treats a stored value as the visitor's own decision and
  // honours it over device language and region FOREVER, so it is written
  // here and nowhere else. "auxclick" is not decoration: a middle-click
  // opens the link in a new tab and never fires "click", so without it a
  // middle-clicked language would not stick. (Right-click -> "open link in
  // new tab" fires neither; that case is covered on the far side, where the
  // detector refuses to redirect anything that arrived with a same-origin
  // referrer.)
  if (langSwitch) {
    var rememberLang = function (e) {
      var a = e.target && e.target.closest && e.target.closest("a[data-lang]");
      if (!a) return;
      try {
        localStorage.setItem("corvus-dev-lang", a.getAttribute("data-lang"));
      } catch (err) { /* storage unavailable: the link still navigates */ }
    };
    langSwitch.addEventListener("click", rememberLang);
    langSwitch.addEventListener("auxclick", rememberLang);
  }

  // ---- one shared document-level dismissal path -----------------------
  document.addEventListener("click", function (e) {
    if (langSwitch && !langSwitch.contains(e.target)) closeLang();
    // Only on the desktop bar: inside the mobile drawer the panels are
    // accordions, and collapsing one because the user tapped the drawer's
    // own padding would just feel broken.
    if (mqDesktop.matches && openItem && !openItem.contains(e.target)) closeAllMega();
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" && e.key !== "Esc") return;
    closeLang();
    if (openItem) {
      var btn = openItem.querySelector(".nav-link--mega");
      closeAllMega();
      if (btn) {
        suppressFocusOpen = true;
        btn.focus();
        suppressFocusOpen = false;
      }
      return;
    }
    if (drawerOpen) {
      setDrawer(false);
      if (navToggle) navToggle.focus();
    }
  });

  // =====================================================================
  // Theme
  // ---------------------------------------------------------------------
  // 2026-09-10、所有者:「白と黒のテーマ変更を廃止に。」
  // 切り替えは廃止した。見た目は 1 つだけで、data-attribute は shell の
  // boot script が dark に固定する。ここに在った localStorage の読み書きと
  // 旧キーからの移行は、保存すべき選択が無くなったので<b>丸ごと消した</b> ——
  // 使われないコードを「念のため」残すと、次に読む人がまだ切り替えが
  // あるものとして扱う。
  // =====================================================================

  // =====================================================================
  // Scroll-driven chrome — the single rAF loop
  // =====================================================================
  var header = document.querySelector(".site-header");
  var hero = document.querySelector(".hero");
  var heroTop = 0;
  var heroHeight = 0;
  var scrolledState = null;
  var lastParallax = null;
  var framePending = false;

  function measureHero() {
    if (!hero) return;
    // The only layout read in this module, and it never happens inside the
    // scroll path — only at startup and on resize/orientation change.
    var rect = hero.getBoundingClientRect();
    heroTop = rect.top + (window.scrollY || window.pageYOffset || 0);
    heroHeight = rect.height;
  }

  function frame() {
    framePending = false;

    // --- read phase (no writes above this line) ---
    var y = window.scrollY || window.pageYOffset || 0;
    var vh = window.innerHeight;

    // --- write phase ---
    if (header) {
      var scrolled = y > 24;
      if (scrolled !== scrolledState) {
        scrolledState = scrolled;
        header.classList.toggle("is-scrolled", scrolled);
      }
    }

    if (hero && !reducedMotion) {
      var top = heroTop - y;
      if (top < vh + 240 && top + heroHeight > -240) {
        var offset = Math.max(-24, Math.min(24, top * -0.06));
        // Quantise to 0.1px: below that nothing is visible, and skipping the
        // write skips a style invalidation on most frames.
        offset = Math.round(offset * 10) / 10;
        if (offset !== lastParallax) {
          lastParallax = offset;
          hero.style.setProperty("--parallax", String(offset));
        }
      }
    }

  }

  function requestFrame() {
    if (framePending) return;
    framePending = true;
    window.requestAnimationFrame(frame);
  }

  function measureAll() {
    measureHero();
  }

  if (header || hero) {
    measureAll();
    frame();
    window.addEventListener("scroll", requestFrame, { passive: true });
    window.addEventListener("resize", function () {
      measureAll();
      requestFrame();
    }, { passive: true });
    window.addEventListener("orientationchange", function () {
      measureAll();
      requestFrame();
    }, { passive: true });
    // Re-measure once after load: web-font metrics can still nudge the
    // document above the hero.
    window.addEventListener("load", function () {
      measureAll();
      requestFrame();
    });
  }

  // ---------------------------------------------------------------------
  // Home opening (scene 0 of the former film). hero-mark.css pauses the
  // mark's ambient light whenever `.film__stage` lacks `is-live`, so the
  // stage is marked live only while it is actually on screen. One
  // observer and no per-frame work; without IntersectionObserver the
  // stage is simply left live.
  // ---------------------------------------------------------------------
  var filmStage = document.getElementById("filmStage");
  if (filmStage) {
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        for (var i = 0; i < entries.length; i++) {
          filmStage.classList.toggle("is-live", entries[i].isIntersecting);
        }
      }).observe(filmStage);
    } else {
      filmStage.classList.add("is-live");
    }
  }

  // =====================================================================
  // Scroll-entrance reveal
  // Progressive enhancement only: <html class="js"> is added by the inline
  // script in site_common.py's page() shell, before any of this runs. If
  // this script never executes (blocked, errors, disabled), the CSS never
  // switches .reveal into its hidden starting state, so content just stays
  // visible with no animation - see the reduced-motion block in style.css.
  // =====================================================================
  if (!reducedMotion) {
    // Elements present in the server-rendered HTML at load time. Content
    // injected later by recipes.js/changelog.js (grid cards, modal body,
    // guide panes) is intentionally not covered here - it renders straight
    // to its normal visible state, which is correct since it wasn't on
    // screen yet for a scroll-entrance to make sense of.
    // The home page's .film (the opening lockup) is excluded: it carries
    // its own entrance (hero-mark.css) and must be on screen at load, not
    // parked at opacity 0 until it intersects. The home sections under it
    // are plain `main > section`s and reveal like any other page's.
    var REVEAL_SELECTOR = [
      "main > .hero", "main > section:not(.film)",
      "main > .card", "main > .toc",
      ".grid > *", ".card-list > *", ".timeline-entry", ".callout",
      ".guide-section", ".steps > li", "main > .tab-bar", "main > h2"
    ].join(", ");

    var targets = Array.prototype.slice.call(document.querySelectorAll(REVEAL_SELECTOR));
    // De-dupe (an element can match more than one selector above) and skip
    // anything nested inside another match, so a card's own children don't
    // also get queued with their own independent delay.
    targets = targets.filter(function (el, i) {
      if (targets.indexOf(el) !== i) return false;
      for (var j = 0; j < targets.length; j++) {
        if (targets[j] !== el && targets[j].contains(el)) return false;
      }
      return true;
    });

    // Stagger delay resets per parent, so each independent list/grid on the
    // page counts its own children from 0 rather than sharing one running
    // total (which would make later sections start their reveal absurdly
    // late). Plain array since parent elements repeat across targets;
    // avoids relying on Map/WeakMap for what stays a tiny list per page.
    var groupParents = [];
    var groupCounts = [];
    targets.forEach(function (el) {
      var parent = el.parentElement;
      var gi = groupParents.indexOf(parent);
      if (gi === -1) {
        gi = groupParents.length;
        groupParents.push(parent);
        groupCounts.push(0);
      }
      el.classList.add("reveal");
      el.style.setProperty("--reveal-index", String(groupCounts[gi]));
      groupCounts[gi] += 1;
    });

    // will-change is promoted per element only for the ~0.9s its transition
    // is actually running, then dropped. Declaring it in CSS for every
    // .reveal on the page (which is what this used to do) leaves a
    // composited layer behind for every card, list item and heading — on the
    // recipes and changelog pages that is hundreds of layers held for the
    // lifetime of the page, which costs far more than it saves.
    function release(e) {
      if (e.target !== this) return;
      this.style.willChange = "";
      this.removeEventListener("transitionend", release);
    }

    if ("IntersectionObserver" in window && targets.length) {
      var io = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            var el = entry.target;
            el.style.willChange = "opacity, transform";
            el.addEventListener("transitionend", release);
            el.classList.add("is-visible");
            io.unobserve(el);
          });
        },
        { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
      );
      targets.forEach(function (el) { io.observe(el); });
    } else {
      // No IntersectionObserver support: reveal everything immediately
      // rather than leaving it permanently hidden.
      targets.forEach(function (el) { el.classList.add("is-visible"); });
    }
  }
})();
