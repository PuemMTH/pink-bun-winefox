# Model Studio

Buildless HTML/CSS/ES modules with a local copy of **Three.js r180**. No CDN is needed for the renderer. The optional web font has a system-font fallback.

From the repository root:

```sh
npm run viewer
```

Open the printed `http://127.0.0.1:4173/` URL. To refresh model assets after editing geometry or textures, run `npm run build:viewer` and click the reload icon in the viewer. To check the animation/geometry adapter, run `npm run check:viewer` after building the model.

`npm run build:viewer` exports both Square Eyes variants and Satou’s Aunt into `dist/viewer/assets/` and copies this website into `dist/viewer/`. That folder can be served by any static HTTP host. Modules need HTTP; double-clicking `index.html` via `file://` is not supported by browser security policies.

## Features

- Six static photo poses: wave, hands by cheeks, hand on hip, shy clasped hands, hands at chest, and open arms. Use **Photo Poses** in the layout selector (or **Show Photo Poses**) to compare them as cards. Selecting a pose pauses the character for framing and PNG capture. Both Square Eyes variants use their YSM photo clips. Other compatible rigs can use the Studio presets.

- Opens in **All Poses**: a scrollable gallery of every main animation of the selected character, starting with standing, walking, running, jumping, crouching and sitting. Every card starts at the same front camera angle. Each pose plays on its own timeline using the selected character's pause, speed, loop and blink settings. Only cards inside the gallery viewport are drawn; all cards reuse the character's geometry and texture.
- Add multiple characters without replacing the current scene. Select the character in the sidebar to edit its own animation, speed, loop and blink state; hide, remove or duplicate it independently.
- Choose **1 / 2 / 4 Views**. Each pane has its own model selector (one character or all visible characters), orbit/zoom controls, and front/side/back/three-quarter/top camera. Switching layouts preserves the existing camera assignments and orbit positions.
- Real YSM/Bedrock bone hierarchy, cube pivots, per-face UVs, nearest-neighbor pixels and inflate.
- Standing, walking, sprinting, jumping, crouching, sitting and other main clips from the actual animation file.
- Pre-parallel sway and blink layers; sprint expression and return to normal face.
- Pause, timeline scrub, speed control, repeated playback per character. **Apply Pose to All Models** copies the selected character's playback settings to characters that contain that clip; unsupported clips are skipped.
- Texture-only, lit and wireframe views; light/dark/transparent backgrounds.
- PNG export of all visible panes in one image (canvas content, without UI controls).
- Local folder import (`ysm.json`, JSON models/animations, PNG textures). Select one model folder, or a parent folder containing several models to add them together. Namespaced file paths keep models with identical file names separate. Imported files stay in the browser; closing the page clears the scene.

## Open and compare characters

1. The default **All Poses** gallery shows all poses of the selected character. Scroll inside the gallery to see the rest. Pick an animation in the sidebar to inspect it in one full pane; choose **All Poses** in the layout selector to return. Scrubbing in gallery mode pauses all cards at the same fraction of their respective clips. PNG export captures the currently visible cards.
2. Use **Add White Shirt** or **Add Satou’s Aunt** to compare the bundled models. **Import Model** opens one model folder or a parent with several. **Add School Uniform** and **Duplicate Selected** add separate instances for pose comparisons.
3. Pick **2 Views** or **4 Views** near the scene title. At the top of each pane, select the character(s) and camera angle. Drag/zoom inside that pane to adjust its camera independently. On narrow screens, panes stack vertically.
4. Select a character's name in **Scene models** to change its animation or playback. Other characters keep playing with their own settings. The bottom camera toolbar applies to the last pane you clicked or focused.
5. Use the checkbox to hide a character or **×** to remove it from this browser scene. Removal also releases that character's GPU resources. If a pane was assigned to a removed character, it falls back to all remaining visible characters.

## Export the model checks

```sh
npm run export:viewer
```

This builds both YSM folders and captures the reference-pack checklist in headless Chrome or Edge. Open the printed `dist/ysm-render-checks/…/index.html` for the actual frames, concept sheets, CSV and provenance. Each PNG records its source animation, pose time and SHA-256 in `manifest.json`. The CSV includes the matching browser renders and keeps the checklist pending for review in Minecraft.

Use `-- --outfit white` to export one outfit, `-- --case school-core-run-jump-1` for one case, or `-- --primary-only` to keep one frame per case. Set `CHROME_PATH` when using Chromium from a custom install path. The exporter reads the reference pack at `docs/ysm-reference-pack-v1`, so keep it available when rerunning exports.

Use `npm run export:viewer -- --sequence` for at least five time samples at every main or extra action camera angle, and five views of each held photo pose. Sequence mode marks held main actions in `manifest.json` and cannot be combined with `--primary-only`.

Add `--inspection-views` to a sequence export to capture Left, Right, Top, and Bottom for every action and photo pose. The turnaround set also includes Top and Bottom. The exporter hides the floor in both vertical views and keeps the front of the model towards the top of the image.

The export uses the Model Studio scene, camera directions, geometry and animation code. Jump samples use explicit ascent, apex and descent velocities, and extra0 captures the first accessory toggle. Model Studio applies one bed orientation during sleep for rigs that supply an upright sleep pose. In YSM, `climb` and `climbing` are crawling poses under a trapdoor. Held items and native simulation require Minecraft.

To repeat the part review, keep the original YSM folders and their render manifest together. Run `npm run export:viewer -- --part-review dist/part-review-baseline` with the review and fix JSON records in `dist/`. The comparison renders both revisions with one camera frame for each clip and view. Its HTML and relative PNGs can be moved together and opened offline.

To compare a new build with a saved installation, copy the three active model folders to a separate baseline folder, then run:

```powershell
npm run export:viewer -- --flight-review <baseline-folder>
```

The exporter writes an English Motion Review under `dist/ysm-flight-reviews/` and refreshes `dist/viewer/flight-review/`. The review includes paired captures for the Aunt braid and crouch-walk fixes, plus flight views for all three models.

## Rendering references

For imported Wine Fox-compatible models without photo clips, Model Studio derives six browser photo presets on load. Imported source animation files are left intact. The hands have no individual finger joints, so the greeting pose uses a raised hand.

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
- `rendering.mjs`: shared lights, renderer, camera directions and model setup.
- `export.mjs`: deterministic browser captures for the checklist runner.
- `model.mjs`: Bedrock geometry and transform adapter.
- `animation.mjs`: keyframe sampling and Molang subset.
- `photo-poses.mjs`: pose labels, rig compatibility and static photo rotations. Edit this file to add or adjust photo presets; no model rebuild is required to edit the browser's pose definitions.
- `studio.mjs`: multi-folder file parsing, independent playback and pane visibility rules.
- `lib/`: pinned upstream Three.js/OrbitControls files; see `lib/THREE-LICENSE.txt` (MIT).

The model's Wine Fox credits and CC BY-NC-SA license continue to apply to the character assets. Three.js and OrbitControls retain their separate MIT license.
