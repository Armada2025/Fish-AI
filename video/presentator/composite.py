"""Paste SadTalker 256px crop frames back into the full-resolution photo.

usage: python composite.py <photo> <frames256.npz> <out.mp4> [--mode delta|face|square] [--audio wav] [--crf 18]

frames256.npz is written by the patched SadTalker when SADTALKER_SAVE_FRAMES=<path> is set.

modes
  delta  (default) only pixels that actually change versus the median (neutral) render are taken
         from the render (blinks, mouth motion); everything else stays the sharp original photo.
         Best for --still clips; no rectangular seam.
  face   render inside a feathered ellipse around the face, original outside.
  square original SadTalker behaviour (whole crop square, cv2.seamlessClone).
"""
import argparse
import subprocess
import sys

import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('photo')
    ap.add_argument('npz')
    ap.add_argument('out')
    ap.add_argument('--mode', default='delta', choices=['delta', 'face', 'square'])
    ap.add_argument('--audio', default=None)
    ap.add_argument('--crf', default='18')
    ap.add_argument('--fps', default='25')
    ap.add_argument('--lo', type=float, default=6.0, help='delta mode: diff (0-255) where blending starts')
    ap.add_argument('--hi', type=float, default=18.0, help='delta mode: diff where render fully replaces')
    ap.add_argument('--dump-mask', default=None, help='write max mask over all frames to this png')
    a = ap.parse_args()

    full = cv2.imread(a.photo)  # BGR
    H, W = full.shape[:2]
    d = np.load(a.npz)
    frames = d['frames']  # N,s,s,3 RGB uint8
    clx, cly, crx, cry = [int(v) for v in d['crop_box']]
    lx, ly, rx, ry = [int(v) for v in d['quad']]
    oy1, oy2, ox1, ox2 = cly + ly, cly + ry, clx + lx, clx + rx
    bw, bh = ox2 - ox1, oy2 - oy1
    # clip box to image
    x0, y0, x1, y1 = max(ox1, 0), max(oy1, 0), min(ox2, W), min(oy2, H)
    print(f'{len(frames)} frames, paste box x{ox1}-{ox2} y{oy1}-{oy2} ({bw}x{bh}), photo {W}x{H}', file=sys.stderr)

    def up(fr):
        p = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_RGB2BGR), (bw, bh), interpolation=cv2.INTER_CUBIC)
        return p[y0 - oy1:y1 - oy1, x0 - ox1:x1 - ox1]

    region = full[y0:y1, x0:x1].astype(np.float32)
    rh, rw = region.shape[:2]

    # ellipse prior: inner face area of the crop square (keeps hair/background/ears from the original)
    yy, xx = np.mgrid[0:rh, 0:rw].astype(np.float32)
    cx, cy = (ox1 + bw * 0.5) - x0, (oy1 + bh * 0.52) - y0
    ell = ((xx - cx) / (bw * 0.30)) ** 2 + ((yy - cy) / (bh * 0.36)) ** 2
    face_mask = np.clip((1.15 - ell) / 0.3, 0, 1)
    face_mask = cv2.GaussianBlur(face_mask, (0, 0), bw * 0.02)

    med = None
    if a.mode == 'delta':
        med = np.median(frames, axis=0).astype(np.uint8)
        med_up = up(med).astype(np.float32)

    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
           '-s', f'{W}x{H}', '-r', a.fps, '-i', '-']
    if a.audio:
        cmd += ['-i', a.audio, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-shortest']
    cmd += ['-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:v', 'libx264', '-preset', 'medium', '-crf', a.crf,
            '-pix_fmt', 'yuv420p', a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    maxmask = np.zeros((rh, rw), np.float32)
    for fr in frames:
        out = full.copy()
        if a.mode == 'square':
            p = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_RGB2BGR), (bw, bh))
            mask = 255 * np.ones(p.shape, p.dtype)
            out = cv2.seamlessClone(p, full, mask, ((ox1 + ox2) // 2, (oy1 + oy2) // 2), cv2.NORMAL_CLONE)
        else:
            r = up(fr).astype(np.float32)
            if a.mode == 'face':
                m = face_mask
            else:
                diff = np.abs(r - med_up).max(axis=2)
                diff = cv2.GaussianBlur(diff, (0, 0), bw * 0.006)
                m = np.clip((diff - a.lo) / (a.hi - a.lo), 0, 1)
                m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(bw * 0.02) | 1,) * 2))
                m = cv2.GaussianBlur(m, (0, 0), bw * 0.012) * face_mask
            maxmask = np.maximum(maxmask, m)
            blended = region * (1 - m[..., None]) + r * m[..., None]
            out[y0:y1, x0:x1] = np.clip(blended + 0.5, 0, 255).astype(np.uint8)
        proc.stdin.write(out.tobytes())
    proc.stdin.close()
    proc.wait()
    if a.dump_mask:
        cv2.imwrite(a.dump_mask, (maxmask * 255).astype(np.uint8))
    print('wrote', a.out, file=sys.stderr)


if __name__ == '__main__':
    main()
