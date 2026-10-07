"""Pakk SadTalkers rå 256x256-bilder (frames256.npz) som en kompakt video + plasseringsdata.

    python npz_til_mp4.py frames256.npz hode.mp4 info.json
"""
import json
import subprocess
import sys

import numpy as np


def main() -> None:
    npz, ut_mp4, ut_json = sys.argv[1:4]
    d = np.load(npz)
    bilder = d["frames"]  # N x 256 x 256 x 3, RGB uint8
    n, h, w, _ = bilder.shape
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", "25",
         "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv444p", ut_mp4],
        stdin=subprocess.PIPE)
    ff.stdin.write(np.ascontiguousarray(bilder).tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg feilet")
    info = {
        "bilder": int(n), "fps": 25, "storrelse": [int(w), int(h)],
        "crop_box": [float(v) for v in d["crop_box"]],
        "quad": [float(v) for v in d["quad"]],
        "original_size": [float(v) for v in d["original_size"]],
    }
    with open(ut_json, "w") as f:
        json.dump(info, f, indent=1)
    print(f"{n} bilder -> {ut_mp4}")


if __name__ == "__main__":
    main()
