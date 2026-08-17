#!/usr/bin/env python3
"""
Amber CRT test-grid with a travelling "pinch" — a horizontal width-modulation
band that slowly rolls up the screen, the way ripple on a failing power supply
modulates scan amplitude.

Everything is drawn analytically (no source bitmap is warped), so the grid
stays crisp at any resolution. The animation loops seamlessly: the fault
profile is periodic over exactly one screen height.

  ./venv/bin/python crt_pinch.py -o crt_pinch.mp4
  ./venv/bin/python crt_pinch.py --still look.png --still-phase 0.5
"""

import argparse
import subprocess
import sys

import numpy as np

# ----------------------------------------------------------------- appearance

# Per-phosphor colour: the unlit glass, the trace itself, the shift added where
# traces cross and drive the beam past full (towards white, as a real tube does),
# and the tint of the halation around them.

PHOSPHORS = {
    "amber": dict(                          # P3-ish, the amber monitor look
        bg=(0.400, 0.425, 0.405),
        line=(1.000, 0.545, 0.130),
        hot=(0.000, 0.260, 0.430),
        halo=(1.000, 0.430, 0.090),
    ),
    "green": dict(                          # P31-ish, the yellow-green terminal
        bg=(0.375, 0.425, 0.390),
        line=(0.330, 1.000, 0.400),
        hot=(0.480, 0.000, 0.360),
        halo=(0.240, 1.000, 0.330),
    ),
}


# ----------------------------------------------------------------- the font
#
# A 5x7 glyph in an 8x8 cell, the way a character-generator ROM of the period
# held it: one byte per scan row, bit 0x80 leftmost. Advance is 6 px across and
# 8 px down, so the spare columns and the bottom row become the gap between
# characters. Rows 7 carries descenders on g j p q y.

FONT_W, FONT_H, GLYPH_W = 6, 8, 5

