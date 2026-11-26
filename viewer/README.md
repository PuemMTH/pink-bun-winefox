# Model Studio

Buildless HTML/CSS/ES modules with a local copy of **Three.js r180**. No CDN is needed for the renderer. The optional web font has a system-font fallback.

From the repository root:

```sh
npm run viewer
```

Open the printed `http://127.0.0.1:4173/` URL. To refresh model assets after editing geometry or textures, run `npm run build:viewer` and click the reload icon in the viewer. To check the animation/geometry adapter, run `npm run check:viewer` after building the model.

`npm run build:viewer` exports the current model into `dist/viewer/assets/` and copies this website into `dist/viewer/`. That folder can be served by any static HTTP host. Modules need HTTP; double-clicking `index.html` via `file://` is not supported by browser security policies.

## Features

- Orbit, zoom, front/side/back camera views.
- Real YSM/Bedrock bone hierarchy, cube pivots, per-face UVs, nearest-neighbor pixels and inflate.
- Standing, walking, sprinting, jumping, crouching, sitting and other main clips from the actual animation file.
- Pre-parallel sway and blink layers; sprint expression and return to normal face.
- Pause, timeline scrub, speed control, repeated playback.
- Texture-only, lit and wireframe views; light/dark/transparent backgrounds.
- PNG export and local folder import (`ysm.json`, JSON models/animations, PNG textures). Imported files stay in the browser.

## Rendering references

The installed YSM 2.6.5 JAR loads `ysm-core.dll`/`.so`. Its native renderer is not open-source in the installed package. This is a compatible browser preview, not a copy of that native renderer.

The adapter follows the publicly available GeckoLib 1.20.1 implementation:

- [BakedModelFactory](https://github.com/bernie-g/geckolib/blob/1.20.1/Fabric/src/main/java/software/bernie/geckolib/loading/object/BakedModelFactory.java): reflect X, preserve absolute pivots and inflate.
- [RenderUtils](https://github.com/bernie-g/geckolib/blob/1.20.1/Fabric/src/main/java/software/bernie/geckolib/util/RenderUtils.java): Z-Y-X Euler transform order; rotation signs `(-x,-y,+z)` after reflection.
- [GeoQuad](https://github.com/bernie-g/geckolib/blob/1.20.1/Fabric/src/main/java/software/bernie/geckolib/cache/object/GeoQuad.java): face corner order, signed UV sizes and mirroring.
- [BakedAnimationsAdapter](https://github.com/bernie-g/geckolib/blob/1.20.1/Fabric/src/main/java/software/bernie/geckolib/loading/json/typeadapter/BakedAnimationsAdapter.java): numeric keyframes, pre/post endpoints and interpolation.
- [YSM parallel layers](https://ysm.cfpa.team/wiki/animation/parallel/): low-priority pre-parallel layers before the main animation.
- [Molang syntax](https://learn.microsoft.com/en-us/minecraft/creator/documents/molang/syntax-guide?view=minecraft-bedrock-stable): degree-based trig and safe expression evaluation.

`animation.mjs` uses a whitelisted expression parser, not JavaScript eval. It supports the math/conditionals needed by the visible main clips. Native stateful hair physics, controller timelines, item rendering and Minecraft lightmaps are not reproduced. Unsupported state variables evaluate to zero. Imported encrypted `.ysm` packages are not supported.

## Files

- `index.html`, `styles.css`: responsive studio UI.
- `app.mjs`: camera, playback, import and PNG export.
- `model.mjs`: Bedrock geometry and transform adapter.
- `animation.mjs`: keyframe sampling and Molang subset.
- `lib/`: pinned upstream Three.js/OrbitControls files; see `lib/THREE-LICENSE.txt` (MIT).

The model's Wine Fox credits and CC BY-NC-SA license continue to apply to the character assets. Three.js and OrbitControls retain their separate MIT license.
