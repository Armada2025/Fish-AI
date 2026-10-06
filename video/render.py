"""Steg 3: Sett sammen den ferdige videoen.

Hvert bilde (frame) bygges med Pillow: bakgrunn -> lysbildeinnhold -> presentatørkort
(snakkende ansikt) -> undertekst -> framdriftslinje. Bildene sendes rett inn i ffmpeg
sammen med talesporet.
"""

import math
import multiprocessing
import os
import subprocess
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import manus

B, H = 1920, 1080
FPS = 25

# Farger
BG_TOPP = (9, 16, 32)
BG_BUNN = (14, 33, 56)
TEKST = (243, 246, 251)
DEMPET = (169, 182, 201)
SVAK = (120, 136, 160)
TEAL = (45, 212, 191)
FIOLETT = (139, 123, 255)
HIMMEL = (56, 189, 248)
RAV = (251, 191, 36)
GRONN = (74, 222, 128)
ORANSJE = (251, 146, 60)
BLA = (96, 165, 250)

# Oppsett
X0, X1 = 90, 1230                # innholdsområde (venstre)
Y_TITTEL = 128
Y0, Y1 = 262, 880
KORT = (1290, 110, 540, 720)     # presentatørkort x, y, b, h (3:4)

FONTMAPPE = Path("/usr/share/fonts/opentype/inter")
_fonter: dict = {}


def font(vekt: str, str_: int, display: bool = False) -> ImageFont.FreeTypeFont:
    navn = f"{'InterDisplay' if display else 'Inter'}-{vekt}.otf"
    nokkel = (navn, str_)
    if nokkel not in _fonter:
        _fonter[nokkel] = ImageFont.truetype(str(FONTMAPPE / navn), str_)
    return _fonter[nokkel]


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def rgba(farge, a: float = 1.0):
    return (*farge[:3], int(round(255 * a)))


# ---------------------------------------------------------------- tegnehjelp

def avrundet(b: int, h: int, r: int, fyll, kant=None, kantbredde: int = 2, ss: int = 3) -> Image.Image:
    """Avrundet rektangel med kantutjevning (tegnes i ss x størrelse og skaleres ned)."""
    im = Image.new("RGBA", (b * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, b * ss - 1, h * ss - 1), r * ss, fill=fyll,
                        outline=kant, width=kantbredde * ss if kant else 0)
    return im.resize((b, h), Image.LANCZOS)


def maske(b: int, h: int, tegn: Callable, ss: int = 4) -> Image.Image:
    im = Image.new("L", (b * ss, h * ss), 0)
    tegn(ImageDraw.Draw(im), ss)
    return im.resize((b, h), Image.LANCZOS)


def farget(m: Image.Image, farge) -> Image.Image:
    im = Image.new("RGBA", m.size, rgba(farge))
    im.putalpha(m)
    return im


def gradient(b: int, h: int, fra, til, retning: str = "x") -> Image.Image:
    t = np.linspace(0, 1, b if retning == "x" else h, dtype=np.float32)
    f, ti = np.array(fra, np.float32), np.array(til, np.float32)
    linje = (f[None, :] * (1 - t[:, None]) + ti[None, :] * t[:, None]).astype(np.uint8)
    if retning == "x":
        arr = np.broadcast_to(linje[None, :, :], (h, b, 3))
    else:
        arr = np.broadcast_to(linje[:, None, :], (h, b, 3))
    return Image.fromarray(np.ascontiguousarray(arr), "RGB")


def tekstbilde(tekst: str, f: ImageFont.FreeTypeFont, farge, a: float = 1.0) -> Image.Image:
    v, o, h_, u = f.getbbox(tekst)
    im = Image.new("RGBA", (h_ + 4, u + 6), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2, 0), tekst, font=f, fill=rgba(farge, a))
    return im


def bryt(tekst: str, f: ImageFont.FreeTypeFont, maks: int) -> list[str]:
    linjer, linje = [], ""
    for ord_ in tekst.split():
        prov = f"{linje} {ord_}".strip()
        if f.getlength(prov) <= maks or not linje:
            linje = prov
        else:
            linjer.append(linje)
            linje = ord_
    if linje:
        linjer.append(linje)
    return linjer


