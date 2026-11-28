# Development guide

## Build pipeline

`npm run build` builds both rigs.

| Source | Builder | Active output |
| --- | --- | --- |
| `vendor/winefox-jk/` and `model.config.json` | `src/build.cjs` | `dist/pink_bun_winefox_square_eyes/` and `dist/pink_bun_winefox_white_square_eyes/` |
| `vendor/winefox-matured/` | `src/build-aunt.cjs` | `dist/satou_aunt/` |

The Satou builder uses Node's standard library and the local Model Studio pose definitions. It reads the original 256×256 RGBA PNG, packs native material luminance into recolored atlas tiles, changes the geometry, and emits YSM JSON, textures, and PNG previews. The white variant shares the rig and replaces clothing geometry and texels in `src/white-outfit.cjs`. The builder also emits the two earlier Satou variants for comparison.

## Make a small change

1. Run `npm run dev`.
2. Change a value in `model.config.json` or a source file.
3. Run `npm run viewer` to review the built model in Model Studio.
4. Run `npm run install:model`, then `/ysm model reload` in Minecraft.
5. Run `npm run pack` before committing a distributable update.

For automatic game copies, configure `local.config.json` and run `npm run dev -- --install`. The watcher builds, validates, and copies all three active models. Run `/ysm model reload` in Minecraft after the copy.

## Configuration

- `bunScale`: multiplier applied to both 14-part stepped buns. Default `1.15`.
- `bowForwardOffset`: forward shift in model units. Default `1.5`. In this geometry, the front is **negative Z**. All bow pivots move together with their cubes.
- `colors`: two hex colors per material, without `#`. Preserve material keys unless also changing their UV allocation in the source.
- `name`: name in the YSM model selector.

## Geometry and animation

Keep the Wine Fox bone names and parent relationships used by the original animations. Custom sprint irises are siblings of the normal iris bones under the original eyelids, preserving blinking. Main animation clips control visibility: `run` shows the spiral pupils and neutral mouth; other main states restore the normal face. Parallel blink animations do not own this visibility.

The wheel's eight expression clips hide the native eyes and mouth and move one pixel decal forward from inside the head. The six photo clips are generated from `viewer/photo-poses.mjs` and written into `extra.animation.json` during build. This keeps the game files and Model Studio exports on the same authored poses.

The skirt follows `DownBody`, with a lining made from three stepped rectangular frames (12 unrotated cubes) and tapered concealed upper thighs. Its wall UVs continue broad pixel pleat shadows across the tiers; there are no dense curved panels underneath the skirt. The visible lower thighs, knees, shins, and feet retain their original geometry. The tests sample 83 actual walk/run thigh keyframes against the inner bounds of the generated lining walls. They check geometry numerically; they do not simulate cloth collision or every animation blend.

During sprinting, the assembled skirt sways gently at the waist: up to 1.2° pitch, 1.8° yaw and 0.8° roll. All pleats and the lining inherit that same motion, replacing the original clip's independent front lift, side stretch and back shortening. The character's running gait and sprint face are unchanged. Geometry checks verify visible but small movement across the sway cycle, no panel separation relative to the common skirt motion, and thigh coverage in the moving lining's coordinate frame.

The skirt tilts as a single piece in jump, stationary crouch, and seated poses. A tucked waistband stays at the hip, and narrow cloth joins connect the upper thighs beneath the pleats. The white outfit uses a tapered hem and small knee caps for coverage at deep bends. Tests check skirt continuity and upward flips while retaining the original leg tracks. The jump arm expression handles zero vertical speed, and the dance and shy poses adjust shoulder angles to clear the shirt.

The bow's geometry and every pivot in its subtree are translated together. This keeps rotation coherent and clears the waistcoat in sampled standing, jumping, sneaking, swimming-idle, and sleeping poses.

## Editable base assets

Open `vendor/winefox-jk/models/main.json` as a Bedrock entity model in Blockbench to edit the source rig and geometry. Keep its explicit per-face UVs. If editing `textures/skin.png`, save it as a non-interlaced, 8-bit RGBA PNG; that is the format supported by the bundled decoder. Preserve the original authors and license when changing base assets.

To inspect the assembled result, import `models/main.json` and the texture listed in `ysm.json` from the relevant model folder in `dist/`. Apply permanent edits in `src/` or `vendor/` and rebuild.

## Checks and publishing

`npm test` builds the models, checks that both Square Eyes outfits preserve the expected body geometry and face texture, and validates Aunt's manifest resources. It checks both flight clips on all three active models. GitHub Actions runs the build, pack, and viewer checks on Linux using Node 22 and uploads all three active ZIPs.

Before publishing an update:

1. Try standing, walking, sprinting, crouching, jumping, and sitting in-game. Check the bow and skirt from front and side.
2. Confirm the spiral eyes disappear when sprinting stops.
3. Test Elytra and Creative flight on all three active models.
4. Run `npm run pack`.
5. Commit source changes, refreshed previews, and the updated model ZIPs in `downloads/` together.

The software previews are orthographic snapshots, not in-game screenshots. They approximate the base pose and expression; real lighting, animation blending, and physics may differ. Current geometry checks pass, but the latest changes still need visual testing in-game.
