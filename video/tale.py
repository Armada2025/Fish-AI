"""Steg 1: Lag talesporet og tidslinjen fra manuset.

Hver replikk syntetiseres med valgt stemme – Googles nevrale norske stemmer (best) eller
Piper (lokal, mer robotaktig) – eller hentes fra en egen innspilling i
egen_stemme/<scene-id>_<nr>.wav hvis den finnes. Resultatet er
  bygg/tale.wav          – hele lydsporet
  bygg/tidslinje.json    – start/slutt for hver scene og replikk (sekunder)
  bygg/undertekster.srt  – undertekster
"""

import base64
import hashlib
import io
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
import wave
from pathlib import Path

import numpy as np

import manus

HER = Path(__file__).resolve().parent
RATE = 24000  # endelig samplingsrate for talesporet
GOOGLE_API = "https://texttospeech.googleapis.com/v1"

# Pauser i sekunder
PAUSE_START = 1.0          # før aller første replikk
PAUSE_SCENE_INN = 0.9      # fra scenen vises til første replikk
PAUSE_REPLIKK = 0.75       # mellom replikker i samme scene
PAUSE_SETNING = 0.32       # mellom setninger i samme replikk
PAUSE_SCENE_UT = 1.3       # etter siste replikk i en scene
PAUSE_SLUTT = 3.0          # etter siste replikk i videoen


def uttale(tekst: str, ordliste: dict) -> str:
    """Bytt ut ord som talesyntesen uttaler feil med lydrett skrivemåte."""
    tekst = tekst.replace(" …", ".").replace("…", ".")  # «…» ignoreres av talesyntesen – gi en pause i stedet
    for ord_, lyd in ordliste.items():
        tekst = re.sub(rf"(?<![\wæøåÆØÅ]){re.escape(ord_)}(?![a-zæøå])", lyd, tekst)
    return tekst


def resample(lyd: np.ndarray, fra: int, til: int) -> np.ndarray:
    if fra == til:
        return lyd
    n = int(round(len(lyd) * til / fra))
    return np.interp(np.linspace(0, len(lyd) - 1, n), np.arange(len(lyd)), lyd).astype(np.float32)


class PiperStemme:
    """Lokal talesyntese (Piper, no-talesyntese-medium). Gratis, men robotaktig."""

    navn = "piper"

    def __init__(self, modell: Path, tempo: float):
        from piper import PiperVoice
        self.v = PiperVoice.load(str(modell), config_path=str(modell) + ".json")
        self.tempo = tempo

    def lag(self, tekst: str) -> np.ndarray:
        from piper import SynthesisConfig
        cfg = SynthesisConfig(length_scale=self.tempo, normalize_audio=True)
        biter = []
        for chunk in self.v.synthesize(uttale(tekst, manus.UTTALE), cfg):
            if biter:
                biter.append(np.zeros(int(PAUSE_SETNING * chunk.sample_rate), dtype=np.float32))
            biter.append(chunk.audio_float_array.astype(np.float32))
            rate = chunk.sample_rate
        return resample(np.concatenate(biter), rate, RATE)


class GoogleStemme:
    """Googles nevrale norske stemmer (Cloud Text-to-Speech). Nøkkel i GOOGLE_TTS_API_KEY."""

    def __init__(self, navn: str | None, tempo: float, cache: Path):
        self.nokkel = os.environ.get("GOOGLE_TTS_API_KEY", "")
        self.tempo = tempo
        self.cache = cache
        cache.mkdir(parents=True, exist_ok=True)
        self.navn = navn or self.velg_stemme()
        print(f"Google-stemme: {self.navn} (tempo {tempo})")

    def _kall(self, sti: str, data: dict | None = None) -> dict:
        req = urllib.request.Request(f"{GOOGLE_API}/{sti}", method="POST" if data else "GET",
                                     data=json.dumps(data).encode() if data else None,
                                     headers={"Content-Type": "application/json"})
        if self.nokkel:
            req.add_header("X-Goog-Api-Key", self.nokkel)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Google Text-to-Speech svarte {e.code}: {e.read().decode()[:400]}\n"
                             "Sjekk at API-et er slått på og at nøkkelen ligger i GOOGLE_TTS_API_KEY.")

    def stemmer(self) -> list[dict]:
        return self._kall("voices?languageCode=nb-NO").get("voices", [])

    def velg_stemme(self) -> str:
        """Foretrekk de mest naturlige stemmetypene: Chirp 3 HD > Chirp HD > Neural2 > WaveNet."""
        rang = ["Chirp3-HD", "Chirp-HD", "Neural2", "Wavenet", "Standard"]
        alle = [v for v in self.stemmer() if any(l.startswith("nb") for l in v.get("languageCodes", []))]
        if not alle:
            raise SystemExit("Fant ingen norske stemmer hos Google Text-to-Speech.")
        def poeng(v):
            n = v["name"]
            typ = next((i for i, r in enumerate(rang) if r in n), len(rang))
            return (typ, v.get("ssmlGender") != "MALE", n)
        return sorted(alle, key=poeng)[0]["name"]

    def lag(self, tekst: str) -> np.ndarray:
        tekst = tekst.replace(" …", ",").replace("…", ",")
        nokkel = hashlib.sha1(f"{self.navn}|{self.tempo}|{tekst}".encode()).hexdigest()[:16]
        fil = self.cache / f"{nokkel}.wav"
        if not fil.exists():
            svar = self._kall("text:synthesize", {
                "input": {"text": tekst},
                "voice": {"languageCode": "nb-NO", "name": self.navn},
                "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": RATE, "speakingRate": self.tempo},
            })
            fil.write_bytes(base64.b64decode(svar["audioContent"]))
        with wave.open(str(fil)) as w:
            rate = w.getframerate()
            lyd = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        lyd = resample(lyd, rate, RATE)
        topp = float(np.abs(lyd).max()) or 1.0
        return lyd / topp * 0.95


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


def lag_tale(stemme, bygg: Path) -> dict:
    """stemme: et objekt med .lag(tekst) -> mono float32 i RATE Hz (PiperStemme eller GoogleStemme)."""
    bygg.mkdir(parents=True, exist_ok=True)
    egen = HER / "egen_stemme"

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
                lyd, kilde = stemme.lag(tekst), stemme.navn
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