FONT = {
    " ": "00 00 00 00 00 00 00 00", "!": "20 20 20 20 20 00 20 00",
    '"': "50 50 50 00 00 00 00 00", "#": "50 50 F8 50 F8 50 50 00",
    "$": "20 78 A0 70 28 F0 20 00", "%": "C0 C8 10 20 40 98 18 00",
    "&": "40 A0 A0 40 A8 90 68 00", "'": "20 20 20 00 00 00 00 00",
    "(": "10 20 40 40 40 20 10 00", ")": "40 20 10 10 10 20 40 00",
    "*": "00 20 A8 70 A8 20 00 00", "+": "00 20 20 F8 20 20 00 00",
    ",": "00 00 00 00 00 20 20 40", "-": "00 00 00 F8 00 00 00 00",
    ".": "00 00 00 00 00 60 60 00", "/": "08 08 10 20 40 80 80 00",
    "0": "70 88 98 A8 C8 88 70 00", "1": "20 60 20 20 20 20 70 00",
    "2": "70 88 08 10 20 40 F8 00", "3": "70 88 08 30 08 88 70 00",
    "4": "10 30 50 90 F8 10 10 00", "5": "F8 80 F0 08 08 88 70 00",
    "6": "30 40 80 F0 88 88 70 00", "7": "F8 08 10 20 40 40 40 00",
    "8": "70 88 88 70 88 88 70 00", "9": "70 88 88 78 08 10 60 00",
    ":": "00 60 60 00 60 60 00 00", ";": "00 60 60 00 60 20 40 00",
    "<": "08 10 20 40 20 10 08 00", "=": "00 00 F8 00 F8 00 00 00",
    ">": "40 20 10 08 10 20 40 00", "?": "70 88 08 10 20 00 20 00",
    "@": "70 88 B8 A8 B8 80 78 00", "A": "20 50 88 F8 88 88 88 00",
    "B": "F0 88 88 F0 88 88 F0 00", "C": "70 88 80 80 80 88 70 00",
    "D": "E0 90 88 88 88 90 E0 00", "E": "F8 80 80 F0 80 80 F8 00",
    "F": "F8 80 80 F0 80 80 80 00", "G": "70 88 80 B8 88 88 78 00",
    "H": "88 88 88 F8 88 88 88 00", "I": "70 20 20 20 20 20 70 00",
    "J": "38 10 10 10 10 90 60 00", "K": "88 90 A0 C0 A0 90 88 00",
    "L": "80 80 80 80 80 80 F8 00", "M": "88 D8 A8 A8 88 88 88 00",
    "N": "88 C8 A8 98 88 88 88 00", "O": "70 88 88 88 88 88 70 00",
    "P": "F0 88 88 F0 80 80 80 00", "Q": "70 88 88 88 A8 90 68 00",
    "R": "F0 88 88 F0 A0 90 88 00", "S": "78 80 80 70 08 08 F0 00",
    "T": "F8 20 20 20 20 20 20 00", "U": "88 88 88 88 88 88 70 00",
    "V": "88 88 88 88 88 50 20 00", "W": "88 88 88 A8 A8 D8 88 00",
    "X": "88 88 50 20 50 88 88 00", "Y": "88 88 50 20 20 20 20 00",
    "Z": "F8 08 10 20 40 80 F8 00", "[": "70 40 40 40 40 40 70 00",
    "\\": "80 80 40 20 10 08 08 00", "]": "70 10 10 10 10 10 70 00",
    "^": "20 50 88 00 00 00 00 00", "_": "00 00 00 00 00 00 F8 00",
    "`": "40 20 10 00 00 00 00 00", "a": "00 00 70 08 78 88 78 00",
    "b": "80 80 F0 88 88 88 F0 00", "c": "00 00 70 88 80 88 70 00",
    "d": "08 08 78 88 88 88 78 00", "e": "00 00 70 88 F8 80 70 00",
    "f": "30 40 40 E0 40 40 40 00", "g": "00 00 78 88 88 78 08 70",
    "h": "80 80 F0 88 88 88 88 00", "i": "20 00 60 20 20 20 70 00",
    "j": "10 00 30 10 10 10 90 60", "k": "80 80 90 A0 C0 A0 90 00",
    "l": "60 20 20 20 20 20 70 00", "m": "00 00 D0 A8 A8 A8 A8 00",
    "n": "00 00 F0 88 88 88 88 00", "o": "00 00 70 88 88 88 70 00",
    "p": "00 00 F0 88 88 F0 80 80", "q": "00 00 78 88 88 78 08 08",
    "r": "00 00 B0 C8 80 80 80 00", "s": "00 00 78 80 70 08 F0 00",
    "t": "40 40 E0 40 40 48 30 00", "u": "00 00 88 88 88 98 68 00",
    "v": "00 00 88 88 88 50 20 00", "w": "00 00 88 A8 A8 A8 50 00",
    "x": "00 00 88 50 20 50 88 00", "y": "00 00 88 88 88 78 08 70",
    "z": "00 00 F8 10 20 40 F8 00", "{": "18 20 20 40 20 20 18 00",
    "|": "20 20 20 20 20 20 20 00", "}": "C0 20 20 10 20 20 C0 00",
    "~": "00 00 68 B0 00 00 00 00",
}


def _glyph_table():
    """FONT unpacked to a (128, FONT_H, FONT_W) bit array, indexed by ord()."""
    table = np.zeros((128, FONT_H, FONT_W), np.uint8)
    for ch, rows in FONT.items():
        octets = [int(b, 16) for b in rows.split()]
        assert len(octets) == FONT_H, ch
        for y, byte in enumerate(octets):
            for x in range(FONT_W):
                table[ord(ch), y, x] = (byte >> (7 - x)) & 1
    return table


GLYPHS = _glyph_table()


def typeset(text, align):
    """Lay text out into a bit page of shape (lines*FONT_H, cols*FONT_W)."""
    lines = text.replace("\\n", "\n").split("\n")
    cols = max(len(ln) for ln in lines)
    if align == "center":
        lines = [ln.center(cols) for ln in lines]
    else:
        lines = [ln.ljust(cols) for ln in lines]

    codes = np.array([[min(ord(c), 127) for c in ln] for ln in lines])
    page = GLYPHS[codes]                          # (rows, cols, FONT_H, FONT_W)
    return page.transpose(0, 2, 1, 3).reshape(len(lines) * FONT_H, cols * FONT_W)


# --------------------------------------------------------------------- text
#
# --text may be repeated. Each occurrence starts a block, and any text option
# after it belongs to that block, so blocks can differ in size and position:
#
#   --text 'TITLE' --text-size 0.10 --text-y -0.23  --text '$?' --text-size 0.18
#
# Options given before the first --text set the default for every block, which
# is what makes the single-block spelling work whatever order it is written in.

