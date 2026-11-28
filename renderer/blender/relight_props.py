"""Reposition the existing shelf and case light sources."""

import math

from mathutils import Vector


def _aim(light, target):
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()


def refine_props(scene):
    """Rake the right shelves and fill the hardware through the front glass."""
    right = scene.objects["East brick library and oak shelves"]
    strips = [obj for obj in right.children if obj.type == "LIGHT"
              and obj.name.startswith("Warm linear library bounce")]
    assert len(strips) == 3
    for light in strips:
        x, _, z = light.location
        light.location = (x+.018, 1.946, z-.019)
        _aim(light, (x-.084, 2.358, z-.343))
        light.data.energy = 9.6
        light.data.spread = math.radians(134)
        light.data.size_y = .046

    crown = scene.objects["Soft glow across upper right books and ivy"]
    crown.location = (2.99, 1.45, 3.10)
    _aim(crown, (2.65, 2.24, 2.85))
    crown.data.energy = 6.6
    crown.data.spread = math.radians(125)

    case = scene.objects["PC - Aurora panoramic tower"]
    fill = scene.objects["Neutral fill through the PC glass"]
    receivers = fill.light_linking.receiver_collection
    assert receivers is not None
    harness = [part for part in case.children if part.name.startswith("GPU rightward braided harness")]
    assert len(harness) == 7
    for part in harness:
        if part.name not in receivers.objects:
            receivers.objects.link(part)
    fill.location = case.matrix_world @ Vector((-.015,-.56,1.25))
    _aim(fill, case.matrix_world @ Vector((.025,-.075,.92)))
    fill.data.energy = 4.7
    fill.data.color = (.91,.83,1)
    fill.data.shape = "RECTANGLE"
    fill.data.size = .48
    fill.data.size_y = .19
    fill.data.spread = math.radians(118)
    return {
        "shelf_strip_lights": [light.name for light in sorted(strips,key=lambda obj: obj.location.z)],
        "shelf_strip_energy_w": 9.6,
        "upper_shelf_fill_energy_w": 6.6,
        "pc_fill_energy_w": round(fill.data.energy, 2),
        "pc_fill_location": [round(value, 4) for value in fill.location],
        "pc_braided_cable_receivers": len(harness),
        "pc_fill_receiver_count": len(receivers.objects),
    }
