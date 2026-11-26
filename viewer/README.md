# Model Studio

Buildless HTML/CSS/ES modules with a local copy of **Three.js r180**. No CDN is needed for the renderer. The optional web font has a system-font fallback.

From the repository root:

```sh
npm run viewer
```

Open the printed `http://127.0.0.1:4173/` URL. To refresh model assets after editing geometry or textures, run `npm run build:viewer` and click the reload icon in the viewer. To check the animation/geometry adapter, run `npm run check:viewer` after building the model.

`npm run build:viewer` exports the current model into `dist/viewer/assets/` and copies this website into `dist/viewer/`. That folder can be served by any static HTTP host. Modules need HTTP; double-clicking `index.html` via `file://` is not supported by browser security policies.

## Features

- Opens in **ทุกท่าทาง**: a scrollable gallery of every main animation of the selected character, starting with standing, walking, running, jumping, crouching and sitting. Every card starts at the same front camera angle. Each pose plays on its own timeline using the selected character's pause, speed, loop and blink settings. Only cards inside the gallery viewport are drawn; all cards reuse the character's geometry and texture.
- Add multiple characters without replacing the current scene. Select the character in the sidebar to edit its own animation, speed, loop and blink state; hide, remove or duplicate it independently.
- Choose **1 / 2 / 4 Views**. Each pane has its own model selector (one character or all visible characters), orbit/zoom controls, and front/side/back/three-quarter/top camera. Switching layouts preserves the existing camera assignments and orbit positions.
- Real YSM/Bedrock bone hierarchy, cube pivots, per-face UVs, nearest-neighbor pixels and inflate.
- Standing, walking, sprinting, jumping, crouching, sitting and other main clips from the actual animation file.
- Pre-parallel sway and blink layers; sprint expression and return to normal face.
- Pause, timeline scrub, speed control, repeated playback per character. **ใช้ท่านี้กับทุกตัว** copies the selected character's playback settings to characters that contain that clip; unsupported clips are skipped.
- Texture-only, lit and wireframe views; light/dark/transparent backgrounds.
- PNG export of all visible panes in one image (canvas content, without UI controls).
- Local folder import (`ysm.json`, JSON models/animations, PNG textures). Select one model folder, or a parent folder containing several models to add them together. Namespaced file paths keep models with identical file names separate. Imported files stay in the browser; closing the page clears the scene.

## Open and compare characters

1. The default **ทุกท่าทาง** gallery shows all poses of the selected character. Scroll inside the gallery to see the rest. Pick an animation in the sidebar to inspect it in one full pane; choose **ทุกท่าทาง** in the layout selector to return. Scrubbing in gallery mode pauses all cards at the same fraction of their respective clips. PNG export captures the currently visible cards.
2. Click **เพิ่มโมเดล** and select a model folder, or the parent folder containing several model directories. You can add more folders later. **เพิ่ม Satou Matsuzaka** and **ทำสำเนาตัวที่เลือก** also add separate instances for comparing poses.
3. Pick **2 Views** or **4 Views** near the scene title. At the top of each pane, select the character(s) and camera angle. Drag/zoom inside that pane to adjust its camera independently. On narrow screens, panes stack vertically.
4. Select a character's name in **ตัวละครในฉาก** to change its animation or playback. Other characters keep playing with their own settings. The bottom camera toolbar applies to the last pane you clicked or focused.
5. Use the checkbox to hide a character or **×** to remove it from this browser scene. Removal also releases that character's GPU resources. If a pane was assigned to a removed character, it falls back to all remaining visible characters.

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
- `studio.mjs`: multi-folder file parsing, independent playback and pane visibility rules.
- `lib/`: pinned upstream Three.js/OrbitControls files; see `lib/THREE-LICENSE.txt` (MIT).

The model's Wine Fox credits and CC BY-NC-SA license continue to apply to the character assets. Three.js and OrbitControls retain their separate MIT license.