TEXT_DEFAULTS = dict(text_size=0.075, text_x=0.0, text_y=0.0, text_align="center",
                     text_bright=1.0, text_box=False, text_margin=0.6,
                     cursor=False, cursor_hz=1.7)


class TextOpt(argparse.Action):
    """Record a text option, keeping the order it was given in."""

    def __call__(self, parser, ns, values, option_string=None):
        ns.text_ops = getattr(ns, "text_ops", []) + [(self.dest, values)]


class TextFlag(TextOpt):
    """The same, for the text options that take no value."""

    def __init__(self, *args, **kw):
        super().__init__(*args, nargs=0, **kw)

    def __call__(self, parser, ns, values, option_string=None):
        super().__call__(parser, ns, True, option_string)


def text_specs(cfg):
    """Split the recorded options into one settings dict per block."""
    base, specs = dict(TEXT_DEFAULTS), []
    for dest, value in getattr(cfg, "text_ops", None) or []:
        if dest == "text":
            specs.append(dict(base, text=value))
        elif specs:
            specs[-1][dest] = value            # applies to the block above it
        else:
            base[dest] = value                 # before any --text: a global default
    return [s for s in specs if s["text"]]


class TextBlock:
    """One run of text, laid out in signal space so the fault warps it."""

    def __init__(self, spec, period):
        self.x, self.y = spec["text_x"], spec["text_y"]
        self.align, self.bright = spec["text_align"], spec["text_bright"]
        self.box, self.margin = spec["text_box"], spec["text_margin"]
        self.cursor = spec["cursor"]

        self.page = typeset(spec["text"], self.align)
        rows, cols = (n // f for n, f in zip(self.page.shape, (FONT_H, FONT_W)))
        self.cell_v = spec["text_size"] * 2.0
        self.cell_u = self.cell_v * FONT_W / FONT_H   # square font pixels
        self.tw = cols * self.cell_u
        self.th = rows * self.cell_v
        self.u0 = self.x - self.tw / 2.0
        self.v0 = self.y - self.th / 2.0

        # a block cursor sitting just past the end of the last line
        last = len(spec["text"].replace("\\n", "\n").split("\n")[-1])
        end = (cols + last) / 2.0 if self.align == "center" else last
        self.cur_u = self.u0 + (end + GLYPH_W / 2.0 / FONT_W) * self.cell_u
        self.cur_v = self.v0 + self.th - self.cell_v * (1.0 - 3.5 / FONT_H)
        self.blinks = max(1, round(period * spec["cursor_hz"]))

    def clear(self, u, v, gain, w):
        """How much of the grid to take out behind this block, 0..1."""
        m = self.margin * self.cell_v
        return (soft_inside(self.tw / 2 + m, u - self.x, w / gain)
                * soft_inside(self.th / 2 + m, v - self.y, w))

    def sample(self, u, v, phase):
        """Nearest-neighbour lookup into the glyph page, in signal space."""
        ph, pw = self.page.shape
        ix = np.floor((u - self.u0) / self.cell_u * FONT_W).astype(np.int32)
        iy = np.floor((v - self.v0) / self.cell_v * FONT_H).astype(np.int32)
        on = (ix >= 0) & (ix < pw) & (iy >= 0) & (iy < ph)
        mask = self.page[np.clip(iy, 0, ph - 1), np.clip(ix, 0, pw - 1)] * on

        if self.cursor and int(phase * self.blinks * 2.0) % 2 == 0:
            hu = GLYPH_W / 2.0 * self.cell_u / FONT_W
            hv = 3.5 * self.cell_v / FONT_H
            mask = np.maximum(mask, (np.abs(u - self.cur_u) < hu)
                              & (np.abs(v - self.cur_v) < hv))
        return mask.astype(np.float32)


def gaussian_blur(a, sigma):
    """FFT gaussian on a 1/4-scale copy, then upsampled. Cheap halation."""
    h, w = a.shape
    s = 4
    small = a[: h // s * s, : w // s * s].reshape(h // s, s, w // s, s).mean((1, 3))

    # zero-pad by 3 sigma, otherwise the FFT wraps the glow onto the far edge
    pad = max(1, int(np.ceil(3.0 * sigma / s)))
    small = np.pad(small, pad)
    sh, sw = small.shape
    fy = np.fft.fftfreq(sh)[:, None]
    fx = np.fft.rfftfreq(sw)[None, :]
    k = np.exp(-2.0 * (np.pi * sigma / s) ** 2 * (fy**2 + fx**2))
    small = np.fft.irfft2(np.fft.rfft2(small) * k, s=(sh, sw))[pad:-pad, pad:-pad]

    up = np.repeat(np.repeat(small, s, 0), s, 1)
    if up.shape != a.shape:                       # pad the ragged edge
        up = np.pad(up, ((0, h - up.shape[0]), (0, w - up.shape[1])), mode="edge")
    return up.astype(np.float32)


def fault_profile(t, sigma, wavelength, asym):
    """
    Shape of the disturbance, as a function of distance down the screen from
    its centre: an oscillation under a bi-gaussian window, so the rail comes
    off the disturbance faster than it settles back — sharp above, ringing
    tail below. asym=1 gives a symmetric bump.

    Summing wrapped copies makes it exactly periodic over t in [-1, 1), which
    is what lets the animation loop seamlessly.
    """
    f = np.zeros_like(t)
    for shift in (-2.0, 0.0, 2.0):               # wrap-around copies -> seamless
        tt = t + shift
        s = np.where(tt >= 0.0, sigma, sigma * asym)
        f += np.exp(-((tt / s) ** 2)) * np.cos(2.0 * np.pi * tt / wavelength)
    return f


def soft_inside(limit, coord, edge):
    """1 where |coord| < limit, fading to 0 over `edge`. Cheap anti-aliasing."""
    return np.clip((limit - np.abs(coord)) / edge + 0.5, 0.0, 1.0)


class Tube:
    """Static per-resolution geometry, built once and reused for every frame."""

    def __init__(self, cfg):
        self.cfg = cfg
        W, H = cfg.width, cfg.height
        asp = W / H
        half = 4 / 3 if cfg.pillarbox else asp   # half-width of the visible screen

        # screen-space normalised coords: y in [-1,1], x in [-asp,asp] (square cells)
        sx = ((np.arange(W, dtype=np.float32) + 0.5) / W * 2.0 - 1.0) * asp
        sy = (np.arange(H, dtype=np.float32) + 0.5) / H * 2.0 - 1.0
        SX, SY = np.meshgrid(sx, sy)

        # tube geometry: gentle pincushion, so the raster bows the way glass does
        self.TX = (SX * (1.0 + cfg.pincushion * SY**2)).astype(np.float32)
        self.TY = (SY * (1.0 + cfg.pincushion * (SX / half) ** 2)).astype(np.float32)

        # glass: the screen aperture, everything outside it is bezel-black. Square
        # corners keep the picture in the frame corners for compositing; the 4:3
        # side bars are part of the aperture either way.
        px = 2.0 / H
        hu, hv = half - cfg.inset, 1.0 - cfg.inset
        if cfg.square_corners:
            self.glass = (soft_inside(hu, SX, px) * soft_inside(hv, SY, px))
        else:
            n = cfg.corner
            se = np.abs(SX / hu) ** n + np.abs(SY / hv) ** n
            self.glass = np.clip((1.0 - se) / (n * px) + 0.5, 0.0, 1.0)
        self.glass = self.glass.astype(np.float32)

        r = np.sqrt((SX / half) ** 2 + SY**2)
        self.shade = (1.0 - cfg.vignette * np.clip(r, 0, 1.6) ** 2.4).astype(np.float32)

        # the pattern: a finite grid of square cells, centred, with a border line
        self.pitch = 2.0 * cfg.fill / cfg.rows
        cols = cfg.cols or int(round(2.0 * half * cfg.fill / self.pitch))
        cols += cols % 2                          # even -> lines land on the border
        self.gu = cols * self.pitch / 2.0         # grid half-extent, signal space
        self.gv = cfg.rows * self.pitch / 2.0

        # the tube overscans, so the lit grey area runs off the glass on every side
        self.ru = half * cfg.overscan
        self.rv = cfg.overscan

        self.w_core = cfg.line_px * px
        self.scan_period = 2.0 / cfg.scanlines
        self.rng = np.random.default_rng(7)

        tint = PHOSPHORS[cfg.phosphor]
        self.bg, self.line, self.hot, self.halo = (
            np.array(tint[k], np.float32) for k in ("bg", "line", "hot", "halo"))

        # text, laid out in signal space so the fault warps it like everything else
        self.blocks = [TextBlock(s, cfg.period) for s in text_specs(cfg)]

    def frame(self, phase):
        """Render one frame; phase 0..1 is one full traverse of the screen."""
        cfg, pitch, w = self.cfg, self.pitch, self.w_core

        # travelling fault: +direction moves the band up the screen. --start slides
        # the whole cycle along, which decides where the band is sitting on the
        # first frame; the loop stays seamless because the shift is constant.
        t = np.mod(self.TY + 1.0
                   + 2.0 * (phase + cfg.start) * cfg.direction, 2.0) - 1.0
        f = fault_profile(t, cfg.band, cfg.ring, cfg.asym)

        gain = 1.0 - cfg.pinch * f               # horizontal scan amplitude
        u = self.TX / gain                       # signal-space coords
        v = self.TY - cfg.vshift * f

        # distance to the nearest grid line, expressed in screen space
        du = np.abs(np.mod(u + pitch / 2, pitch) - pitch / 2) * gain
        dv = np.abs(np.mod(v + pitch / 2, pitch) - pitch / 2)

        # a line only exists inside the pattern; the pattern narrows with the scan
        in_u = soft_inside(self.gu + w, u, w / gain)
        in_v = soft_inside(self.gv + w, v, w)
        inten = (np.exp(-((du / w) ** 2)) + np.exp(-((dv / w) ** 2))) * in_u * in_v
        if not cfg.grid:
            inten *= 0.0

        # every box clears before any text is laid down, so one block's box can
        # never rub out a neighbouring block's characters
        for b in self.blocks:
            if b.box:                            # clear the grid out behind the text
                inten *= 1.0 - b.clear(u, v, gain, w)
        for b in self.blocks:
            inten += b.sample(u, v, phase) * b.bright

        # raster structure: the beam only exists on scan lines
        scan = 0.5 + 0.5 * np.cos(2.0 * np.pi * v / self.scan_period)
        inten *= 1.0 - cfg.scan_depth * 0.7 * (1.0 - scan)

        # beam current rises slightly where the scan is compressed
        inten *= 1.0 + 0.20 * np.clip(f, 0, None)

        # unlit outside the raster, so the pinch pulls dark edges in at the sides
        lit = soft_inside(self.ru, u, w / gain) * soft_inside(self.rv, v, w)
        inten *= lit

        core = np.clip(inten, 0.0, 1.0).astype(np.float32)
        hot = np.clip(inten - 1.0, 0.0, 1.0).astype(np.float32)

        halo = (gaussian_blur(core, cfg.glow_px) * cfg.glow
                + gaussian_blur(core, cfg.glow_px * 4.0) * cfg.glow * 0.9)

        bg = lit * (1.0 - cfg.scan_depth * 0.55 * (1.0 - scan))
        img = (self.bg * bg[:, :, None]
               + self.line * core[:, :, None]
               + self.hot * hot[:, :, None]
               + self.halo * halo[:, :, None])

        img *= (self.shade * self.glass)[:, :, None]
        img += self.rng.normal(0.0, cfg.grain, (cfg.height, cfg.width, 1))

        return np.clip(img * 255.0, 0, 255).astype(np.uint8)


def encode(cfg):
    tube = Tube(cfg)
    frames = int(round(cfg.fps * cfg.period))
    ff = subprocess.Popen(
        [cfg.ffmpeg, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{cfg.width}x{cfg.height}", "-r", str(cfg.fps), "-i", "-",
         "-an", "-c:v", "libx264", "-preset", "slow", "-crf", str(cfg.crf),
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", cfg.output],
        stdin=subprocess.PIPE,
    )
    for n in range(frames):
        ff.stdin.write(tube.frame(n / frames).tobytes())
        if n % 20 == 0:
            print(f"\r  frame {n + 1}/{frames}", end="", file=sys.stderr, flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"\r  wrote {cfg.output} ({frames} frames, {cfg.period:g}s loop)   ",
          file=sys.stderr)


def still(cfg):
    tube = Tube(cfg)
    ff = subprocess.Popen(
        [cfg.ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-s", f"{cfg.width}x{cfg.height}", "-i", "-",
         "-frames:v", "1", cfg.still],
        stdin=subprocess.PIPE,
    )
    ff.stdin.write(tube.frame(cfg.still_phase).tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"  wrote {cfg.still}", file=sys.stderr)


def main():
    import imageio_ffmpeg

    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-o", "--output", default="crt_pinch.mp4")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--period", type=float, default=16.0,
                   help="seconds to travel one screen height (= seamless loop length)")
    p.add_argument("--direction", type=float, default=1.0, help="1 = up, -1 = down")
    p.add_argument("--start", type=float, default=0.0,
                   help="how far into the cycle the loop begins, 0..1. 0 puts the "
                        "band across the middle of the screen on the first frame, "
                        "0.5 puts it at the top and bottom edges (default 0)")
    p.add_argument("--phosphor", choices=tuple(PHOSPHORS), default="amber",
                   help="tube colour")
    p.add_argument("--rows", type=int, default=12, help="grid rows top to bottom")
    p.add_argument("--cols", type=int, default=0, help="grid columns (0 = fill the width)")
    p.add_argument("--fill", type=float, default=0.93, help="grid height / screen height")
    p.add_argument("--inset", type=float, default=0.012, help="glass edge inset")
    p.add_argument("--corner", type=float, default=8.0, help="screen corner squareness")
    p.add_argument("--square-corners", action="store_true",
                   help="no rounded black corners; picture reaches the frame corners")
    p.add_argument("--overscan", type=float, default=1.25, help="raster size / screen size")
    p.add_argument("--pinch", type=float, default=0.075, help="width-modulation depth")
    p.add_argument("--band", type=float, default=0.22, help="height of the disturbance")
    p.add_argument("--ring", type=float, default=1.50, help="ringing wavelength")
    p.add_argument("--asym", type=float, default=0.55,
                   help="sharpness above the band vs below (1 = symmetric)")
    p.add_argument("--vshift", type=float, default=0.022, help="vertical pull in the band")
    p.add_argument("--pincushion", type=float, default=0.022)
    p.add_argument("--line-px", type=float, default=1.55)
    p.add_argument("--glow", type=float, default=0.42)
    p.add_argument("--glow-px", type=float, default=6.0)
    p.add_argument("--scanlines", type=int, default=280)
    p.add_argument("--scan-depth", type=float, default=0.40)
    p.add_argument("--vignette", type=float, default=0.22)
    p.add_argument("--grain", type=float, default=0.010)
    p.add_argument("--text", action=TextOpt,
                   help=r"text to display; \n splits lines. Repeat it for more "
                        "blocks — the text options below apply to whichever "
                        "--text precedes them")
    p.add_argument("--text-size", type=float, action=TextOpt,
                   help="character cell height as a fraction of screen height "
                        "(default 0.075)")
    p.add_argument("--text-x", type=float, action=TextOpt,
                   help="offset right, in [-1,1] (default 0)")
    p.add_argument("--text-y", type=float, action=TextOpt,
                   help="offset down, in [-1,1] (default 0)")
    p.add_argument("--text-align", choices=("center", "left"), action=TextOpt,
                   help="default center")
    p.add_argument("--text-bright", type=float, action=TextOpt, help="default 1.0")
    p.add_argument("--text-box", action=TextFlag,
                   help="clear the grid out behind the text")
    p.add_argument("--text-margin", type=float, action=TextOpt,
                   help="--text-box padding, in character cells (default 0.6)")
    p.add_argument("--no-grid", dest="grid", action="store_false",
                   help="text only, on a bare raster")
    p.add_argument("--cursor", action=TextFlag, help="blinking block cursor")
    p.add_argument("--cursor-hz", type=float, action=TextOpt, help="default 1.7")
    p.add_argument("--crf", type=int, default=14)
    p.add_argument("--pillarbox", action="store_true", help="4:3 picture, black sides")
    p.add_argument("--still", help="render a single PNG instead of a video")
    p.add_argument("--still-phase", type=float, default=0.5)
    cfg = p.parse_args()
    cfg.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    still(cfg) if cfg.still else encode(cfg)


if __name__ == "__main__":
    main()
