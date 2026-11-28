"""Fit the standalone computer and furniture details to the room."""

from math import pi
from pathlib import Path

import bpy
from mathutils import Matrix


_PC_DETAILS = {
    "pc-case": ("Top I/O", "USB-C", "USB-A", "Headphone jack"),
    "graphics-card": ("Dual-slot I/O", "PCIe edge PCB", "12V power socket", "PCIe gold",
                      "HDMI ", "DisplayPort ", "Bracket retention screw"),
    "motherboard": ("CPU socket frame", "CPU metal load plate", "Socket latch arm",
                    "PCIe x16", "PCIe latch", "ATX ", "Chipset heatsink", "Rear I/O block",
                    "DIMM ", "PCB routed conductor", "Solder landing pad", "PCB white"),
    "rgb-ram": ("DIMM ", "Slotted DIMM"),
    "cooling-pump": ("AIO metal crimp", "AIO rubber strain", "Radiator "),
    "braided-power-cables": ("Keyed cable connector", "Connector retention latch",
                             "Braided sleeve strain relief"),
}
_FAN_PARTS = ("Open-through fan", "RGB ring segment", "Anti-vibration corner", "Steel fan screw",
              "Slotted screw", "Rear motor strut", "Fan ", "Swept fan blade", "Recessed PWM")
_DRAWER_PARTS = ("Drawer ", "Hollow cabinet", "Fixed outer rail", "Cabinet rail travel",
                 "Sliding inner rail", "Desk - walnut drawer", "Desk - brass ")
_CHAIR_PARTS = ("Height control mechanism", "Pneumatic height", "Height lever")


def _load(scene, assets, slug, prefixes):
    path = assets / slug / "model.blend"
    with bpy.data.libraries.load(str(path), link=False) as (available, imported):
        imported.objects = [name for name in available.objects if name.startswith(prefixes)]
    assert imported.objects, (slug, prefixes)
    collection = bpy.data.collections.new(f"Fitted · {slug}")
    scene.collection.children.link(collection)
    parts = [part for part in imported.objects if part]
    for part in parts:
        collection.objects.link(part)
        part.name = f"Fitted {slug} / {part.name}"
        part["standalone_asset"] = slug
    bpy.context.view_layer.update()
    return collection, parts


def _attach(parts, anchor, transform):
    """Transform only the imported roots so the drawer and fan pivots stay editable."""
    bpy.context.view_layer.update()
    anchor_inverse = anchor.matrix_world.inverted()
    for part in parts:
        if part.parent not in parts:
            world = transform(part) @ part.matrix_world
            part.parent = anchor
            part.matrix_parent_inverse = Matrix.Identity(4)
            part.matrix_basis = anchor_inverse @ world


def _hide(parts):
    for part in parts:
        part.hide_render = True
        part.hide_set(True)


def _wire_light(parts, group, receivers=None):
    for part in parts:
        if part.type in {"MESH", "CURVE", "FONT"}:
            part.lightgroup = group
            if receivers is not None:
                receivers.objects.link(part)


def apply_pc(scene, assets):
    """Install new case parts, usable drawers, and chair controls in the room."""
    assets = Path(assets).resolve()
    case = scene.objects["PC - Aurora panoramic tower"]
    fill = scene.objects["Neutral fill through the PC glass"].light_linking.receiver_collection
    assert fill is not None
    identity = Matrix.Identity(4)
    counts = {}
    for slug, prefixes in _PC_DETAILS.items():
        collection, parts = _load(scene, assets, slug, prefixes)
        mount = bpy.data.objects.new(f"Mount for {slug}", None)
        collection.objects.link(mount)
        mount.parent = case
        _attach(parts, mount, lambda _part: identity)
        _wire_light(parts, "PC case and LEDs", fill if slug != "pc-case" else None)
        counts[slug] = len(parts)

    collection, fans = _load(scene, assets, "rgb-fans", _FAN_PARTS)
    mount = bpy.data.objects.new("Mount for rgb-fans", None)
    collection.objects.link(mount)
    mount.parent = case
    case_world = case.matrix_world.copy()
    diagonal = Matrix.Diagonal((.82, .95, .93, 1))
    heights = (.14, .44, .74)
    positions = (.49, .88, 1.27)

    def fan_frame(part):
        slot = min(range(3), key=lambda i: abs(heights[i] - part.matrix_world.translation.z))
        return (case_world @ Matrix.Translation((.335, .057, positions[slot]))
                @ diagonal @ Matrix.Translation((0, 0, -heights[slot])))

    old_fans = [part for part in case.children
                if part.name.startswith(("PC - fan housing", "PC - fan blade", "PC - fan hub",
                                         "PC - fan RGB ring"))]
    assert len(old_fans) == 63, len(old_fans)
    _attach(fans, mount, fan_frame)
    _wire_light(fans, "PC case and LEDs")
    _hide(old_fans)
    counts["rgb-fans"] = len(fans)

    old_drawers = [obj for obj in scene.objects if obj.name.startswith(
        ("Desk - drawer case", "Desk - walnut drawer", "Desk - brass handle", "Desk - brass pull"))]
    assert len(old_drawers) == 13, len(old_drawers)
    _, drawers = _load(scene, assets, "walnut-desk", _DRAWER_PARTS)
    assert sum(part.type == "EMPTY" for part in drawers) == 3
    _wire_light(drawers, "Desk and chair")
    _hide(old_drawers)
    counts["walnut-desk"] = len(drawers)

    _, controls = _load(scene, assets, "rolling-chair", _CHAIR_PARTS)
    chair = scene.objects["Chair - ergonomic office chair"]
    point = chair.matrix_world.translation
    inverse = (Matrix.Translation(point)
               @ Matrix.Rotation(chair.rotation_euler.z - pi, 4, "Z")
               @ Matrix.Translation(-point))
    _attach(controls, chair, lambda _part: inverse)
    receivers = scene.objects["Chair - warm ruby rim"].light_linking.receiver_collection
    _wire_light(controls, "Desk and chair", receivers)
    bpy.context.view_layer.update()
    counts["rolling-chair"] = len(controls)
    return {
        "installed_from_items": counts,
        "retained_named_shells": [
            "PC case shell, glass, visible RTX label, chassis, RGB emitters and harness routes",
            "desk worktop and trim", "chair seat and casters",
        ],
        "replaced_scene_parts": {"fan_parts": len(old_fans), "drawer_parts": len(old_drawers)},
    }
