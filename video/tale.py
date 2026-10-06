"""Steg 1: Lag talesporet og tidslinjen fra manuset.

Hver replikk syntetiseres med Piper (norsk stemme), eller hentes fra en egen
innspilling i egen_stemme/<scene-id>_<nr>.wav hvis den finnes. Resultatet er
  bygg/tale.wav          – hele lydsporet
  bygg/tidslinje.json    – start/slutt for hver scene og replikk (sekunder)
  bygg/undertekster.srt  – undertekster
"""

import json
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

import manus

HER = Path(__file__).resolve().parent
RATE = 22050

# Pauser i sekunder
PAUSE_START = 1.0          # før aller første replikk
PAUSE_SCENE_INN = 0.9      # fra scenen vises til første replikk
PAUSE_REPLIKK = 0.75       # mellom replikker i samme scene
PAUSE_SETNING = 0.32       # mellom setninger i samme replikk
PAUSE_SCENE_UT = 1.3       # etter siste replikk i en scene
PAUSE_SLUTT = 3.0          # etter siste replikk i videoen


def uttale(tekst: str) -> str:
    """Bytt ut ord som talesyntesen uttaler feil med lydrett skrivemåte."""
    for ord_, lyd in manus.UTTALE.items():
        tekst = re.sub(rf"(?<![\wæøåÆØÅ]){re.escape(ord_)}(?![a-zæøå])", lyd, tekst)
    return tekst


def last_stemme(modell: Path):
    from piper import PiperVoice
    return PiperVoice.load(str(modell), config_path=str(modell) + ".json")


def syntetiser(stemme, tekst: str, tempo: float) -> np.ndarray:
    from piper import SynthesisConfig
    cfg = SynthesisConfig(length_scale=tempo, normalize_audio=True)
    biter = []
    stillhet = np.zeros(int(PAUSE_SETNING * RATE), dtype=np.float32)
    for chunk in stemme.synthesize(uttale(tekst), cfg):
        if biter:
            biter.append(stillhet)
        biter.append(chunk.audio_float_array.astype(np.float32))
    return np.concatenate(biter)


def les_wav(sti: Path) -> np.ndarray:
    """Les en vilkårlig lydfil som mono float32 i RATE Hz (via ffmpeg)."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(sti), "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def skriv_wav(sti: Path, lyd: np.ndarray) -> None:
    pcm = (np.clip(lyd, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(sti), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def srt_tid(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def lag_tale(modell: Path, bygg: Path, tempo: float = 1.05) -> dict:
    bygg.mkdir(parents=True, exist_ok=True)
    egen = HER / "egen_stemme"
    stemme = None

    spor: list[np.ndarray] = []
    t = 0.0

    def legg_til(lyd: np.ndarray) -> None:
        nonlocal t
        spor.append(lyd)
        t += len(lyd) / RATE

    def stille(sek: float) -> None:
        legg_til(np.zeros(int(round(sek * RATE)), dtype=np.float32))

    tidslinje = {"scener": []}
    stille(PAUSE_START - PAUSE_SCENE_INN)
    for s_nr, scene in enumerate(manus.SCENER):
        s = {"id": scene["id"], "start": t, "replikker": []}
        stille(PAUSE_SCENE_INN)
        for r_nr, tekst in enumerate(manus.replikker(scene)[0]):
            if r_nr:
                stille(PAUSE_REPLIKK)
            fil = egen / f"{scene['id']}_{r_nr + 1}.wav"
            if fil.exists():
                lyd, kilde = les_wav(fil), "egen"
            else:
                if stemme is None:
                    stemme = last_stemme(modell)
                lyd, kilde = syntetiser(stemme, tekst, tempo), "tts"
            start = t
            legg_til(lyd * 0.9)
            s["replikker"].append({"tekst": tekst, "start": start, "slutt": t, "kilde": kilde})
            print(f"  {scene['id']:>10} {r_nr + 1}: {start:6.2f}–{t:6.2f}s ({kilde})")
        stille(PAUSE_SLUTT if s_nr == len(manus.SCENER) - 1 else PAUSE_SCENE_UT)
        s["slutt"] = t
        tidslinje["scener"].append(s)
    tidslinje["varighet"] = t

    lyd = np.concatenate(spor)
    skriv_wav(bygg / "tale.wav", lyd)
    (bygg / "tidslinje.json").write_text(json.dumps(tidslinje, ensure_ascii=False, indent=2))

    linjer = []
    nr = 1
    for s in tidslinje["scener"]:
        for r in s["replikker"]:
            linjer += [str(nr), f"{srt_tid(r['start'])} --> {srt_tid(r['slutt'])}", r["tekst"], ""]
            nr += 1
    (bygg / "undertekster.srt").write_text("\n".join(linjer), encoding="utf-8")
    print(f"Tale: {t:.1f} s -> {bygg / 'tale.wav'}")
    return tidslinje
