"""Sett sammen animerte hodebiter (fra hode_bit.sh) til én presentatørvideo.

    python hode_komposit.py --foto meg.jpg --plan plan.json --biter <mappe> --lyd tale.wav \
        --ut presentator.mp4 [--utsnitt X Y B H] [--storrelse 540 720]

<mappe> inneholder bit_01/, bit_02/, … med hode.mp4 og info.json. Hodet limes inn i bildet med en
myk oval maske (kropp og bakgrunn forblir originalbildet), gjøres litt skarpere og fargejusteres.
Skjøtene mellom bitene tones mykt over, og hver bit justeres til nøyaktig riktig antall bilder,
så munnen holder seg synkron med talen.
"""
import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

FPS = 25
OVERTONING = 8  # bilder


def les_bilder(mp4: Path, b: int, h: int):
    p = subprocess.Popen(["ffmpeg", "-v", "fatal", "-i", str(mp4), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    n = b * h * 3
    while True:
        data = p.stdout.read(n)
        if len(data) < n:
            break
        yield np.frombuffer(data, np.uint8).reshape(h, b, 3)
    p.wait()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--foto", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--biter", required=True)
    ap.add_argument("--lyd")
    ap.add_argument("--ut", required=True)
    ap.add_argument("--utsnitt", type=int, nargs=4, metavar=("X", "Y", "B", "H"))
    ap.add_argument("--storrelse", type=int, nargs=2, default=[540, 720], metavar=("B", "H"))
    ap.add_argument("--skarphet", type=float, default=0.6)
    a = ap.parse_args()

    foto = cv2.cvtColor(cv2.imread(a.foto), cv2.COLOR_BGR2RGB)
    fh, fb = foto.shape[:2]
    ux, uy, uw, uh = a.utsnitt or (0, 0, fb, fh)
    kb, kh = a.storrelse
    s = kb / uw
    bakgrunn = cv2.resize(foto[uy:uy + uh, ux:ux + uw], (kb, kh), interpolation=cv2.INTER_AREA).astype(np.float32)

    plan = json.loads(Path(a.plan).read_text())
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{kb}x{kh}", "-r", str(FPS),
           "-i", "-"]
    if a.lyd:
        cmd += ["-i", a.lyd, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", a.ut]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    forrige = None
    for bit in plan["biter"]:
        mappe = Path(a.biter) / f"bit_{bit['nr']:02d}"
        info = json.loads((mappe / "info.json").read_text())
        clx, cly, _, _ = info["crop_box"]
        lx, ly, rx, ry = info["quad"]
        # Limeboks i kortets koordinater
        x1, y1 = (clx + lx - ux) * s, (cly + ly - uy) * s
        x2, y2 = (clx + rx - ux) * s, (cly + ry - uy) * s
        bw, bh = int(round(x2 - x1)), int(round(y2 - y1))
        x1, y1 = int(round(x1)), int(round(y1))
        # Klipp boksen til kortet
        cx0, cy0, cx1, cy1 = max(x1, 0), max(y1, 0), min(x1 + bw, kb), min(y1 + bh, kh)
        yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
        ell = ((xx - bw * 0.5) / (bw * 0.37)) ** 2 + ((yy - bh * 0.47) / (bh * 0.47)) ** 2
        maske = np.clip((1.12 - ell) / 0.35, 0, 1)
        maske = cv2.GaussianBlur(maske, (0, 0), bw * 0.03)[cy0 - y1:cy1 - y1, cx0 - x1:cx1 - x1, None]
        orig = bakgrunn[cy0:cy1, cx0:cx1]
        fargejust = None

        bilder = les_bilder(mappe / "hode.mp4", *info["storrelse"])
        siste = None
        for i in range(bit["bilder"]):
            f = next(bilder, None)
            if f is None:
                f = siste  # biten ble litt kortere enn planlagt – hold siste bilde
            siste = f
            r = cv2.resize(f, (bw, bh), interpolation=cv2.INTER_CUBIC).astype(np.float32)
            if a.skarphet > 0:
                r = r + a.skarphet * (r - cv2.GaussianBlur(r, (0, 0), 1.2))
            r = r[cy0 - y1:cy1 - y1, cx0 - x1:cx1 - x1]
            if fargejust is None:  # fargejuster mot bildet ut fra første (nøytrale) bilde i biten
                m = maske[..., 0] > 0.5
                fargejust = (orig[m].mean(0) + 1) / (r[m].mean(0) + 1)
            r = r * fargejust
            ut = bakgrunn.copy()
            ut[cy0:cy1, cx0:cx1] = orig * (1 - maske) + r * maske
            if forrige is not None and i < OVERTONING:  # myk overgang fra forrige bit
                w = (i + 1) / (OVERTONING + 1)
                ut = forrige * (1 - w) + ut * w
            ff.stdin.write(np.clip(ut, 0, 255).astype(np.uint8).tobytes())
        forrige = ut
        print(f"bit {bit['nr']:02d}: {bit['bilder']} bilder", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"Ferdig: {a.ut}")


if __name__ == "__main__":
    main()
