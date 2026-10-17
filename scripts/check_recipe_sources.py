#!/usr/bin/env python3
"""レシピ集が、いまサイトが配っている版から作られているかを確かめる。

なぜ要るか
----------
2026-09-20 以降、`extract_recipes.py` はレシピ・テクスチャ・表示名を**配布物**
(downloads/ の pack zip とブランド zip)から読む。おかげで「まだ配られていない
作り方」が載ることは無くなったが、**逆向きの古さ**が残る —— 新しい版を配り始めた
のに早見表を作り直していなければ、サイトは新しい zip を配りながら**古い作り方**を
表示し続ける。しかも出力は正常に見え、リンク切れも起きないので誰も気づかない。

Cherry V1.1.0 はレシピを 9 件足すと予告されている(2026-09-20、Cherry セッション)。
つまりこれは仮定の話ではない。

何を見るか
----------
`data/recipes.json` の "sources"(生成時に読んだ配布物の版)と、
`glimpse_manifest.json` がいま配っている版を突き合わせる。1 つでも違えば RED。

直しかた: `python3 scripts/extract_recipes.py` を走らせ直して、
`scripts/build.py` でページを作り直す。
"""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    recipes_path = ROOT / "data" / "recipes.json"
    manifest_path = ROOT / "glimpse_manifest.json"
    for p in (recipes_path, manifest_path):
        if not p.exists():
            print(f"RED: {p} is missing")
            return 1

    recipes = json.loads(recipes_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    sources = recipes.get("sources")
    if not sources:
        print("RED: data/recipes.json carries no 'sources' block, so nothing can tell whether "
              "it was generated from what the site currently serves. Re-run "
              "scripts/extract_recipes.py.")
        return 1

    # いま配られている版。ブランドは名前で決め打ちせず、マニフェストの**形**から拾う
    # (mod_id と jars を持つブロック)。次にブランドが増えたとき黙って外れないように。
    live = {}
    pack = manifest.get("pack") or {}
    # 2026-09-28: Alpha is retired (data/retirement.json) and its recipes are no longer part of the sheet at
    # all (extract_recipes.py: RETIRED). The pack is then NOT a source: a `pack` entry left in `sources` is a
    # sheet still describing it, and is named as such below (nothing publishes it as a recipe source now).
    rp = ROOT / "data" / "retirement.json"
    retirement = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    retired = bool((retirement.get("alpha") or {}).get("retired"))
    if pack.get("latest") and not retired:
        live["pack"] = pack["latest"]
    # 2026-10-17: ASTRAEA's service has ended (data/retirement.json, "astraea": retired). Like Alpha, a retired product
    # is not a source of the sheet: its jar is not opened and it is not in `live`. The assertions below check that the
    # sheet holds no trace of it (no tab, no card, no item), so a sheet that still shows it goes RED.
    retired_blocks = {k for k, v in retirement.items() if isinstance(v, dict) and v.get("retired")}
    bare_checked = {}      # block -> (recipe result ids in its jar, recipe json count)
    bare_set_aside = {}    # block -> (uncraftable json, recolouring json, nested jars read)
    recipe_less = []
    bad = []
    for block, info in manifest.items():
        if not (isinstance(info, dict) and "mod_id" in info):
            continue
        if block in retired_blocks:
            continue
        if isinstance(info.get("jars"), dict):
            if info.get("latest"):
                live[block] = info["latest"]
        elif str(info.get("file_name", "")).endswith(".jar"):
            # 2026-10-05: a brand published as ONE bare jar (Tsubomi, Aureum). The old shape test (mod_id + a
            # jars dict) could not see it, so Tsubomi was invisible to this gate. Whether such a jar is a
            # recipe source is decided by OPENING it, not by a list typed here.
            jar = ROOT / "downloads" / info["file_name"]
            if not jar.exists():
                bad.append(f"{block}: the manifest publishes {info['file_name']} but downloads/ does not have it")
                continue
            if hashlib.sha256(jar.read_bytes()).hexdigest() != info.get("sha256"):
                bad.append(f"{block}: {info['file_name']} does not hash to the manifest's sha256")
                continue
            # 2026-10-16 (Halia 1.2.0): the jar carries the Aerie inside itself (META-INF/jars/, listed in its own
            # fabric.mod.json "jars"). Its recipes, and its item tags, are part of what the jar publishes; they are
            # read from the nested bytes, not from a copy on disk. Recipes are paired with the jar they came from.
            with zipfile.ZipFile(jar) as outer_jf:
                jars = [("", outer_jf)]
                listed = json.loads(outer_jf.read("fabric.mod.json").decode("utf-8")).get("jars", [])
                for entry in listed:
                    jars.append((entry["file"], zipfile.ZipFile(io.BytesIO(outer_jf.read(entry["file"])))))
                bodies = {}
                for where, jf in jars:
                    for n in jf.namelist():
                        if n.startswith(f"data/{info['mod_id']}/recipe/") and n.endswith(".json"):
                            bodies[(where, n)] = json.loads(jf.read(n).decode("utf-8"))

                def tag_values(ns, tag):
                    # A tag is looked up in every jar of the package (Halia's tags are in the outer jar and the Aerie's
                    # in the nested one); the first that defines it is the one the game reads.
                    for _where, jf in jars:
                        member = f"data/{ns}/tags/item/{tag}.json"
                        if member in jf.namelist():
                            return json.loads(jf.read(member).decode("utf-8"))["values"]
                    return None

                def only_air(ing):
                    if isinstance(ing, list):
                        ing = ing[0] if len(ing) == 1 else None
                    if not (isinstance(ing, str) and ing.startswith("#")):
                        return False
                    ns, tag = ing[1:].split(":", 1)
                    values = tag_values(ns, tag)
                    if values is None:
                        return False
                    return bool(values) and all(v == "minecraft:air" for v in values)

                # 2026-10-12 (Halia 1.1.0): a recipe whose every ingredient is a tag holding nothing but air can
                # never be crafted (Halia keeps 11 such files as its creative-tab listing; 1.2.0 keeps 31). Decided by
                # opening the tag in the jar, never by a list typed here. Such a file owes the sheet no card.
                # 2026-10-16 (Halia 1.2.0): the Aerie's 320 "any dye recolours this device" recipes (type
                # halia:recoloring) are not cards either; the sheet says so in one line. Any other recipe type is a card.
                names = []
                set_aside_air = set_aside_recolour = 0
                for key in sorted(bodies):
                    body = bodies[key]
                    if body.get("type") == "halia:recoloring":
                        set_aside_recolour += 1
                        continue
                    if (body.get("type") == "minecraft:crafting_shapeless" and body.get("ingredients")
                            and all(only_air(i) for i in body["ingredients"])):
                        set_aside_air += 1
                        continue
                    names.append(key)

                def result_of(body):
                    r = body["result"]
                    return r if isinstance(r, str) else r["id"]

                results = sorted({result_of(bodies[k]) for k in names})
                # A result that carries a second obtainable item (Halia's material box names the blade it becomes
                # on an anvil) owes the sheet one more card.
                second = sum(1 for k in names
                             if isinstance(bodies[k]["result"], dict)
                             and any(c.endswith(":required_blade")
                                     for c in (bodies[k]["result"].get("components") or {})))
            if names:
                if info.get("latest"):
                    live[block] = info["latest"]
                bare_checked[block] = (results, len(names) + second)
                bare_set_aside[block] = (set_aside_air, set_aside_recolour, len(jars) - 1)
            else:
                recipe_less.append(block)

    if not live:
        print("RED: the manifest declares no published version at all - this checker is reading "
              "the wrong shape, and an empty comparison would pass for the wrong reason.")
        return 1

    for name in sorted(set(live) | set(sources)):
        was, now = sources.get(name), live.get(name)
        if was is None:
            bad.append(f"{name}: published as {now}, but the sheet was not generated from it at all")
        elif now is None:
            bad.append(f"{name}: the sheet was generated from {was}, but nothing publishes it now")
        elif was != now:
            bad.append(f"{name}: the sheet was generated from {was}, the site now serves {now}")

    # A retired product must leave no trace in the sheet (2026-10-17, ASTRAEA): not a source, no tab, no card, no item.
    for block in sorted(retired_blocks & set(manifest)):
        if block in sources:
            bad.append(f"{block}: retired (data/retirement.json), but the sheet still names it as a source")
        tabs = [i for i, c in enumerate(recipes.get("cats", [])) if str(c[0]).lower() == block]
        if tabs:
            bad.append(f"{block}: retired, but the sheet still has its tab {[recipes['cats'][i][0] for i in tabs]}")
        cards = [c for c in recipes.get("cards", []) if c[0] in tabs or str(c[1]).split(":", 1)[0] == block]
        if cards:
            bad.append(f"{block}: retired, but the sheet still has {len(cards)} card(s) for it")
        items = [k for k in recipes.get("items", {}) if k.split(":", 1)[0] == block]
        if items:
            bad.append(f"{block}: retired, but the sheet still describes {len(items)} item(s) of it (e.g. {items[0]})")

    # A matching version does not prove the sheet is COMPLETE. For a bare-jar brand every recipe json must have
    # become a card of the brand's own tab (extract_recipes.py: EVERY_RECIPE_SHOWN); count that here, from the
    # jar and from the sheet, so a sheet that recorded the right version but lost the revived Teleport Elevator
    # (or any other recipe) goes RED.
    for block, (results, n_json) in sorted(bare_checked.items()):
        tab = [i for i, c in enumerate(recipes.get("cats", [])) if str(c[0]).lower() == block]
        if len(tab) != 1:
            bad.append(f"{block}: its jar carries {n_json} recipe json but the sheet has no single tab named "
                       f"{block!r} (tabs: {[c[0] for c in recipes.get('cats', [])]})")
            continue
        cards = [c for c in recipes.get("cards", []) if c[0] == tab[0]]
        if len(cards) != n_json:
            bad.append(f"{block}: its jar carries {n_json} recipe json but its tab has {len(cards)} card(s)")
        # A card may be keyed by an id qualified with what its components select (`ns:item[...]`).
        have = {c[1].split("[", 1)[0] for c in cards}
        gone = [r for r in results if r not in have]
        if gone:
            bad.append(f"{block}: the jar's recipes make {', '.join(gone)}, which has no card in the "
                       f"{block!r} tab")

    if bad:
        print("RED: the recipe sheet is out of step with what the site publishes:")
        for line in bad:
            print(f"  - {line}")
        print("  Fix: python3 scripts/extract_recipes.py && python3 scripts/build.py")
        return 1

    print("GREEN: recipe sheet generated from " +
          ", ".join(f"{k} {v}" for k, v in sorted(sources.items())) +
          " - the same versions the site publishes" +
          "".join(f"; {b}: all {n} jar recipe(s) have a card (set aside: {bare_set_aside[b][0]} that cannot be "
                  f"crafted, {bare_set_aside[b][1]} recolouring; {bare_set_aside[b][2] + 1} jar(s) read)"
                  for b, (_r, n) in sorted(bare_checked.items())) +
          ("; bare jar(s) with no recipe, not a source: " + ", ".join(recipe_less) if recipe_less else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ---------------------------------------------------------------------------
# 2026-09-20 の Pages 障害。次に同じ形を見たときのために結果だけ残す。
# ---------------------------------------------------------------------------
# レシピ集を push したあと、ビルドが 2 回続けて `duration=0` で errored になった
# （"Page build failed." という一般的な文言だけ）。再ビルドを要求しても即座に同じ。
# **サイトは直前の成功コミットのまま凍り、全セッションの push が出ない状態**だった。
#
# 切り分けに、公開物を 1 バイトも変えないコミットを 1 つ push したところ **通った**
# （duration=303054、約 5 分）。つまり原因は push した内容ではなく、GitHub 側の
# 一過性の即時拒否である。
#
# 途中で立てて**捨てた**仮説: 「公開サイトが 3.92 GB あるので Pages の 1 GB 上限に
# 当たった」。直前に成功したコミットの時点で**すでに 3.92 GB**（1739 ファイル）
# だったので、説明になっていない。サイズは今も上限を大きく超えているが、ビルドは通る。
#
# 教訓: `duration=0` の失敗は**内容ではなく拒否**。まず押し直す。そして
# 「コミットは入った」は「配信に出た」ではない —— ライブの URL を測るまでは、
# どちらも本物の事実で、指しているものが違う。
