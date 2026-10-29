#!/usr/bin/env python3
"""
Every recipe the recipe sheet (data/recipes.json, scripts/extract_recipes.py) does not show, read from the
distributed zips: OUKA's machine recipes (Precision Assembly Line, Hydraulic Impact Crusher, Molecular
Centrifuge, Bio-Reactor Culture Vat, Sub-Crustal Thermal Bore), Cherry's Advanced Cherry Fabricator, and the
furnace and blast-furnace recipes of both. Writes data/recipes_machines.json and the icons it needs into
assets/img/recipes/ (named by content: m<sha1>.png, so they never collide with the sheet's t<N>.png).

The sheet only reads crafting-table grids. Its generator needs the mod-pack project and the vanilla client
jar, which this repo does not have, so the machine recipes are a second file beside it rather than a
change to it. The portal (web/scripts/extract_wiki.py) shows both as one codex.

  python3 scripts/extract_machine_recipes.py          # regenerate
  python3 scripts/extract_machine_recipes.py --check  # GREEN only if the file matches the published zips

Source is the distributed zip named in glimpse_manifest.json (downloads/), never a working tree: the site
must not describe a recipe nobody has been given (same rule as extract_recipes.py).

Vanilla items a machine recipe uses but the sheet never needed have no icon in the sheet. Their 16x16
textures are kept in scripts/vanilla_icons/ (from the Minecraft 26.1 asset set) with their official names
below; a recipe naming a vanilla item missing from both is an error, not a "?" on the live site.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import unicodedata
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "recipes_machines.json"
IMG = ROOT / "assets" / "img" / "recipes"
VANILLA_DIR = Path(__file__).resolve().parent / "vanilla_icons"
SHEET = ROOT / "data" / "recipes.json"

BRANDS = ("ouka", "cherry")

# Station id -> the block that does the work. The order is the order of the chips on the page.
STATIONS = [
    ("assembly", "ouka:precision_assembly_line"),
    # OUKA V1.7 81347: the Next-Generation Automation Assembly Line (recipe type ouka:assembly_ng), a station of its own.
    ("assembly_ng", "ouka:assembly_line_ng"),
    ("crusher", "ouka:hydraulic_crusher"),
    ("centrifuge", "ouka:molecular_centrifuge"),
    ("culture", "ouka:bio_reactor_culture_vat"),
    ("bore", "ouka:sub_crustal_thermal_bore"),
    ("fabricator", "cherry:advanced_cherry_fabricator"),
    ("furnace", "minecraft:furnace"),
    ("blast", "minecraft:blast_furnace"),
]
# OUKA V1.6.0: the heavy-industry machines that have recipes of type ouka:process. One station each (the recipe's own
# "machine" field names it), in the order a player builds them. A process recipe naming a machine that is not here
# stops the build: a machine added later must be given its chip, not dropped without a word.
PROCESS_MACHINES = [
    "supersonic_jet_mill", "cryo_oxygen_extractor",
    "gas_centrifuge_tower", "heavy_water_electrolyser", "pyrolytic_carbon_press", "electrolytic_refining_cell", "catalyst_pelletiser",
    "catalytic_smelting_furnace", "vacuum_sintering_furnace", "hot_isostatic_press", "rotary_calciner", "superconducting_coil_winder",
    "superconducting_fractionating_tower", "plasma_arc_gasifier", "syngas_synthesis_reactor",
    "crystal_pulling_furnace", "laser_ablation_bed", "high_pressure_ion_implanter", "auto_calibration_manipulator",
    # OUKA V1.7 81347: the Carbide Forge.
    "carbide_forge",
    # OUKA V1.7 91209: the ice industry.
    "cryo_compressor", "quantum_cryo_synthesizer",
]
_AT = [i for i, s in enumerate(STATIONS) if s[0] == "fabricator"][0]
STATIONS[_AT:_AT] = [(m, "ouka:" + m) for m in PROCESS_MACHINES]
TYPE_STATION = {
    "ouka:assembly": "assembly",
    "ouka:assembly_ng": "assembly_ng",
    "ouka:crushing": "crusher",
    "ouka:centrifuging": "centrifuge",
    "ouka:culturing": "culture",
    "ouka:quarry_vein": "bore",
    "minecraft:smelting": "furnace",
    "minecraft:blasting": "blast",
}
# Shown by the sheet already (crafting table, smithing, campfire).
SHEET_TYPES = {"minecraft:crafting_shaped", "minecraft:crafting_shapeless", "minecraft:smithing_transform",
               "minecraft:campfire_cooking"}

# Vanilla items the sheet has no entry for: [ja, en, texture file in scripts/vanilla_icons/, kind].
VANILLA = {
    "minecraft:ice": ["氷", "Ice", "ice.png", "cube"],
    # OUKA V1.7 91209: the stabilised ice is drawn with the vanilla frosted-ice texture, so the OUKA jar has no icon file of its own.
    "ouka:stabilised_frosted_ice": ["安定化霜氷", "Frosted Ice (Stabilised)", "stabilised_frosted_ice.png", "cube"],
    "minecraft:ancient_debris": ["古代の残骸", "Ancient Debris", "ancient_debris.png", "cube"],
    "minecraft:coal": ["石炭", "Coal", "coal.png", "flat"],
    "minecraft:coarse_dirt": ["粗い土", "Coarse Dirt", "coarse_dirt.png", "cube"],
    "minecraft:copper_ore": ["銅鉱石", "Copper Ore", "copper_ore.png", "cube"],
    "minecraft:emerald": ["エメラルド", "Emerald", "emerald.png", "flat"],
    "minecraft:furnace": ["かまど", "Furnace", "furnace.png", "cube"],
    "minecraft:glow_berries": ["グロウベリー", "Glow Berries", "glow_berries.png", "flat"],
    "minecraft:glowstone_dust": ["グロウストーンダスト", "Glowstone Dust", "glowstone_dust.png", "flat"],
    "minecraft:gold_ore": ["金鉱石", "Gold Ore", "gold_ore.png", "cube"],
    "minecraft:gravel": ["砂利", "Gravel", "gravel.png", "cube"],
    "minecraft:honey_bottle": ["ハチミツ入りの瓶", "Honey Bottle", "honey_bottle.png", "flat"],
    # Used by a machine recipe; the sheet named them only through ASTRAEA's cards, which left the sheet on 2026-10-17.
    "minecraft:iron_bars": ["鉄格子", "Iron Bars", "iron_bars.png", "cube"],
    "minecraft:stone_button": ["石のボタン", "Stone Button", "stone_button.png", "cube"],
    "minecraft:yellow_dye": ["黄色の染料", "Yellow Dye", "yellow_dye.png", "flat"],
    "minecraft:iron_ore": ["鉄鉱石", "Iron Ore", "iron_ore.png", "cube"],
    "minecraft:lapis_lazuli": ["ラピスラズリ", "Lapis Lazuli", "lapis_lazuli.png", "flat"],
    "minecraft:raw_copper": ["銅の原石", "Raw Copper", "raw_copper.png", "flat"],
    "minecraft:raw_gold": ["金の原石", "Raw Gold", "raw_gold.png", "flat"],
    "minecraft:raw_iron": ["鉄の原石", "Raw Iron", "raw_iron.png", "flat"],
    "minecraft:red_sand": ["赤い砂", "Red Sand", "red_sand.png", "cube"],
    "minecraft:rotten_flesh": ["腐った肉", "Rotten Flesh", "rotten_flesh.png", "flat"],
    "minecraft:wheat_seeds": ["小麦の種", "Wheat Seeds", "wheat_seeds.png", "flat"],
    "minecraft:rooted_dirt": ["根付いた土", "Rooted Dirt", "rooted_dirt.png", "cube"],
    "minecraft:spyglass": ["望遠鏡", "Spyglass", "spyglass.png", "flat"],
    "minecraft:sugar": ["砂糖", "Sugar", "sugar.png", "flat"],
    # OUKA V1.7 71208: the Wonder part ammunition (wonder_part_ammo_mod_he / _mod_i) uses these two. Textures are the
    # 26.3 client jar's own (byte-identical to the existing icons from that jar), not the 26.1 set.
    "minecraft:end_crystal": ["エンドクリスタル", "End Crystal", "end_crystal.png", "flat"],
    "minecraft:fire_charge": ["ファイヤーチャージ", "Fire Charge", "fire_charge.png", "flat"],
}
# Conventional (c:) tags the jars use but do not define (Fabric defines them): the item that stands for each.
C_TAG = {"ores": "minecraft:{}_ore", "raw_materials": "minecraft:raw_{}", "ingots": "minecraft:{}_ingot"}

DIMENSIONS = {"minecraft:overworld": "overworld", "minecraft:the_nether": "nether", "minecraft:the_end": "end"}


def die(msg: str) -> None:
    print(f"extract_machine_recipes: {msg}", file=sys.stderr)
    sys.exit(1)


def published_jar(manifest: dict, brand: str) -> tuple[str, zipfile.ZipFile]:
    info = manifest.get(brand) or {}
    name = info.get("file_name")
    if not name or not (ROOT / "downloads" / name).is_file():
        die(f"{brand}: glimpse_manifest.json names no zip in downloads/ ({name!r})")
    outer = zipfile.ZipFile(ROOT / "downloads" / name)
    jars = [n for n in outer.namelist() if n.endswith(".jar") and Path(n).name.startswith(f"{brand}-")]
    if len(jars) != 1:
        die(f"{brand}: expected one {brand}-*.jar in {name}, found {jars}")
    return info["latest"], zipfile.ZipFile(io.BytesIO(outer.read(jars[0])))


class Jar:
    def __init__(self, brand: str, zf: zipfile.ZipFile):
        self.brand, self.zf = brand, zf
        self.names = set(zf.namelist())
        self.lang = {code: json.loads(zf.read(f"assets/{brand}/lang/{code}.json"))
                     for code in ("ja_jp", "en_us") if f"assets/{brand}/lang/{code}.json" in self.names}

    def json(self, path: str):
        return json.loads(self.zf.read(path))

    def display(self, iid: str) -> tuple[str, str]:
        ns, path = iid.split(":", 1)
        out = []
        for code in ("ja_jp", "en_us"):
            table = self.lang.get(code, {})
            out.append(table.get(f"item.{ns}.{path}") or table.get(f"block.{ns}.{path}") or "")
        if not out[1]:
            die(f"{iid}: no English name in the {self.brand} jar")
        return out[0] or out[1], out[1]

    def texture(self, iid: str) -> bytes | None:
        """The item's inventory icon: items/<id>.json -> its gui model -> layer0. A GeckoLib item (Cherry's
        guns) has no flat icon, only a 3D model whose texture is a UV atlas: it is drawn from the side."""
        ns, path = iid.split(":", 1)
        model = None
        d = f"assets/{ns}/items/{path}.json"
        if d in self.names:
            node = self.json(d)["model"]
            geo = f"assets/{ns}/geckolib/models/item/{path}.geo.json"
            inner = node.get("model")
            if isinstance(inner, dict) and inner.get("type") == "geckolib:geckolib" and geo in self.names:
                return self.side_view(geo, f"assets/{ns}/textures/item/{path}.png")
            model = self._gui_model(node)
        model = model or f"{ns}:item/{path}"
        for _ in range(6):
            mns, mpath = model.split(":", 1) if ":" in model else ("minecraft", model)
            mfile = f"assets/{mns}/models/{mpath}.json"
            if mfile not in self.names:
                break
            m = self.json(mfile)
            tex = m.get("textures", {})
            ref = tex.get("layer0") or tex.get("all") or tex.get("front") or tex.get("side") or tex.get("particle")
            if ref and not ref.startswith("#"):
                tns, tpath = ref.split(":", 1) if ":" in ref else ("minecraft", ref)
                tfile = f"assets/{tns}/textures/{tpath}.png"
                if tfile in self.names:
                    return self.zf.read(tfile)
            if not m.get("parent") or m["parent"].startswith(("minecraft:", "builtin/", "item/", "block/")):
                break
            model = m["parent"]
        flat = f"assets/{ns}/textures/item/{path}.png"
        return self.zf.read(flat) if flat in self.names else None

    def side_view(self, geo_path: str, tex_path: str, out: int = 64) -> bytes:
        """The model seen from its right-hand (east) side, barrel to the right, each cube's east face
        painted with its own patch of the atlas, nearer cubes over farther ones. Rotated cubes are drawn
        unrotated: at 64 px the difference is a pixel or two."""
        from PIL import Image

        geo = self.json(geo_path)["minecraft:geometry"][0]
        atlas = Image.open(io.BytesIO(self.zf.read(tex_path))).convert("RGBA")
        sx = atlas.width / geo["description"].get("texture_width", atlas.width)
        sy = atlas.height / geo["description"].get("texture_height", atlas.height)
        faces = []
        for bone in geo["bones"]:
            for c in bone.get("cubes", []):
                (x, y, z), (w, h, dpt) = c["origin"], c["size"]
                uv = c.get("uv", {})
                face = uv.get("east") if isinstance(uv, dict) else None
                if face is None or h <= 0 or dpt <= 0:
                    continue
                faces.append((x + w, z, y, dpt, h, face))
        if not faces:
            die(f"{geo_path}: no cube has an east face")
        zmin = min(f[1] for f in faces); zmax = max(f[1] + f[3] for f in faces)
        ymin = min(f[2] for f in faces); ymax = max(f[2] + f[4] for f in faces)
        scale = (out - 4) / max(zmax - zmin, ymax - ymin)
        img = Image.new("RGBA", (out, out), (0, 0, 0, 0))
        ox = (out - (zmax - zmin) * scale) / 2
        oy = (out - (ymax - ymin) * scale) / 2
        for _, z, y, dpt, h, face in sorted(faces, key=lambda f: f[0]):
            u, v = face["uv"]; uw, vh = face.get("uv_size", [dpt, h])
            patch = atlas.crop((round(u * sx), round(v * sy),
                                max(round(u * sx) + 1, round((u + uw) * sx)), max(round(v * sy) + 1, round((v + vh) * sy))))
            # -z is the muzzle; on screen it points right, so the patch is mirrored.
            x0 = ox + (zmax - (z + dpt)) * scale
            y0 = oy + (ymax - (y + h)) * scale
            pw, ph = max(1, round(dpt * scale)), max(1, round(h * scale))
            patch = patch.transpose(Image.Transpose.FLIP_LEFT_RIGHT).resize((pw, ph), Image.Resampling.NEAREST)
            img.alpha_composite(patch, (round(x0), round(y0)))
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    def _gui_model(self, node: dict) -> str | None:
        t = node.get("type", "")
        if t.endswith("model"):
            return node.get("model")
        if t.endswith("special"):
            return node.get("base")
        if t.endswith("select"):
            for case in node.get("cases", []):
                when = case.get("when")
                if when == "gui" or (isinstance(when, list) and "gui" in when):
                    return self._gui_model(case["model"])
            if "fallback" in node:
                return self._gui_model(node["fallback"])
        for key in ("on_false", "on_true", "fallback"):
            if key in node:
                return self._gui_model(node[key])
        return None

    def tag_first(self, tag: str, depth: int = 0) -> str | None:
        ns, path = tag.split(":", 1)
        f = f"data/{ns}/tags/item/{path}.json"
        if f in self.names and depth < 4:
            for v in self.json(f).get("values", []):
                v = v.get("id") if isinstance(v, dict) else v
                if v.startswith("#"):
                    got = self.tag_first(v[1:], depth + 1)
                    if got:
                        return got
                else:
                    return v
        if ns == "c" and "/" in path:
            kind, metal = path.split("/", 1)
            if kind in C_TAG:
                return C_TAG[kind].format(metal)
        return None


def ingredient(jar: Jar, v, n: int = 1) -> dict:
    """One input slot. A tag or a list of alternatives shows its first item and says "any of"."""
    if isinstance(v, dict):
        v = v.get("item") or v.get("id") or ("#" + v["tag"] if "tag" in v else None)
    if isinstance(v, list):
        first = ingredient(jar, v[0], n)
        return {**first, "any": True}
    if not isinstance(v, str):
        die(f"unreadable ingredient {v!r}")
    if v.startswith("#"):
        iid = jar.tag_first(v[1:])
        if not iid:
            die(f"tag {v} has no item to stand for it")
        return {"id": iid, "n": n, "any": True}
    return {"id": v, "n": n}


def read_recipes(jar: Jar) -> list[dict]:
    out = []
    for name in sorted(jar.names):
        if not name.endswith(".json"):
            continue
        is_recipe = name.startswith(f"data/{jar.brand}/recipe/")
        is_fab = name.startswith(f"data/{jar.brand}/fabricating/")
        if not (is_recipe or is_fab):
            continue
        x = jar.json(name)
        rid = f"{jar.brand}:{name.split('/', 3)[3][:-5]}"
        if is_fab:
            out.append({
                "id": rid, "station": "fabricator",
                "inputs": [ingredient(jar, i["item"], i.get("count", 1)) for i in x["ingredients"]],
                "outputs": [{"id": x["result"]["item"], "n": x["result"].get("count", 1)}],
                "time": x.get("time"),
            })
            continue
        t = x.get("type")
        if t in SHEET_TYPES:
            continue
        station = TYPE_STATION.get(t)
        if t == "ouka:process":
            station = x["machine"].split(":", 1)[1]
            if x["machine"] != "ouka:" + station or station not in PROCESS_MACHINES:
                die(f"{rid}: the process machine {x['machine']!r} has no station here (add it to PROCESS_MACHINES)")
        if station is None:
            die(f"{rid}: recipe type {t!r} has no station here (add it to TYPE_STATION)")
        res = x.get("result") or {}
        rec = {"id": rid, "station": station}
        if t in ("minecraft:smelting", "minecraft:blasting"):
            rec["inputs"] = [ingredient(jar, x["ingredient"])]
            rec["outputs"] = [{"id": res["id"], "n": res.get("count", 1)}]
            rec["time"] = x.get("cookingtime", 200 if t.endswith("smelting") else 100)
            rec["xp"] = x.get("experience", 0)
        elif t in ("ouka:assembly", "ouka:assembly_ng", "ouka:culturing"):
            rec["inputs"] = [ingredient(jar, i["ingredient"], i.get("count", 1)) for i in x["inputs"]]
            rec["outputs"] = [{"id": res["id"], "n": res.get("count", 1)}]
            if "time" in x:
                rec["time"] = x["time"]
            if "water" in x:
                rec["water"] = x["water"]
        elif t == "ouka:process":
            rec["inputs"] = [ingredient(jar, i["ingredient"], i.get("count", 1)) for i in x["inputs"]]
            rec["outputs"] = [{"id": o["result"]["id"], "n": o["result"].get("count", 1), **({"every": o["every"]} if "every" in o else {})}
                              for o in x["outputs"]]
            rec["time"] = x["ticks"]
        elif t == "ouka:crushing":
            rec["inputs"] = [ingredient(jar, x["ingredient"], x.get("count", 1))]
            rec["outputs"] = [{"id": res["id"], "n": res.get("count", 1)}]
        elif t == "ouka:centrifuging":
            rec["inputs"] = [ingredient(jar, x["ingredient"])]
            rec["outputs"] = [{"id": o["result"]["id"], "n": o["result"].get("count", 1),
                               "chance": o.get("chance", 1)} for o in x["outputs"]]
        elif t == "ouka:quarry_vein":
            dim = DIMENSIONS.get(x["dimension"])
            if dim is None:
                die(f"{rid}: dimension {x['dimension']} has no name on the page")
            rec["inputs"] = []
            rec["outputs"] = [{"id": res["id"], "n": x.get("min", 1), "nMax": x.get("max", 1)}]
            rec["dimension"] = dim
            rec["weight"] = x.get("weight", 1)
        out.append(rec)
    # A vein's share of its dimension's draws, which is what a player can act on.
    totals: dict[str, int] = {}
    for r in out:
        if "weight" in r:
            totals[r["dimension"]] = totals.get(r["dimension"], 0) + r["weight"]
    for r in out:
        if "weight" in r:
            r["share"] = round(100 * r["weight"] / totals[r["dimension"]], 1)
            del r["weight"]
    for r in out:
        r["brand"] = jar.brand
    return out


_KATA = re.compile(r"[ァ-ヶ]")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    return _KATA.sub(lambda m: chr(ord(m.group(0)) - 0x60), s)


def build() -> tuple[dict, dict[str, bytes]]:
    manifest = json.loads((ROOT / "glimpse_manifest.json").read_text(encoding="utf-8"))
    sheet = json.loads(SHEET.read_text(encoding="utf-8"))
    jars, sources, recipes = {}, {}, []
    for brand in BRANDS:
        sources[brand], zf = published_jar(manifest, brand)
        jars[brand] = Jar(brand, zf)
        recipes += read_recipes(jars[brand])

    wanted = {s[1] for s in STATIONS}
    for r in recipes:
        wanted |= {i["id"] for i in r["inputs"]} | {o["id"] for o in r["outputs"]}

    items: dict[str, list] = {}
    pngs: dict[str, bytes] = {}
    unknown: list[str] = []
    for iid in sorted(wanted):
        if iid in sheet["items"]:
            continue  # the sheet's own name and icon are used
        ns = iid.split(":", 1)[0]
        if ns in jars and iid not in VANILLA:
            ja, en = jars[ns].display(iid)
            png = jars[ns].texture(iid)
            if png is None:
                die(f"{iid}: no inventory texture in the {ns} jar")
            kind = "flat"
        elif iid in VANILLA:
            ja, en, fname, kind = VANILLA[iid]
            f = VANILLA_DIR / fname
            if not f.is_file():
                die(f"{iid}: scripts/vanilla_icons/{fname} is missing")
            png = f.read_bytes()
        else:
            unknown.append(iid)
            continue
        icon = "m" + hashlib.sha1(png).hexdigest()[:12]
        pngs[icon] = png
        items[iid] = [ja, en, icon, kind]

    if unknown:
        die(f"a machine recipe uses {unknown}, but neither the sheet, a jar nor VANILLA knows them")

    def names(iid: str) -> tuple[str, str]:
        v = items.get(iid) or sheet["items"].get(iid) or ["", ""]
        return v[0], v[1]

    search = {}
    for r in recipes:
        words = [r["brand"]]
        for iid in [o["id"] for o in r["outputs"]] + [i["id"] for i in r["inputs"]]:
            ja, en = names(iid)
            words += [ja, norm(ja), iid, iid.split(":", 1)[1], en.lower()]
        search[r["id"]] = " ".join(w for w in words if w)

    data = {
        "sources": sources,
        "stations": [{"id": sid, "item": item} for sid, item in STATIONS],
        "items": items,
        "recipes": recipes,
        "search": search,
    }
    return data, pngs


def main() -> None:
    data, pngs = build()
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        ok = OUT.is_file() and OUT.read_text(encoding="utf-8") == text
        missing = [k for k in pngs if not (IMG / f"{k}.png").is_file()]
        if ok and not missing:
            print(f"MACHINE RECIPES = GREEN ({len(data['recipes'])} recipes from "
                  + ", ".join(f"{b} {v}" for b, v in data["sources"].items()) + ")")
            return
        print("MACHINE RECIPES = RED: data/recipes_machines.json does not match the published zips"
              + (f" (icons missing: {missing[:5]})" if missing else ""))
        print("  Fix: python3 scripts/extract_machine_recipes.py")
        sys.exit(1)
    OUT.write_text(text, encoding="utf-8")
    for k, png in pngs.items():
        (IMG / f"{k}.png").write_bytes(png)
    by = {}
    for r in data["recipes"]:
        by[r["station"]] = by.get(r["station"], 0) + 1
    print(f"extract_machine_recipes: {len(data['recipes'])} recipes {by}, {len(data['items'])} new items, "
          f"{len(pngs)} icons")


if __name__ == "__main__":
    main()
