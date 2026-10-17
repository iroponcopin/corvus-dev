#!/usr/bin/env python3
"""ONE-TIME MIGRATION: lift the portal-only strings out of the pre-4.0 portal export.

The 3D portal that went live on 2026-09-29 was built from `Minecraft/corvus-web`, whose source is not
in this repository. Some of its copy exists nowhere else: the header's "Brands", the footer headings,
the Store demo's 37 strings, the recipe and skin viewers' labels, the changelog's "Series", the
Discord page's Status block... (`hsd_portal_strings.json` in the audit lists 90 of them). This script
reads them, in all 13 languages, from the export that is still laid over this tree — the RSC flight
payloads (`index.txt`) and the HTML — and writes `web/src/i18n/legacy.json`.

Run it ONCE, before the new export is applied (`npm run apply` overwrites those pages). After that the
JSON is the source of truth for these strings and is edited by hand like any copy table.

    python3 -B web/scripts/capture_legacy_strings.py
"""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

WIKI = Path(__file__).resolve().parents[2]
OUT = WIKI / "web" / "src" / "i18n" / "legacy.json"
LANGS = ["ja", "en", "es", "fr", "zh", "ko", "pt-br", "it", "ar", "ru", "id", "de", "tr"]


def page_dir(lang: str, section: str) -> Path:
    base = WIKI if lang == "ja" else WIKI / lang
    return base / section if section else base


# ---------------------------------------------------------------- RSC flight payloads

def rows_of(path: Path) -> dict:
    data = path.read_text(encoding="utf-8")
    rows: dict = {}
    i, n = 0, len(data)
    head = re.compile(r"([0-9a-f]*):")
    while i < n:
        m = head.match(data, i)
        if not m:
            j = data.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        rid, j = m.group(1), m.end()
        if data.startswith("T", j):
            k = data.find(",", j)
            length = int(data[j + 1:k], 16)
            raw = data[k + 1:].encode("utf-8")[:length].decode("utf-8", errors="ignore")
            rows[rid] = ("T", raw)
            i = k + 1 + len(raw)
            continue
        e = data.find("\n", j)
        e = n if e < 0 else e
        payload = data[j:e]
        i = e + 1
        if payload.startswith("I["):
            rows[rid] = ("I", json.loads(payload[1:]))
        elif payload.startswith("HL["):
            continue
        else:
            try:
                rows[rid] = ("J", json.loads(payload))
            except ValueError:
                rows[rid] = ("RAW", payload)
    return rows


def resolve(value, rows, depth=0):
    if depth > 60:
        return value
    if isinstance(value, str):
        if value == "$undefined":
            return None
        m = re.match(r"^\$([0-9a-f]+)$", value)
        if m and m.group(1) in rows and rows[m.group(1)][0] in ("J", "T"):
            return resolve(rows[m.group(1)][1], rows, depth + 1)
        return value
    if isinstance(value, list):
        return [resolve(x, rows, depth + 1) for x in value]
    if isinstance(value, dict):
        return {k: resolve(v, rows, depth + 1) for k, v in value.items()}
    return value


def client_props(path: Path) -> dict[int, list[dict]]:
    """module id -> list of resolved props (tree order) for every client component instance."""
    rows = rows_of(path)
    out: dict[int, list[dict]] = {}
    seen: set = set()

    def walk(node):
        if isinstance(node, str):
            m = re.match(r"^\$L?([0-9a-f]+)$", node)
            if m and m.group(1) in rows and m.group(1) not in seen:
                seen.add(m.group(1))
                if rows[m.group(1)][0] == "J":
                    walk(rows[m.group(1)][1])
            return
        if isinstance(node, list):
            if len(node) == 4 and node[0] == "$" and isinstance(node[1], str):
                tag, props = node[1], node[3] or {}
                if tag.startswith("$L"):
                    r = rows.get(tag[2:])
                    if r and r[0] == "I":
                        clean = {k: v for k, v in props.items() if k != "children"}
                        out.setdefault(int(r[1][0]), []).append(resolve(clean, rows))
                for v in props.values():
                    walk(v)
                return
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)

    for rid, (kind, value) in list(rows.items()):
        if kind == "J" and rid not in seen:
            seen.add(rid)
            walk(value)
    return out


def first(props: dict[int, list[dict]], module: int) -> dict:
    found = props.get(module)
    if not found:
        raise SystemExit(f"client module {module} not found")
    return found[0]


