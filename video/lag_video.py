#!/usr/bin/env python3
"""Lag presentasjonsvideoen «KI i Copilot».

Steg (kan kjøres hver for seg):
  python lag_video.py tale                 # 1. tale (Google-stemme; --stemme piper for lokal) -> bygg/tale.wav
  bash presentator.sh <foto> bygg/tale.wav # 2. snakkende ansikt (SadTalker) -> bygg/presentator.mp4
  python lag_video.py render --foto <foto> # 3. lysbilder + presentatør + lyd -> bygg/ki-i-copilot.mp4
  python lag_video.py forhandsvis          # enkeltbilder for rask kontroll
  python lag_video.py manus                # skriv MANUS.md (for å lese inn selv)
"""

import argparse
import json
import subprocess
import tarfile
import urllib.request
from pathlib import Path

HER = Path(__file__).resolve().parent
BYGG = HER / "bygg"
RESSURSER = HER / "ressurser"
STEMME_URL = "https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-no-talesyntese-medium.tar.gz"
STEMME = RESSURSER / "stemme" / "no-talesyntese-medium.onnx"


def hent_stemme() -> Path:
    if STEMME.exists():
        return STEMME
    STEMME.parent.mkdir(parents=True, exist_ok=True)
    arkiv = STEMME.parent / "stemme.tar.gz"
    print(f"Laster ned norsk stemme fra {STEMME_URL} ...")
    urllib.request.urlretrieve(STEMME_URL, arkiv)
    with tarfile.open(arkiv) as tar:
        tar.extractall(STEMME.parent, filter="data")
    arkiv.unlink()
    return STEMME


def kmd_tale(args) -> None:
    import tale
    if args.stemme == "piper":
        stemme = tale.PiperStemme(hent_stemme(), args.tempo or 1.3)
    else:
        navn = args.stemme.split(":", 1)[1] if ":" in args.stemme else None
        stemme = tale.GoogleStemme(navn, args.tempo or 1.0, BYGG / "tts_cache")
    tale.lag_tale(stemme, BYGG)


def kmd_stemmer(args) -> None:
    import tale
    for v in tale.GoogleStemme("-", 1.0, BYGG / "tts_cache").stemmer():
        print(f"{v['name']:32s} {v.get('ssmlGender', ''):8s} {','.join(v.get('languageCodes', []))}")


def felles(args) -> dict:
    return dict(
        tidslinje=json.loads((BYGG / "tidslinje.json").read_text()),
        lyd=BYGG / "tale.wav",
        presentator=Path(args.presentator) if args.presentator else None,
        foto=Path(args.foto) if args.foto else None,
        utsnitt=tuple(args.utsnitt) if args.utsnitt else None,
        navn=args.navn,
        rolle=args.rolle,
    )


def kmd_render(args) -> None:
    import render
    render.lag_video(**felles(args), ut=Path(args.ut), fra=args.fra, til=args.til, jobber=args.jobber)


def kmd_forhandsvis(args) -> None:
    import render
    opts = felles(args)
    tider = args.tider
    if not tider:  # ett bilde midt i hver replikk som avslutter en scene
        tider = [round(s["replikker"][-1]["slutt"] - 0.5, 2) for s in opts["tidslinje"]["scener"]]
    render.forhandsvis(**opts, tider=tider, mappe=Path(args.mappe))


def kmd_manus(args) -> None:
    import manus
    linjer = [f"# Manus: {manus.TITTEL}", "", f"_{manus.UNDERTITTEL}_", "",
              "Les inn hver replikk som en egen fil i `egen_stemme/` (f.eks. `intro_1.wav`) "
              "for å bruke din egen stemme i stedet for talesyntesen.", ""]
    for nr, scene in enumerate(manus.SCENER, 1):
        linjer += [f"## {nr}. {scene['tittel']}", ""]
        for r_nr, tekst in enumerate(manus.replikker(scene)[0], 1):
            linjer.append(f"**`{scene['id']}_{r_nr}`** – {tekst}")
            linjer.append("")
    (HER / "MANUS.md").write_text("\n".join(linjer), encoding="utf-8")
    print(f"Skrev {HER / 'MANUS.md'}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="kommando", required=True)

    t = sub.add_parser("tale", help="lag talesporet og tidslinjen")
    t.add_argument("--stemme", default="google",
                   help="«google» (velger beste norske stemme), «google:<navn>» eller «piper»")
    t.add_argument("--tempo", type=float, default=None,
                   help="Google: talehastighet (1.0 = normal, høyere = raskere). Piper: lengdeskala (høyere = saktere)")
    t.set_defaults(func=kmd_tale)

    sv = sub.add_parser("stemmer", help="list Googles norske stemmer")
    sv.set_defaults(func=kmd_stemmer)

    def presentator_valg(r):
        r.add_argument("--presentator", default=str(BYGG / "presentator.mp4"),
                       help="video av snakkende ansikt (fra presentator.sh)")
        r.add_argument("--foto", help="bilde av presentatøren (brukes også som reserve hvis videoen mangler)")
        r.add_argument("--utsnitt", type=int, nargs=4, metavar=("X", "Y", "B", "H"),
                       help="utsnitt av bildet i piksler (bredde:høyde bør være 3:4)")
        r.add_argument("--navn", default="", help="navn på navneskiltet")
        r.add_argument("--rolle", default="", help="tekst under navnet")

    r = sub.add_parser("render", help="sett sammen den ferdige videoen")
    presentator_valg(r)
    r.add_argument("--ut", default=str(BYGG / "ki-i-copilot.mp4"))
    r.add_argument("--fra", type=float, default=0.0, help="start (s) – for raske tester")
    r.add_argument("--til", type=float, default=None, help="slutt (s) – for raske tester")
    r.add_argument("--jobber", type=int, default=0, help="antall parallelle prosesser (0 = alle kjerner)")
    r.set_defaults(func=kmd_render)

    f = sub.add_parser("forhandsvis", help="lag enkeltbilder (PNG) for rask kontroll")
    presentator_valg(f)
    f.add_argument("--tider", type=float, nargs="*", help="tidspunkter i sekunder (standard: ett per scene)")
    f.add_argument("--mappe", default=str(BYGG / "forhandsvisning"))
    f.set_defaults(func=kmd_forhandsvis)

    m = sub.add_parser("manus", help="skriv MANUS.md")
    m.set_defaults(func=kmd_manus)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
