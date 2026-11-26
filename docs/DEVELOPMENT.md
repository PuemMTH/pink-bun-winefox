# Development guide

## Build pipeline

`vendor/winefox-jk/` + `model.config.json` → `src/build.cjs` → `dist/pink_bun_winefox/`

The build uses only Node's standard library. It reads the original 256×256 RGBA PNG, packs native material luminance into recolored atlas tiles, changes the geometry, and emits YSM JSON, the texture, and two PNG previews. No game installation or absolute personal path is required.

## Make a small change

1. Run `npm run dev`.
2. Change a value in `model.config.json` or a source file.
3. Check `docs/preview.png` and `docs/preview-run-face.png`.
4. Run `npm run install:model`, then `/ysm model reload` in Minecraft.
5. Run `npm run pack` before committing a distributable update.

For automatic game copies, configure `local.config.json` and run `npm run dev -- --install`. No filesystem watcher can trigger the Minecraft reload command automatically; execute it in-game after the copy.

## Configuration

- `bunScale`: multiplier applied to both 14-part stepped buns. Default `1.15`.
- `bowForwardOffset`: forward shift in model units. Default `1.5`. In this geometry, the front is **negative Z**. All bow pivots move together with their cubes.
- `colors`: two hex colors per material, without `#`. Preserve material keys unless also changing their UV allocation in the source.
- `name`: name in the YSM model selector.

## Geometry and animation

Keep the Wine Fox bone names and parent relationships used by the original animations. Custom sprint irises are siblings of the normal iris bones under the original eyelids, preserving blinking. Main animation clips control visibility: `run` shows the spiral pupils and neutral mouth; other main states restore the normal face. Parallel blink animations do not own this visibility.

The skirt follows `DownBody`, with a lining made from three stepped rectangular frames (12 unrotated cubes) and tapered concealed upper thighs. Each lining face uses one texel for flat pixel shading; there are no dense curved panels underneath the skirt. The visible lower thighs, knees, shins, and feet retain their original geometry. The tests sample 83 actual walk/run thigh keyframes against the inner bounds of the generated lining walls. They check geometry numerically; they do not simulate cloth collision or every animation blend.

During sprinting, the assembled skirt sways gently at the waist: up to 1.2° pitch, 1.8° yaw and 0.8° roll. All pleats and the lining inherit that same motion, replacing the original clip's independent front lift, side stretch and back shortening. The character's running gait and sprint face are unchanged. Geometry checks verify visible but small movement across the sway cycle, no panel separation relative to the common skirt motion, and thigh coverage in the moving lining's coordinate frame.

The bow's geometry and every pivot in its subtree are translated together. This keeps rotation coherent and clears the waistcoat in sampled standing, jumping, sneaking, swimming-idle, and sleeping poses.

## Editable base assets

Open `vendor/winefox-jk/models/main.json` as a Bedrock entity model in Blockbench to edit the source rig and geometry. Keep its explicit per-face UVs. If editing `textures/skin.png`, save it as a non-interlaced, 8-bit RGBA PNG; that is the format supported by the bundled decoder. Preserve the original authors and license when changing base assets.

To inspect the assembled result, import `dist/pink_bun_winefox/models/main.json` and its `textures/pink_bun.png`. Apply permanent edits in `src/` or `vendor/` and rebuild, rather than editing generated output only.

## Checks and publishing

`npm test` builds and checks parent links, declared resources, texture bounds, unchanged original face texels, vest shading, skirt coverage, sprint face reset, bun scale, and bow clearance. GitHub Actions runs the same build/check/pack on Linux using Node 22.

Before publishing an update:

1. Try standing, walking, sprinting, crouching, jumping, and sitting in-game. Check the bow and skirt from front and side.
2. Confirm the spiral eyes disappear when sprinting stops.
3. Run `npm run pack`.
4. Commit source changes, `docs/preview*.png`, and `downloads/pink-bun-winefox.zip` together.

The software previews are orthographic snapshots, not in-game screenshots. They approximate the base pose and expression; real lighting, animation blending, and physics may differ. Current geometry checks pass, but the latest changes still need visual testing in-game.
