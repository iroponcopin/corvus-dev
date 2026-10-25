#!/usr/bin/env python3
"""門（オフライン）: data/local_ai.json が Corvus Store の local_ai の約束どおりか。

Corvus Store 5.5.204 の「ローカル AI」モデルの鏡（mirror）を manifest の `local_ai` ブロックで告げる。
ランチャーは **manifest を信じて** モデルを取りに行き、ハッシュで検証する。ここが一つでも違えば、
利用者の手元にモデルは届かない（届いたものは検証で捨てられる）。だから配る前に、ネットワーク無しで
性質を確かめる。

判定する性質（すべて成り立って合格）:

  1. data/local_ai.json は {model} だけを持つ。model は {file, bytes, sha256, sources} だけを持つ。
  2. model の file・bytes・sha256 は Store の LocalAiSpec の定数と**等しい**（ここに写しを持つ。
     Store の Java ファイルが在る環境では、そのファイルの定数とも突き合わせる。無ければ NOTE を出す）。
  3. sha256 は 64 桁の小文字 16 進。
  4. sources は list。各 source は {name, parts} だけを持ち、name は空でなく、"huggingface" では**ない**
     （組み込みの取得元は Store が末尾に足す。manifest に書いてはならない）。name は重複しない。
  5. parts が空の source は「まだ埋まっていない鏡」として合格（Store は飛ばす）。
  6. parts が空でない source は: 各 part が {url, bytes, sha256} だけを持ち、url は https、bytes は正の整数、
     sha256 は 64 桁の小文字 16 進。bytes の合計が model.bytes と等しい。
  7. 埋まった parts は、data/local_ai_mirror_parts.json に書いた計画（順序・bytes・sha256）と**一致**する。
     計画そのものは、part が 3 つ・名前が part00..02・bytes の合計が model.bytes・sha256 が 64 桁。
     （連結後の sha256 は、ファイルを読まずには確かめられない。それは公開後の検査の仕事。）

Store に渡す形は、builder がこのファイルをそのまま `local_ai` に写す。ネットワーク検査は
check_published_artefacts.py の仕事（公開後）。

使い方:
    python3 scripts/check_local_ai.py
    python3 scripts/check_local_ai.py --self-test
"""
import copy
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_AI_FILE = os.path.join(ROOT, "data", "local_ai.json")
MIRROR_PLAN_FILE = os.path.join(ROOT, "data", "local_ai_mirror_parts.json")

