#!/usr/bin/env python3
"""Builds skin/index.html in every language, and the sealed skin blob it serves.

Owner's instruction, verbatim:
    「ウェブサイトからSparxie 3D Modelをスキンとして配信します。
     ですがダウンロードにはPIN Codeが必要となり、そのコードは **** として設定してください。
     DLボタンをクリックしてから **** を入力することでスキンファイルをダウンロードできます。
     PIN CODEはウェブサイト等には一切記載せず、私が直接配布します。」
  (↑ この引用の PIN は **** に伏せてある。この repo は公開されているので、
     所有者の言葉をそのまま写すと PIN がサイトに載ることになる。)

WHAT IS AND IS NOT IN THIS REPOSITORY
-------------------------------------
IN:   the SEALED blob (downloads/sparxie-skin.acsk), its salt, its iteration
      count, and the sha256 of the PLAINTEXT png.
OUT:  the PIN. It is never written to a file, a page, a script or a commit.
      This build reads it from the environment variable CORVUS_SKIN_PIN and
      uses it only to derive a key. Running the build without that variable
      re-publishes whatever blob is already committed and says so.

WHY THE FILE IS ENCRYPTED RATHER THAN THE BUTTON GUARDED
--------------------------------------------------------
On a static host a "check the PIN in JavaScript" gate is theatre twice over:
the comparison is readable in the page source, and the file itself is one
direct URL away. Sealing the file means the PIN is genuinely required — the
bytes on the server are ciphertext and the key exists only in the visitor's
browser for the moment they type it.

HONEST LIMIT (told to the owner, not buried here)
-------------------------------------------------
The PIN's length is the strength. Four digits is 10,000 possibilities; the owner moved
to an eight digit PIN on 2026-09-07, which is 10^8 and puts a brute force out of casual
reach at these iterations. Either way, someone who downloads the blob can
try them all offline; at 600,000 PBKDF2 iterations that is on the order of an
hour of one CPU, and much less with optimised code. This gate stops casual
copying and keeps the file out of search results. It is NOT secrecy. Rotating
the PIN means re-sealing (this script with a new CORVUS_SKIN_PIN), which
changes the blob — old copies stay readable with the old PIN.
"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import (  # noqa: E402
    esc, page, write_page, load_bundle, available_langs, ROOT, asset_root_prefix,
)
import skin_crypt  # noqa: E402

# The one source of the picture, and the ONLY one: this is the exact file the
# in-game NPC wears. Sparxie is drawn on the vanilla player skeleton (slim arms),
# so "the skin the site hands out" and "the texture the NPC wears" are the same
# bytes — there is nothing left that could drift between them.
#
# Until 2026-09-07 the NPC was a 1,360-box voxel sculpture and this had to be a
# separate, lossy projection of it. The owner then supplied the finished 64x64
# skin ("既存のものは全く似ておらず承認できないため、削除です") and the sculpture
# went away, which is what collapsed the two files into one.
MODS = ROOT.parent / "mods-src" / "sorakaze-planarcadia"
SKIN_SOURCE = (MODS / "src" / "main" / "resources" / "assets" / "sorakaze_planarcadia"
               / "textures" / "entity" / "sparxie.png")

# Two renderings, so the page can show what it is handing out without handing it
# over. mods-src/.../tools/check_sparxie_skin.py writes them and compares them
# byte for byte on every build.
PREVIEWS = (
    (MODS / "docs" / "sparxie-model.png", "sparxie-model.png"),
    (MODS / "docs" / "sparxie-front.png", "sparxie-front.png"),
)
PREVIEW_NAME = PREVIEWS[0][1]
PREVIEW_PATH = ROOT / "assets" / "img" / PREVIEW_NAME

BLOB_NAME = "sparxie-skin.acsk"
BLOB_PATH = ROOT / "downloads" / BLOB_NAME
PLAIN_NAME = "Sparxie.png"
MANIFEST = ROOT / "data" / "skin_gate.json"

# A fixed, PUBLIC salt. Random-per-build would make every rebuild churn the
# repository for no security gain: there is exactly one secret here and no
# rainbow table to defeat.
SALT = hashlib.sha256(b"aurora-corvus-sparxie-skin-v1").digest()[:skin_crypt.SALT_LEN]

ENV_PIN = "CORVUS_SKIN_PIN"

TITLE = {
    "ja": "Sparxie スキン",
    "en": "Sparxie skin",
}
LEDE = {
    "ja": ("Sparxie を Minecraft のスキンとして配布しています。"
           "ダウンロードには PIN コードが必要です。"
           "<b>PIN はこのサイトのどこにも書かれていません</b> —— 所有者から直接受け取ってください。"),
    "en": ("Sparxie is available as a Minecraft skin. Downloading it needs a PIN code. "
           "<b>The PIN is written nowhere on this site</b> — the owner hands it out directly."),
}
BUTTON = {"ja": "ダウンロード", "en": "Download"}
PIN_LABEL = {"ja": "PIN コード", "en": "PIN code"}
UNLOCK = {"ja": "解錠して保存", "en": "Unlock and save"}
WORKING = {"ja": "解錠しています…", "en": "Unlocking…"}
WRONG = {"ja": "PIN が違います。", "en": "That PIN is not right."}
DONE = {"ja": "保存しました。", "en": "Saved."}
NOTE = {
    "ja": ("64×64 の<b>細腕(Alex)</b>スキンです。"
           "Minecraft ランチャーの「スキン」からそのまま読み込めます。"),
    "en": ("A 64×64 <b>slim (Alex)</b> skin. Load it straight into the Minecraft "
           "launcher's Skins tab."),
}
CAVEAT = {
    "ja": ("これはパック内の Sparxie が着ているものと<b>まったく同じファイル</b>です —— "
           "売り子はバニラのプレイヤーの体(細腕)でこの絵を着ています。"
           "ランチャーでも「Alex(細腕)」を選んでください。"),
    "en": ("This is the <b>exact same file</b> the Sparxie in the pack wears — she is drawn on "
           "the vanilla player skeleton with slim arms. Pick the <b>Alex (slim)</b> model in "
           "the launcher."),
}


def text(table, lang):
    return table.get(lang, table["en"])


def seal_blob() -> dict:
    """Seal the skin, or keep the committed blob and say so."""
    if not SKIN_SOURCE.exists():
        raise SystemExit(
            f"ERROR: the skin source is missing: {SKIN_SOURCE}\n"
            f"  It is the owner's Design/Sparxie/24055800.png, copied into the mod.\n"
            f"  Refusing to publish a skin page with nothing behind it.")
    plain = SKIN_SOURCE.read_bytes()
    digest = hashlib.sha256(plain).hexdigest()
    pin = os.environ.get(ENV_PIN, "")
    if pin:
        blob = skin_crypt.seal(plain, pin, SALT)
        BLOB_PATH.parent.mkdir(parents=True, exist_ok=True)
        BLOB_PATH.write_bytes(blob)
        print(f"sealed {len(plain):,} bytes -> {BLOB_PATH.relative_to(ROOT)} "
              f"({len(blob):,} bytes, {skin_crypt.ITERATIONS:,} iterations)")
    elif BLOB_PATH.exists():
        # The PIN is absent, so the blob cannot be re-sealed. That is fine ONLY
        # while the skin has not changed. If it has, publishing would ship a
        # page that hands out yesterday's picture — so refuse, loudly, here.
        old = {}
        if MANIFEST.exists():
            old = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if old.get("plain_sha256") != digest:
            raise SystemExit(
                f"ERROR: the skin changed but the sealed blob cannot be re-made.\n"
                f"  in-game skin sha256 : {digest}\n"
                f"  sealed blob is of   : {old.get('plain_sha256', '(no manifest)')}\n"
                f"  Export the PIN for this build only:\n"
                f"      {ENV_PIN}=**** python3 scripts/build_skin_gate.py\n"
                f"  Publishing now would hand visitors the previous picture.")
        print(f"{ENV_PIN} is not set: keeping the committed blob "
              f"{BLOB_PATH.relative_to(ROOT)} ({BLOB_PATH.stat().st_size:,} bytes); "
              f"the skin has not changed, so it is still the right one.")
    else:
        raise SystemExit(
            f"ERROR: there is no sealed blob at {BLOB_PATH} and {ENV_PIN} is not set,\n"
            f"  so this build cannot make one. Export the PIN for this build only:\n"
            f"      {ENV_PIN}=**** python3 scripts/build_skin_gate.py\n"
            f"  The PIN is never stored in this repository.")
    manifest = {
        "_note": ("The sealed skin. The PIN is NOT here and never will be: this file carries the "
                  "public salt, the iteration count and the sha256 of the PLAINTEXT png so that "
                  "check_site.py can prove the blob really decrypts to the shipped skin."),
        "blob": f"downloads/{BLOB_NAME}",
        "plain_name": PLAIN_NAME,
        "plain_sha256": digest,
        "plain_bytes": len(plain),
        "salt_hex": SALT.hex(),
        "iterations": skin_crypt.ITERATIONS,
        "magic": skin_crypt.MAGIC.decode("ascii"),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    return manifest


def copy_preview() -> bool:
    """Put both views where the page can show them. Missing is a hard stop:
    a skin page with no picture of the skin is a worse page than no page."""
    for source, name in PREVIEWS:
        if not source.exists():
            raise SystemExit(
                f"ERROR: a preview is missing: {source}\n"
                f"  Run: python3 mods-src/sorakaze-planarcadia/tools/check_sparxie_skin.py")
        target = ROOT / "assets" / "img" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return True


def body(lang: str, manifest: dict, prefix: str) -> str:
    blob_url = f"{prefix}{manifest['blob']}"
    model_url = f"{prefix}assets/img/{PREVIEWS[0][1]}"
    worn_url = f"{prefix}assets/img/{PREVIEWS[1][1]}"
    alt = "Sparxie" if lang != "ja" else "スパークシー"
    shot = ("image-rendering:pixelated;max-width:150px;height:auto;"
            "border-radius:12px;flex:0 1 auto")
    return f"""