# ---------------------------------------------------------------- HTML (server-rendered copy)

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Node:
    def __init__(self, tag: str, attrs: dict, parent: "Node | None"):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.children: list = []

    def text(self) -> str:
        parts: list[str] = []

        def rec(n):
            for c in n.children:
                if isinstance(c, str):
                    parts.append(c)
                elif c.tag not in ("script", "style", "svg"):
                    rec(c)
        rec(self)
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def find_all(self, pred) -> list["Node"]:
        found: list[Node] = []

        def rec(n):
            for c in n.children:
                if isinstance(c, Node):
                    if pred(c):
                        found.append(c)
                    rec(c)
        rec(self)
        return found

    def find(self, pred) -> "Node | None":
        r = self.find_all(pred)
        return r[0] if r else None


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, dict(attrs), self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def html_of(path: Path) -> Node:
    t = Tree()
    t.feed(path.read_text(encoding="utf-8"))
    return t.root


def by_class(cls: str):
    return lambda n: cls in n.classes()


def by_id(i: str):
    return lambda n: n.attrs.get("id") == i


def by_tag(tag: str):
    return lambda n: n.tag == tag


def must(node: "Node | None", what: str) -> Node:
    if node is None:
        raise SystemExit(f"not found: {what}")
    return node


def meta_description(root: Node) -> str:
    m = must(root.find(lambda n: n.tag == "meta" and n.attrs.get("name") == "description"), "meta description")
    return m.attrs["content"]


# ---------------------------------------------------------------- capture

