#!/bin/bash
# Steg 2 (full animasjon): hele hodet beveger seg – hodebevegelser, mimikk, blunk og leppesynk.
#
#   bash presentator_hode.sh <foto> [X Y B H]
#
# Talen deles i 6 biter (skjøter i pausene mellom replikker). Hver bit animeres med SadTalker,
# og bitene settes sammen med myke overganger -> bygg/presentator.mp4 (540x720).
# Tar ca. 5 timer på 4 CPU-kjerner. Kan gjenopptas: ferdige biter hoppes over ved ny kjøring.
set -euo pipefail
HER="$(cd "$(dirname "$0")" && pwd)"
R="$HER/ressurser/presentator"
PY="$R/venv/bin/python"
[ $# -ge 1 ] || { sed -n 2,9p "$0"; exit 1; }
FOTO="$(realpath "$1")"; shift
UTSNITT=()
[ $# -eq 4 ] && UTSNITT=(--utsnitt "$@")
[ -f "$HER/bygg/tale.wav" ] || { echo "Mangler bygg/tale.wav – kjør først: python lag_video.py tale"; exit 1; }
[ -x "$PY" ] || bash "$HER/presentator/oppsett.sh"

B="$HER/bygg/hode"
mkdir -p "$B"
# Ny tale gir ny oppdeling (og gamle biter forkastes)
SJEKK="$(md5sum "$HER/bygg/tale.wav" | cut -c1-12)"
if [ "$(cat "$B/tale.md5" 2>/dev/null)" != "$SJEKK" ]; then
  rm -rf "$B"/*; echo "$SJEKK" > "$B/tale.md5"
  python3 "$HER/presentator/del_opp.py" "$HER/bygg/tidslinje.json" "$HER/bygg/tale.wav" "$B" 6
fi

for wav in "$B"/bit_*.wav; do
  n="$(basename "$wav" .wav)"
  if [ -s "$B/$n/hode.mp4" ]; then echo "$n: ferdig fra før"; continue; fi
  echo "$n: animerer ($(date +%T)) ..."
  bash "$HER/presentator/hode_bit.sh" "$FOTO" "$wav" "$B/$n"
done

"$PY" "$HER/presentator/hode_komposit.py" --foto "$FOTO" --plan "$B/plan.json" --biter "$B" \
  --lyd "$HER/bygg/tale.wav" --ut "$HER/bygg/presentator.mp4" "${UTSNITT[@]}"
echo "Ferdig: bygg/presentator.mp4"
