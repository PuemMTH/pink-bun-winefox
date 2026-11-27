"""Orthographic CPU rasterizer: barycentric UVs, cutout alpha and a depth buffer."""

from dataclasses import dataclass, field, replace
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageColor, PngImagePlugin

from .model import Model, load_model


@dataclass(frozen=True)
class RenderOptions:
    width: int = 512
    height: int = 768
    animation: str | None = "auto"
    time: float = 0.0
    yaw: float = 0.0
    pitch: float = 3.0
    roll: float = 0.0
    zoom: float = 1.0
    padding: float = 0.08
    background: str | tuple | None = None
    shading: str = "lit"
    ambient: float = 0.7
    light_direction: tuple = (-3, 6, -5)
    supersample: int = 1
    alpha_cutoff: int = 3
    loop: bool = True
    blink: bool = False
    speed: float | None = None
    head_yaw: float = 0.0
    head_pitch: float = 0.0
    variables: dict = field(default_factory=dict)
    bone_overrides: dict = field(default_factory=dict)

    def validate(self):
        if any(
            not isinstance(v, int) or isinstance(v, bool) or v < 1
            for v in (self.width, self.height, self.supersample)
        ):
            raise ValueError("width, height and supersample must be positive integers")
        if (
            self.supersample > 4
            or self.width * self.height * self.supersample**2 > 16_777_216
        ):
            raise ValueError(
                "Use supersample <= 4 and at most 16,777,216 working pixels"
            )
        if not all(
            math.isfinite(v)
            for v in (
                self.time,
                self.yaw,
                self.pitch,
                self.roll,
                self.zoom,
                self.padding,
                self.ambient,
                self.head_yaw,
                self.head_pitch,
            )
        ):
            raise ValueError("Render parameters must be finite")
        if (
            self.time < 0
            or self.zoom <= 0
            or not 0 <= self.padding < 0.5
            or not 0 <= self.ambient <= 1
        ):
            raise ValueError("Invalid time, zoom, padding or ambient")
        if self.shading not in ("lit", "unlit"):
            raise ValueError("shading must be 'lit' or 'unlit'")
        if not isinstance(self.alpha_cutoff, int) or not 0 <= self.alpha_cutoff <= 255:
            raise ValueError("alpha_cutoff must be an integer in 0..255")
        if self.speed is not None and not math.isfinite(self.speed):
            raise ValueError("speed must be finite")
        light = np.asarray(self.light_direction, dtype=float)
        if (
            light.shape != (3,)
            or not np.isfinite(light).all()
            or np.linalg.norm(light) < 1e-12
        ):
            raise ValueError("light_direction must be a finite non-zero vector")


def _background(value):
    if value is None or (isinstance(value, str) and value == "transparent"):
        return (0, 0, 0, 0)
    if isinstance(value, str):
        return ImageColor.getcolor(value, "RGBA")
    value = tuple(value)
    if len(value) == 3:
        value += (255,)
    if len(value) != 4 or any(
        not isinstance(v, int) or not 0 <= v <= 255 for v in value
    ):
        raise ValueError(
            "background must be None, a color name/hex, or an RGB(A) tuple"
        )
    return value


def _camera(yaw, pitch, roll):
    yaw, pitch, roll = np.radians([yaw, pitch, roll])
    forward = np.array(
        [
            -math.sin(yaw) * math.cos(pitch),
            -math.sin(pitch),
            math.cos(yaw) * math.cos(pitch),
        ]
    )
    right = np.array([-math.cos(yaw), 0, -math.sin(yaw)])
    up = np.cross(right, forward)
    return (
        right * math.cos(roll) + up * math.sin(roll),
        up * math.cos(roll) - right * math.sin(roll),
        forward,
    )


