"""Write and validate a Sponge v2 Minecraft schematic using the standard library.

    stats = write_schematic({(0, 0, 0): "minecraft:stone_bricks"}, Path("guild.schem"))

Input coordinates use Minecraft X, Y-up, Z. The file normalizes the input region
to its minimum corner. The returned ``origin`` records that source corner.
No Minecraft files or worlds are modified.

Format reference:
https://github.com/SpongePowered/Schematic-Specification/blob/master/versions/schematic-2.md
"""

from collections import Counter
import gzip
from io import BytesIO
from pathlib import Path
import struct


AIR = "minecraft:air"


def _string(value):
    encoded = value.encode("utf-8")
    if len(encoded) > 65535:
        raise ValueError("NBT string exceeds 65535 bytes")
    return struct.pack(">H", len(encoded)) + encoded


def _tag(kind, name, payload):
    return bytes([kind]) + _string(name) + payload


def _int(name, value):
    return _tag(3, name, struct.pack(">i", value))


def _varint(value):
    encoded = bytearray()
    while value > 127:
        encoded.append((value & 127) | 128)
        value >>= 7
    encoded.append(value)
    return encoded


def _decode_nbt(source):
    """Decode the NBT types emitted by this writer without using its encoder."""
    stream = BytesIO(source)

    def read(length):
        value = stream.read(length)
        if len(value) != length:
            raise ValueError("Truncated NBT data")
        return value

    def unpack(fmt):
        return struct.unpack(fmt, read(struct.calcsize(fmt)))[0]

    def text():
        return read(unpack(">H")).decode("utf-8")

    def payload(kind):
        if kind == 2:
            return unpack(">H")
        if kind == 3:
            return unpack(">i")
        if kind == 7:
            length = unpack(">i")
            if length < 0:
                raise ValueError("Negative byte array length")
            return read(length)
        if kind == 8:
            return text()
        if kind == 10:
            result = {}
            while True:
                child_kind = unpack(">B")
                if child_kind == 0:
                    return result
                name = text()
                if name in result:
                    raise ValueError("Duplicate NBT field " + name)
                result[name] = payload(child_kind)
        if kind == 11:
            length = unpack(">i")
            if length < 0:
                raise ValueError("Negative int array length")
            return [unpack(">i") for _ in range(length)]
        raise ValueError("Unsupported NBT tag " + str(kind))

    if unpack(">B") != 10 or text() != "Schematic":
        raise ValueError("Expected a named Schematic root compound")
    result = payload(10)
    if stream.read(1):
        raise ValueError("Trailing NBT data")
    return result


def validate_schematic(destination, blocks=None):
    """Read the saved gzip/NBT and optionally check every expected block."""
    data = _decode_nbt(gzip.decompress(Path(destination).read_bytes()))
    if data["Version"] != 2 or data["Offset"] != [0, 0, 0]:
        raise ValueError("Unexpected schematic version or offset")
    width, height, length = (data[key] for key in ("Width", "Height", "Length"))
    if min(width, height, length) < 1:
        raise ValueError("Schematic dimensions must be positive")
    palette = data["Palette"]
    if sorted(palette.values()) != list(range(len(palette))):
        raise ValueError("Palette indices must be contiguous")
    if data["PaletteMax"] != len(palette) or palette.get(AIR) != 0:
        raise ValueError("Invalid palette size or default air")

    indices = []
    value = shift = 0
    for byte in data["BlockData"]:
        value |= (byte & 127) << shift
        if byte & 128:
            shift += 7
            if shift >= 35:
                raise ValueError("Block palette varint exceeds 32 bits")
        else:
            if value >= len(palette):
                raise ValueError("Block palette index out of range")
            indices.append(value)
            value = shift = 0
    if shift or len(indices) != width * height * length:
        raise ValueError("Truncated varint or wrong block array length")

    counts = Counter(indices)
    if blocks is not None:
        origin = tuple(min(point[axis] for point in blocks) for axis in range(3))
        expected_size = [
            max(point[i] for point in blocks) - origin[i] + 1 for i in range(3)
        ]
        if expected_size != [width, height, length]:
            raise ValueError("Saved bounds differ from source")
        expected_counts = Counter({0: width * height * length - len(blocks)})
        for (x, y, z), state in blocks.items():
            index = (
                x
                - origin[0]
                + (z - origin[2]) * width
                + (y - origin[1]) * width * length
            )
            if state not in palette or indices[index] != palette[state]:
                raise ValueError(f"Saved block differs at {(x, y, z)}")
            expected_counts[palette[state]] += 1
        if counts != +expected_counts:
            raise ValueError("Saved occupied/default-air counts differ from source")
        if set(palette) != {AIR, *blocks.values()}:
            raise ValueError("Saved block palette differs from source")

    return {
        "format": "Sponge v2",
        "data_version": data["DataVersion"],
        "size": [width, height, length],
        "palette_size": len(palette),
        "total_blocks": len(indices),
        "non_air_blocks": len(indices) - counts[0],
        "roundtrip": "passed",
    }


