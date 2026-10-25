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
SETTING_BLOCKS = {"ai_chat", "difficulty_lock", "spawn_lock", "local_ai"}   # spawn_lock: 2026-10-22 (Halia V1.4 switches); local_ai: 2026-10-25 (model mirror, Store 5.5.204)
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "https://iroponcopin.github.io/corvus-dev"


def fetch(url, timeout=120):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.geturl(), resp.read()


# ---- local_ai: the model mirror's parts, over the network (2026-10-25) -------------------------------------------
# A part that is listed must answer 200 with exactly its bytes, and must serve a Range (the Store resumes downloads
# with it). The first MiB is read as a bounded Range, never the whole 1.8 GB part. An empty source is skipped and
# printed as skipped: the Store does not use it, so there is nothing to measure.
LOCAL_AI_RANGE = 1024 * 1024


def _open(req, timeout=120):
    return urllib.request.urlopen(req, timeout=timeout)


def probe_local_ai_part(url, want_bytes, opener=_open):
    """Returns None when the part is as promised, else the reason it is not. Never downloads the whole part."""
    try:
        with opener(urllib.request.Request(url, method="HEAD", headers={"User-Agent": "corvus-site-check"})) as r:
            status, length = r.status, r.headers.get("Content-Length")
    except urllib.error.HTTPError as exc:
        return "HTTP %d（取得できない。公開されていない可能性）" % exc.code
    except Exception as exc:
        return "取得できない —— %s" % exc
    if status != 200:
        return "HEAD が %d を返した（200 が必要）" % status
    if length is None or int(length) != int(want_bytes):
        return "Content-Length が約束と違う —— 約束 %s / 実物 %s" % (want_bytes, length)
    try:
        with opener(urllib.request.Request(url, headers={"User-Agent": "corvus-site-check",
                                                         "Range": "bytes=0-%d" % (LOCAL_AI_RANGE - 1)})) as r:
            status, content_range, body = r.status, r.headers.get("Content-Range"), r.read()
    except Exception as exc:
        return "Range 読み出しが失敗 —— %s" % exc
    if status != 206:
        return "Range が効かない（206 が必要、実際 %d）。Store は途中再開できない" % status
    if not content_range or not content_range.endswith("/%d" % int(want_bytes)):
        return "Content-Range の総量が約束と違う —— %s" % content_range
    if len(body) != min(LOCAL_AI_RANGE, int(want_bytes)):
        return "Range で返った長さが違う —— %d" % len(body)
    return None


def check_local_ai_block(block, opener=_open):
    """The local_ai block's listed sources. Returns (failures, skipped_names, probed_count)."""
    failures, skipped, probed = [], [], 0
    model = (block or {}).get("model") or {}
    for src in model.get("sources") or []:
        name = src.get("name", "?")
        parts = src.get("parts") or []
        if not parts:
            skipped.append(name)
            continue
        for i, part in enumerate(parts):
            probed += 1
            why = probe_local_ai_part(part["url"], part["bytes"], opener)
            if why:
                failures.append("local_ai %s part %d (%s): %s" % (name, i, part["url"], why))
    return failures, skipped, probed


def _self_test_local_ai():
    """Serves two fake parts from a local server (HEAD + Range) and plants one defect per rule. Each must be red."""
    import http.server
    import threading

    body = bytes(range(256)) * (3 * 1024 * 1024 // 256 + 1)   # 3 MiB + a little
    size = len(body)

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _answer(self, head):
            if self.path == "/gone":
                self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
            if self.path == "/locked":
                self.send_response(401); self.send_header("Content-Length", "0"); self.end_headers(); return
            if self.path == "/norange":
                self.send_response(200); self.send_header("Content-Length", str(size)); self.end_headers()
                if not head:
                    self.wfile.write(body)
                return
            rng = self.headers.get("Range")
            if head or not rng:
                self.send_response(200); self.send_header("Content-Length", str(size)); self.end_headers()
                if not head:
                    self.wfile.write(body)
                return
            start, end = rng.split("=")[1].split("-")
            start, end = int(start), min(int(end), size - 1)
            chunk = body[start:end + 1]
            self.send_response(206)
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
            self.send_header("Content-Length", str(len(chunk)))
            self.end_headers()
            self.wfile.write(chunk)

        def do_HEAD(self):
            self._answer(True)

        def do_GET(self):
            self._answer(False)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % server.server_address[1]
    failures = []

    def expect(label, want_red, url, want_bytes):
        why = probe_local_ai_part(base + url, want_bytes)
        if want_red and not why:
            failures.append("NOT RED: " + label)
        elif not want_red and why:
            failures.append("NOT GREEN: %s: %s" % (label, why))
        else:
            print("  %s  %s%s" % ("red as wanted" if want_red else "green control", label, ("（%s）" % why) if why else ""))

    expect("a part that answers 200 with its bytes and serves Range", False, "/ok", size)
    expect("a part whose length differs from the manifest", True, "/ok", size + 1)
    expect("a part that is not there (404)", True, "/gone", size)
    expect("a part that asks for sign-in (401)", True, "/locked", size)
    expect("a part that ignores Range", True, "/norange", size)

    # the block-level check: empty sources skipped; a listed source probed; a planted 404 fails by name
    blk_empty = {"model": {"sources": [{"name": "corvus", "parts": []}]}}
    f, sk, n = check_local_ai_block(blk_empty)
    if f or sk != ["corvus"] or n:
        failures.append("NOT GREEN: an empty source must be skipped, not probed")
    else:
        print("  green control  an empty mirror source is skipped")
    blk_gone = {"model": {"sources": [{"name": "corvus", "parts": [
        {"url": base + "/gone", "bytes": size, "sha256": "0" * 64}]}]}}
    f, _sk, n = check_local_ai_block(blk_gone)
    if not f or n != 1:
        failures.append("NOT RED: a listed source whose part is 404 must fail by name")
    else:
        print("  red as wanted  a listed part that is 404 fails by name")

    server.shutdown()
    if failures:
        print("PUBLISHED ARTEFACTS SELF-TEST (local_ai) = FAIL")
        for x in failures:
            print("  - " + x)
        return 1
    print("PUBLISHED ARTEFACTS SELF-TEST (local_ai) = PASS")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--wait", type=int, default=0,
                    help="manifest が期待どおりになるまで待つ上限（秒）。この site の配備は実測 約 150 秒。")
    ap.add_argument("--self-test", action="store_true", help="planted defects for the local_ai network check (offline).")
    ap.add_argument("--expect", action="append", default=[],
                    help="brand=version（例 aureum=1.0.1）。配備待ちの終了条件に使う。")
    args = ap.parse_args()
    if args.self_test:
        return _self_test_local_ai()

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
            if brand == "local_ai":
                f, skipped, probed = check_local_ai_block(block)
                failures.extend(f)
                print("  local_ai: %d part(s) probed, source(s) skipped (empty mirror): %s"
                      % (probed, ", ".join(skipped) or "none"))
                if not probed and not skipped:
                    failures.append("local_ai: no sources at all")
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
