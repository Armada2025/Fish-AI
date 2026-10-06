#!/bin/bash
# Installer verktøyene for det snakkende ansiktet (kjøres én gang, ca. 4 GB).
#   SadTalker (blunk/mimikk)  – github.com/OpenTalker/SadTalker, med CPU-optimalisering (OpenVINO)
#   Wav2Lip   (leppesynk)     – github.com/Rudrabha/Wav2Lip
# Alt legges i video/ressurser/presentator/ (ignoreres av git). Krever git, ffmpeg og uv.
set -euo pipefail
HER="$(cd "$(dirname "$0")" && pwd)"          # video/presentator
R="$(cd "$HER/.." && pwd)/ressurser/presentator"
mkdir -p "$R"
cd "$R"

if [ ! -d SadTalker ]; then
  git clone -q https://github.com/OpenTalker/SadTalker.git
  git -C SadTalker checkout -q cd4c0465ae0b54a6f85af57f5c65fec9fe23e7f8
  git -C SadTalker apply "$HER/sadtalker.diff"
  cp "$HER/fast_generator.py" SadTalker/src/facerender/modules/
fi
if [ ! -d Wav2Lip ]; then
  git clone -q https://github.com/Rudrabha/Wav2Lip.git
  git -C Wav2Lip checkout -q bac9a81e63ecc153202353372e5724b83d9e6322
fi

if [ ! -x venv/bin/python ]; then
  uv venv -q --python 3.10 venv
  uv pip install -q --python venv/bin/python -r "$HER/requirements.txt"
fi

hent() {  # hent <url> <fil>
  [ -s "$2" ] || { mkdir -p "$(dirname "$2")"; echo "Laster ned $(basename "$2") ..."; curl -fsSL -o "$2" "$1"; }
}
ST=https://github.com/OpenTalker/SadTalker/releases/download
hent $ST/v0.0.2-rc/mapping_00109-model.pth.tar      SadTalker/checkpoints/mapping_00109-model.pth.tar
hent $ST/v0.0.2-rc/mapping_00229-model.pth.tar      SadTalker/checkpoints/mapping_00229-model.pth.tar
hent $ST/v0.0.2-rc/SadTalker_V0.0.2_256.safetensors SadTalker/checkpoints/SadTalker_V0.0.2_256.safetensors
hent https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4HG.pth    SadTalker/gfpgan/weights/alignment_WFLW_4HG.pth
hent https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth SadTalker/gfpgan/weights/detection_Resnet50_Final.pth
hent https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth      SadTalker/gfpgan/weights/parsing_parsenet.pth
hent https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth          SadTalker/gfpgan/weights/GFPGANv1.4.pth
hent $ST/v0.0.2/wav2lip.pth                          Wav2Lip/checkpoints/wav2lip.pth
echo "Oppsett ferdig: $R"
