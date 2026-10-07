"""Del talesporet i biter for parallell hodeanimasjon.

    python del_opp.py <tidslinje.json> <tale.wav> <utmappe> [antall=15]

Skjøtene legges midt i pausene mellom replikker (lukket munn), så overgangene blir
minst mulig synlige. Hver bit kuttes på hele videobilder (25 bilder/s), så bitene kan
settes sammen bilde for bilde. Skriver bit_NN.wav (16 kHz mono) og plan.json.
"""
import json
import subprocess
import sys
from pathlib import Path

FPS = 25


def main() -> None:
    tidslinje, tale, ut = json.loads(Path(sys.argv[1]).read_text()), sys.argv[2], Path(sys.argv[3])
    antall = int(sys.argv[4]) if len(sys.argv) > 4 else 15
    ut.mkdir(parents=True, exist_ok=True)
    total = int(round(tidslinje["varighet"] * FPS))
    # Midt i pausene mellom replikker (også ved sceneskift) – der er munnen lukket
    replikker = [r for sc in tidslinje["scener"] for r in sc["replikker"]]
    kandidater = sorted({int(round((x["slutt"] + y["start"]) / 2 * FPS)) for x, y in zip(replikker, replikker[1:])})
    grenser = [0]
    for k in range(1, antall):
        ideal = k * total / antall
        valg = min((c for c in kandidater if c > grenser[-1] + FPS * 10), key=lambda c: abs(c - ideal), default=None)
        if valg is not None and valg < total - FPS * 10:
            grenser.append(valg)
    grenser.append(total)
    plan = []
    for i, (a, b) in enumerate(zip(grenser, grenser[1:]), 1):
        fil = ut / f"bit_{i:02d}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a / FPS:.3f}", "-t", f"{(b - a) / FPS:.3f}",
                        "-i", tale, "-ac", "1", "-ar", "16000", str(fil)], check=True)
        plan.append({"nr": i, "fil": fil.name, "start_bilde": a, "bilder": b - a,
                     "start": round(a / FPS, 3), "varighet": round((b - a) / FPS, 3)})
        print(f"bit {i:02d}: {a / FPS:7.2f}–{b / FPS:7.2f} s ({(b - a) / FPS:5.1f} s)")
    (ut / "plan.json").write_text(json.dumps({"fps": FPS, "bilder_totalt": total, "biter": plan}, indent=1))


if __name__ == "__main__":
    main()
