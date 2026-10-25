#!/usr/bin/env python3
"""公開の直前に、Minecraft の版の切り替えが**正しく**済んでいるかを判定する。

**なぜ数では判定できないか**（2026-09-20 に 2 セッションで別々に数えて食い違った）:
`+mc26.2` の出現を数えると 132、zip のファイル名だけなら 68、生成物だけなら 15 と、
数える対象で答えが変わる。しかもどの数も単独では可否を決められない。**履歴まで書き換えれば
「0 件になった」と言えてしまう**からである。数ではなく性質で見る。

判定する性質は 6 つで、**すべて同時に**成り立って初めて合格:

  1. 現行のリンクが古い版の zip を 1 つも指していない
     （`download/`・`cherry/`・`glimpse_manifest.json`・`releases.json`）
  2. **かつ** 履歴の記載が 1 文字も変わっていない
     （`changelog/`・`changelog_feed/`・`data/changelog.json`。26.2 で出したのは事実であり、
       書き換えれば嘘になる。基準表と突き合わせるので、消しても書き換えても赤くなる）
  4. **かつ** 現行のページが指す zip が git に追跡されている
     （追跡されていなければ、push でページだけが出てファイルが出ない = リンクが 404）
  3. **かつ** 現行の導入手順に古い版の例示が残っていない
     （`guide/`・`data/guide.json`。リンクではないので切れはしないが、読んだ人は
       存在しないファイル名を探すことになる）
  5. **かつ** manifest のどのブランドも、**中身**が新しい版を宣言している成果物を指している
     （zip なら中の jar、jar ならそれ自身の fabric.mod.json を読む。1〜4 はファイル名を見るので、
       `aureum-1.0.0.jar` のように名前に mc の版を持たない配布物を構造的に見られない。
       **判定できなかったブランドがあれば、それ自体が赤** —— 「見なかった」は「合格」ではない）
  6. **かつ** manifest の `sha256` と `file_size` が、指しているファイルを今も正しく説明している
     （生成器は実ファイルから計算するので構造的には正しい。壊れるのは manifest を手で直したときと、
       成果物だけ差し替えて生成器を回さなかったとき。ランチャーは manifest を信じて検証するので、
       食い違えば配布物は届かない）

使い方:
    python3 scripts/check_release_version_switch.py --old 26.2 --new 26.3 --baseline <表>
    python3 scripts/check_release_version_switch.py --old 26.2 --new 26.3 --write-baseline <表>
    python3 scripts/check_release_version_switch.py --self-test

`--write-baseline` は**切り替えの前に**走らせて、履歴の現状を記録する。

**この検査自身の試験**: `--self-test` は木の写しを作り、6 つの性質それぞれを壊して
**赤くなることを確かめる**。緑の自己試験は飾りにすぎない（2026-09-20、Cherry が
自己試験の全部緑のまま中心の判定を丸ごと削除しても緑だった例を報告している）。
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile

# 現行のリンクを持つ所（この下に古い版の zip 名があってはならない）
LIVE_DIRS = ("download", "cherry")
LIVE_FILES = ("glimpse_manifest.json", "releases.json")
# 履歴（1 文字も変えてはならない）
HISTORY_MARKERS = ("changelog",)
HISTORY_FILES = ("data/changelog.json",)
# 現行の導入手順（古い版の例示が残ってはならない）
GUIDE_DIRS = ("guide",)
GUIDE_FILES = ("data/guide.json",)

READ = (".html", ".json")


def walk(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "downloads", "node_modules", "assets")]
        for name in files:
            if name.endswith(READ):
                path = os.path.join(base, name)
                yield os.path.relpath(path, root).replace(os.sep, "/")


def read(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def is_live(rel):
    parts = rel.split("/")
    return rel in LIVE_FILES or any(p in LIVE_DIRS for p in parts[:-1])


def is_history(rel):
    return rel in HISTORY_FILES or any(m in rel for m in HISTORY_MARKERS)


def is_guide(rel):
    parts = rel.split("/")
    return rel in GUIDE_FILES or any(p in GUIDE_DIRS for p in parts[:-1])


def zip_pattern(version):
    return re.compile(r"[A-Za-z_]+_MODs_v[0-9.]+\+mc" + re.escape(version) + r"\.zip")


def any_pattern(version):
    return re.compile(r"\+mc" + re.escape(version))


def history_counts(root, old):
    """履歴の各ファイルに古い版が何回出るか。書き換えも削除も捕まえるための基準表。"""
    pat = any_pattern(old)
    out = {}
    for rel in walk(root):
        if is_history(rel):
            hits = len(pat.findall(read(root, rel)))
            if hits:
                out[rel] = hits
    return out


def declared_mc_versions(path):
    """成果物の**中身**が宣言している Minecraft 版を全部返す。

    ファイル名は見ない。`aureum-1.0.0.jar` のように名前に mc の版を持たない配布物が
    あるので、名前を見る検査は構造的にそれを取りこぼす（2026-09-20、Aureum の 26.3 版が
    版数もファイル名も 1.0.0 のまま published になり、所有者の実機でだけ表に出た）。

    zip なら中の jar すべて、jar ならそれ自身の fabric.mod.json の depends.minecraft を読む。
    返すのは {宣言文字列: [どこで]} 。読めない場合は例外を投げず空を返す —— 判定不能を
    「合格」に化けさせないため、呼び側が「1 つも読めなかった」ことを失敗として扱う。
    """
    import zipfile, io, json as _json
    found = {}

    def from_jar(fp, label):
        try:
            with zipfile.ZipFile(fp) as jz:
                if "fabric.mod.json" not in jz.namelist():
                    return
                d = _json.loads(jz.read("fabric.mod.json").decode("utf-8", "replace"))
        except Exception:
            return
        mc = (d.get("depends") or {}).get("minecraft")
        if mc is not None:
            found.setdefault(str(mc), []).append(label)

    try:
        if path.lower().endswith(".jar"):
            with open(path, "rb") as fh:
                from_jar(io.BytesIO(fh.read()), os.path.basename(path))
        elif path.lower().endswith(".zip"):
            with zipfile.ZipFile(path) as z:
                for name in z.namelist():
                    if name.lower().endswith(".jar"):
                        from_jar(io.BytesIO(z.read(name)), name)
    except Exception:
        return {}
    return found


def placeholder_problem(path, mod_id):
    """空の退役 placeholder である理由。空なら "" を返す。

    data/retirement.json が `placeholder_mod_id` を宣言した退役ブランドだけが対象。成果物の
    zip の中の jar が**ちょうど 1 つ**で、その fabric.mod.json の id が宣言どおり、
    jar の中身は META-INF/MANIFEST.MF と fabric.mod.json だけ、depends は fabricloader だけ、
    entrypoints・mixins 等の欄は空、でなければならない。1 つでも外れれば "" ではなく理由を返す
    （中身のある placeholder は、Minecraft の宣言が無い物として赤になる）。
    """
    import zipfile, io, json as _json
    try:
        with zipfile.ZipFile(path) as z:
            jars = [n for n in z.namelist() if n.lower().endswith(".jar")]
            if len(jars) != 1:
                return "zip の中の jar が %d 個（placeholder は 1 個だけ）" % len(jars)
            with zipfile.ZipFile(io.BytesIO(z.read(jars[0]))) as jz:
                names = [n for n in jz.namelist() if not n.endswith("/")]
                meta = _json.loads(jz.read("fabric.mod.json").decode("utf-8", "replace"))
    except Exception as exc:
        return "読めない (%s)" % exc
    if meta.get("id") != mod_id:
        return "jar の id が %r（宣言は %r）" % (meta.get("id"), mod_id)
    stray = sorted(set(names) - {"META-INF/MANIFEST.MF", "fabric.mod.json"})
    if stray:
        return "中身がある: %s" % ", ".join(stray[:5])
    deps = set((meta.get("depends") or {}).keys())
    if deps - {"fabricloader"}:
        return "depends が fabricloader 以外: %s" % ", ".join(sorted(deps - {"fabricloader"}))
    for field in ("entrypoints", "mixins", "accessWidener", "jars", "provides", "breaks",
                  "conflicts", "recommends", "suggests"):
        if meta.get(field):
            return "fabric.mod.json に %s がある" % field
    return ""


#: Minecraft ではない配布物。性質 5 の「Minecraft の版を宣言しているか」は意味を持たない。
#: 2026-10-04: Noctua（Palworld のサーバー側 MOD）。
NOT_MINECRAFT = frozenset({"noctua", "agent"})
# 2026-10-18: manifest の鍵のうち、ファイルを配らない「設定」。成果物が無いので性質 5 の対象外だが、黙って飛ばさず
# 名前で数え、file_name を持っていたら（ファイルの block と取り違えた）赤にする。
SETTING_KEYS = frozenset({"difficulty_lock", "ai_chat", "spawn_lock", "local_ai"})   # 2026-10-12: Corvus Agent runs beside a server, not in the game; 2026-10-22: spawn_lock (Halia switches); 2026-10-25: local_ai (model mirror, Store 5.5.204)


def check(root, old, new, baseline):
    failures = []
    notes = []

    # 性質 1: 現行のリンクに古い zip 名が無い
    zip_old = zip_pattern(old)
    live_bad = []
    for rel in walk(root):
        if is_live(rel) and zip_old.search(read(root, rel)):
            live_bad.append(rel)
    if live_bad:
        failures.append("1. 現行のリンクが %s の zip を指している (%d 件): %s"
                        % (old, len(live_bad), ", ".join(sorted(live_bad)[:6])))

    # 性質 2: 履歴が基準表と一致する
    now = history_counts(root, old)
    if baseline is None:
        failures.append("2. 履歴の基準表が渡されていない。--write-baseline を切り替えの前に走らせること。")
    else:
        for rel, want in sorted(baseline.items()):
            got = now.get(rel, 0)
            if got != want:
                failures.append("2. 履歴が変わっている: %s は %s の記載が %d 件のはずが %d 件"
                                % (rel, old, want, got))
        # **新しい履歴の追記は赤にしない。** 公開そのものが履歴を増やす（今回なら Cherry 1.0.1 の
        # 項目が 13 言語ぶん増える）。増えた履歴が古い版に言及するのは正当で、たとえば
        # 「1.0.0 は 26.2 向けだった」は事実である。性質 2 が禁じるのは **既存の履歴を書き換える/消す**
        # ことだけで、増やすことではない。消しても改名しても、基準表側の件数が減るので上で捕まる。
        if not baseline:
            # 2026-09-28: Alpha's history was erased on the owner's instruction (「抹消」). The one entry that
            # named the old version (v2.5.0, the jar rename) went with it, so there is NO history left that
            # mentions it, and this property has nothing to protect. Said on every run, not passed in silence;
            # the self-test keeps a synthetic control so the property can still be seen to fire.
            notes.append("2. 履歴の基準表が空: 26.2 に言及する履歴が 1 件も残っていない"
                         "（Alpha の履歴は 2026-09-28 に所有者の指示で消した）。この性質は今は守る物が無い")
        added = sorted(set(now) - set(baseline))
        if added:
            notes.append("2. 履歴が増えている（正当な追記として許す）: %s"
                         % ", ".join("%s(%d)" % (r, now[r]) for r in added[:6]))

    # 性質 4: 現行のページが指す zip が、**git に追跡されている**
    # 「正しいディレクトリにある」「git が追跡している」「公開される」は別の事実で、
    # push が作用するのは追跡されているものだけである（2026-09-20、Cherry の指摘で
    # Alpha・Cherry の両方の 26.3 版 zip が未追跡のままだと判明した）。
    # 未追跡のまま公開すると、**ダウンロードを宣伝するページは全部出て、ファイルだけが出ない** ——
    # ページは正しく、リンクだけが 404 になる。見た目には何も壊れていないので気づきにくい。
    wanted = set()
    zip_new = zip_pattern(new)
    for rel in walk(root):
        if is_live(rel):
            wanted.update(zip_new.findall_names(read(root, rel)) if False else
                          re.findall(r"[A-Za-z_]+_MODs_v[0-9.]+\+mc" + re.escape(new) + r"\.zip",
                                     read(root, rel)))
    if wanted:
        tracked = set()
        try:
            import subprocess
            out = subprocess.run(["git", "-C", root, "ls-files", "downloads"],
                                 capture_output=True, text=True).stdout
            tracked = {os.path.basename(x) for x in out.splitlines() if x}
        except Exception as exc:                                  # git が無い場合は判定できない
            failures.append("4. git に問い合わせられなかったので追跡を判定できない: %s" % exc)
        else:
            missing = sorted(n for n in wanted if n not in tracked)
            if missing:
                failures.append("4. 現行のページが指す zip が git に追跡されていない（push しても"
                                " ファイルが出ず、リンクが 404 になる）: %s" % ", ".join(missing))

    # 性質 3: 現行の導入手順に古い版の例示が無い
    any_old = any_pattern(old)
    guide_bad = []
    for rel in walk(root):
        if is_guide(rel) and any_old.search(read(root, rel)):
            guide_bad.append(rel)
    if guide_bad:
        failures.append("3. 現行の導入手順に %s の例示が残っている (%d 件): %s"
                        % (old, len(guide_bad), ", ".join(sorted(guide_bad)[:6])))

    # 性質 5: manifest の**どのブランドも**、中身が新しい版を宣言している成果物を指している
    # 性質 1 と 4 はファイル名（`..._MODs_v<版>+mc26.3.zip`）を見るので、**名前に mc の版を
    # 持たない配布物を構造的に見られない**。2026-09-20、Aureum の 26.3 版は版数もファイル名も
    # 1.0.0 のままで published になり、Alpha と Cherry を 26.3 へ出した同じ日に取り残された。
    # 門は 4 性質すべて緑だった。**数えていたのは綴りで、配っているものの一覧ではなかった。**
    # ここでは名前を一切見ず、zip なら中の jar、jar ならそれ自身の fabric.mod.json を読む。
    manifest_rel = "glimpse_manifest.json"
    manifest_path = os.path.join(root, manifest_rel)
    # 退役ブランドの placeholder だけは Minecraft の宣言を持たないのが正しい（2026-10-18、ASTRAEA 1.5.5 は
    # 空の placeholder jar で、agents が ASTRAEA を外すために置く）。免除は data/retirement.json が
    # `placeholder_mod_id` を宣言し、かつ jar が**本当に空**のときだけ。宣言が無いブランドは免除されない。
    try:
        with open(os.path.join(root, "data", "retirement.json"), encoding="utf-8") as fh:
            retirement = json.load(fh)
    except Exception:
        retirement = {}
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, encoding="utf-8") as fh:
                manifest = json.load(fh)
        except Exception as exc:
            failures.append("5. %s が読めないので、配っているものを数えられない: %s"
                            % (manifest_rel, exc))
        else:
            # **飛ばしたものを数える。**この輪は block["file_name"] を読むので、その鍵の綴りが
            # 違うブランドは黙って抜けて緑のまま残る —— 性質 5 が防ぐはずの欠陥を、性質 5 自身が
            # 持っていた（2026-09-20、OUKA セッションの指摘）。判定した数と、判定すべき数を
            # 突き合わせ、差があれば赤にする。「見なかった」を「合格」に化けさせない。
            judged = []
            skipped = []
            for brand in sorted(manifest):
                if brand == "launcher":       # ランチャーは MOD ではないので mc を宣言しない
                    continue
                block = manifest[brand]
                if brand in SETTING_KEYS:
                    if isinstance(block, dict) and "file_name" in block:
                        failures.append("5. %s は設定の鍵なのに file_name を持っている" % brand)
                    else:
                        notes.append("5. %s は設定（ファイルを配らない）なので成果物の判定から外した" % brand)
                    continue
                if not isinstance(block, dict):
                    skipped.append("%s（辞書ではない）" % brand)
                    continue
                file_name = block.get("file_name")
                if not file_name:
                    skipped.append("%s（file_name が無い）" % brand)
                    continue
                judged.append(brand)
                art = os.path.join(root, "downloads", file_name)
                if not os.path.isfile(art):
                    failures.append("5. manifest の %s が指すファイルが downloads に無い: %s"
                                    % (brand, file_name))
                    continue
                ret = retirement.get(brand) if isinstance(retirement.get(brand), dict) else {}
                pid = ret.get("placeholder_mod_id")
                if ret.get("retired") and pid and block.get("mod_id") == pid:
                    why = placeholder_problem(art, pid)
                    if why:
                        failures.append("5. manifest の %s (%s) は退役の placeholder (%s) と宣言されているが、"
                                        "空ではない: %s。空でない物は Minecraft の宣言が無いので赤。"
                                        % (brand, file_name, pid, why))
                    else:
                        notes.append("5. %s (%s) は data/retirement.json が宣言した空の退役 placeholder "
                                     "(%s) なので、Minecraft の宣言を免除" % (brand, file_name, pid))
                    continue
                if brand in NOT_MINECRAFT:
                    # 名指しで除外する（黙って飛ばさない）。Noctua は Palworld のサーバー側 MOD で、
                    # Minecraft の版を宣言する物が存在しない。ファイルがあることは上で確かめ、
                    # sha256 と file_size は性質 6 が同じ輪で確かめる。
                    continue
                declared = declared_mc_versions(art)
                if not declared:
                    failures.append("5. manifest の %s (%s) から Minecraft の宣言を 1 つも読めな"
                                    "かったので判定できない" % (brand, file_name))
                    continue
                stale = sorted(v for v in declared if new not in v)
                if stale:
                    where = declared[stale[0]][:3]
                    failures.append("5. manifest の %s (%s) の中身が %s 向けではない —— 宣言は %s"
                                    " (例: %s)。**名前ではなく中身が古い**ので、性質 1 と 4 では"
                                    "見えない。" % (brand, file_name, new, ", ".join(stale),
                                                    ", ".join(where)))

            if skipped:
                failures.append("5. manifest に、性質 5 が判定できなかったブランドがある (%d 件): %s"
                                "。判定した %d 件が緑でも、この %d 件については**何も確かめていない**。"
                                % (len(skipped), ", ".join(skipped), len(judged), len(skipped)))

            # 性質 6: manifest の sha256 と file_size が、いま指しているファイルを正しく説明している
            # build_glimpse_manifest.py は実ファイルから計算するので構造的には正しい。壊れるのは
            # **manifest を手で直したとき**と**成果物だけ差し替えて生成器を回さなかったとき**で、
            # 後者は corvus-pack-update-is-version-only の形（版数だけ動いて中身が届かない）になる。
            # ブランドごとの検査は cherry と ouka にしかなく、pack・launcher・aureum には無かった
            # （2026-09-20、OUKA セッションの指摘。当日の実測は 5 ブランドとも一致）。
            import hashlib
            for brand in sorted(manifest):
                block = manifest[brand]
                if not isinstance(block, dict):
                    continue
                file_name = block.get("file_name")
                want_sha = block.get("sha256")
                want_size = block.get("file_size")
                if not file_name or (want_sha is None and want_size is None):
                    continue
                art = os.path.join(root, "downloads", file_name)
                if not os.path.isfile(art):
                    continue                     # 不在は性質 5 が既に赤にしている
                try:
                    digest = hashlib.sha256()
                    size = 0
                    with open(art, "rb") as fh:
                        while True:
                            chunk = fh.read(1 << 20)
                            if not chunk:
                                break
                            size += len(chunk)
                            digest.update(chunk)
                    got_sha = digest.hexdigest()
                except Exception as exc:
                    failures.append("6. manifest の %s (%s) を読めないので照合できない: %s"
                                    % (brand, file_name, exc))
                    continue
                if want_size is not None and int(want_size) != size:
                    failures.append("6. manifest の %s (%s) の file_size が実物と違う —— "
                                    "manifest %s / 実物 %d。**ランチャーは manifest を信じて"
                                    "検証するので、配布物は届かない。**"
                                    % (brand, file_name, want_size, size))
                if want_sha is not None and str(want_sha).lower() != got_sha:
                    failures.append("6. manifest の %s (%s) の sha256 が実物と違う —— "
                                    "manifest %s… / 実物 %s…。**生成器を回さずに成果物だけ"
                                    "差し替えると、この形になる。**"
                                    % (brand, file_name, str(want_sha)[:16], got_sha[:16]))

    return failures, notes


def self_test(root, old, new):
    """**わざと壊して、6 つの性質がそれぞれ赤くなることを確かめる。**

    緑の自己試験は何も証明しない。ここで求めるのは「壊したら赤くなる」であって
    「今は緑」ではない。壊しても緑なら、その性質は飾りである。
    """
    print("=== 自己試験: 壊したら赤くなるか ===")
    base = history_counts(root, old)
    results = []

    def run(label, mutate, want_property, baseline=None):
        tmp = tempfile.mkdtemp(prefix="relswitch-")
        work = os.path.join(tmp, "site")
        shutil.copytree(root, work, ignore=shutil.ignore_patterns(".git", "downloads", "assets", "node_modules"))
        mutate(work)
        fails, _ = check(work, old, new, base if baseline is None else baseline)
        hit = [f for f in fails if f.startswith("%d." % want_property)]
        shutil.rmtree(tmp, ignore_errors=True)
        ok = bool(hit)
        results.append(ok)
        print("  %-52s -> %s%s" % (label, "赤 OK" if ok else "**緑のまま = この性質は飾り**",
                                   ("  " + hit[0][:80]) if hit else ""))

    def plant_live(work):
        target = os.path.join(work, "download", "index.html")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n<a href=\"../downloads/Alpha_MODs_v4.4.0+mc%s.zip\">x</a>\n" % old)

    def erase_history(work):
        for rel in sorted(base):
            path = os.path.join(work, rel)
            if os.path.isfile(path):
                text = read(work, rel).replace("+mc" + old, "+mc" + new)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
                return

    def plant_guide(work):
        target = os.path.join(work, "guide", "index.html")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n<code>alpha-guns-1.0.0+mc%s.jar</code>\n" % old)

    run("現行のリンクに古い zip を 1 つ植える", plant_live, 1)
    if base:
        run("履歴を 1 ファイルだけ新しい版に書き換える", erase_history, 2)
    run("導入手順に古い例示を 1 つ植える", plant_guide, 3)

    def untrack_zip(work):
        """現行のページが新しい zip を指しているのに、その実体が追跡されていない状態を作る。"""
        target = os.path.join(work, "download", "index.html")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n<a href=\"../downloads/Alpha_MODs_v9.9.9+mc%s.zip\">x</a>\n" % new)

    run("追跡されていない zip を指すリンクを植える", untrack_zip, 4)

    # --- 性質 5 ---
    # run() は downloads を複製しないので、そのままでは性質 5 が**常に**赤くなり、
    # 変異試験が空振りになる（「壊したから赤い」ではなく「素材が無いから赤い」）。
    # そこで素材を置く段と壊す段を分け、**置いただけでは緑**であることを対照で示す。
    def _stage_downloads(work):
        """manifest が指す成果物を作業複製へ持ち込む（ここまでは壊していない）。"""
        src = os.path.join(root, "downloads")
        dst = os.path.join(work, "downloads")
        os.makedirs(dst, exist_ok=True)
        with open(os.path.join(work, "glimpse_manifest.json"), encoding="utf-8") as fh:
            man = json.load(fh)
        for brand, block in man.items():
            if brand == "launcher" or not isinstance(block, dict):
                continue
            name = block.get("file_name")
            if name and os.path.isfile(os.path.join(src, name)):
                shutil.copy2(os.path.join(src, name), os.path.join(dst, name))
        return man

    def stage_only(work):
        _stage_downloads(work)

    def stale_artefact(work):
        """素材を置いたうえで、1 ブランドだけ**古い版の中身**を指させる。

        名前も版数も変えない手もあるが、ここでは実際に起きた形を再現する:
        2026-09-20、aureum は published のまま中身だけ 26.2 だった。
        """
        man = _stage_downloads(work)
        src = os.path.join(root, "downloads")
        old_jars = sorted(n for n in os.listdir(src)
                          if n.startswith("aureum-") and n.endswith(".jar")
                          and declared_mc_versions(os.path.join(src, n))
                          and all(new not in v for v in declared_mc_versions(os.path.join(src, n))))
        if not old_jars:
            return                                  # 素材が無ければ何も壊せない
        stale = old_jars[0]
        shutil.copy2(os.path.join(src, stale), os.path.join(work, "downloads", stale))
        man["aureum"]["file_name"] = stale
        with open(os.path.join(work, "glimpse_manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(man, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    def run_green(label, mutate, must_not_fire, baseline=None):
        """**壊していないときは緑**であることを確かめる。赤が空振りでない証拠。"""
        tmp = tempfile.mkdtemp(prefix="relswitch-")
        work = os.path.join(tmp, "site")
        shutil.copytree(root, work, ignore=shutil.ignore_patterns(".git", "downloads", "assets", "node_modules"))
        mutate(work)
        fails, _ = check(work, old, new, base if baseline is None else baseline)
        hit = [f for f in fails if f.startswith("%d." % must_not_fire)]
        shutil.rmtree(tmp, ignore_errors=True)
        ok = not hit
        results.append(ok)
        print("  %-52s -> %s%s" % (label, "緑 OK（対照）" if ok else "**赤い = この対照は無効**",
                                   ("  " + hit[0][:80]) if hit else ""))

    def drop_file_name(work):
        """1 ブランドの file_name を消す = 性質 5 が**黙って飛ばす**状態を作る。

        これが赤くならないなら、性質 5 は「判定したものが緑」と「全部を判定した」を
        取り違えている（2026-09-20、OUKA セッションの指摘で見つかった実際の穴）。
        """
        man = _stage_downloads(work)
        for brand in sorted(man):
            if brand != "launcher" and isinstance(man[brand], dict) and man[brand].get("file_name"):
                man[brand].pop("file_name")
                break
        with open(os.path.join(work, "glimpse_manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(man, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    def wrong_sha(work):
        """manifest の sha256 だけを 1 文字変える = 生成器を回さず手で直した形。"""
        man = _stage_downloads(work)
        for brand in sorted(man):
            b = man[brand]
            if isinstance(b, dict) and b.get("sha256") and b.get("file_name"):
                h = b["sha256"]
                b["sha256"] = ("f" if h[0] != "f" else "0") + h[1:]
                break
        with open(os.path.join(work, "glimpse_manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(man, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    def wrong_size(work):
        """manifest の file_size だけを 1 増やす = 成果物だけ差し替えた形。"""
        man = _stage_downloads(work)
        for brand in sorted(man):
            b = man[brand]
            if isinstance(b, dict) and b.get("file_size") and b.get("file_name"):
                b["file_size"] = int(b["file_size"]) + 1
                break
        with open(os.path.join(work, "glimpse_manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(man, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    if not base:
        # 2026-09-28: no real history mentions the old version any more (see check()), so there is nothing
        # to erase. The property is exercised on a SYNTHETIC baseline instead -- a history file that "used to"
        # carry one mention and now carries none -- with the matching green control first, so that a red
        # here means the property fired and not that the material was missing.
        synthetic = {"changelog/index.html": 1}

        def plant_one_mention(work):
            path = os.path.join(work, "changelog", "index.html")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write("\n<p>+mc%s</p>\n" % old)

        run_green("履歴が基準表どおり（合成の基準表・対照）", plant_one_mention, 2, baseline=synthetic)
        run("履歴の 1 件が消えた（合成の基準表）", lambda work: None, 2, baseline=synthetic)

    def retirement_undeclared(work):
        """placeholder は残し、退役の宣言だけを外す = 宣言の無いブランドは免除されない（負の対照）。"""
        _stage_downloads(work)
        rp = os.path.join(work, "data", "retirement.json")
        with open(rp, encoding="utf-8") as fh:
            doc = json.load(fh)
        doc["astraea"]["retired"] = False
        with open(rp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)

    def placeholder_with_content(work):
        """退役の placeholder に中身（クラス）を入れる = 「空」の条件を破る。"""
        import zipfile, io
        man = _stage_downloads(work)
        path = os.path.join(work, "downloads", man["astraea"]["file_name"])
        with zipfile.ZipFile(path) as z:
            entries = {n: z.read(n) for n in z.namelist()}
        jar_name = next(n for n in entries if n.endswith(".jar"))
        with zipfile.ZipFile(io.BytesIO(entries[jar_name])) as jz:
            inner = {n: jz.read(n) for n in jz.namelist()}
        inner["x/Y.class"] = b"\xca\xfe"
        jb = io.BytesIO()
        with zipfile.ZipFile(jb, "w") as jz:
            for n, b in inner.items():
                jz.writestr(n, b)
        entries[jar_name] = jb.getvalue()
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for n, b in entries.items():
                z.writestr(n, b)
        with open(path, "wb") as fh:
            fh.write(out.getvalue())

    run_green("成果物を置いただけ（壊していない）", stage_only, 5)
    run("退役の宣言を外す（宣言の無い placeholder は免除されない）", retirement_undeclared, 5)
    run("退役の placeholder に中身（クラス）を入れる", placeholder_with_content, 5)
    run("1 ブランドだけ中身が古い成果物を指させる", stale_artefact, 5)
    run("1 ブランドの file_name を消す（黙って飛ばされる形）", drop_file_name, 5)
    run_green("成果物を置いただけ（性質 6 の対照）", stage_only, 6)
    run("manifest の sha256 を 1 文字変える", wrong_sha, 6)
    run("manifest の file_size を 1 増やす", wrong_size, 6)

    ok = all(results)
    print("=== 自己試験 = %s（6 つの性質すべてが、壊されたときに赤くなる必要がある）"
          % ("PASS" if ok else "FAIL"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--old", default="26.2")
    ap.add_argument("--new", default="26.3")
    ap.add_argument("--baseline")
    ap.add_argument("--write-baseline")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.write_baseline:
        counts = history_counts(args.root, args.old)
        total = sum(counts.values())
        # **数の意味を表そのものに書く。** 2026-09-20、同じものを数えて 54 と 27 が出た
        # （出現数と行数）。どちらも正しいが、意味を書かずに並べると片方を「壊れている」と
        # 直してしまう事故が起こる。
        doc = {"_note": "履歴の基準表。値は **出現数**（1 行に 2 回出る行があるので行数とは違う）。"
                        "合計 %d 出現 / %d ファイル。性質 2 はこの表と突き合わせ、"
                        "既存の履歴の書き換え・削除を捕まえる。追記は許す。" % (total, len(counts)),
               "_old_version": args.old, "counts": counts}
        with open(args.write_baseline, "w", encoding="utf-8") as handle:
            json.dump(doc, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        print("履歴の基準表を書きました: %s（%d ファイル、%s の出現 %d 件）"
              % (args.write_baseline, len(counts), args.old, total))
        return 0

    if args.self_test:
        return 0 if self_test(args.root, args.old, args.new) else 1

    baseline = None
    if args.baseline and os.path.isfile(args.baseline):
        with open(args.baseline, encoding="utf-8") as handle:
            loaded = json.load(handle)
        baseline = loaded.get("counts", loaded) if isinstance(loaded, dict) else loaded

    failures, notes = check(args.root, args.old, args.new, baseline)
    for n in notes:
        print("  note: " + n)
    if failures:
        print("RELEASE VERSION SWITCH = FAIL (%d)" % len(failures))
        for f in failures:
            print("  - " + f)
        return 1
    print("RELEASE VERSION SWITCH = PASS（現行は %s のみ、履歴は %s のまま、導入手順も切替済み）"
          % (args.new, args.old))
    return 0


if __name__ == "__main__":
    sys.exit(main())
