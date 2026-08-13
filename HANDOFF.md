# Handoff — amber CRT "pinch" loop generator

**Date:** 2026-08-12
**Status:** Working and delivering finished files. No known bugs.

A procedural recreation of an amber CRT displaying a test grid, with a band of
collapsed horizontal scan amplitude — a "pinch" — rolling slowly up the screen,
as happens when ripple gets into the rail feeding the horizontal output stage.
Built from a reference photo of a real faulty monitor, for use as B-roll, title
cards and transitions in YouTube videos.

---

## 1. Where things are

> **The code does not live in this directory.** This doc is the only thing here.

| What | Where |
|---|---|
| Renderer + README | `~/wip/questionable_commands/crt_pinch/` |
| Script | `~/wip/questionable_commands/crt_pinch/crt_pinch.py` (~19 KB, single file) |
| Full flag reference | `~/wip/questionable_commands/crt_pinch/README.md` |

Two loose ends worth deciding early:

- The renderer sits **inside the `questionable_commands` git repo, untracked**,
  along with ~190 MB of rendered video. Either move it out (here, perhaps), or
  gitignore the media before anyone runs `git add`.
- **There is no committed venv.** The one used to produce the current files was
  in a temporary session scratchpad and is gone. Recreate it — see below.

## 2. Quick start

```sh
cd ~/wip/questionable_commands/crt_pinch
python3 -m venv venv && ./venv/bin/pip install numpy imageio-ffmpeg

./venv/bin/python crt_pinch.py -o out.mp4          # ~2-5 min at 1080p60
./venv/bin/python crt_pinch.py --still look.png --still-phase 0.35   # ~2 s
```

`imageio-ffmpeg` ships its own ffmpeg binary, so **nothing is installed
system-wide** and no Homebrew ffmpeg is needed. Get the binary path with:

```sh
./venv/bin/python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
```

Iterate on `--still`, not on video. A still is ~2 s; a 1080p60 loop is minutes.

## 3. How it works

Nothing is warped from a source bitmap — every pixel is evaluated analytically,
so output is sharp at any resolution. Per frame:

1. Screen pixels map through a mild **pincushion** into tube coordinates.
2. The **fault profile** `f` — an oscillation under a bi-gaussian window — is
   evaluated at each pixel's distance from the travelling band.
3. Horizontal scan gain becomes `1 - pinch·f`, so signal-space `u = x / gain`.
4. Grid lines, and text, are evaluated in that signal space.
5. Scanlines, beam-current bloom, halation, vignette, glass aperture, grain.

Because the text is sampled at the *same warped coordinates* as the grid, the
fault mangles the characters exactly as it mangles the grid. That is the whole
point of doing it here rather than as an overlay in an editor.

## 4. Decisions that are load-bearing

Read this section before changing the model. Each of these was a wrong turn
first, and the symptom is not obvious from the code.

**The grid is finite, and that is essential.** With an infinite grid, narrowing
the scan drags *extra* columns in from off-screen — the opposite of a pinch.
With a finite grid, the picture's own left/right edges pull inward, which is
what the reference photo shows.

**The tube overscans** (`--overscan 1.25`). The lit raster is deliberately
larger than the glass. Without it, the pinch pulls the raster edge into view and
takes black bites out of the sides of the picture. Real sets overscan; so does
this.

**Line width is converted to screen space** before it becomes brightness. Skip
that and traces get thinner inside the compressed band, which reads as a focus
error rather than a geometry error.

**The fault profile must stay C¹ continuous.** An earlier attempt used a hard
one-sided step for a sharp leading edge; it *tears* the grid — a visible
sideways jump, like a roll bar, not a pinch. The bi-gaussian window
(`--asym`, sharp above / long tail below) gives the asymmetry without the tear.

**The FFT blur must be zero-padded.** `gaussian_blur` works on a ¼-scale copy;
unpadded, the FFT wraps glow from one edge onto the opposite one and paints a
bright rim around the frame.

**A bright rim at the screen edge may be an illusion.** Measured, the margin is
*darker* (57) than the interior (91) — it only looks lighter against the black
bezel. Measure pixels before chasing this one; it cost time already.

