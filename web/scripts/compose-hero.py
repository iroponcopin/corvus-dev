"""Composite the three cinema acts (backgrounds + eagle + crow) into one frame sequence for the scroll-scrubbed hero.
Poses follow web/src/components/cinema/timeline.ts (simplified: no blur, no grade). argv: cinema_dir out_dir W H step narrow(0/1)"""
import os, sys
from PIL import Image

src, out, W, H, step, narrow = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6] == "1"
os.makedirs(out, exist_ok=True)
EAGLE_ASPECT, BEAK_TIP_X, HEAD_TOP_Y = 921 / 1400, 0.185, 0.107
CROW_ASPECT, CROW_BODY_H, CROW_BODY_CX = 1260 / 580, 0.37, 0.53

def c01(x): return max(0.0, min(1.0, x))
def smooth(a, b, x):
    t = c01((x - a) / (b - a)); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t

# The visible window: on a phone the 16:9 frame is cover-cropped to a centred strip ~0.26 of its width.
vw = H * 390 / 844 if narrow else W
x0 = (W - vw) / 2
vh = H

def bg(act, i):
    return Image.open(f"{src}/{act}/bg/f{i + 1:03d}.webp").convert("RGB").resize((W, H), Image.LANCZOS)

eagle_cache, crow_cache = {}, {}
def eagle(i):
    if i not in eagle_cache:
        eagle_cache[i] = Image.open(f"{src}/act1/eagle/h{i + 1:03d}.webp").convert("RGBA").transpose(Image.FLIP_LEFT_RIGHT)
    return eagle_cache[i]
def crow(i):
    if i not in crow_cache:
        crow_cache[i] = Image.open(f"{src}/act2/crow/c{i + 1:03d}.webp").convert("RGBA")
    return crow_cache[i]

def paste(base, img, left, top, w, h, alpha):
    if alpha <= 0.001 or w < 2 or h < 2: return
    im = img.resize((int(w), int(h)), Image.LANCZOS)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im.putalpha(a)
    base.paste(im, (int(left), int(top)), im)

frames = []
for j in range(113): frames.append(("act1", j, j / 112, 0.0))
for j in range(182): frames.append(("act2", j, 1.0, j / 181))
for j in range(196): frames.append(("act3", j, 1.0, 1.0))

n = 0
for k, (act, j, p, a) in enumerate(frames):
    if k % step: continue
    base = bg(act, j)
    if act == "act1":
        te = smooth(0.3, 0.8, p)
        H0 = lerp(0.5 * vh, (0.95 if narrow else 1.15) * vh, te) * (1 + 0.03 * smooth(0.8, 1, p))
        W0 = H0 * EAGLE_ASPECT
        beakX = (0.25 if narrow else 0.73) * vw
        headY = (0.55 if narrow else 0.12) * vh
        left = max(lerp(vw - 0.45 * W0, beakX - BEAK_TIP_X * W0, te), vw - W0)
        top = max(lerp(vh - 0.2 * H0, headY - HEAD_TOP_Y * H0, te), vh - H0)
        idx = round(c01((p - 0.35) / 0.65) * 59)
        paste(base, eagle(idx), x0 + left, top, W0, H0, smooth(0.28, 0.36, p))
    elif act == "act2":
        rise = smooth(0.55, 1, a)
        hF = (0.13 if narrow else 0.3) / CROW_BODY_H * vh
        h = lerp(0.55 * hF, hF, rise); w = h * CROW_ASPECT
        bottom = lerp(vh + 0.9 * h, vh + 0.02 * vh, rise)
        cx = (0.5 if narrow else 0.68) * vw
        idx = round(c01((a - 0.55) / 0.45) * 104)
        paste(base, crow(idx), x0 + cx - CROW_BODY_CX * w, bottom - h, w, h, smooth(0.5, 0.6, a))
    n += 1
    base.save(f"{out}/{n:04d}.png", optimize=False, compress_level=1)
print(n)