def tekstblokk(tekst: str, f, farge, maks: int, linjeh: int) -> Image.Image:
    linjer = bryt(tekst, f, maks)
    b = int(max(f.getlength(l) for l in linjer)) + 4
    im = Image.new("RGBA", (b, linjeh * len(linjer) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(linjer):
        d.text((2, i * linjeh), l, font=f, fill=rgba(farge))
    return im


# ---------------------------------------------------------------- ikoner

def ikon(navn: str, s: int, farge=TEKST) -> Image.Image:
    """Enkle, egne strek-ikoner (ingen varemerker)."""
    def t(d: ImageDraw.ImageDraw, k: int):
        S = s * k
        w = max(2, int(S * 0.085))
        p = lambda *xy: [v * S for v in xy]
        if navn == "dokument":
            d.rounded_rectangle(p(0.2, 0.08, 0.8, 0.92), int(S * 0.06), outline=255, width=w)
            for y in (0.32, 0.47, 0.62, 0.77):
                d.line(p(0.32, y, 0.68 if y < 0.7 else 0.55, y), fill=255, width=w)
        elif navn == "epost":
            d.rounded_rectangle(p(0.08, 0.2, 0.92, 0.8), int(S * 0.07), outline=255, width=w)
            d.line(p(0.12, 0.26, 0.5, 0.55, 0.88, 0.26), fill=255, width=w, joint="curve")
        elif navn == "mote":
            for cx, cy, r in ((0.36, 0.34, 0.13), (0.66, 0.38, 0.11)):
                d.ellipse(p(cx - r, cy - r, cx + r, cy + r), outline=255, width=w)
            d.arc(p(0.1, 0.55, 0.62, 1.05), 180, 360, fill=255, width=w)
            d.arc(p(0.46, 0.58, 0.9, 1.0), 200, 340, fill=255, width=w)
        elif navn == "tabell":
            d.rounded_rectangle(p(0.1, 0.14, 0.9, 0.86), int(S * 0.06), outline=255, width=w)
            for x in (0.37, 0.63):
                d.line(p(x, 0.14, x, 0.86), fill=255, width=w)
            for y in (0.38, 0.62):
                d.line(p(0.1, y, 0.9, y), fill=255, width=w)
        elif navn == "lysbilde":
            d.rounded_rectangle(p(0.08, 0.14, 0.92, 0.7), int(S * 0.05), outline=255, width=w)
            d.line(p(0.5, 0.7, 0.5, 0.86), fill=255, width=w)
            d.line(p(0.32, 0.88, 0.68, 0.88), fill=255, width=w)
            for x, y in ((0.3, 0.52), (0.45, 0.4), (0.6, 0.3)):
                d.line(p(x, 0.58, x, y), fill=255, width=int(w * 1.4))
        elif navn == "sjekk":
            d.line(p(0.18, 0.52, 0.42, 0.75, 0.84, 0.28), fill=255, width=int(w * 1.3), joint="curve")
        elif navn == "stjerne":
            def stj(cx, cy, r):
                q = r * 0.22
                pts = [(cx, cy - r), (cx + q, cy - q), (cx + r, cy), (cx + q, cy + q),
                       (cx, cy + r), (cx - q, cy + q), (cx - r, cy), (cx - q, cy - q)]
                d.polygon([(x * S, y * S) for x, y in pts], fill=255)
            stj(0.42, 0.55, 0.36)
            stj(0.8, 0.2, 0.15)
        elif navn == "boble":
            d.rounded_rectangle(p(0.08, 0.14, 0.92, 0.7), int(S * 0.16), outline=255, width=w)
            d.polygon([(v * S) for v in (0.28, 0.66, 0.28, 0.88, 0.48, 0.68)], fill=255)
            for x in (0.32, 0.5, 0.68):
                d.ellipse(p(x - 0.05, 0.37, x + 0.05, 0.47), fill=255)
        elif navn == "apper":
            for x, y in ((0.12, 0.12), (0.54, 0.12), (0.12, 0.54), (0.54, 0.54)):
                d.rounded_rectangle(p(x, y, x + 0.34, y + 0.34), int(S * 0.07), outline=255, width=w)
        elif navn == "kompass":
            d.ellipse(p(0.08, 0.08, 0.92, 0.92), outline=255, width=w)
            d.polygon([(v * S) for v in (0.5, 0.2, 0.6, 0.5, 0.5, 0.8, 0.4, 0.5)], fill=255)
        elif navn == "las":
            d.rounded_rectangle(p(0.18, 0.44, 0.82, 0.9), int(S * 0.08), outline=255, width=w)
            d.arc(p(0.3, 0.1, 0.7, 0.6), 180, 360, fill=255, width=w)
            d.line(p(0.3, 0.35, 0.3, 0.45), fill=255, width=w)
            d.line(p(0.7, 0.35, 0.7, 0.45), fill=255, width=w)
            d.ellipse(p(0.45, 0.59, 0.55, 0.69), fill=255)
        elif navn == "person":
            d.ellipse(p(0.32, 0.1, 0.68, 0.46), outline=255, width=w)
            d.arc(p(0.14, 0.56, 0.86, 1.2), 180, 360, fill=255, width=w)
        elif navn == "skjold":
            d.polygon([(v * S) for v in (0.5, 0.08, 0.86, 0.22, 0.8, 0.6, 0.5, 0.92, 0.2, 0.6, 0.14, 0.22)],
                      outline=255, width=w)
            d.line(p(0.34, 0.5, 0.46, 0.62, 0.68, 0.38), fill=255, width=w, joint="curve")
        elif navn == "klokke":
            d.ellipse(p(0.08, 0.08, 0.92, 0.92), outline=255, width=w)
            d.line(p(0.5, 0.24, 0.5, 0.5, 0.68, 0.62), fill=255, width=w, joint="curve")
        elif navn == "pil":
            d.line(p(0.1, 0.5, 0.85, 0.5), fill=255, width=int(w * 1.2))
            d.line(p(0.6, 0.25, 0.88, 0.5, 0.6, 0.75), fill=255, width=int(w * 1.2), joint="curve")
        elif navn == "varsel":
            d.polygon([(v * S) for v in (0.5, 0.1, 0.92, 0.86, 0.08, 0.86)], outline=255, width=w)
            d.line(p(0.5, 0.38, 0.5, 0.62), fill=255, width=w)
            d.ellipse(p(0.46, 0.7, 0.54, 0.78), fill=255)
        else:
            raise ValueError(navn)
    return farget(maske(s, s, t), farge)


def ikonbrikke(navn: str, s: int, farge, bakgrunn_a: float = 0.16, rund: bool = True) -> Image.Image:
    """Ikon i en farget sirkel/firkant."""
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    if rund:
        bg = farget(maske(s, s, lambda d, k: d.ellipse((0, 0, s * k - 1, s * k - 1), fill=255)), farge)
    else:
        bg = avrundet(s, s, int(s * 0.26), rgba(farge))
    a = bg.getchannel("A").point(lambda v: int(v * bakgrunn_a))
    bg.putalpha(a)
    im.alpha_composite(bg)
    ik = ikon(navn, int(s * 0.56), farge if bakgrunn_a < 0.5 else TEKST)
    im.alpha_composite(ik, ((s - ik.width) // 2, (s - ik.height) // 2))
    return im


# ---------------------------------------------------------------- elementer

@dataclass
class El:
    bilde: Optional[Image.Image]
    x: int
    y: int
    inn: float
    ut: Optional[float] = None
    flytt: tuple = (0, 24)            # forskyvning ved inngang
    varighet: float = 0.45
    velg: Optional[Callable[[float], Optional[Image.Image]]] = None  # dynamisk bilde

    def alfa(self, t: float) -> float:
        a = ease((t - self.inn) / self.varighet)
        if self.ut is not None:
            a *= 1 - ease((t - self.ut) / 0.35)
        return a


def med_alfa(im: Image.Image, a: float) -> Image.Image:
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im


def overskrift(scene: dict, nr: int, antall: int, start: float) -> list[El]:
    els = []
    oy = tekstbilde(f"{nr:02d} / {antall:02d}", font("SemiBold", 22), TEAL)
    els.append(El(oy, X0, Y_TITTEL - 40, start + 0.05))
    merke = tekstbilde("KI I COPILOT", font("SemiBold", 22), SVAK)
    els.append(El(merke, X0 + oy.width + 18, Y_TITTEL - 40, start + 0.05))
    tittel = tekstbilde(scene["tittel"], font("Bold", 62, True), TEKST)
    els.append(El(tittel, X0 - 3, Y_TITTEL - 4, start + 0.12))
    strek = gradient(120, 6, TEAL, FIOLETT).convert("RGBA")
    strek.putalpha(maske(120, 6, lambda d, k: d.rounded_rectangle((0, 0, 120 * k - 1, 6 * k - 1), 3 * k, fill=255)))
    els.append(El(strek, X0, Y_TITTEL + 88, start + 0.25, flytt=(-30, 0)))
    return els


# ---------------------------------------------------------------- tidshjelp

def tider(scene: dict, tid: dict):
    """Starttid for hver del, og starttid for outro (eller None)."""
    _, starter, outro = manus.replikker(scene)
    r = tid["replikker"]
    del_t = [r[i]["start"] for i in starter]
    outro_t = r[outro]["start"] if scene.get("outro") else None
    return del_t, outro_t


def aktiv_indeks(t: float, starter: list[float], outro_t: Optional[float] = None) -> int:
    if outro_t is not None and t >= outro_t - 0.05:
        return -1
    i = -1
    for j, s in enumerate(starter):
        if t >= s - 0.05:
            i = j
    return i


PALETT = [TEAL, FIOLETT, HIMMEL, RAV, GRONN]
FARGENAVN = {"teal": TEAL, "fiolett": FIOLETT, "rod": (248, 113, 113), "gronn": GRONN, "rav": RAV}
APPFARGER = {"dokument": BLA, "epost": HIMMEL, "mote": FIOLETT, "tabell": GRONN, "lysbilde": ORANSJE}


def merknadskort(tekst: str, farge, ikonnavn: str = "stjerne", maks: int = X1 - X0) -> Image.Image:
    f = font("SemiBold", 30)
    linjer = bryt(tekst, f, maks - 130)
    b = min(maks, int(max(f.getlength(l) for l in linjer)) + 130)
    h = 44 * len(linjer) + 40
    im = avrundet(b, h, min(42, h // 2), rgba(farge, 0.12), rgba(farge, 0.6), 2)
    im.alpha_composite(ikon(ikonnavn, 40, farge), (32, (h - 40) // 2))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(linjer):
        d.text((92, 18 + i * 44), l, font=f, fill=rgba(farge))
    return im


def to_tilstander(lag: Callable[[bool], Image.Image]) -> dict:
    return {True: lag(True), False: lag(False)}


# ---------------------------------------------------------------- scenetyper

def sc_tittel(scene, tid, nr, antall) -> list[El]:
    s = tid["start"]
    els = []
    pille = avrundet(250, 48, 24, rgba(TEAL, 0.14), rgba(TEAL, 0.55), 2)
    tp = tekstbilde("PRESENTASJON", font("SemiBold", 21), TEAL)
    pille.alpha_composite(tp, ((250 - tp.width) // 2, 12))
    els.append(El(pille, X0, 330, s + 0.25))

    f = font("Bold", 150, True)
    m = Image.new("L", (1150, 190), 0)
    ImageDraw.Draw(m).text((0, 0), scene["tittel"], font=f, fill=255)
    tittel = gradient(1150, 190, (255, 255, 255), (150, 200, 255)).convert("RGBA")
    tittel.putalpha(m)
    els.append(El(tittel, X0 - 6, 400, s + 0.45, flytt=(0, 40), varighet=0.7))
    stj = ikon("stjerne", 110, TEAL)
    els.append(El(stj, X0 + int(f.getlength(scene["tittel"])) + 30, 400, s + 0.9, flytt=(0, 0), varighet=0.6))

    ut = tekstblokk(scene["undertittel"], font("Regular", 44), DEMPET, 1100, 58)
    els.append(El(ut, X0, 610, s + 0.8))
    strek = gradient(220, 6, TEAL, FIOLETT).convert("RGBA")
    els.append(El(strek, X0, 700, s + 1.0, flytt=(-40, 0)))
    return els


def sc_agenda(scene, tid, nr, antall) -> list[El]:
    els = overskrift(scene, nr, antall, tid["start"])
    r = tid["replikker"]
    a, b = r[0]["start"], r[-1]["slutt"]
    n = len(scene["punkter"])
    # Punktene rulles ut i takt med opplesningen (jevnt fordelt over replikkene)
    starter = [a - 0.1 + i * (b - a) * 0.84 / n for i in range(n)]
    for i, tekst in enumerate(scene["punkter"]):
        farge = PALETT[i % len(PALETT)]
        im = Image.new("RGBA", (X1 - X0, 92), (0, 0, 0, 0))
        sirkel = farget(maske(68, 68, lambda d, k: d.ellipse((0, 0, 68 * k - 1, 68 * k - 1), fill=255)), farge)
        sirkel.putalpha(sirkel.getchannel("A").point(lambda v: int(v * 0.18)))
        im.alpha_composite(sirkel, (0, 10))
        nt = tekstbilde(str(i + 1), font("Bold", 32), farge)
        im.alpha_composite(nt, ((68 - nt.width) // 2, 10 + (68 - nt.height) // 2 + 2))
        tb = tekstbilde(tekst, font("SemiBold", 38), TEKST)
        im.alpha_composite(tb, (98, 22))
        if i < n - 1:
            ImageDraw.Draw(im).line((98, 90, X1 - X0 - 40, 90), fill=rgba(TEKST, 0.08), width=2)
        els.append(El(im, X0, Y0 - 8 + i * 100, starter[i], flytt=(-36, 0)))
    return els


def sc_punkter(scene, tid, nr, antall) -> list[El]:
    els = overskrift(scene, nr, antall, tid["start"])
    del_t, outro_t = tider(scene, tid)
    deler = scene["deler"]
    radh, mellom = 100, 22
    avslutt = scene.get("avslutning")
    ut_tid = outro_t - 0.1 if avslutt and outro_t else None

    for i, d_ in enumerate(deler):
        farge = PALETT[i % len(PALETT)]

        def lag(aktiv, d_=d_, farge=farge):
            im = avrundet(X1 - X0, radh, 22, rgba(TEKST, 0.075 if aktiv else 0.035),
                          rgba(farge, 0.55) if aktiv else rgba(TEKST, 0.06), 2)
            if aktiv:
                im.alpha_composite(avrundet(6, radh - 36, 3, rgba(farge)), (0, 18))
            im.alpha_composite(ikonbrikke(d_["ikon"], 64, farge, 0.18 if aktiv else 0.1), (26, (radh - 64) // 2))
            tb = tekstbilde(d_["punkt"], font("SemiBold", 38), TEKST if aktiv else (200, 210, 224))
            im.alpha_composite(tb, (118, (radh - tb.height) // 2 + 2))
            return im
        bilder = to_tilstander(lag)
        utfor = outro_t if not avslutt else None

        def velg(t, i=i, bilder=bilder, utfor=utfor):
            return bilder[aktiv_indeks(t, del_t, utfor) == i]
        els.append(El(None, X0, Y0 + i * (radh + mellom), del_t[i] - 0.1, ut=ut_tid, flytt=(-36, 0), velg=velg))

    if scene.get("merknad") and outro_t:
        im = merknadskort(scene["merknad"], TEAL, "stjerne")
        els.append(El(im, X0, Y0 + len(deler) * (radh + mellom) + 14, outro_t - 0.05, flytt=(0, 20)))

    if avslutt and ut_tid:
        f = font("Bold", 120, True)
        m = Image.new("L", (1150, 160), 0)
        ImageDraw.Draw(m).text((0, 0), avslutt, font=f, fill=255)
        im = gradient(1150, 160, (255, 255, 255), (150, 200, 255)).convert("RGBA")
        im.putalpha(m)
        els.append(El(im, X0, Y0 + 120, ut_tid + 0.35, flytt=(0, 40), varighet=0.7))
        stj = ikon("stjerne", 90, TEAL)
        els.append(El(stj, X0 + int(f.getlength(avslutt)) + 30, Y0 + 120, ut_tid + 0.8, flytt=(0, 0), varighet=0.6))
    return els


def sc_neste_ord(scene, tid, nr, antall) -> list[El]:
    els = overskrift(scene, nr, antall, tid["start"])
    r = [x["start"] for x in tid["replikker"]]

    # 1) Kjede: tekst -> språkmodell -> svar
    f = font("SemiBold", 28)
    noder = []
    for i, (ik, tekst) in enumerate(scene["kjede"]):
        b = int(f.getlength(tekst)) + 110
        im = avrundet(b, 80, 40, rgba(TEKST, 0.06), rgba(PALETT[i], 0.5), 2)
        im.alpha_composite(ikonbrikke(ik, 52, PALETT[i], 0.2), (14, 14))
        im.alpha_composite(tekstbilde(tekst, f, TEKST), (80, 22))
        noder.append(im)
    tot = sum(n.width for n in noder)
    gap = (X1 - X0 - tot) // (len(noder) - 1)
    x = X0
    for i, im in enumerate(noder):
        els.append(El(im, x, Y0, r[0] + 0.3 + i * 0.9, flytt=(0, 16)))
        if i < len(noder) - 1:
            els.append(El(ikon("pil", 40, DEMPET), x + im.width + (gap - 40) // 2, Y0 + 20, r[0] + 0.7 + i * 0.9,
                          flytt=(-16, 0)))
        x += im.width + gap

    # 2) Setning med tomrom som fylles
    fs = font("Medium", 40, True)
    setning = scene["setning"]
    sw = int(fs.getlength(setning))
    kort_b, kort_h = X1 - X0, 104
    valgt = scene["kandidater"][0][0]
    cache: dict = {}

    def setningskort(t):
        fylt = t >= r[3] - 0.05
        markor = (not fylt) and int(t * 2.5) % 2 == 0
        n = (fylt, markor)
        if n not in cache:
            im = avrundet(kort_b, kort_h, 24, rgba(TEKST, 0.07), rgba(TEKST, 0.12), 2)
            d = ImageDraw.Draw(im)
            d.text((34, 28), setning, font=fs, fill=rgba(TEKST))
            bx = 34 + sw + 18
            if fylt:
                d.text((bx, 28), valgt, font=font("Bold", 40, True), fill=rgba(TEAL))
                d.line((bx, 82, bx + font("Bold", 40, True).getlength(valgt), 82), fill=rgba(TEAL), width=4)
            else:
                d.line((bx, 82, bx + 150, 82), fill=rgba(DEMPET, 0.8), width=4)
                if markor:
                    d.rectangle((bx + 4, 30, bx + 8, 76), fill=rgba(TEKST))
            cache[n] = im
        return cache[n]
    sy = Y0 + 122
    els.append(El(None, X0, sy, r[1] + 0.2, velg=setningskort))

    # 3) Sannsynlighetsstolper
    by = sy + kort_h + 34
    maksp = max(p for _, p in scene["kandidater"])
    full = 700
    for i, (ord_, p) in enumerate(scene["kandidater"]):
        t_i = r[2] + 1.6 + i * 0.45
        bcache: dict = {}

        def stolpe(t, i=i, ord_=ord_, p=p, t_i=t_i, bcache=bcache):
            g = ease((t - t_i) / 0.8)
            vinner = t >= r[3] - 0.05
            farge = TEAL if (i == 0 and vinner) else (HIMMEL if not vinner else SVAK)
            n = (int(g * 40), vinner)
            if n not in bcache:
                im = Image.new("RGBA", (X1 - X0, 56), (0, 0, 0, 0))
                d = ImageDraw.Draw(im)
                d.text((0, 8), ord_, font=font("SemiBold", 32), fill=rgba(TEKST if (i == 0 or not vinner) else DEMPET))
                d.rounded_rectangle((160, 12, 160 + full, 44), 16, fill=rgba(TEKST, 0.06))
                w = int(full * p / maksp * n[0] / 40)
                if w > 8:
                    d.rounded_rectangle((160, 12, 160 + w, 44), 16, fill=rgba(farge, 0.95))
                d.text((160 + full + 24, 10), f"{int(round(p * n[0] / 40))} %", font=font("SemiBold", 30),
                       fill=rgba(farge if n[0] else DEMPET))
                bcache[n] = im
            return bcache[n]
        els.append(El(None, X0, by + i * 64, t_i - 0.2, flytt=(-24, 0), velg=stolpe))

    # 4) Advarsel
    im = merknadskort(scene["advarsel"], RAV, "varsel")
    els.append(El(im, X0, by + len(scene["kandidater"]) * 64 + 18, r[4] + 0.2, flytt=(0, 20)))
    return els


def sc_kolonner(scene, tid, nr, antall) -> list[El]:
    els = overskrift(scene, nr, antall, tid["start"])
    del_t, outro_t = tider(scene, tid)
    kb = (X1 - X0 - 30) // 2
    kh = (Y1 - 112 if scene.get("merknad") else Y1) - Y0
    for i, d_ in enumerate(scene["deler"]):
        farge = FARGENAVN[d_["farge"]]
        x = X0 + i * (kb + 30)
        t0 = del_t[i]

        def lag(aktiv, farge=farge):
            return avrundet(kb, kh, 26, rgba(TEKST, 0.075 if aktiv else 0.04),
                            rgba(farge, 0.65) if aktiv else rgba(TEKST, 0.08), 2)
        bilder = to_tilstander(lag)

        def velg(t, i=i, bilder=bilder):
            return bilder[aktiv_indeks(t, del_t, outro_t) == i]
        els.append(El(None, x, Y0, t0 - 0.1, velg=velg))

        hode = Image.new("RGBA", (kb - 40, 76), (0, 0, 0, 0))
        hode.alpha_composite(ikonbrikke(d_["ikon"], 60, farge, 0.2), (0, 4))
        if d_.get("undernavn"):
            hode.alpha_composite(tekstbilde(d_["navn"], font("Bold", 34), farge), (78, -2))
            hode.alpha_composite(tekstbilde(d_["undernavn"], font("Regular", 22), DEMPET), (79, 44))
        else:
            hode.alpha_composite(tekstbilde(d_["navn"], font("Bold", 34), farge), (78, 12))
        els.append(El(hode, x + 26, Y0 + 24, t0 + 0.05))
        y = Y0 + 112
        if d_.get("sitat"):
            fq = font("MediumItalic", 28)
            linjer = bryt(d_["sitat"], fq, kb - 92)
            qh = len(linjer) * 39 + 36
            q = avrundet(kb - 52, qh, 18, rgba((0, 0, 0), 0.22), rgba(farge, 0.35), 2)
            q.alpha_composite(avrundet(5, qh - 28, 2, rgba(farge)), (0, 14))
            dq = ImageDraw.Draw(q)
            for j, l in enumerate(linjer):
                dq.text((24, 16 + j * 39), l, font=fq, fill=rgba(TEKST))
            els.append(El(q, x + 26, y, t0 + 0.5))
            y += qh + 26
        for j, p in enumerate(d_.get("punkter", [])):
            fp = font("Regular", 28)
            linjer = bryt(p, fp, kb - 110)
            im = Image.new("RGBA", (kb - 52, 40 * len(linjer) + 8), (0, 0, 0, 0))
            dd = ImageDraw.Draw(im)
            dd.ellipse((4, 13, 18, 27), fill=rgba(farge))
            for k_, l in enumerate(linjer):
                dd.text((36, k_ * 40), l, font=fp, fill=rgba(TEKST))
            els.append(El(im, x + 26, y, t0 + 0.9 + j * 0.8, flytt=(-20, 0)))
            y += im.height + 18
        if d_.get("etiketter"):
            r_ = tid["replikker"][manus.replikker(scene)[1][i]]
            ex = x + 26
            for j, e in enumerate(d_["etiketter"]):
                fe = font("SemiBold", 24)
                ef = HL_FARGER.get(e, farge)
                im = avrundet(int(fe.getlength(e)) + 40, 42, 21, rgba(ef, 0.16), rgba(ef, 0.7), 2)
                im.alpha_composite(tekstbilde(e, fe, ef), (20, 7))
                if ex + im.width > x + kb - 20:
                    ex, y = x + 26, y + 54
                tj = r_["start"] + (0.18 + 0.2 * j) * (r_["slutt"] - r_["start"])
                els.append(El(im, ex, y, tj, flytt=(0, -12), varighet=0.3))
                ex += im.width + 12
    if scene.get("merknad") and outro_t:
        els.append(El(merknadskort(scene["merknad"], RAV, "varsel"), X0, Y1 - 88, outro_t - 0.05, flytt=(0, 20)))
    return els


def sc_flyt(scene, tid, nr, antall) -> list[El]:
    """Loddrett tidslinje: fire steg som tennes etter tur."""
    els = overskrift(scene, nr, antall, tid["start"])
    del_t, _ = tider(scene, tid)
    radh, mellom = 104, 22
    for i, d_ in enumerate(scene["deler"]):
        tittel, under = d_["boks"]
        farge = [TEAL, FIOLETT, HIMMEL, GRONN][i % 4]
        y = Y0 + i * (radh + mellom)

        def lag(aktiv, d_=d_, farge=farge, i=i, tittel=tittel, under=under):
            im = avrundet(X1 - X0, radh, 22, rgba(TEKST, 0.08 if aktiv else 0.035),
                          rgba(farge, 0.7) if aktiv else rgba(TEKST, 0.07), 2)
            im.alpha_composite(ikonbrikke(d_["ikon"], 68, farge, 0.22 if aktiv else 0.12), (22, (radh - 68) // 2))
            nt = tekstbilde(f"{i + 1}", font("Bold", 26), farge)
            im.alpha_composite(nt, (112, 14))
            im.alpha_composite(tekstbilde(tittel, font("Bold", 34), TEKST if aktiv else (200, 210, 224)), (146, 12))
            im.alpha_composite(tekstbilde(under, font("Regular", 27), DEMPET), (146, 56))
            return im
        bilder = to_tilstander(lag)

        def velg(t, i=i, bilder=bilder):
            return bilder[aktiv_indeks(t, del_t) == i]
        els.append(El(None, X0, y, del_t[i] - 0.1, flytt=(-36, 0), velg=velg))
        if i:
            # liten pil mellom stegene
            pil = ikon("pil", 26, DEMPET).rotate(-90, expand=True)
            els.append(El(pil, X0 + 22 + 34 - 13, y - mellom + 2 - 6, del_t[i] - 0.1, flytt=(0, -10)))
    ay = Y0 + len(scene["deler"]) * (radh + mellom) + 8
    els.append(El(merknadskort(scene["advarsel"], RAV, "varsel"), X0, ay, del_t[-1] + 2.2, flytt=(0, 20)))
    return els


def sc_app(scene, tid, nr, antall) -> list[El]:
    els = overskrift(scene, nr, antall, tid["start"])
    del_t, outro_t = tider(scene, tid)
    farge = APPFARGER[scene["app"]]
    tw = int(font("Bold", 62, True).getlength(scene["tittel"]))
    els.append(El(ikonbrikke(scene["app"], 76, farge, 0.95, rund=False), X0 + tw + 30, Y_TITTEL + 2,
                  tid["start"] + 0.35, flytt=(0, 0), varighet=0.5))
    els.append(El(tekstbilde(scene["ingress"], font("Regular", 34), DEMPET), X0, Y0 - 4, tid["start"] + 0.5))

    radh, mellom = 86, 14
    ry = Y0 + 66
    for i, d_ in enumerate(scene["deler"]):
        def lag(aktiv, d_=d_):
            im = avrundet(X1 - X0, radh, 20, rgba(TEKST, 0.075 if aktiv else 0.035),
                          rgba(farge, 0.6) if aktiv else rgba(TEKST, 0.06), 2)
            im.alpha_composite(ikonbrikke("sjekk", 50, farge, 0.22 if aktiv else 0.12), (22, 18))
            tb = tekstbilde(d_["punkt"], font("SemiBold", 34), TEKST if aktiv else (200, 210, 224))
            im.alpha_composite(tb, (96, (radh - tb.height) // 2 + 2))
            return im
        bilder = to_tilstander(lag)

        def velg(t, i=i, bilder=bilder):
            return bilder[aktiv_indeks(t, del_t, outro_t) == i]
        els.append(El(None, X0, ry + i * (radh + mellom), del_t[i] - 0.1, flytt=(-36, 0), velg=velg))

    # «Prøv selv» – eksempelprompt
    fe = font("Medium", 29)
    linjer = bryt(f"«{scene['eksempel']}»", fe, X1 - X0 - 64)
    eh = 74 + 40 * len(linjer) + 22
    eks = avrundet(X1 - X0, eh, 24, rgba((43, 76, 126), 0.55), rgba(farge, 0.75), 2)
    fl = font("SemiBold", 22)
    chip = avrundet(int(fl.getlength("PRØV SELV")) + 66, 36, 18, rgba(farge, 0.25))
    chip.alpha_composite(ikon("boble", 22, farge), (14, 7))
    chip.alpha_composite(tekstbilde("PRØV SELV", fl, TEKST), (44, 5))
    eks.alpha_composite(chip, (30, 22))
    de = ImageDraw.Draw(eks)
    for j, l in enumerate(linjer):
        de.text((32, 74 + j * 40), l, font=fe, fill=rgba(TEKST))
    ey = ry + len(scene["deler"]) * (radh + mellom) + 16
    els.append(El(eks, X0, ey, outro_t - 0.1, flytt=(0, 24)))
    return els


HL_FARGER = {"Mål": TEAL, "Format": FIOLETT, "Kilde": RAV, "Kontekst": HIMMEL, "Forventninger": FIOLETT}


def sc_chat(scene, tid, nr, antall) -> list[El]:
    els = overskrift(scene, nr, antall, tid["start"])
    (r1a, r1b), (r2a, r2b), (r3a, _), (r4a, _) = [(x["start"], x["slutt"]) for x in tid["replikker"]]
    vx, vy, vb, vh = X0, Y0 - 12, X1 - X0, Y1 - Y0 + 18

    # Vindu
    vindu = avrundet(vb, vh, 26, rgba((16, 26, 46), 0.92), rgba(TEKST, 0.1), 2)
    d = ImageDraw.Draw(vindu)
    d.line((0, 58, vb, 58), fill=rgba(TEKST, 0.08), width=2)
    vindu.alpha_composite(ikonbrikke("stjerne", 36, TEAL, 0.22), (22, 11))
    vindu.alpha_composite(tekstbilde("Copilot", font("Bold", 25), TEKST), (70, 14))
    vindu.alpha_composite(tekstbilde("Chat", font("Regular", 22), SVAK), (172, 17))
    for i, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
        d.ellipse((vb - 100 + i * 26, 22, vb - 86 + i * 26, 36), fill=rgba(c, 0.6))
    els.append(El(vindu, vx, vy, tid["start"] + 0.2))

    # Brukerens prompt – skrives fortløpende, deler fremheves senere
    deler = scene["prompt"]
    f = font("Medium", 28)
    maks = 820
    ord_: list[tuple[str, Optional[str]]] = []
    for tekst, etikett in deler:
        for o in tekst.replace(" ", " \x00").split("\x00"):
            if o:
                ord_.append((o, etikett))
    # Linjebryting på ordnivå
    linjer, linje, lb = [], [], 0.0
    for o, e in ord_:
        w = f.getlength(o)
        if lb + f.getlength(o.rstrip()) > maks and linje:
            linjer.append(linje)
            linje, lb = [], 0.0
        linje.append((o, e, lb))
        lb += w
    linjer.append(linje)
    linjeh = 40
    pb = int(max(sum(f.getlength(o) for o, _, _ in l) for l in linjer)) + 48
    ph = linjeh * len(linjer) + 34
    total = sum(len(o) for o, _ in ord_)
    t_skriv0, t_skriv1 = r1a + 0.4, r1b - 0.3
    hl_tider = {"Mål": r2a + 0.15 * (r2b - r2a), "Format": r2a + 0.45 * (r2b - r2a),
                "Kilde": r2a + 0.72 * (r2b - r2a)}
    cache: dict = {}

    def boble(t):
        k = total if t >= t_skriv1 else int(total * max(0.0, (t - t_skriv0) / (t_skriv1 - t_skriv0)))
        hl = tuple(e for e, tt in hl_tider.items() if t >= tt)
        markor = k < total and int(t * 2.5) % 2 == 0
        nokkel = (k, hl, markor)
        if nokkel in cache:
            return cache[nokkel]
        im = avrundet(pb, ph, 22, rgba((43, 76, 126), 1.0))
        dd = ImageDraw.Draw(im)
        igjen = k
        sx, sy = 24, 16
        for li, l in enumerate(linjer):
            for o, e, x in l:
                if igjen <= 0:
                    break
                vis = o[:igjen]
                igjen -= len(o)
                farge = HL_FARGER[e] if e in hl else TEKST
                dd.text((sx + x, sy + li * linjeh), vis, font=f, fill=rgba(farge))
                if e in hl and vis.strip():
                    lw = f.getlength(vis.rstrip())
                    yy = sy + li * linjeh + 36
                    dd.line((sx + x, yy, sx + x + lw, yy), fill=rgba(farge, 0.9), width=3)
                if igjen <= 0 and markor:
                    cx = sx + x + f.getlength(vis) + 2
                    dd.rectangle((cx, sy + li * linjeh + 4, cx + 3, sy + li * linjeh + 34), fill=rgba(TEKST))
        cache[nokkel] = im
        return im

    bx = vx + vb - 28 - pb
    by = vy + 82
    els.append(El(None, bx, by, r1a + 0.1, velg=boble))

    # Etiketter Mål / Format / Kilde
    cx = vx + vb - 28
    chips = []
    for e in ("Kilde", "Format", "Mål"):
        fe = font("SemiBold", 22)
        im = avrundet(int(fe.getlength(e)) + 40, 38, 19, rgba(HL_FARGER[e], 0.16), rgba(HL_FARGER[e], 0.7), 2)
        im.alpha_composite(tekstbilde(e, fe, HL_FARGER[e]), (20, 6))
        cx -= im.width
        chips.append((e, im, cx))
        cx -= 12
    for e, im, x in chips:
        els.append(El(im, x, by + ph + 12, hl_tider[e], flytt=(0, -12), varighet=0.3))

    # Copilot svarer
    sy0 = by + ph + 58
    av = ikonbrikke("stjerne", 44, TEAL, 0.22)
    els.append(El(av, vx + 24, sy0, r3a - 0.2, flytt=(0, 10)))
    prikker = []
    for fase in range(3):
        im = avrundet(110, 50, 25, rgba(TEKST, 0.08))
        dd = ImageDraw.Draw(im)
        for j in range(3):
            a = 1.0 if j == fase else 0.35
            dd.ellipse((26 + j * 22, 20, 36 + j * 22, 30), fill=rgba(TEKST, a))
        prikker.append(im)
    t_svar = r3a + 0.7
    els.append(El(None, vx + 82, sy0, r3a - 0.2, ut=t_svar - 0.3, flytt=(0, 10), varighet=0.25,
                  velg=lambda t: prikker[int(t * 6) % 3]))

    sb = 740
    f_i = font("Medium", 26)
    rader = scene["tabell"]
    kol = [24, 250, 480]
    rad_h = 38
    sh = 20 + 36 + 12 + rad_h * len(rader) + 14 + 36 + 18
    svar = avrundet(sb, sh, 22, rgba(TEKST, 0.075), rgba(TEKST, 0.1), 2)
    els.append(El(svar, vx + 82, sy0, t_svar, flytt=(0, 16)))
    els.append(El(tekstbilde(scene["svar_intro"], f_i, TEKST), vx + 82 + 24, sy0 + 18, t_svar + 0.1, flytt=(0, 10)))
    ty = sy0 + 20 + 36 + 12
    for i, rad in enumerate(rader):
        im = Image.new("RGBA", (sb - 32, rad_h), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        if i == 0:
            dd.rounded_rectangle((0, 0, sb - 33, rad_h - 1), 10, fill=rgba(TEKST, 0.07))
        else:
            dd.line((8, rad_h - 1, sb - 40, rad_h - 1), fill=rgba(TEKST, 0.07), width=1)
        for j, celle in enumerate(rad):
            ff = font("SemiBold" if i == 0 else "Regular", 23 if i == 0 else 25)
            farge = SVAK if i == 0 else TEKST
            if j == 2 and i > 0:
                farge = GRONN if celle.startswith("+") else (248, 113, 113)
            dd.text((kol[j] - 8, 7 if i == 0 else 6), celle, font=ff, fill=rgba(farge))
        els.append(El(im, vx + 82 + 16, ty + i * rad_h, t_svar + 0.3 + i * 0.14, flytt=(0, 8), varighet=0.3))
    els.append(El(tekstblokk(scene["svar_slutt"], f_i, DEMPET, sb - 48, 34), vx + 82 + 24,
                  ty + rad_h * len(rader) + 14, t_svar + 1.2, flytt=(0, 10)))

    # Sjekk mot kilden + merknad om fiktive tall
    kb = vb - (82 + sb) - 46
    kort = avrundet(kb, 200, 22, rgba(RAV, 0.12), rgba(RAV, 0.65), 2)
    kort.alpha_composite(ikonbrikke("sjekk", 56, RAV, 0.25), (22, 22))
    kort.alpha_composite(tekstblokk(scene["sjekk"], font("SemiBold", 26), RAV, kb - 44, 34), (22, 94))
    els.append(El(kort, vx + 82 + sb + 22, sy0 + 50, r4a + 0.2, flytt=(0, 16)))
    merk = tekstblokk(scene["merknad"], font("Italic", 21), SVAK, kb - 10, 28)
    els.append(El(merk, vx + 82 + sb + 26, sy0 + 50 + 200 + 16, t_svar + 0.6, flytt=(0, 0)))
    return els


def sc_fire(scene, tid, nr, antall) -> list[El]:
    els = overskrift(scene, nr, antall, tid["start"])
    del_t, outro_t = tider(scene, tid)
    kb, kh, mellom = (X1 - X0 - 24) // 2, 196, 24
    for i, d_ in enumerate(scene["deler"]):
        tittel, tekst = d_["kort"]
        farge = [TEAL, HIMMEL, FIOLETT, RAV][i % 4]
        x = X0 + (i % 2) * (kb + mellom)
        y = Y0 + (i // 2) * (kh + mellom)

        def lag(aktiv, i=i, farge=farge, tittel=tittel, tekst=tekst):
            im = avrundet(kb, kh, 24, rgba(TEKST, 0.08 if aktiv else 0.04),
                          rgba(farge, 0.7) if aktiv else rgba(TEKST, 0.08), 2)
            sirkel = farget(maske(64, 64, lambda d, k: d.ellipse((0, 0, 64 * k - 1, 64 * k - 1), fill=255)), farge)
            sirkel.putalpha(sirkel.getchannel("A").point(lambda v: int(v * 0.2)))
            im.alpha_composite(sirkel, (28, 30))
            nt = tekstbilde(str(i + 1), font("Bold", 30), farge)
            im.alpha_composite(nt, (28 + (64 - nt.width) // 2, 30 + (64 - nt.height) // 2 + 2))
            im.alpha_composite(tekstbilde(tittel, font("Bold", 40), farge), (112, 36))
            im.alpha_composite(tekstblokk(tekst, font("Regular", 30), TEKST if aktiv else DEMPET, kb - 140, 38), (112, 100))
            return im
        bilder = to_tilstander(lag)

        def velg(t, i=i, bilder=bilder):
            return bilder[aktiv_indeks(t, del_t, outro_t) == i]
        els.append(El(None, x, y, del_t[i] - 0.1, velg=velg))

    if outro_t:
        tip = merknadskort("Tips: " + scene["tips"], TEAL, "boble")
        els.append(El(tip, X0, Y0 + 2 * kh + mellom + 34, outro_t - 0.1, flytt=(0, 24)))
    return els


BYGGERE = {"tittel": sc_tittel, "agenda": sc_agenda, "punkter": sc_punkter, "neste_ord": sc_neste_ord,
           "kolonner": sc_kolonner, "flyt": sc_flyt, "app": sc_app, "chat": sc_chat, "fire": sc_fire}


# ---------------------------------------------------------------- bakgrunn og presentatør

def lag_bakgrunn() -> tuple[np.ndarray, np.ndarray]:
    base = np.asarray(gradient(B, H, BG_TOPP, BG_BUNN, "y")).astype(np.int16)
    gb, gh = B + 400, H + 300
    glod = Image.new("RGB", (gb, gh), (0, 0, 0))
    d = ImageDraw.Draw(glod)
    for cx, cy, r, f, a in ((250, 200, 420, TEAL, 0.22), (1500, 950, 520, FIOLETT, 0.22),
                            (1100, 120, 300, HIMMEL, 0.12), (450, 1150, 380, FIOLETT, 0.1)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=tuple(int(c * a) for c in f))
    glod = glod.filter(ImageFilter.GaussianBlur(160))
    return base, np.asarray(glod).astype(np.int16)


def bakgrunn(base: np.ndarray, glod: np.ndarray, t: float) -> Image.Image:
    ox = int(200 + 160 * math.sin(t * 0.07))
    oy = int(150 + 110 * math.cos(t * 0.05))
    arr = base + glod[oy:oy + H, ox:ox + B]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


class Presentator:
    """Leser presentatørvideoen (eller et stillbilde) bilde for bilde, beskåret til kortet."""

    def __init__(self, video: Optional[Path], foto: Optional[Path], utsnitt, fra: float):
        _, _, kb, kh = KORT
        self.storrelse = (kb, kh)
        self.proc = None
        self.siste = None
        if video and video.exists():
            vb, vh = self._dim(video)
            x, y, w, h = self._utsnitt(utsnitt, foto, vb, vh)
            vf = f"crop={w}:{h}:{x}:{y},scale={kb}:{kh}:flags=lanczos,fps={FPS}"
            self.proc = subprocess.Popen(
                ["ffmpeg", "-v", "fatal", "-ss", f"{fra:.3f}", "-i", str(video), "-vf", vf,
                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
            print(f"Presentatør: video {video.name} ({vb}x{vh}), utsnitt {x},{y} {w}x{h}")
        elif foto:
            im = Image.open(foto).convert("RGB")
            x, y, w, h = self._utsnitt(utsnitt, foto, *im.size)
            self.stillbilde = im.crop((x, y, x + w, y + h)).resize((kb, kh), Image.LANCZOS)
            print("Presentatør: stillbilde (ingen presentatørvideo funnet)")
        else:
            raise SystemExit("Trenger enten --presentator-video eller --foto")

    @staticmethod
    def _dim(video: Path) -> tuple[int, int]:
        ut = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                             "stream=width,height", "-of", "csv=p=0", str(video)],
                            capture_output=True, text=True, check=True).stdout.strip()
        b, h = ut.split(",")[:2]
        return int(b), int(h)

    @staticmethod
    def _utsnitt(utsnitt, foto, vb, vh):
        if utsnitt and foto and Image.open(foto).size != (vb, vh):
            utsnitt = None  # videoen er allerede beskåret (f.eks. fra leppesynk.py) – bruk hele
        if utsnitt:
            x, y, w, h = utsnitt
        else:
            w = min(vb, int(vh * 3 / 4))
            h = int(w * 4 / 3)
            x, y = (vb - w) // 2, max(0, (vh - h) // 2)
        w -= w % 2
        h -= h % 2
        return max(0, x), max(0, y), min(w, vb), min(h, vh)

    def neste(self, t: float) -> Image.Image:
        if self.proc is None:
            z = 1.0 + 0.02 * math.sin(t * 0.3)
            kb, kh = self.storrelse
            im = self.stillbilde.resize((int(kb * z), int(kh * z)), Image.BILINEAR)
            return im.crop(((im.width - kb) // 2, (im.height - kh) // 2,
                            (im.width - kb) // 2 + kb, (im.height - kh) // 2 + kh))
        n = self.storrelse[0] * self.storrelse[1] * 3
        data = self.proc.stdout.read(n)
        if len(data) == n:
            self.siste = Image.frombuffer("RGB", self.storrelse, data)
        elif self.siste is None:  # forbi slutten av presentatørvideoen
            self.siste = Image.new("RGB", self.storrelse, (16, 24, 40))
        return self.siste

    def lukk(self):
        if self.proc:
            self.proc.stdout.close()
            self.proc.kill()


def lag_kortlag(navn: str, rolle: str):
    x, y, kb, kh = KORT
    r = 30
    kortmaske = maske(kb, kh, lambda d, k: d.rounded_rectangle((0, 0, kb * k - 1, kh * k - 1), r * k, fill=255))
    skygge = Image.new("RGBA", (kb + 120, kh + 120), (0, 0, 0, 0))
    ImageDraw.Draw(skygge).rounded_rectangle((60, 75, 60 + kb, 75 + kh), r, fill=(0, 0, 0, 150))
    skygge = skygge.filter(ImageFilter.GaussianBlur(26))
    ramme = avrundet(kb, kh, r, (0, 0, 0, 0), rgba(TEKST, 0.16), 2)
    # mørk overgang nederst for navneskilt
    nedre = Image.new("RGBA", (kb, kh), (0, 0, 0, 0))
    if navn or rolle:
        g = np.zeros((kh, kb, 4), np.uint8)
        hoyde = 190
        alfa = (np.clip((np.arange(kh) - (kh - hoyde)) / hoyde, 0, 1) ** 1.4 * 200).astype(np.uint8)
        g[:, :, 3] = alfa[:, None]
        nedre = Image.fromarray(g, "RGBA")
        if navn:
            nedre.alpha_composite(tekstbilde(navn, font("SemiBold", 32), TEKST), (28, kh - 96))
        if rolle:
            nedre.alpha_composite(tekstbilde(rolle, font("Regular", 23), (210, 220, 232)), (28, kh - 52))
    return kortmaske, skygge, ramme, nedre


def lydniva(lyd: Path, antall: int) -> np.ndarray:
    with wave.open(str(lyd)) as w:
        rate = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    per = rate / FPS
    niv = np.zeros(antall, np.float32)
    for i in range(antall):
        seg = a[int(i * per):int((i + 1) * per)]
        if len(seg):
            niv[i] = math.sqrt(float((seg ** 2).mean()))
    return np.clip(niv / (np.percentile(niv[niv > 0.01], 90) + 1e-6), 0, 1) if (niv > 0.01).any() else niv


def undertekstbilde(tekst: str) -> Image.Image:
    f = font("Medium", 34)
    linjer = bryt(tekst, f, 1640)
    if len(linjer) > 2:
        f = font("Medium", 30)
        linjer = bryt(tekst, f, 1700)
    lh = int(f.size * 1.36)
    bb = int(max(f.getlength(l) for l in linjer)) + 64
    bh = lh * len(linjer) + 30
    im = avrundet(bb, bh, 18, (6, 11, 22, 196))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(linjer):
        d.text(((bb - f.getlength(l)) / 2, 14 + i * lh), l, font=f, fill=rgba(TEKST))
    return im


# ---------------------------------------------------------------- hovedløkke

class Renderer:
    """Bygger alle lag én gang, og lager deretter ett bilde om gangen."""

    def __init__(self, tidslinje: dict, lyd: Path, presentator: Optional[Path], foto: Optional[Path],
                 utsnitt, navn: str, rolle: str, fra_bilde: int = 0):
        self.tl = tidslinje
        self.varighet = tidslinje["varighet"]
        scener = manus.SCENER
        assert len(scener) == len(tidslinje["scener"]), "Tidslinjen passer ikke med manuset – kjør «tale» på nytt"
        self.elementer = []
        for nr, (scene, tid) in enumerate(zip(scener, tidslinje["scener"]), 1):
            self.elementer.append((tid, BYGGERE[scene["type"]](scene, tid, nr, len(scener))))
        self.replikker = [r for s in tidslinje["scener"] for r in s["replikker"]]
        self.undertekster = [undertekstbilde(r["tekst"]) for r in self.replikker]
        self.niva = lydniva(lyd, int(math.ceil(self.varighet * FPS)) + 2)
        self.base, self.glod = lag_bakgrunn()
        self.kortmaske, self.skygge, self.ramme, self.nedre = lag_kortlag(navn, rolle)
        self._pres_args = (presentator, foto, utsnitt)
        self.pres = Presentator(*self._pres_args, fra_bilde / FPS)

    def hopp_til(self, n: int) -> None:
        """Start presentatørvideoen på nytt fra bilde n (brukes av forhåndsvisningen)."""
        self.pres.lukk()
        self.pres = Presentator(*self._pres_args, n / FPS)

    def bilde(self, n: int) -> Image.Image:
        t = n / FPS
        ramme_ = bakgrunn(self.base, self.glod, t)

        # Lysbildeinnhold
        siste = self.tl["scener"][-1]
        for tid, els in self.elementer:
            if not (tid["start"] - 0.01 <= t < tid["slutt"] + 0.01):
                continue
            scene_ut = 1.0 if tid is siste else 1 - ease((t - (tid["slutt"] - 0.4)) / 0.4)
            for el in els:
                a = el.alfa(t) * scene_ut
                if a <= 0.003:
                    continue
                im = el.velg(t) if el.velg else el.bilde
                if im is None:
                    continue
                k = 1 - ease((t - el.inn) / el.varighet)
                ramme_.alpha_composite(med_alfa(im, a), (int(el.x + el.flytt[0] * k), int(el.y + el.flytt[1] * k)))

        # Presentatørkort (glir inn i starten)
        kx, ky, kb, kh = KORT
        inn = ease((t - 0.15) / 0.8)
        ansikt = self.pres.neste(t)
        if inn > 0:
            ansikt = ansikt.convert("RGBA")
            ansikt.putalpha(self.kortmaske)
            ansikt.alpha_composite(self.nedre)
            ansikt.alpha_composite(self.ramme)
            # Lydstolper som viser at presentatøren snakker
            v = float(self.niva[min(n, len(self.niva) - 1)])
            d = ImageDraw.Draw(ansikt)
            for j in range(4):
                hv = 6 + 26 * v * (0.55 + 0.45 * abs(math.sin(t * 9 + j * 1.7)))
                bx = kb - 34 - (3 - j) * 12
                d.rounded_rectangle((bx, kh - 40 - hv, bx + 6, kh - 40), 3, fill=rgba(TEAL, 0.95))
            dx = int((1 - inn) * 80)
            ramme_.alpha_composite(med_alfa(self.skygge, inn), (kx - 60 + dx, ky - 60))
            ramme_.alpha_composite(med_alfa(ansikt, inn), (kx + dx, ky))

        # Undertekst
        for r, im in zip(self.replikker, self.undertekster):
            if r["start"] - 0.05 <= t <= r["slutt"] + 0.3:
                a = min(ease((t - r["start"] + 0.05) / 0.15), 1 - ease((t - r["slutt"] - 0.15) / 0.15))
                ramme_.alpha_composite(med_alfa(im, a), ((B - im.width) // 2, 1040 - im.height))
                break

        # Framdriftslinje
        d = ImageDraw.Draw(ramme_)
        d.rectangle((0, 0, B, 4), fill=rgba(TEKST, 0.06))
        d.rectangle((0, 0, int(B * t / self.varighet), 4), fill=rgba(TEAL, 0.9))

        bilde = ramme_.convert("RGB")
        mork = min(ease(t / 0.6), 1 - ease((t - (self.varighet - 0.9)) / 0.9))
        if mork < 0.999:
            bilde = Image.blend(Image.new("RGB", (B, H), (0, 0, 0)), bilde, max(0.0, mork))
        return bilde

    def lukk(self):
        self.pres.lukk()


def _render_bit(jobb) -> str:
    n0, n1, sti, opts = jobb
    r = Renderer(fra_bilde=n0, **opts)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{B}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-g", str(FPS * 4), str(sti)], stdin=subprocess.PIPE)
    t0 = time.time()
    for n in range(n0, n1):
        ff.stdin.write(r.bilde(n).tobytes())
        if (n - n0 + 1) % (FPS * 30) == 0:
            print(f"  bit {n0 // FPS:>4}s: {(n - n0 + 1) / FPS:.0f}/{(n1 - n0) / FPS:.0f}s "
                  f"({(n - n0 + 1) / (time.time() - t0):.1f} bilder/s)", flush=True)
    ff.stdin.close()
    ff.wait()
    r.lukk()
    return str(sti)


def lag_video(tidslinje: dict, lyd: Path, presentator: Optional[Path], foto: Optional[Path],
              utsnitt, navn: str, rolle: str, ut: Path, fra: float = 0.0, til: Optional[float] = None,
              jobber: int = 0) -> None:
    varighet = tidslinje["varighet"]
    til = min(til or varighet, varighet)
    n0, n1 = int(round(fra * FPS)), int(math.ceil(til * FPS))
    jobber = jobber or os.cpu_count() or 1
    jobber = max(1, min(jobber, (n1 - n0) // (FPS * 5) or 1))
    opts = dict(tidslinje=tidslinje, lyd=lyd, presentator=presentator, foto=foto,
                utsnitt=utsnitt, navn=navn, rolle=rolle)
    ut.parent.mkdir(parents=True, exist_ok=True)
    bitmappe = ut.parent / "biter"
    bitmappe.mkdir(exist_ok=True)
    grenser = [n0 + (n1 - n0) * i // jobber for i in range(jobber + 1)]
    jobbliste = [(grenser[i], grenser[i + 1], bitmappe / f"bit_{i:02d}.mp4", opts) for i in range(jobber)]
    print(f"Rendrer {(n1 - n0) / FPS:.1f} s video i {jobber} parallelle biter ...")
    t0 = time.time()
    if jobber == 1:
        biter = [_render_bit(jobbliste[0])]
    else:
        with multiprocessing.get_context("fork").Pool(jobber) as pool:
            biter = pool.map(_render_bit, jobbliste)
    liste = bitmappe / "liste.txt"
    liste.write_text("".join(f"file '{Path(b).resolve()}'\n" for b in biter))
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(liste),
         "-ss", f"{n0 / FPS:.3f}", "-t", f"{(n1 - n0) / FPS:.3f}", "-i", str(lyd),
         "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", str(ut)], check=True)
    for b in biter:
        Path(b).unlink()
    liste.unlink()
    print(f"Ferdig: {ut} ({time.time() - t0:.0f} s)")


def forhandsvis(tidslinje: dict, lyd: Path, presentator: Optional[Path], foto: Optional[Path],
                utsnitt, navn: str, rolle: str, tider: list[float], mappe: Path) -> list[Path]:
    """Lag enkeltbilder (PNG) på gitte tidspunkter – for rask visuell kontroll."""
    mappe.mkdir(parents=True, exist_ok=True)
    filer = []
    r = Renderer(tidslinje, lyd, presentator, foto, utsnitt, navn, rolle)
    for t in tider:
        n = int(round(t * FPS))
        r.hopp_til(n)
        sti = mappe / f"bilde_{t:07.2f}s.png"
        r.bilde(n).save(sti)
        filer.append(sti)
        print(sti)
    r.lukk()
    return filer
