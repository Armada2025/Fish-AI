#!/bin/bash
# Steg 2: Lag det snakkende ansiktet -> bygg/presentator.mp4
#
#   bash presentator.sh <foto> [X Y B H]
#
# X Y B H er utsnittet av bildet som vises i presentatørkortet (forhold 3:4), f.eks. 150 400 1200 1600.
#
# 2a. SadTalker lager et kort basisklipp (12 s) fra bildet: naturlige blunk, lukket munn.
#     Bare pikslene som endrer seg (øynene) hentes fra SadTalker – resten er originalbildet.
# 2b. Wav2Lip legger munnbevegelser til talen oppå basisklippet, som går i løkke.
#
# Hele SadTalker for 15 min tale ville tatt ~22 timer på en vanlig CPU; denne kombinasjonen tar ~1 time.
set -euo pipefail
HER="$(cd "$(dirname "$0")" && pwd)"
R="$HER/ressurser/presentator"
PY="$R/venv/bin/python"
[ $# -ge 1 ] || { sed -n 2,13p "$0"; exit 1; }
FOTO="$(realpath "$1")"; shift
UTSNITT=()
[ $# -eq 4 ] && UTSNITT=(--utsnitt "$@")
[ -f "$HER/bygg/tale.wav" ] || { echo "Mangler bygg/tale.wav – kjør først: python lag_video.py tale"; exit 1; }
[ -x "$PY" ] || bash "$HER/presentator/oppsett.sh"

B="$HER/bygg/basis"
mkdir -p "$B"
if [ ! -s "$B/basis.mp4" ]; then
  echo "2a. Basisklipp med SadTalker (ca. 20–30 min på CPU) ..."
  # Nesten stillhet (svak rosa støy, ca. −62 dBFS) gir lukket munn
  ffmpeg -v error -y -f lavfi -i "anoisesrc=color=pink:amplitude=0.0008:duration=12:sample_rate=16000" \
    -ac 1 "$B/stillhet.wav"
  ( cd "$R/SadTalker" && SADTALKER_SEED=7 SADTALKER_BLINK_MIN=50 SADTALKER_BLINK_MAX=90 \
      SADTALKER_SKIP_PASTE=1 SADTALKER_SAVE_FRAMES="$B/frames256.npz" \
      "$PY" inference.py --cpu --batch_size 4 --preprocess full --still --size 256 \
      --driven_audio "$B/stillhet.wav" --source_image "$FOTO" --result_dir "$B/sadtalker" ) > "$B/sadtalker.log" 2>&1 \
    || { echo "SadTalker feilet – se $B/sadtalker.log"; tail -5 "$B/sadtalker.log"; exit 1; }
  "$PY" "$HER/presentator/composite.py" "$FOTO" "$B/frames256.npz" "$B/basis.mp4" --mode delta
fi

echo "2b. Leppesynk med Wav2Lip over hele talen (ca. 40–60 min på CPU) ..."
"$PY" -u "$HER/leppesynk.py" --base "$B/basis.mp4" --lyd "$HER/bygg/tale.wav" --ut "$HER/bygg/presentator.mp4" \
  --wav2lip "$R/Wav2Lip" --ansiktsvekter "$R/SadTalker/gfpgan/weights" "${UTSNITT[@]}"
echo "Ferdig: bygg/presentator.mp4"
