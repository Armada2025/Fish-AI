#!/bin/bash
# Full hodeanimasjon (SadTalker) for én lydbit – brukes når jobben fordeles på flere maskiner.
#
#   bash hode_bit.sh <foto> <lydbit.wav> <utmappe>
#
# Resultat i <utmappe>:
#   hode.mp4   – det animerte ansiktet (256x256, 25 bilder/s, uten lyd)
#   info.json  – hvor ansiktet hører hjemme i bildet (brukes av hode_komposit.py)
# Alle maskiner bruker samme innstillinger og frø, så bitene passer sammen.
set -euo pipefail
HER="$(cd "$(dirname "$0")" && pwd)"
R="$(cd "$HER/.." && pwd)/ressurser/presentator"
PY="$R/venv/bin/python"
[ $# -eq 3 ] || { sed -n 2,9p "$0"; exit 1; }
FOTO="$(realpath "$1")"; LYD="$(realpath "$2")"; UT="$3"
mkdir -p "$UT"; UT="$(realpath "$UT")"
[ -x "$PY" ] || bash "$HER/oppsett.sh"

ffmpeg -v error -y -i "$LYD" -ac 1 -ar 16000 "$UT/lyd16k.wav"
t0=$(date +%s)
( cd "$R/SadTalker" && SADTALKER_SEED=7 SADTALKER_BLINK_MIN=50 SADTALKER_BLINK_MAX=90 \
    SADTALKER_SKIP_PASTE=1 SADTALKER_SAVE_FRAMES="$UT/frames256.npz" \
    "$PY" inference.py --cpu --batch_size 4 --preprocess full --size 256 \
    --driven_audio "$UT/lyd16k.wav" --source_image "$FOTO" --result_dir "$UT/sadtalker" ) > "$UT/sadtalker.log" 2>&1 \
  || { echo "SadTalker feilet – se $UT/sadtalker.log"; tail -5 "$UT/sadtalker.log"; exit 1; }
"$PY" "$HER/npz_til_mp4.py" "$UT/frames256.npz" "$UT/hode.mp4" "$UT/info.json"
rm -rf "$UT/frames256.npz" "$UT/sadtalker"
echo "Ferdig på $(( $(date +%s) - t0 )) s: $UT/hode.mp4 + $UT/info.json"
