# Vortex Infini

A first-person browser game: fly through a procedurally generated, endless
energy vortex tunnel through space. Steer with the mouse or ZQSD/arrow keys,
hold Shift to boost, thread the glowing gates, dodge the walls, and collect
energy orbs as the tunnel gets faster and tighter forever.

Built with [Three.js](https://threejs.org/) (vendored locally in
`src/vendor/three`, no CDN/network dependency) plus a custom shader-based
tunnel, bloom/chromatic-aberration/vignette post-processing, and a
WebAudio-synthesized soundtrack — no external assets required.

## Run it

The game must be served over HTTP — opening `index.html` directly by
double-clicking it (`file://…`) won't work, since browsers block ES module
imports on that protocol.

**Windows:** double-click `Lancer-Vortex-Infini.bat`. It starts a local
server and opens the game in your browser automatically. Requires
[Python](https://www.python.org/downloads/) (check "Add python.exe to PATH"
during install).

**Any other static file server works too**, e.g.:

```
python3 -m http.server 8000
```

Then open `http://localhost:8000/`.

---

Made with Claude
