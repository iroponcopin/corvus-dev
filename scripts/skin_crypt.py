#!/usr/bin/env python3
"""Corvus —— <b>スキン配布の錠。</b>暗号の実装はここ 1 か所にしかない。

所有者の指示(逐語):
  「ウェブサイトからSparxie 3D Modelをスキンとして配信します。
   ですがダウンロードにはPIN Codeが必要となり、そのコードは **** として設定してください。
   DLボタンをクリックしてから **** を入力することでスキンファイルをダウンロードできます。
   PIN CODEはウェブサイト等には一切記載せず、私が直接配布します。」
  (↑ この引用の PIN は **** に伏せてある。この repo は公開されているので、
     所有者の言葉をそのまま写すと PIN がサイトに載ることになる。)

## なぜ「JS で PIN を比べる」ではないのか

静的サイトでは、JS の中の比較は<b>ページのソースを開けば読める</b>。それどころか
PIN を突き止めなくても、<b>スキンの URL を直接叩けば</b>ファイルは落ちてしまう。
だから錠は<b>ファイルそのものに掛ける</b>: サーバーに置くのは暗号文で、
PIN からしか鍵が出ない。PIN はリポジトリにも HTML にも JS にも入らない
(ビルド時に環境変数 {@code CORVUS_SKIN_PIN} から受け取るだけである)。

## 仕組み(標準の道具だけで、ブラウザと Python が同じ計算をする)

    master     = PBKDF2-HMAC-SHA256(PIN, salt, iterations, 64 バイト)
    encKey     = master[0:32]
    macKey     = master[32:64]
    keystream  = HMAC-SHA256(encKey, "ACSK" || uint32be(block)) を連結
    ciphertext = plaintext XOR keystream
    tag        = HMAC-SHA256(macKey, salt || uint32be(len) || ciphertext)

暗号化してから MAC を掛ける(encrypt-then-MAC)。PIN が違えば tag が合わないので
<b>1 バイトも復号せずに断る</b>。ブラウザ側は WebCrypto の PBKDF2 と HMAC だけで
同じ計算ができる —— 外部ライブラリは 1 つも要らない。

## 正直に書いておく限界

<b>PIN の桁数がそのまま強さである。</b>4 桁なら 10,000 通りしかなく、
暗号文を落とした人が総当たりすれば反復 {@link #ITERATIONS} 回でも数時間で開く。
所有者は 2026-09-07 に 8 桁へ変えた —— 10<sup>8</sup> 通りで、同じ反復回数なら
総当たりは現実的でなくなる(桁を増やすことが、この錠でいちばん効く手当てである)。
それでもここが守っているのは
「URL を知っているだけの人」と「配られていない人が気軽に落とすこと」であって、
<b>本気の攻撃者ではない</b>。守っている中身がスキンの PNG であることを踏まえた
釣り合いの取れた設計だが、<b>秘密ではない</b>ことは所有者に伝えてある。
"""
from __future__ import annotations

import hashlib
import hmac
import struct

MAGIC = b"ACSK1"
SALT_LEN = 16
TAG_LEN = 32
ITERATIONS = 600_000
KEYSTREAM_LABEL = b"ACSK"


def derive(pin: str, salt: bytes, iterations: int = ITERATIONS) -> tuple[bytes, bytes]:
    master = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations, dklen=64)
    return master[:32], master[32:]


def keystream(enc_key: bytes, length: int) -> bytes:
    out = bytearray()
    block = 0
    while len(out) < length:
        out += hmac.new(enc_key, KEYSTREAM_LABEL + struct.pack(">I", block), hashlib.sha256).digest()
        block += 1
    return bytes(out[:length])


def tag_of(mac_key: bytes, salt: bytes, plain_len: int, ciphertext: bytes) -> bytes:
    return hmac.new(mac_key, salt + struct.pack(">I", plain_len) + ciphertext, hashlib.sha256).digest()


def seal(plaintext: bytes, pin: str, salt: bytes, iterations: int = ITERATIONS) -> bytes:
    """暗号文を作る。**salt は呼び手が渡す** —— ビルドが決定的であるために。"""
    if len(salt) != SALT_LEN:
        raise ValueError("salt must be %d bytes" % SALT_LEN)
    enc_key, mac_key = derive(pin, salt, iterations)
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, keystream(enc_key, len(plaintext))))
    tag = tag_of(mac_key, salt, len(plaintext), ciphertext)
    return (MAGIC + salt + struct.pack(">I", iterations)
            + struct.pack(">I", len(plaintext)) + tag + ciphertext)


def open_sealed(blob: bytes, pin: str) -> bytes:
    """復号する。**PIN が違えば例外**(1 バイトも返さない)。"""
    if not blob.startswith(MAGIC):
        raise ValueError("not an ACSK1 blob")
    at = len(MAGIC)
    salt = blob[at:at + SALT_LEN]
    at += SALT_LEN
    iterations = struct.unpack(">I", blob[at:at + 4])[0]
    at += 4
    plain_len = struct.unpack(">I", blob[at:at + 4])[0]
    at += 4
    tag = blob[at:at + TAG_LEN]
    at += TAG_LEN
    ciphertext = blob[at:]
    if len(ciphertext) != plain_len:
        raise ValueError("length field disagrees with the ciphertext")
    enc_key, mac_key = derive(pin, salt, iterations)
    if not hmac.compare_digest(tag, tag_of(mac_key, salt, plain_len, ciphertext)):
        raise ValueError("wrong PIN (the tag does not match)")
    return bytes(a ^ b for a, b in zip(ciphertext, keystream(enc_key, plain_len)))