<section class="panel">
  <h1>{esc(text(TITLE, lang))}</h1>
  <p style="display:flex;gap:1.25rem;align-items:flex-end;flex-wrap:wrap;margin-bottom:1rem">
    <img src="{esc(model_url)}" alt="{esc(alt)}" style="{shot}">
    <img src="{esc(worn_url)}" alt="{esc(alt)}" style="{shot}">
  </p>
  <p>{text(LEDE, lang)}</p>
  <p class="skin-note">{text(CAVEAT, lang)}</p>
  <div class="skin-gate" id="skin-gate"
       data-blob="{esc(blob_url)}"
       data-salt="{esc(manifest['salt_hex'])}"
       data-iterations="{manifest['iterations']}"
       data-name="{esc(manifest['plain_name'])}"
       data-sha256="{esc(manifest['plain_sha256'])}">
    <button type="button" class="btn" id="skin-dl">{esc(text(BUTTON, lang))}</button>
    <div class="skin-pin" id="skin-pin" hidden>
      <label for="skin-pin-input">{esc(text(PIN_LABEL, lang))}</label>
      <input id="skin-pin-input" type="password" inputmode="numeric" autocomplete="off"
             maxlength="16" size="8">
      <button type="button" class="btn" id="skin-unlock">{esc(text(UNLOCK, lang))}</button>
    </div>
    <p class="skin-status" id="skin-status" role="status" aria-live="polite"></p>
    <p class="skin-note">{esc(text(NOTE, lang))}</p>
  </div>
