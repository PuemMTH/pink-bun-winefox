"""Pack textures from the user's local Minecraft client into a render atlas."""

import argparse
import hashlib
import importlib.util
from io import BytesIO
import json
import math
from pathlib import Path
from zipfile import ZipFile

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
FACES = ("north", "south", "east", "west", "up", "down")
TILE_SIZE = 16


def palette_states():
    source = Path(__file__).with_name("guild_blocks.py")
    spec = importlib.util.spec_from_file_location("city_block_palette", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.PALETTE)


def tinted(image, rgb):
    result = image.convert("RGBA").copy()
    result.putdata([
        (round(r * rgb[0] / 255), round(g * rgb[1] / 255), round(b * rgb[2] / 255), a)
        for r, g, b, a in result.getdata()
    ])
    return result


def prepare(jar, output):
    output.mkdir(parents=True, exist_ok=True)
    originals = output / "minecraft-textures"
    source_records = {}
    tiles = {}
    states = {}
    tile_sources = {}

    with ZipFile(jar) as archive:
        assert "assets/minecraft/textures/block/stone_bricks.png" in archive.namelist(), (
            "The selected jar does not contain vanilla client block textures"
        )
        version = json.loads(archive.read("version.json"))["id"]

        def source(relative):
            entry = "assets/minecraft/textures/" + relative
            raw = archive.read(entry)
            target = originals / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            source_records[relative] = {
                "archive_entry": entry,
                "file": "minecraft-textures/" + relative,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            return raw

        def png(relative):
            with Image.open(BytesIO(source(relative))) as image:
                return image.convert("RGBA")

        # Vanilla plains temperature 0.8 and downfall 0.4 select these colormap texels.
        temperature, downfall = 0.8, 0.4
        sample_xy = (round((1 - temperature) * 255), round((1 - temperature * downfall) * 255))
        grass_color = png("colormap/grass.png").getpixel(sample_xy)[:3]
        foliage_color = png("colormap/foliage.png").getpixel(sample_xy)[:3]
        spruce_color = (0x61, 0x99, 0x61)
        water_color = (0x3F, 0x76, 0xE4)

        def block(name):
            relative = "block/" + name + ".png"
            image = png(relative)
            # Animated vanilla water stores its frames vertically. Capture frame zero.
            if image.size != (TILE_SIZE, TILE_SIZE):
                assert image.width == TILE_SIZE and image.height % TILE_SIZE == 0, image.size
                image = image.crop((0, 0, TILE_SIZE, TILE_SIZE))
            metadata = "assets/minecraft/textures/" + relative + ".mcmeta"
            if metadata in archive.namelist():
                source(relative + ".mcmeta")
            return image

        def tile(name, texture=None, color=None):
            if name not in tiles:
                texture = texture or name
                image = block(texture)
                tiles[name] = tinted(image, color) if color else image
                tile_sources[name] = ["block/" + texture + ".png"]
            return name

        for state in palette_states():
            base = state.removeprefix("minecraft:").split("[")[0]
            if base == "grass_block":
                if "grass_block_side_tinted" not in tiles:
                    side = block("grass_block_side")
                    overlay = tinted(block("grass_block_side_overlay"), grass_color)
                    tiles["grass_block_side_tinted"] = Image.alpha_composite(side, overlay)
                    tile_sources["grass_block_side_tinted"] = [
                        "block/grass_block_side.png", "block/grass_block_side_overlay.png",
                        "colormap/grass.png",
                    ]
                side = "grass_block_side_tinted"
                top = tile("grass_block_top_tinted", "grass_block_top", grass_color)
                tile_sources[top].append("colormap/grass.png")
                faces = {face: side for face in FACES}
                faces.update(up=top, down=tile("dirt"))
            elif base.endswith("_log"):
                side, end = tile(base), tile(base + "_top")
                axis = "x" if "axis=x" in state else "z" if "axis=z" in state else "y"
                ends = {"x": ("east", "west"), "y": ("up", "down"), "z": ("north", "south")}[axis]
                faces = {face: end if face in ends else side for face in FACES}
            elif base in ("oak_leaves", "spruce_leaves"):
                color = spruce_color if base == "spruce_leaves" else foliage_color
                name = tile(base + "_tinted", base, color)
                if base == "oak_leaves":
                    tile_sources[name].append("colormap/foliage.png")
                faces = dict.fromkeys(FACES, name)
            elif base == "water":
                name = tile("water_still_tinted", "water_still", water_color)
                faces = dict.fromkeys(FACES, name)
            else:
                faces = dict.fromkeys(FACES, tile(base))
            states[state] = faces

    columns = 8
    rows = 2 ** math.ceil(math.log2(max(1, math.ceil(len(tiles) / columns))))
    width, height = columns * TILE_SIZE, rows * TILE_SIZE
    atlas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    mapping = {}
    for index, (name, image) in enumerate(tiles.items()):
        x, y = index % columns * TILE_SIZE, index // columns * TILE_SIZE
        atlas.paste(image, (x, y))
        mapping[name] = {
            "pixel": [x, y, TILE_SIZE, TILE_SIZE],
            "uv": [x / width, y / height],
            "uv_size": [TILE_SIZE / width, TILE_SIZE / height],
            "sources": list(dict.fromkeys(tile_sources[name])),
        }
    atlas_path = output / "minecraft-atlas.png"
    atlas.save(atlas_path)
    rgb_hex = lambda color: "#" + "".join(f"{value:02x}" for value in color)
    metadata = {
        "texture": atlas_path.name,
        "size": [width, height],
        "tile_size": TILE_SIZE,
        "uv_origin": "top-left; invert V for Blender",
        "source": {"jar": jar.name, "version": version,
                   "sha256": hashlib.sha256(jar.read_bytes()).hexdigest()},
        "tints": {
            "biome": "plains", "temperature": temperature, "downfall": downfall,
            "colormap_pixel": list(sample_xy), "grass": rgb_hex(grass_color),
            "foliage": rgb_hex(foliage_color), "spruce_foliage": rgb_hex(spruce_color),
            "water": rgb_hex(water_color),
            "note": "Grass and oak foliage sampled from client colormaps; spruce and plains water use vanilla tint constants.",
        },
        "states": states,
        "tiles": mapping,
        "source_files": source_records,
        "atlas_sha256": hashlib.sha256(atlas_path.read_bytes()).hexdigest(),
    }
    (output / "minecraft-atlas.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    assert set(states) == set(palette_states())
    assert all(Image.open(originals / rel).size for rel in source_records if rel.endswith(".png"))
    assert len({tuple(value["pixel"][:2]) for value in mapping.values()}) == len(tiles)
    print(f"Minecraft {version}: {len(states)} block states, {len(tiles)} tiles, {width}x{height} atlas")
    print(atlas_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "dist/blender")
    args = parser.parse_args()
    prepare(args.jar.resolve(), args.out.resolve())


if __name__ == "__main__":
    main()
