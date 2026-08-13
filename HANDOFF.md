# Open items

Everything else that used to be in this file — how the renderer works, the
flags, the font, the decisions that are load-bearing if you change the model —
now lives in [`README.md`](README.md).

Nothing here is blocking. Roughly in order of value:

1. **Pin the dependencies.** Install is documented in the README as prose
   (`numpy`, `imageio-ffmpeg`; Pillow only for ad-hoc pixel inspection), with
   no versions. A `requirements.txt` would make renders reproducible — the
   current output was made with numpy 2.5.2.
2. **A P4 paper-white phosphor** is a three-line entry in the `PHOSPHORS`
   table if it is wanted.
3. **Supersample the text mask** if small-format output shows glyph jaggies.
   Lookup is nearest-neighbour; at 1080p each font pixel covers many screen
   pixels and the bloom hides the edges, but warped glyph edges may stair-step
   at small sizes.
4. **No automated tests.** The two worth pinning down if this grows are the
   loop-seamlessness check — `frame(0)` and `frame(1.0)` must agree to within
   rounding, and the wrap-around step must match a normal inter-frame step —
   and the font proof sheet. Both are one-liners today.
5. **The reference photo's fault is slightly deeper than the shipped default.**
   `--pinch 0.10 --band 0.26` is closer to it, if a more dramatic look is
   wanted.