</section>
<script>
(function () {{
  var root = document.getElementById('skin-gate');
  if (!root || !window.crypto || !window.crypto.subtle) {{ return; }}
  var pinBox = document.getElementById('skin-pin');
  var input = document.getElementById('skin-pin-input');
  var status = document.getElementById('skin-status');
  var MSG = {{
    working: {json.dumps(text(WORKING, lang))},
    wrong: {json.dumps(text(WRONG, lang))},
    done: {json.dumps(text(DONE, lang))}
  }};
  document.getElementById('skin-dl').addEventListener('click', function () {{
    pinBox.hidden = false;
    input.focus();
  }});
  function hex(s) {{
    var out = new Uint8Array(s.length / 2);
    for (var i = 0; i < out.length; i++) {{ out[i] = parseInt(s.substr(i * 2, 2), 16); }}
    return out;
  }}
  function u32(n) {{
    return new Uint8Array([(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255]);
  }}
  function join(parts) {{
    var total = 0, i;
    for (i = 0; i < parts.length; i++) {{ total += parts[i].length; }}
    var out = new Uint8Array(total), at = 0;
    for (i = 0; i < parts.length; i++) {{ out.set(parts[i], at); at += parts[i].length; }}
    return out;
  }}
  function same(a, b) {{
    if (a.length !== b.length) {{ return false; }}
    var diff = 0;
    for (var i = 0; i < a.length; i++) {{ diff |= a[i] ^ b[i]; }}
    return diff === 0;
  }}
  async function hmac(keyBytes, data) {{
    var key = await crypto.subtle.importKey('raw', keyBytes, {{ name: 'HMAC', hash: 'SHA-256' }},
      false, ['sign']);
    return new Uint8Array(await crypto.subtle.sign('HMAC', key, data));
  }}
  async function unlock() {{
    status.textContent = MSG.working;
    var res = await fetch(root.dataset.blob, {{ cache: 'no-store' }});
    var blob = new Uint8Array(await res.arrayBuffer());
    var magic = 'ACSK1';
    for (var i = 0; i < magic.length; i++) {{
      if (blob[i] !== magic.charCodeAt(i)) {{ status.textContent = MSG.wrong; return; }}
    }}
    var at = magic.length;
    var salt = blob.slice(at, at + 16); at += 16;
    var iterations = (blob[at] << 24 | blob[at + 1] << 16 | blob[at + 2] << 8 | blob[at + 3]) >>> 0;
    at += 4;
    var plainLen = (blob[at] << 24 | blob[at + 1] << 16 | blob[at + 2] << 8 | blob[at + 3]) >>> 0;
    at += 4;
    var tag = blob.slice(at, at + 32); at += 32;
    var ct = blob.slice(at);
    var base = await crypto.subtle.importKey('raw', new TextEncoder().encode(input.value),
      'PBKDF2', false, ['deriveBits']);
    var master = new Uint8Array(await crypto.subtle.deriveBits(
      {{ name: 'PBKDF2', salt: salt, iterations: iterations, hash: 'SHA-256' }}, base, 512));
    var encKey = master.slice(0, 32), macKey = master.slice(32, 64);
    var want = await hmac(macKey, join([salt, u32(plainLen), ct]));
    if (!same(want, tag)) {{ status.textContent = MSG.wrong; return; }}
    var stream = [], block = 0, made = 0;
    var label = new TextEncoder().encode('ACSK');
    while (made < plainLen) {{
      stream.push(await hmac(encKey, join([label, u32(block)])));
      made += 32; block += 1;
    }}
    var ks = join(stream);
    var plain = new Uint8Array(plainLen);
    for (var j = 0; j < plainLen; j++) {{ plain[j] = ct[j] ^ ks[j]; }}
    var url = URL.createObjectURL(new Blob([plain], {{ type: 'image/png' }}));
    var a = document.createElement('a');
    a.href = url; a.download = root.dataset.name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () {{ URL.revokeObjectURL(url); }}, 4000);
    status.textContent = MSG.done;
  }}
  document.getElementById('skin-unlock').addEventListener('click', function () {{
    unlock().catch(function () {{ status.textContent = MSG.wrong; }});
  }});
  input.addEventListener('keydown', function (e) {{
    if (e.key === 'Enter') {{ document.getElementById('skin-unlock').click(); }}
  }});
}})();
</script>
"""


def main():
    manifest = seal_blob()
    copy_preview()
    for lang in available_langs():
        bundle = load_bundle(lang)
        prefix = asset_root_prefix(1, lang)
        html = page(
            lang=lang,
            section="skin/",
            title=text(TITLE, lang),
            description=text(LEDE, lang).replace("<b>", "").replace("</b>", ""),
            active="",
            body=body(lang, manifest, prefix),
            depth=1,
        )
        write_page(lang, "skin/", html)


if __name__ == "__main__":
    main()
