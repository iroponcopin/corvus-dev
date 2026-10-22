#!/usr/bin/env python3
"""**公開されているもの**が manifest の約束どおりか確かめる。門ではなく、公開後の手順。

`check_release_version_switch.py` は push の**前**に走るので、見られるのは
リポジトリの `downloads/` までである。**利用者に届くのは配信側だけ**で、
これは push して配備が終わって初めて存在する。性質にすると「まだ配備されていない」
だけで赤くなるか、待ち時間を門の中に抱え込むことになる（2026-09-20、OUKA セッション）。
なので門はリポジトリ側、この道具は配信側、と分けてある。

**いつ走らせるか**は「自分が push したとき」**ではない**。GitHub Pages の再配備は
サイト全体を出し直すので、**他ブランドが push しただけで配信側は変わりうる**。
自分が何もしていなくても測り直す理由になる。

判定できなかったものは**失敗として数える**。取得できなかった、manifest に
sha256 が無い、などを「合格」に化けさせない。
"""
SETTING_BLOCKS = {"ai_chat", "difficulty_lock", "spawn_lock"}   # spawn_lock: 2026-10-22 (Halia V1.4 switches)
import argparse
import hashlib
import json
import sys
import time
import urllib.request

BASE = "https://iroponcopin.github.io/corvus-dev"


def fetch(url, timeout=120):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.geturl(), resp.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--wait", type=int, default=0,
                    help="manifest が期待どおりになるまで待つ上限（秒）。この site の配備は実測 約 150 秒。")
    ap.add_argument("--expect", action="append", default=[],
                    help="brand=version（例 aureum=1.0.1）。配備待ちの終了条件に使う。")
    args = ap.parse_args()

    expect = {}
    for item in args.expect:
        if "=" not in item:
            print("--expect は brand=version の形で書く: %r" % item); return 2
        k, v = item.split("=", 1)
        expect[k.strip()] = v.strip()

    deadline = time.time() + args.wait
    manifest = None
    while True:
        try:
            _, raw = fetch(args.base + "/glimpse_manifest.json")
            manifest = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            manifest = None
            reason = "manifest を取得できない: %s" % exc
        else:
            missing = [k for k, v in expect.items()
                       if str((manifest.get(k) or {}).get("latest")) != v]
            if not missing:
                break
            reason = "まだ配備されていない: %s" % ", ".join(
                "%s は %s のはずが %s" % (k, expect[k], (manifest.get(k) or {}).get("latest"))
                for k in missing)
        if time.time() >= deadline:
            if manifest is None:
                print("PUBLISHED ARTEFACTS = FAIL（%s）" % reason); return 1
            print("  %s" % reason)
            break
        time.sleep(10)

    failures, checked = [], []
    for brand in sorted(manifest):
        block = manifest[brand]
        if not isinstance(block, dict):
            continue
        # Settings, not downloads: they carry no file by design (and must never carry one).
        if brand in SETTING_BLOCKS:
            if "file_name" in block:
                failures.append("%s: a setting block must not name a file" % brand)
            continue
        name, want_sha, want_size = (block.get("file_name"), block.get("sha256"),
                                     block.get("file_size"))
        if not name:
            failures.append("%s: manifest に file_name が無いので測れない" % brand); continue
        if want_sha is None and want_size is None:
            failures.append("%s (%s): manifest に sha256 も file_size も無いので測れない"
                            % (brand, name)); continue
        url = "%s/downloads/%s" % (args.base, name)
        try:
            got_url, body = fetch(url, timeout=600)
        except Exception as exc:
            failures.append("%s (%s): 取得できない —— %s" % (brand, name, exc)); continue
        if not got_url.endswith("/" + name):
            failures.append("%s: %s を要求したのに %s が返った（別のものを測ってしまう）"
                            % (brand, name, got_url)); continue
        got_sha = hashlib.sha256(body).hexdigest()
        checked.append(brand)
        if want_size is not None and int(want_size) != len(body):
            failures.append("%s (%s): バイト数が manifest と違う —— 約束 %s / 実物 %d"
                            % (brand, name, want_size, len(body)))
        if want_sha is not None and str(want_sha).lower() != got_sha:
            failures.append("%s (%s): sha256 が manifest と違う —— 約束 %s… / 実物 %s…。"
                            "**ランチャーは manifest を信じて検証するので、届かない。**"
                            % (brand, name, str(want_sha)[:16], got_sha[:16]))

    for brand in sorted(manifest):
        b = manifest[brand]
        if isinstance(b, dict) and b.get("file_name") and brand not in checked:
            pass                                   # 既に failures に理由が入っている

    print("  照合したブランド: %d 件（%s）" % (len(checked), ", ".join(checked) or "なし"))
    if failures:
        print("PUBLISHED ARTEFACTS = FAIL (%d)" % len(failures))
        for f in failures:
            print("  - %s" % f)
        return 1
    if not checked:
        print("PUBLISHED ARTEFACTS = FAIL（1 件も照合できなかった）"); return 1
    print("PUBLISHED ARTEFACTS = PASS（配信されている実物が manifest の約束どおり）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