def write_schematic(blocks, destination, data_version=3465):
    """Write integer block coordinates and block-state names to a .schem file.

    ``data_version=3465`` targets Minecraft Java 1.20.1. Unspecified positions
    in the rectangular region become air. The block-state registry is supplied
    by the caller; this function validates the container and palette encoding.
    """
    if not blocks:
        raise ValueError("At least one block is required")
    for point, state in blocks.items():
        if len(point) != 3 or any(type(value) is not int for value in point):
            raise ValueError("Block coordinates must contain three integers")
        if not isinstance(state, str) or ":" not in state or not state:
            raise ValueError("Block states must include a namespace")
    if type(data_version) is not int or data_version <= 0:
        raise ValueError("Minecraft data version must be a positive integer")

    destination = Path(destination)
    origin = tuple(min(point[axis] for point in blocks) for axis in range(3))
    size = [max(point[i] for point in blocks) - origin[i] + 1 for i in range(3)]
    if any(span > 65535 for span in size):
        raise ValueError("Schematic dimensions exceed unsigned short storage")
    palette = {
        state: index
        for index, state in enumerate([AIR] + sorted(set(blocks.values()) - {AIR}))
    }
    encoded = {state: _varint(index) for state, index in palette.items()}
    width, height, length = size
    block_data = bytearray()
    for y in range(origin[1], origin[1] + height):
        for z in range(origin[2], origin[2] + length):
            for x in range(origin[0], origin[0] + width):
                block_data.extend(encoded[blocks.get((x, y, z), AIR)])

    fields = _int("Version", 2) + _int("DataVersion", data_version)
    for name, span in zip(("Width", "Height", "Length"), size):
        fields += _tag(2, name, struct.pack(">H", span))
    fields += _tag(11, "Offset", struct.pack(">iiii", 3, 0, 0, 0))
    fields += _int("PaletteMax", len(palette))
    fields += _tag(
        10,
        "Palette",
        b"".join(_int(state, index) for state, index in palette.items()) + b"\0",
    )
    fields += _tag(7, "BlockData", struct.pack(">i", len(block_data)) + block_data)
    metadata = (
        _tag(8, "Name", _string(destination.stem))
        + _tag(8, "Author", _string("puemmth"))
        + b"\0"
    )
    fields += _tag(10, "Metadata", metadata)
    source = _tag(10, "Schematic", fields + b"\0")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(gzip.compress(source, mtime=0))
    stats = validate_schematic(destination, blocks)
    stats["origin"] = list(origin)
    stats["file_bytes"] = destination.stat().st_size
    return stats


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        sample = {
            (-3, 2, 8): "minecraft:stone_bricks",
            (-1, 2, 8): "minecraft:oak_planks",
            (-3, 3, 9): "minecraft:glass",
            (-2, 3, 9): AIR,
        }
        stats = write_schematic(sample, Path(directory) / "roundtrip.schem")
        assert stats["size"] == [3, 2, 2]
        assert stats["non_air_blocks"] == 3
        assert stats["origin"] == [-3, 2, 8]
        for value in (0, 127, 128, 16383, 16384, 0x7FFFFFFF):
            data = _varint(value)
            decoded = sum((byte & 127) << (7 * i) for i, byte in enumerate(data))
            assert decoded == value
        print(stats)