**Loops are seamless by construction.** The fault profile is made exactly
periodic by summing wrapped copies (`shift in (-2, 0, 2)`), so it is periodic
over one screen height. Verified: `frame(0)` and `frame(1.0)` agree to within
rounding, and the wrap-around step matches a normal inter-frame step. **Anything
time-varying you add must divide evenly into the loop** or you break this. The
cursor already does — `--cursor-hz` snaps to a whole number of blinks.

**`--direction 1` is up.** The sign was wrong once and is easy to get wrong
again; the band position is `TY = -2·phase (mod 2)`.

## 5. The font

A 5×7 glyph in an 8×8 cell, one byte per scan row, bit `0x80` leftmost — the
layout a character-generator ROM of the period used. It is a table in the
script, not a font file, so there is nothing to install and it renders as crisp
phosphor blocks at any resolution. Full printable ASCII, descenders on `g j p q y`.

It was authored by hand, so **proof it after touching a glyph** — one bad `3`
already got through and was caught this way:

```sh
./venv/bin/python crt_pinch.py --still proof.png --no-grid --text-size 0.058 \
  --text '!"#$%&'"'"'()*+,-./0123456789:;<=>?\n@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_\n`abcdefghijklmnopqrstuvwxyz{|}~'
```

Glyph lookup is nearest-neighbour. At 1080p each font pixel is many screen
pixels and the bloom hides the edges, but at small output sizes warped glyph
edges may show stair-stepping. Supersampling the text mask is the fix if it
ever matters.

## 6. Rendered deliverables

In `~/wip/questionable_commands/crt_pinch/`. All are 16 s seamless loops.

| File | Notes |
|---|---|
| `crt_pinch_1920x1080.mp4` | 48 MB, 1080p60, picture fills the 16:9 frame |
| `crt_pinch_2560x1440.mp4` | 84 MB, 1440p60 — survives YouTube's re-encode better |
| `crt_pinch_4x3_1920x1080.mp4` | 44 MB, 4:3 tube pillarboxed in a 1080p60 frame |
| `crt_pinch_960x540.gif` | 12 MB, 12 fps |
| `crt_pinch_sample.gif` | 8.1 MB, 12 fps, reads "Sample..." — built to a <10 MB cap |

### GIF sizing

**Render GIFs from their own grain-free pass** (`--grain 0`) at the target
resolution. Film grain changes every pixel every frame and destroys GIF
inter-frame compression — it was worth 60 MB on the first attempt. Also scale
`--scanlines` to pixel height (`140` at 540p ≈ `280` at 1080p), otherwise
downscaling moirés the raster.

Measured size ladder at 960×540, 16 s:

| Variant | Size |
|---|---|
| 64 colours, 12 fps | 11 MB |
| 32 colours, 12 fps | 8.1 MB ← shipped |
| 24 colours, 12 fps | 7.1 MB |
| 32 colours, 10 fps | 7.0 MB |

32 colours costs nothing visible — the image is one hue on grey. To go much
smaller, drop resolution and **re-render** rather than downscale.

## 7. Feature flags added after the first cut

- `--text`, `--text-size/-x/-y/-align/-bright`, `--text-box`, `--text-margin`,
  `--no-grid`, `--cursor`, `--cursor-hz` — title screens and transitions.
- `--phosphor amber|green` — a table at the top of the script; each entry
  carries glass, trace, over-drive shift and halation tint so a tube changes as
  a whole. Adding an entry adds a choice automatically.
- `--square-corners` — fills the frame corners. Note it deliberately keeps the
  4:3 side bars under `--pillarbox`, since one mask does both jobs. Pair with
  `--inset 0` (and `--vignette 0`) for a genuinely edge-to-edge frame.

## 8. Open items

Nothing is blocking. Candidates, roughly in order of value:

1. **Decide where this lives** and keep the rendered media out of git.
2. **Commit a venv recipe or `requirements.txt`** — currently only prose in the
   README (`numpy`, `imageio-ffmpeg`; Pillow only for ad-hoc pixel inspection).
3. **A P4 paper-white phosphor** is a three-line table entry if wanted.
4. **Supersample the text mask** if small-format output shows glyph jaggies.
5. **No automated tests.** The loop-seamlessness check and the font proof sheet
   are both one-liners and are the two things worth pinning down if this grows.
6. The reference photo's fault is slightly deeper than the shipped default;
   `--pinch 0.10 --band 0.26` is closer to it if a more dramatic look is wanted.
