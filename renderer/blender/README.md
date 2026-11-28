# Blender conversion

The converter reads the built YSM assets and creates an editable Blender mesh, a rigid armature, packed pixel texture and the available review actions. The four Satou variants have 47 actions each; the aunt source provides 33 of those actions. It uses the existing Python YSM geometry and animation adapter.

## Convert

Run `npm test` from the repository root first. Use regular Python with the dependencies listed in `renderer/python/pyproject.toml` to prepare the model data.

```powershell
python renderer/blender/convert.py --prepare --model dist/pink_bun_winefox --prepared dist/blender/school-prepared.json
python renderer/blender/convert.py --prepare --model dist/pink_bun_winefox_white --prepared dist/blender/white-prepared.json

blender --background --python-exit-code 1 --python renderer/blender/convert.py -- --prepared dist/blender/school-prepared.json --out output/blender/satou-school.blend
blender --background --python-exit-code 1 --python renderer/blender/convert.py -- --prepared dist/blender/white-prepared.json --out output/blender/satou-white.blend
```

The Blender stage requires Blender 4.4 or later for slotted actions. It was verified with Blender 5.3.0. It requires no added Blender Python packages. The prepared JSON is an intermediate file used during conversion.

## Render

The studio script adds an orthographic camera, soft lights and a floor. It renders one selected time per action into PNG files, then saves the Blender scene ready for editing.

```powershell
blender --background output/blender/satou-school.blend --python-exit-code 1 --python renderer/blender/render.py -- --out output/blender/renders --outfit school
blender --background output/blender/satou-white.blend --python-exit-code 1 --python renderer/blender/render.py -- --out output/blender/renders --outfit white
```

Use `--only idle run face_neutral` to render selected actions. Each render records the action, frame and time in the outfit's `*-renders.json`. The studio can be rerun on its saved scene. Lighting changes the appearance from the web previews.

## Edit and play

Each character contains a root Empty, an armature and a mesh. The mesh has one vertex group per YSM bone and an Armature modifier with rigid weights. Select the mesh in Edit Mode to change geometry and UVs, or select the rig in Pose Mode to adjust the joints.

In the Action Editor, select an action named `character - Rig | clip`. Actions include 25 main clips, `extra0` through `extra7`, six `studio_photo_*` poses and eight `face_*` expressions. They run at 30 frames per second. The first sample is frame 1, so a pose at time `t` occurs at frame `1 + 30*t`. Original key times are included alongside the 30 fps samples. Each action stores its clip ID, duration and sample rate as custom properties.

The texture image is packed in the blend file and uses nearest-neighbor interpolation. The material uses an alpha cutout for the eye and face decals. Original model credits and license metadata are stored in a Blender Text block.

## Render integration

The conversion script creates the character without cameras or lights. `build_character(prepared, root)` returns the root, rig, mesh, actions and source payload. `select_action(character_or_rig, clip, time=0)` assigns the action slot and moves the scene to the requested time. Scene layout should transform the root Empty, which parents both the rig and mesh.

The conversion preserves model-only transforms. Render scenes can add the bed orientation used for `sleep` and support props for seated poses. The animation sampler uses the same Molang subset as Model Studio. Jump uses an ascent/apex/descent velocity profile, and the ribbon toggle starts from its default state. Game-driven item poses, controller transitions and native hair simulation require the Minecraft runtime.

## Validation

Before saving, the converter compares Blender's evaluated mesh against the Python adapter at eight actual poses, including running, jump apex, sitting, dancing at 4.8917 seconds, a photo pose and two expressions. The maximum world-space vertex error must remain below 0.00002 units. Results are saved beside each blend as `*.validation.json`.

Wine Fox author metadata and CC BY-NC-SA 4.0 attribution remain in the converted files. See the repository's `ATTRIBUTION.md` and `LICENSE`.

## Refresh a character in an existing scene

Convert the current model with `convert.py`, then replace the scene's character while keeping its cameras, lights, environment, pose and floor contact:

```powershell
blender --background --python-exit-code 1 --python renderer/blender/refresh_character.py -- --scene output/blender-scenes/city-sunset/satou-minecraft-sunset.blend --character output/blender/latest/satou-school.blend --out output/blender-scenes/city-sunset-latest/satou-minecraft-sunset.blend --render
```

The refresh imports the source's actions and records the imported Blender file's SHA-256 in the scene and its `.import.json`. The latest five converted variants and their source fingerprints are listed in `output/blender/latest/manifest.json`. The sunset generator also accepts `--character`; it uses `output/blender/latest/satou-school.blend` when that file exists.

## Refresh all five characters and the RGB monitor room

`import_all_characters.py --prepare` prepares the current five built models. Run the same script inside Blender to convert them, validate their poses and create `satou-all-characters.blend` plus a comparison render. Validation times clamp to each source clip's duration; absent face clips are not fabricated for the aunt.

See [MONITOR_ROOM_RGB.md](MONITOR_ROOM_RGB.md) for screenshot preparation, the RGB case, timber/brick shelves, room rebuild and validation commands. Six main displays use distinct game captures; two right displays show code. Two joined floor monitors use two more captures, with the RTX 5070 case placed behind them to match the annotated reference.
