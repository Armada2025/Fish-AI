#!/usr/bin/env python3
"""Steg 2b: Leppesynk med Wav2Lip over et kort basisklipp (eller et stillbilde).

Basisklippet (f.eks. 12 s fra SadTalker med naturlige blunk og lukket munn) spilles
fram og tilbake i løkke gjennom hele talen. Wav2Lip lager munnbevegelsene, og bare
munn- og kjeveområdet blandes inn med myk overgang, slik at øyne og hud forblir skarpe.

Kjøres med et Python-miljø som har torch, librosa, opencv og Wav2Lip-koden:
  python leppesynk.py --base base.mp4 --lyd bygg/tale.wav --ut bygg/presentator.mp4 \
      --wav2lip /sti/til/Wav2Lip --utsnitt 150 400 1200 1600
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch

FPS = 25
MEL_STEG = 16


def les_bilder(sti: Path, utsnitt, storrelse) -> list[np.ndarray]:
    """Les basisklippet (eller ett bilde), beskjær og skaler til arbeidsstørrelsen (BGR)."""
    b, h = storrelse
    if sti.suffix.lower() in (".jpg", ".jpeg", ".png"):
        rammer = [cv2.imread(str(sti))]
    else:
        cap = cv2.VideoCapture(str(sti))
        rammer = []
        while True:
            ok, f = cap.read()
            if not ok:
                break
            rammer.append(f)
    ut = []
    for f in rammer:
        if utsnitt:
            x, y, w, hh = utsnitt
            f = f[y:y + hh, x:x + w]
        ut.append(cv2.resize(f, (b, h), interpolation=cv2.INTER_AREA))
    return ut


def finn_ansikt(bilde: np.ndarray, vektmappe: Path) -> tuple[int, int, int, int]:
    """Ansiktsboks (topp, bunn, venstre, høyre) med RetinaFace fra facexlib."""
    from facexlib.detection import init_detection_model
    modell = init_detection_model("retinaface_resnet50", half=False, device="cpu", model_rootpath=str(vektmappe))
    with torch.no_grad():
        bokser = modell.detect_faces(bilde, 0.9)
    if len(bokser) == 0:
        raise SystemExit("Fant ikke noe ansikt – oppgi --boks manuelt")
    x1, y1, x2, y2 = max(bokser, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))[:4]
    return int(y1), int(y2), int(x1), int(x2)


def last_modell(wav2lip_mappe: Path, vekter: Path):
    sys.path.insert(0, str(wav2lip_mappe))
    from models import Wav2Lip
    modell = Wav2Lip()
    sd = torch.load(str(vekter), map_location="cpu")["state_dict"]
    modell.load_state_dict({k.replace("module.", ""): v for k, v in sd.items()})
    return modell.eval()


def mel_biter(lyd: Path, wav2lip_mappe: Path, antall: int) -> list[np.ndarray]:
    sys.path.insert(0, str(wav2lip_mappe))
    import audio
    wav = audio.load_wav(str(lyd), 16000)
    mel = audio.melspectrogram(wav)
    biter = []
    for i in range(antall):
        s = int(i * 80.0 / FPS)
        if s + MEL_STEG > mel.shape[1]:
            biter.append(mel[:, -MEL_STEG:])
        else:
            biter.append(mel[:, s:s + MEL_STEG])
    return biter


def blandemaske(h: int, w: int) -> np.ndarray:
    """Myk maske for nedre del av ansiktsboksen (munn, kinn og kjeve)."""
    m = np.zeros((h, w), np.float32)
    cv2.ellipse(m, (w // 2, int(h * 0.74)), (int(w * 0.36), int(h * 0.26)), 0, 0, 360, 1.0, -1)
    k = max(3, int(w * 0.12) | 1)
    m = cv2.GaussianBlur(m, (k, k), 0)
    return m[..., None]


def fiks_munnfarge(bgr: np.ndarray) -> np.ndarray:
    """Wav2Lip gir ofte et fiolett skjær inne i munnen. Trekk mørke piksler mot naturlig mørkerødt."""
    b, g, r = bgr[..., 0], bgr[..., 1], bgr[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = (b - y) * 0.564 + 128
    cr = (r - y) * 0.713 + 128
    w = np.clip((110 - y) / 70, 0, 1) * 0.85
    cb = cb * (1 - w) + 118 * w
    cr = cr * (1 - w) + 142 * w
    return np.stack([y + 1.773 * (cb - 128),
                     y - 0.714 * (cr - 128) - 0.344 * (cb - 128),
                     y + 1.403 * (cr - 128)], axis=-1)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", required=True, help="basisklipp (mp4) eller bilde")
    p.add_argument("--lyd", required=True)
    p.add_argument("--ut", required=True)
    p.add_argument("--wav2lip", required=True, help="mappe med Wav2Lip-koden (github.com/Rudrabha/Wav2Lip)")
    p.add_argument("--vekter", help="wav2lip.pth (standard: <wav2lip>/checkpoints/wav2lip.pth)")
    p.add_argument("--ansiktsvekter", help="mappe med detection_Resnet50_Final.pth (facexlib)")
    p.add_argument("--utsnitt", type=int, nargs=4, metavar=("X", "Y", "B", "H"), help="beskjæring av basisklippet")
    p.add_argument("--storrelse", type=int, nargs=2, default=[540, 720], metavar=("B", "H"))
    p.add_argument("--boks", type=int, nargs=4, metavar=("TOPP", "BUNN", "V", "H"), help="ansiktsboks i arbeidsstørrelsen")
    p.add_argument("--fra", type=float, default=0.0)
    p.add_argument("--til", type=float, default=None)
    p.add_argument("--batch", type=int, default=64)
    p.add_argument("--detalj", type=float, default=0.6, help="hvor mye hudtekstur fra originalen som legges tilbake (0–1)")
    a = p.parse_args()

    torch.set_num_threads(max(1, torch.get_num_threads()))
    wl = Path(a.wav2lip)
    vekter = Path(a.vekter) if a.vekter else wl / "checkpoints" / "wav2lip.pth"
    b, h = a.storrelse

    rammer = les_bilder(Path(a.base), a.utsnitt, (b, h))
    # Fram og tilbake gir en sømløs løkke uten hopp
    if len(rammer) > 2:
        rammer = rammer + rammer[-2:0:-1]
    print(f"Basis: {len(rammer)} bilder i løkke ({len(rammer) / FPS:.1f} s), arbeidsstørrelse {b}x{h}")

    if a.boks:
        y1, y2, x1, x2 = a.boks
    else:
        y1, y2, x1, x2 = finn_ansikt(rammer[0], Path(a.ansiktsvekter))
    y2 = min(h, y2 + int(0.06 * (y2 - y1)))  # litt ekstra under haken (som Wav2Lips «pads»)
    bh, bw = y2 - y1, x2 - x1
    print(f"Ansiktsboks: topp {y1}, bunn {y2}, venstre {x1}, høyre {x2} ({bw}x{bh})")
    maske = blandemaske(bh, bw)

    varighet = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                     a.lyd], capture_output=True, text=True, check=True).stdout)
    til = min(a.til or varighet, varighet)
    n0, n1 = int(round(a.fra * FPS)), int(np.ceil(til * FPS))
    mel = mel_biter(Path(a.lyd), wl, n1)
    modell = last_modell(wl, vekter)

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{b}x{h}", "-r", str(FPS),
         "-i", "-", "-ss", f"{a.fra:.3f}", "-t", f"{(n1 - n0) / FPS:.3f}", "-i", a.lyd,
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-shortest", a.ut], stdin=subprocess.PIPE)

    t0 = time.time()
    for start in range(n0, n1, a.batch):
        idx = list(range(start, min(n1, start + a.batch)))
        basis = [rammer[i % len(rammer)] for i in idx]
        ansikter = np.stack([cv2.resize(f[y1:y2, x1:x2], (96, 96)) for f in basis]).astype(np.float32)
        maskert = ansikter.copy()
        maskert[:, 48:] = 0
        inn = np.concatenate([maskert, ansikter], axis=3) / 255.0
        mels = np.stack([mel[i] for i in idx])[..., None]
        with torch.no_grad():
            pred = modell(torch.from_numpy(mels).permute(0, 3, 1, 2).float(),
                          torch.from_numpy(inn).permute(0, 3, 1, 2).float())
        pred = (pred.permute(0, 2, 3, 1).numpy() * 255.0).clip(0, 255)
        for f, gen in zip(basis, pred):
            orig = f[y1:y2, x1:x2].astype(np.float32)
            gen = fiks_munnfarge(cv2.resize(gen.astype(np.float32), (bw, bh), interpolation=cv2.INTER_CUBIC))
            if a.detalj > 0:
                # Legg tilbake fin hudtekstur (høyfrekvent detalj) fra originalen
                detalj = orig - cv2.GaussianBlur(orig, (0, 0), 2.0)
                gen = gen + a.detalj * detalj
            ny = f.copy()
            ny[y1:y2, x1:x2] = np.clip(orig * (1 - maske) + gen * maske, 0, 255).astype(np.uint8)
            ff.stdin.write(ny.tobytes())
        ferdig = idx[-1] - n0 + 1
        if ferdig % (FPS * 60) < a.batch:
            print(f"  {idx[-1] / FPS:6.1f}s / {til:.1f}s  ({ferdig / (time.time() - t0):.1f} bilder/s)", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"Ferdig: {a.ut} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