def render(model, options=None, **parameters):
    """Return a Pillow RGBA image. A loaded Model can be reused for many renders."""
    if not isinstance(model, Model):
        model = load_model(model)
    options = replace(options or RenderOptions(), **parameters)
    options.validate()
    mesh = model.mesh(
        options.animation,
        options.time,
        loop=options.loop,
        blink=options.blink,
        speed=options.speed,
        head_yaw=options.head_yaw,
        head_pitch=options.head_pitch,
        variables=options.variables,
        bone_overrides=options.bone_overrides,
    )
    vertices, uvs, indices = mesh.vertices, mesh.uvs, mesh.triangles
    normals = np.cross(
        vertices[indices[:, 1]] - vertices[indices[:, 0]],
        vertices[indices[:, 2]] - vertices[indices[:, 0]],
    )
    lengths = np.linalg.norm(normals, axis=1)
    visible = lengths > 1e-12
    indices, normals = indices[visible], normals[visible] / lengths[visible, None]
    if not len(indices):
        raise ValueError("The selected pose contains no visible triangles")
    right, up, forward = _camera(options.yaw, options.pitch, options.roll)
    projected = vertices @ np.column_stack((right, up, forward))
    used = projected[indices.reshape(-1)]
    low, high = used[:, :2].min(axis=0), used[:, :2].max(axis=0)
    width, height = (
        options.width * options.supersample,
        options.height * options.supersample,
    )
    span = np.maximum(high - low, 1e-9)
    scale = (
        min(width / span[0], height / span[1])
        * (1 - 2 * options.padding)
        * options.zoom
    )
    center = (low + high) / 2
    screen = projected.copy()
    screen[:, 0] = width / 2 + (projected[:, 0] - center[0]) * scale
    screen[:, 1] = height / 2 - (projected[:, 1] - center[1]) * scale
    pixels = np.empty((height, width, 4), dtype=np.uint8)
    pixels[:] = _background(options.background)
    depth = np.full((height, width), np.inf)
    texture = model.texture
    th, tw = texture.shape[:2]
    light = np.array(options.light_direction, dtype=float, copy=True)
    light /= np.linalg.norm(light)
    normals *= np.where(normals @ forward > 0, -1, 1)[:, None]
    shades = options.ambient + (1 - options.ambient) * np.maximum(0, normals @ light)
    srgb = np.arange(256) / 255
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    for triangle, shade in zip(indices, shades):
        a, b, c = screen[triangle]
        minx = max(0, math.floor(min(a[0], b[0], c[0])))
        maxx = min(width, math.ceil(max(a[0], b[0], c[0])))
        miny = max(0, math.floor(min(a[1], b[1], c[1])))
        maxy = min(height, math.ceil(max(a[1], b[1], c[1])))
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if minx >= maxx or miny >= maxy or abs(denominator) < 1e-10:
            continue
        x, y = np.meshgrid(np.arange(minx, maxx) + 0.5, np.arange(miny, maxy) + 0.5)
        wa = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / denominator
        wb = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / denominator
        wc = 1 - wa - wb
        z = wa * a[2] + wb * b[2] + wc * c[2]
        window = depth[miny:maxy, minx:maxx]
        mask = (wa >= -1e-9) & (wb >= -1e-9) & (wc >= -1e-9) & (z <= window + 1e-10)
        iy, ix = np.nonzero(mask)
        if not len(iy):
            continue
        tex = (
            wa[iy, ix, None] * uvs[triangle[0]]
            + wb[iy, ix, None] * uvs[triangle[1]]
            + wc[iy, ix, None] * uvs[triangle[2]]
        )
        tx = np.clip(np.floor(tex[:, 0] * tw).astype(int), 0, tw - 1)
        ty = np.clip(np.floor(tex[:, 1] * th).astype(int), 0, th - 1)
        rgba = texture[ty, tx]
        opaque = (rgba[:, 3] > 0) & (rgba[:, 3] >= options.alpha_cutoff)
        iy, ix, rgba = iy[opaque], ix[opaque], rgba[opaque]
        rgb = rgba[:, :3]
        if options.shading == "lit":
            color = linear[rgb] * shade
            color = np.where(
                color <= 0.0031308, color * 12.92, 1.055 * color ** (1 / 2.4) - 0.055
            )
            rgb = np.clip(np.rint(color * 255), 0, 255).astype(np.uint8)
        pixels[miny + iy, minx + ix, :3] = rgb
        pixels[miny + iy, minx + ix, 3] = 255
        window[iy, ix] = z[iy, ix]
    image = Image.fromarray(pixels)
    if options.supersample > 1:
        image = image.resize((options.width, options.height), Image.Resampling.LANCZOS)
    image.info["Model"] = str(model.name)
    image.info["Renderer"] = "ysm-render Python CPU"
    metadata = model.info.get("metadata", {})
    license = metadata.get("license")
    if license:
        image.info["License"] = str(
            license.get("type", license) if isinstance(license, dict) else license
        )
    if metadata.get("authors"):
        image.info["Authors"] = ", ".join(
            str(author.get("name", "")) if isinstance(author, dict) else str(author)
            for author in metadata["authors"]
        )
    return image


def render_to_file(model, output, options=None, **parameters):
    """Render a PNG, creating its parent directory, and return its absolute Path."""
    image = render(model, options, **parameters)
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = PngImagePlugin.PngInfo()
    for key, value in image.info.items():
        metadata.add_text(key, str(value))
    image.save(output, format="PNG", pnginfo=metadata)
    return output