def capture(lang: str) -> dict:
    s: dict = {}

    # Header (client 6019) and footer (server).
    home_rsc = client_props(page_dir(lang, "") / "index.txt")
    nav = first(home_rsc, 6019)["nav"]
    links = {l["key"]: l for l in nav["links"]}
    s["chrome"] = {
        "primaryLabel": nav["labels"]["primary"],
        "brandsLabel": nav["brandsLabel"],
        "launcherLabel": links["launcher"]["label"],
        "skinLabel": links["skin"]["label"],
        "homeLabel": nav["labels"]["home"],
    }
    home_html = html_of(page_dir(lang, "") / "index.html")
    footer = must(home_html.find(by_tag("footer")), "footer")
    heads = [h.text() for h in footer.find_all(by_tag("h2"))]
    if len(heads) != 4:
        raise SystemExit(f"{lang}: footer headings {heads}")
    legal = must(footer.find(by_class("pt-footer-legal")), "footer legal")
    s["chrome"]["footerGetStarted"] = heads[1]
    s["chrome"]["footerReference"] = heads[2]
    s["chrome"]["footerStatus"] = heads[3]
    s["chrome"]["legalTitle"] = must(legal.find(by_tag("p")), "legal title").text()

    # Home (client 46179 + server tiles).
    hero = first(home_rsc, 46179)
    explore = must(home_html.find(by_class("ph-explore")), "home explore")
    tiles = explore.find_all(by_class("ph-tile"))
    skin_tile = [t for t in tiles if t.attrs.get("href", "").rstrip("/").endswith("skin")]
    s["home"] = {
        "eyebrow": hero["eyebrow"],
        "sub": hero["sub"],
        "ctaStore": hero["ctaStore"]["label"],
        "symbolLabel": hero["symbolLabel"],
        "brandsTitle": hero["constellationTitle"],
        "hint": hero["hint"],
        "explore": must(explore.find(by_tag("h2")), "explore h2").text(),
        "skinTile": must(skin_tile[0].find(by_tag("p")) if skin_tile else None, "skin tile").text(),
        "cards": {c["id"]: {"jp": c.get("jp"), "line": c["line"], "status": c["status"]} for c in hero["cards"]},
    }

    # Corvus Store (client 39232 + server copy).
    store_rsc = client_props(page_dir(lang, "launcher") / "index.txt")
    hub = first(store_rsc, 39232)
    copyb = first(store_rsc, 34950)
    s["copyButton"] = {"label": copyb["label"], "done": copyb["done"]}
    store_html = html_of(page_dir(lang, "launcher") / "index.html")
    notes_h = must(store_html.find(by_id("hub-notes-h")), "hub-notes-h").text()
    notes_sec = must(store_html.find(lambda n: n.attrs.get("aria-labelledby") == "hub-notes-h"), "notes section")
    english_only = [p for p in notes_sec.find_all(by_class("pg-note"))]
    eo = must(english_only[0] if english_only else None, "notes english-only")
    eo_link = must(eo.find(by_tag("a")), "version history link").text()
    eo_text = eo.text()[: len(eo.text()) - len(eo_link)].strip()
    guide_sec = must(store_html.find(lambda n: n.attrs.get("aria-labelledby") == "hub-guide-h"), "guide section")
    get_sec = must(store_html.find(by_id("hub-get")), "hub-get")
    mac_note = [f.find(by_class("pg-note")) for f in get_sec.find_all(by_class("pg-file"))][0]
    s["store"] = {
        "products": {
            pid: {k: p.get(k) for k in ("name", "jp", "category", "badge", "tagline", "headline", "about")}
            for pid, p in hub["products"].items()
        },
        "text": hub["text"],
        "copy": {k: v for k, v in hub["copy"].items() if k not in ("downloadHref",)},
        "tagline": meta_description(store_html),
        "modsHeading": must(store_html.find(by_id("hub-products-h")), "hub-products-h").text(),
        "macNote": must(mac_note, "mac note").text(),
        "whatsNew": notes_h.split(" · ")[0],
        "notesEnglishOnly": eo_text,
        "versionHistory": re.sub(r"\s*[→←]\s*$", "", eo_link),
        "guideTitle": must(store_html.find(by_id("hub-guide-h")), "hub-guide-h").text(),
        "guideNote": must(guide_sec.find(by_class("pg-note")), "guide note").text(),
    }

    # Download (server).
    dl_html = html_of(page_dir(lang, "download") / "index.html")
    alpha_sec = must(dl_html.find(lambda n: n.attrs.get("aria-labelledby") == "dl-alpha"), "dl-alpha")
    alpha_note = must(alpha_sec.find(by_class("pg-note")), "alpha note")
    alpha_link = must(alpha_note.find(by_tag("a")), "alpha link").text()
    s["download"] = {
        "metaDescription": meta_description(dl_html),
        "alphaNote": alpha_note.text()[: len(alpha_note.text()) - len(alpha_link)].strip(),
    }

    # Recipes (client 54907).
    rec = first(client_props(page_dir(lang, "recipes") / "index.txt"), 54907)
    s["recipes"] = {"labels": rec["labels"]}
    if lang == "ja":
        s["recipes"]["kinds"] = {iid: it.get("kind") for iid, it in rec["data"]["items"].items()}
    stations = rec["data"].get("stations")
    if stations is not None:
        s["recipes"]["stations"] = stations

    # Changelog (client 7381).
    cl = first(client_props(page_dir(lang, "changelog") / "index.txt"), 7381)
    s["changelog"] = {
        "labels": cl["labels"],
        "brandNames": {b["id"]: b["name"] for b in cl["brands"]},
    }

    # Coming next (client 29374).
    up = first(client_props(page_dir(lang, "upcoming") / "index.txt"), 29374)
    s["upcoming"] = {"more": up["more"], "nodes": {n["id"]: {k: n.get(k) for k in ("headline", "body", "linkName", "statusLabel", "target")} for n in up["nodes"]}}

    # Sparxie skin (client 40941).
    sk = first(client_props(page_dir(lang, "skin") / "index.txt"), 40941)
    skin_html = html_of(page_dir(lang, "skin") / "index.html")
    s["skin"] = {"labels": sk["labels"], "description": meta_description(skin_html)}

    # Discord (server).
    dc_html = html_of(page_dir(lang, "discord") / "index.html")
    status = must(dc_html.find(lambda n: n.attrs.get("aria-labelledby") == "dc-status"), "dc-status")
    dts = [d.text() for d in status.find_all(by_tag("dt"))]
    dds = [d.text() for d in status.find_all(by_tag("dd"))]
    hero_eyebrow = must(dc_html.find(by_class("pt-eyebrow")), "discord eyebrow").text()
    s["discord"] = {
        "eyebrow": hero_eyebrow,
        "statusTitle": must(status.find(by_id("dc-status")), "dc-status h2").text(),
        "statusInvite": dts[0],
        "statusPermissions": dts[1],
        "statusLatest": dts[2],
        "statusFeed": dts[3],
        "published": dds[0],
        "statusNote": must(status.find(by_class("pg-note")), "status note").text(),
    }

    # Plates (client 51846): accessible labels per page.
    s["plates"] = {}
    for section in ("ouka", "cherry", "aureum", "alpha", "discord"):
        found = client_props(page_dir(lang, section) / "index.txt").get(51846)
        if found:
            s["plates"][section] = found[0].get("alt")
    return s


def main() -> None:
    if not (WIKI / "portal" / "build.json").exists():
        raise SystemExit("the pre-4.0 portal export is not laid over this tree; nothing to capture")
    build = json.loads((WIKI / "portal" / "build.json").read_text(encoding="utf-8"))
    if str(build.get("what", "")).startswith("Corvus portal 4"):
        raise SystemExit("this tree already carries the 4.x export; legacy.json must not be re-captured")
    nf = html_of(WIKI / "404.html")
    out = {
        "_about": ("Portal-only copy of the pre-4.0 portal (Minecraft/corvus-web), captured once from its "
                   "export by web/scripts/capture_legacy_strings.py. Source of truth from 4.0 on; edit by hand."),
        "_captured_from": {k: build.get(k) for k in ("wiki_commit", "corvus_store", "ouka", "cherry", "aureum")},
        "notFoundTitle": must(nf.find(by_tag("title")), "404 title").text(),
        "langs": {},
    }
    for lang in LANGS:
        out["langs"][lang] = capture(lang)
        print(lang, "ok", file=sys.stderr)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", OUT.relative_to(WIKI))


if __name__ == "__main__":
    main()
