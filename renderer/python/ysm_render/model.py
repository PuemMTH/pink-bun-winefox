"""Load character assets and transform Bedrock cubes into a posed triangle mesh."""

from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
import json
import math
from pathlib import Path
import posixpath
from zipfile import ZipFile, is_zipfile

import numpy as np
from PIL import Image

from .animation import pose_for

_FACES = {
    "north": [2, 4, 6, 0],
    "south": [5, 3, 1, 7],
    "west": [3, 2, 0, 1],
    "east": [4, 5, 7, 6],
    "up": [3, 5, 4, 2],
    "down": [0, 6, 7, 1],
}


def _vec(value, default=(0, 0, 0)):
    value = np.asarray(default if value is None else value, dtype=np.float64)
    if value.ndim == 0:
        value = np.repeat(value, 3)
    if value.shape != (3,) or not np.isfinite(value).all():
        raise ValueError("Expected three finite coordinates")
    return value


def _position(value):
    return _vec(value) * [-1 / 16, 1 / 16, 1 / 16]


def _rotation(value):
    x, y, z = np.radians(_vec(value) * [-1, -1, 1])
    cx, cy, cz, sx, sy, sz = (
        math.cos(x),
        math.cos(y),
        math.cos(z),
        math.sin(x),
        math.sin(y),
        math.sin(z),
    )
    return np.array(
        [
            [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
            [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
            [-sy, cy * sx, cy * cx],
        ]
    )


def cube_geometry(cube, description, bone_pivot):
    """Return bone-local face vertices, normalized UVs and triangle indices."""
    origin, size = _vec(cube["origin"]), _vec(cube["size"])
    inflate = float(cube.get("inflate", 0))
    if not math.isfinite(inflate) or (size < 0).any():
        raise ValueError("Invalid cube size/inflate")
    low = np.array([-(origin[0] + size[0]), origin[1], origin[2]]) - inflate
    high = np.array([-origin[0], origin[1] + size[1], origin[2] + size[2]]) + inflate
    high = np.where(high < low, low + 0.001, high)
    x, y, z = low
    X, Y, Z = high
    corners = (
        np.array(
            [
                [x, y, z],
                [x, y, Z],
                [x, Y, z],
                [x, Y, Z],
                [X, Y, z],
                [X, Y, Z],
                [X, y, z],
                [X, y, Z],
            ]
        )
        / 16
    )
    if "rotation" in cube:
        pivot = _position(cube.get("pivot"))
        corners = (corners - pivot) @ _rotation(cube["rotation"]).T + pivot
    corners -= bone_pivot
    width, height = float(description["texture_width"]), float(
        description["texture_height"]
    )
    if not math.isfinite(width + height) or width <= 0 or height <= 0:
        raise ValueError("Texture dimensions must be positive")
    uv = cube.get("uv", {})
    if not isinstance(uv, (list, dict)):
        raise ValueError("Cube UV must be a box UV array or a face mapping")
    box_uv = None
    if isinstance(uv, list):
        u, v = uv
        w, h, d = size
        box_uv = {
            "north": ([u + d, v + d], [w, h]),
            "east": ([u, v + d], [d, h]),
            "south": ([u + 2 * d + w, v + d], [w, h]),
            "west": ([u + d + w, v + d], [d, h]),
            "up": ([u + d, v], [w, d]),
            "down": ([u + d + w, v + d], [w, -d]),
        }
    vertices, uvs, triangles = [], [], []
    for name, order in _FACES.items():
        if box_uv:
            (u, v), (du, dv) = box_uv[name]
            turns = 0
        else:
            face = uv.get(name)
            if face is None:
                continue
            u, v = face["uv"]
            du, dv = face.get("uv_size", [0, 0])
            turns = math.floor(float(face.get("uv_rotation", 0)) / 90 + 0.5) % 4
        tex = [[u + du, v], [u, v], [u, v + dv], [u + du, v + dv]]
        tex = tex[turns:] + tex[:turns]
        if cube.get("mirror"):
            order = _FACES[
                {"east": "west", "west": "east", "up": "down", "down": "up"}.get(
                    name, name
                )
            ]
        start = len(vertices)
        vertices.extend(corners[order])
        uvs.extend(np.asarray(tex) / [width, height])
        triangles.extend([[start, start + 1, start + 2], [start, start + 2, start + 3]])
    result = (
        np.asarray(vertices, dtype=float).reshape(-1, 3),
        np.asarray(uvs, dtype=float).reshape(-1, 2),
        np.asarray(triangles, dtype=np.int32).reshape(-1, 3),
    )
    if not np.isfinite(result[0]).all() or not np.isfinite(result[1]).all():
        raise ValueError("Cube coordinates and UVs must be finite")
    return result


@dataclass(frozen=True)
class Mesh:
    vertices: np.ndarray
    uvs: np.ndarray
    triangles: np.ndarray


class Model:
    """Reusable model; texture/geometry are loaded once, poses are sampled per call."""

    def __init__(
        self, geometry, texture, animations=None, info=None, *, geometry_index=0
    ):
        self.info = deepcopy(info or {})
        geometries = geometry.get("minecraft:geometry", [])
        if not 0 <= geometry_index < len(geometries):
            raise ValueError(
                "Expected Bedrock minecraft:geometry and a valid geometry_index"
            )
        geometry = deepcopy(geometries[geometry_index])
        self.bones = {bone["name"]: bone for bone in geometry.get("bones", [])}
        if not self.bones or len(self.bones) != len(geometry["bones"]):
            raise ValueError("Bone names must be present and unique")
        self.animations = deepcopy(
            (animations or {}).get("animations", animations or {})
        )
        self.texture = np.array(texture.convert("RGBA"), dtype=np.uint8)
        self.texture.setflags(write=False)
        properties = self.info.get("properties", {})
        height = float(properties.get("height_scale") or 0.7)
        width = float(properties.get("width_scale") or height)
        self.scale = _vec([width, height, width])
        if (self.scale <= 0).any():
            raise ValueError("Model scale must be positive")
        self._parts = []
        all_uvs, all_triangles, count = [], [], 0
        self.cube_count = 0
        description = geometry.get("description", {})
        for name, bone in self.bones.items():
            if bone.get("parent") and bone["parent"] not in self.bones:
                raise ValueError(f"Unknown parent bone: {bone['parent']}")
            for cube in bone.get("cubes", []):
                if not all(key in cube for key in ("origin", "size", "uv")):
                    continue
                vertices, uvs, triangles = cube_geometry(
                    cube, description, _position(bone.get("pivot"))
                )
                self._parts.append((name, vertices, count))
                all_uvs.append(uvs)
                all_triangles.append(triangles + count)
                count += len(vertices)
                self.cube_count += 1
        self._vertex_count = count
        self._uvs = np.concatenate(all_uvs) if all_uvs else np.empty((0, 2))
        self._triangles = (
            np.concatenate(all_triangles)
            if all_triangles
            else np.empty((0, 3), dtype=np.int32)
        )
        self._uvs.setflags(write=False)
        self._triangles.setflags(write=False)
        self._add_photo_poses()
        self.bone_matrices(
            animation=None
        )  # Validate hierarchy cycles before rendering.

    @property
    def name(self):
        return self.info.get("metadata", {}).get("name", "Custom model")

    @property
    def triangle_count(self):
        return len(self._triangles)

    def _add_photo_poses(self):
        required = {
            "Head",
            "UpperBody",
            "LeftArm",
            "RightArm",
            "LeftForeArm",
            "RightForeArm",
            "LeftLeg",
            "RightLeg",
        }
        if "idle" not in self.animations or not required.issubset(self.bones):
            return
        presets = json.loads(
            Path(__file__).with_name("photo_poses.json").read_text(encoding="utf-8")
        )
        neutral = pose_for(self.animations, "idle", 1, blink=False)
        for name, preset in presets.items():
            if name in self.animations:
                continue
            bones = deepcopy(neutral)
            for bone, channels in preset["bones"].items():
                if bone in self.bones:
                    bones.setdefault(bone, {}).update(channels)
            self.animations[name] = {
                "loop": True,
                "animation_length": 1,
                "bones": bones,
            }

    def pose(
        self,
        animation="auto",
        time=0,
        *,
        loop=True,
        blink=True,
        speed=None,
        head_yaw=0,
        head_pitch=0,
        variables=None,
        bone_overrides=None,
    ):
        if not math.isfinite(time) or time < 0:
            raise ValueError("time must be finite and non-negative")
        if animation == "auto":
            animation = "idle" if "idle" in self.animations else None
        if animation is not None and animation not in self.animations:
            raise ValueError(
                f"Unknown animation {animation!r}; inspect model.animations for available names"
            )
        if animation is not None:
            duration = float(self.animations[animation].get("animation_length", 1)) or 1
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError("Invalid animation duration")
            time = time % duration if loop else min(time, duration)
        if speed is None:
            speed = 5.6 if animation == "run" else 3 if animation == "walk" else 0
        pose = pose_for(
            self.animations,
            animation,
            time,
            blink=blink,
            speed=speed,
            head_yaw=head_yaw,
            head_pitch=head_pitch,
            variables=variables,
        )
        for bone, channels in (bone_overrides or {}).items():
            if bone not in self.bones:
                raise ValueError(f"Unknown override bone: {bone}")
            for kind, value in channels.items():
                if kind not in ("rotation", "position", "scale"):
                    raise ValueError(f"Unknown bone channel: {kind}")
                pose.setdefault(bone, {})[kind] = _vec(value).tolist()
        return pose

    def bone_matrices(self, animation="auto", time=0, **parameters):
        pose = self.pose(animation, time, **parameters)
        world, visiting = {}, set()
        root = np.diag([*self.scale, 1.0])

        def resolve(name):
            if name in world:
                return world[name]
            if name in visiting:
                raise ValueError("Cyclic bone hierarchy")
            visiting.add(name)
            bone, value = self.bones[name], pose.get(name, {})
            parent = bone.get("parent")
            position = _position(bone.get("pivot")) - (
                _position(self.bones[parent].get("pivot")) if parent else 0
            )
            local = np.eye(4)
            local[:3, :3] = _rotation(
                _vec(bone.get("rotation")) + _vec(value.get("rotation"))
            ) @ np.diag(_vec(value.get("scale"), (1, 1, 1)))
            local[:3, 3] = position + _position(value.get("position"))
            world[name] = (resolve(parent) if parent else root) @ local
            visiting.remove(name)
            return world[name]

        for name in self.bones:
            resolve(name)
        return world

    def mesh(self, animation="auto", time=0, **parameters):
        matrices = self.bone_matrices(animation, time, **parameters)
        vertices = np.empty((self._vertex_count, 3))
        for name, points, start in self._parts:
            matrix = matrices[name]
            vertices[start : start + len(points)] = (
                points @ matrix[:3, :3].T + matrix[:3, 3]
            )
        return Mesh(vertices, self._uvs, self._triangles)


def _json(data):
    return json.loads(data.decode("utf-8-sig"))


def _image(data):
    with Image.open(BytesIO(data)) as image:
        return image.convert("RGBA")


def _manifest_model(read, manifest_name, skin, geometry_index):
    manifest_name = str(manifest_name).replace("\\", "/")
    info = _json(read(manifest_name))
    player = info.get("files", {}).get("player", {})
    base = posixpath.dirname(manifest_name)
    asset = lambda name: read(posixpath.join(base, name.replace("\\", "/")))
    try:
        geometry = _json(asset(player["model"]["main"]))
        choice = player["texture"][skin]
        texture = _image(asset(choice if isinstance(choice, str) else choice["uv"]))
        animations = {"animations": {}}
        for filename in player.get("animation", {}).values():
            animations["animations"].update(
                _json(asset(filename)).get("animations", {})
            )
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("Incomplete ysm.json or invalid texture/skin index") from error
    return Model(geometry, texture, animations, info, geometry_index=geometry_index)


def load_model(
    path, *, texture=None, animations=None, manifest=None, skin=0, geometry_index=0
):
    """Load a YSM folder/ZIP, viewer assets folder, or geometry JSON + explicit assets."""
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if skin < 0:
        raise ValueError("skin must be non-negative")
    if path.is_file() and is_zipfile(path):
        with ZipFile(path) as archive:

            def read(name):
                name = posixpath.normpath(name.replace("\\", "/"))
                if name.startswith(("/", "../")) or ":" in name:
                    raise ValueError("Asset path escapes model archive")
                entry = archive.getinfo(name)
                if entry.file_size > 64 * 1024 * 1024:
                    raise ValueError("Model asset exceeds 64 MiB")
                return archive.read(entry)

            candidates = [
                name
                for name in archive.namelist()
                if name == "ysm.json" or name.endswith("/ysm.json")
            ]
            if manifest is None and len(candidates) != 1:
                raise ValueError(
                    "ZIP must contain one ysm.json, or pass manifest='model/ysm.json'"
                )
            return _manifest_model(
                read, manifest or candidates[0], skin, geometry_index
            )
    if path.is_file() and path.suffix.lower() == ".ysm":
        raise ValueError(
            "Encrypted .ysm packages are not supported; use JSON assets or a ZIP"
        )
    root = path if path.is_dir() else path.parent

    def read(name):
        if str(name).startswith(("/", "\\")) or ":" in str(name):
            raise ValueError("Asset path must be relative to the model folder")
        target = (root / name).resolve()
        if not target.is_relative_to(root):
            raise ValueError("Asset path escapes model folder")
        return target.read_bytes()

    if (
        manifest
        or (path.is_dir() and (path / "ysm.json").is_file())
        or path.name == "ysm.json"
    ):
        return _manifest_model(read, manifest or "ysm.json", skin, geometry_index)
    if path.is_dir():
        info = _json(read("info.json")) if (path / "info.json").is_file() else {}
        return Model(
            _json(read("model.json")),
            _image(read("texture.png")),
            (
                _json(read("animations.json"))
                if (path / "animations.json").is_file()
                else {}
            ),
            info,
            geometry_index=geometry_index,
        )
    if texture is None:
        raise ValueError(
            "For a geometry JSON, pass texture='texture.png' and optionally animations='animation.json'"
        )
    animation_data = {"animations": {}}
    for file in (
        [animations] if isinstance(animations, (str, Path)) else animations or []
    ):
        animation_data["animations"].update(
            _json(Path(file).read_bytes()).get("animations", {})
        )
    return Model(
        _json(path.read_bytes()),
        _image(Path(texture).read_bytes()),
        animation_data,
        geometry_index=geometry_index,
    )
