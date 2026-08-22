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

Any static file server works, e.g.:

```
python3 -m http.server 8000
```

Then open `http://localhost:8000/`.

---

Made with Claude