# Store の LocalAiSpec の写し（corvus-launcher-int: core/src/main/java/net/sorakaze/glimpse/core/localai/LocalAiSpec.java,
# 2026-10-25, 取り込み時点の値）。Store 側の定数を変えたら、この写しも変えてここで突き合わせる。
STORE_SPEC_FILE = "/Volumes/ORICO/Corvus developer/Minecraft/glimpse-launcher-int/core/src/main/java/net/sorakaze/glimpse/core/localai/LocalAiSpec.java"
SPEC = {
    "file": "gemma-4-E4B_q4_0-it.gguf",
    "bytes": 5_154_941_280,
    "sha256": "676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee",
}
RESERVED_NAMES = {"huggingface"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def spec_problems_against_store(store_text):
    """Compares SPEC with the Store's Java constants. Pure: takes the file's text."""
    problems = []
    m_file = re.search(r'MODEL_FILE\s*=\s*"([^"]+)"', store_text)
    m_bytes = re.search(r"MODEL_BYTES\s*=\s*([0-9_]+)L", store_text)
    m_sha = re.search(r'MODEL_SHA256\s*=\s*"([0-9a-f]+)"', store_text)
    if not (m_file and m_bytes and m_sha):
        return ["LocalAiSpec: MODEL_FILE / MODEL_BYTES / MODEL_SHA256 not found in the Store source"]
    if m_file.group(1) != SPEC["file"]:
        problems.append(f"file: Store {m_file.group(1)!r} != site {SPEC['file']!r}")
    if int(m_bytes.group(1).replace("_", "")) != SPEC["bytes"]:
        problems.append(f"bytes: Store {m_bytes.group(1)} != site {SPEC['bytes']}")
    if m_sha.group(1) != SPEC["sha256"]:
        problems.append("sha256: Store and site differ")
    return problems


def plan_problems(plan):
    """The documented mirror plan (data/local_ai_mirror_parts.json). Pure."""
    problems = []
    if not isinstance(plan, dict):
        return ["mirror plan is not an object"]
    joined = plan.get("joined")
    if not isinstance(joined, dict) or joined.get("file") != SPEC["file"] or joined.get("bytes") != SPEC["bytes"] \
            or joined.get("sha256") != SPEC["sha256"]:
        problems.append("mirror plan: 'joined' must name the pinned model file, bytes and sha256")
    parts = plan.get("parts")
    if not isinstance(parts, list) or len(parts) != 3:
        problems.append("mirror plan: 'parts' must list exactly 3 parts")
        return problems
    total = 0
    for i, p in enumerate(parts):
        want_name = f"{SPEC['file']}.part{i:02d}"
        if not isinstance(p, dict) or set(p) != {"name", "bytes", "sha256"}:
            problems.append(f"mirror plan part {i}: must be exactly {{name, bytes, sha256}}")
            continue
        if p["name"] != want_name:
            problems.append(f"mirror plan part {i}: name {p['name']!r} != {want_name!r}")
        if not _is_int(p["bytes"]) or p["bytes"] <= 0:
            problems.append(f"mirror plan part {i}: bytes must be a positive integer")
        else:
            total += p["bytes"]
        if not isinstance(p["sha256"], str) or not HEX64.match(p["sha256"]):
            problems.append(f"mirror plan part {i}: sha256 must be 64 lowercase hex")
    if total != SPEC["bytes"]:
        problems.append(f"mirror plan: parts add up to {total}, not {SPEC['bytes']}")
    return problems


def block_problems(block, plan):
    """The whole data/local_ai.json against the rules above. Pure: takes the parsed JSON and the parsed plan."""
    problems = []
    if not isinstance(block, dict) or set(block) != {"model"}:
        return ["local_ai.json must be exactly {model: {...}}"]
    model = block["model"]
    if not isinstance(model, dict) or set(model) != {"file", "bytes", "sha256", "sources"}:
        return ["local_ai.json model must be exactly {file, bytes, sha256, sources}"]
    if model["file"] != SPEC["file"]:
        problems.append(f"model.file {model['file']!r} is not the pinned model {SPEC['file']!r}")
    if not _is_int(model["bytes"]) or model["bytes"] != SPEC["bytes"]:
        problems.append(f"model.bytes {model['bytes']!r} is not the pinned size {SPEC['bytes']}")
    if not isinstance(model["sha256"], str) or model["sha256"] != SPEC["sha256"]:
        problems.append("model.sha256 is not the pinned model hash (lowercase, 64 hex)")
    sources = model["sources"]
    if not isinstance(sources, list):
        return problems + ["model.sources must be a list"]
    names = []
    plan_parts = plan.get("parts", []) if isinstance(plan, dict) else []
    for si, src in enumerate(sources):
        if not isinstance(src, dict) or set(src) != {"name", "parts"}:
            problems.append(f"source {si}: must be exactly {{name, parts}}")
            continue
        name = src["name"]
        if not isinstance(name, str) or not name:
            problems.append(f"source {si}: name must be a non-empty string")
        elif name in RESERVED_NAMES:
            problems.append(f"source {si}: name {name!r} is the Store's built-in source; do not list it")
        elif name in names:
            problems.append(f"source {si}: name {name!r} appears twice")
        names.append(name)
        parts = src["parts"]
        if not isinstance(parts, list):
            problems.append(f"source {name!r}: parts must be a list")
            continue
        if not parts:
            continue  # not filled in yet: the Store skips it
        total = 0
        for pi, p in enumerate(parts):
            if not isinstance(p, dict) or set(p) != {"url", "bytes", "sha256"}:
                problems.append(f"source {name!r} part {pi}: must be exactly {{url, bytes, sha256}}")
                continue
            if not isinstance(p["url"], str) or not p["url"].startswith("https://"):
                problems.append(f"source {name!r} part {pi}: url must be https")
            if not _is_int(p["bytes"]) or p["bytes"] <= 0:
                problems.append(f"source {name!r} part {pi}: bytes must be a positive integer")
            else:
                total += p["bytes"]
            if not isinstance(p["sha256"], str) or not HEX64.match(p["sha256"]):
                problems.append(f"source {name!r} part {pi}: sha256 must be 64 lowercase hex")
            if pi < len(plan_parts) and isinstance(plan_parts[pi], dict):
                want = plan_parts[pi]
                if p.get("bytes") != want.get("bytes") or p.get("sha256") != want.get("sha256"):
                    problems.append(f"source {name!r} part {pi}: bytes/sha256 differ from data/local_ai_mirror_parts.json")
        if len(parts) != len(plan_parts):
            problems.append(f"source {name!r}: {len(parts)} parts, but the plan lists {len(plan_parts)}")
        if total != SPEC["bytes"]:
            problems.append(f"source {name!r}: parts add up to {total}, not {SPEC['bytes']}")
    return problems


def run_all():
    """Reads the shipped files and runs every rule. Returns the list of problems."""
    with open(LOCAL_AI_FILE, encoding="utf-8") as f:
        block = json.load(f)
    with open(MIRROR_PLAN_FILE, encoding="utf-8") as f:
        plan = json.load(f)
    problems = plan_problems(plan) + block_problems(block, plan)
    if os.path.isfile(STORE_SPEC_FILE):
        with open(STORE_SPEC_FILE, encoding="utf-8") as f:
            problems += spec_problems_against_store(f.read())
    else:
        print(f"  NOTE  Store source not present here ({STORE_SPEC_FILE}); the copy of LocalAiSpec was not cross-checked.")
    return problems


def self_test():
    """Every rule must turn a planted defect red, and the shipped data must be green."""
    with open(LOCAL_AI_FILE, encoding="utf-8") as f:
        good_block = json.load(f)
    with open(MIRROR_PLAN_FILE, encoding="utf-8") as f:
        good_plan = json.load(f)
    failures = []

    def expect_red(label, block, plan):
        found = block_problems(block, plan) + plan_problems(plan)
        if not found:
            failures.append(f"NOT RED: {label}")
        else:
            print(f"  red as wanted  {label}: {found[0]}")

    def expect_green(label, block, plan):
        found = block_problems(block, plan) + plan_problems(plan)
        if found:
            failures.append(f"NOT GREEN: {label}: {found}")
        else:
            print(f"  green control  {label}")

    expect_green("shipped data/local_ai.json (empty mirror)", good_block, good_plan)

    filled = copy.deepcopy(good_block)
    filled["model"]["sources"][0]["parts"] = [
        {"url": "https://example.invalid/p%02d" % i, "bytes": p["bytes"], "sha256": p["sha256"]}
        for i, p in enumerate(good_plan["parts"])]
    expect_green("filled mirror matching the plan", filled, good_plan)

    def plant(label, mutate, base=good_block, plan=good_plan):
        b = copy.deepcopy(base)
        p = copy.deepcopy(plan)
        mutate(b, p)
        expect_red(label, b, p)

    plant("extra top-level key", lambda b, p: b.update({"other": 1}))
    plant("model key missing", lambda b, p: b["model"].pop("sha256"))
    plant("file renamed", lambda b, p: b["model"].update({"file": "other.gguf"}))
    plant("bytes differ from the Store", lambda b, p: b["model"].update({"bytes": 5154941281}))
    plant("bytes as float", lambda b, p: b["model"].update({"bytes": float(SPEC["bytes"])}))
    plant("sha256 differs from the Store", lambda b, p: b["model"].update({"sha256": "a" * 64}))
    plant("sha256 uppercase", lambda b, p: b["model"].update({"sha256": SPEC["sha256"].upper()}))
    plant("the built-in source listed", lambda b, p: b["model"]["sources"].append(
        {"name": "huggingface", "parts": []}))
    plant("duplicate source name", lambda b, p: b["model"]["sources"].append({"name": "corvus", "parts": []}))
    plant("source without a name", lambda b, p: b["model"]["sources"][0].update({"name": ""}))

    def http_part(b, p):
        b["model"]["sources"][0]["parts"] = [{"url": "http://example.invalid/p0", "bytes": SPEC["bytes"],
                                              "sha256": "b" * 64}]
    plant("part url is http", http_part)

    def short_part(b, p):
        b["model"]["sources"][0]["parts"] = [{"url": "https://example.invalid/p0", "bytes": 100, "sha256": "b" * 64}]
    plant("parts do not add up to the model size", short_part)

    def bad_part_sha(b, p):
        b["model"]["sources"][0]["parts"] = [{"url": "https://example.invalid/p0", "bytes": SPEC["bytes"],
                                              "sha256": "xyz"}]
    plant("part sha256 malformed", bad_part_sha)

    def part_extra(b, p):
        b["model"]["sources"][0]["parts"] = [{"url": "https://example.invalid/p0", "bytes": SPEC["bytes"],
                                              "sha256": "b" * 64, "name": "x"}]
    plant("part with an extra key", part_extra)

    def wrong_plan_sha(b, p):
        filled_b = copy.deepcopy(filled)
        filled_b["model"]["sources"][0]["parts"][1]["sha256"] = "d" * 64
        b.clear(); b.update(filled_b)
    plant("filled part disagrees with the documented plan", wrong_plan_sha)

    plant("plan: a part missing", lambda b, p: p["parts"].pop())
    plant("plan: parts do not add up", lambda b, p: p["parts"][0].update({"bytes": 1}))
    plant("plan: wrong part name", lambda b, p: p["parts"][0].update({"name": "x.part00"}))

    def spec_drift(_b, _p):
        bad = "public static final String MODEL_FILE = \"other.gguf\";\n" \
              "public static final long MODEL_BYTES = 5_154_941_280L;\n" \
              "public static final String MODEL_SHA256 = \"%s\";\n" % SPEC["sha256"]
        if not spec_problems_against_store(bad):
            failures.append("NOT RED: Store constant drift is not seen")
        else:
            print("  red as wanted  Store constant drift (file renamed in the Store)")
    spec_drift(None, None)

    green_store = ("public static final String MODEL_FILE = \"%s\";\n"
                   "public static final long MODEL_BYTES = 5_154_941_280L;\n"
                   "public static final String MODEL_SHA256 = \"%s\";\n") % (SPEC["file"], SPEC["sha256"])
    if spec_problems_against_store(green_store):
        failures.append("NOT GREEN: the Store text that matches the copy")
    else:
        print("  green control  Store constants equal the copy")

    if failures:
        print("LOCAL AI GATE SELF-TEST = FAIL")
        for f in failures:
            print("  - " + f)
        return 1
    print("LOCAL AI GATE SELF-TEST = PASS (every planted defect is red; the shipped data is green)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    problems = run_all()
    if problems:
        print("LOCAL AI = FAIL (%d)" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1
    print("LOCAL AI = PASS (data/local_ai.json matches the Store's pinned model and the documented plan)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
