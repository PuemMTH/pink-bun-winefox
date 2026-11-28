"""Fit model-library peripherals to their established room anchors."""

from math import pi
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


class Peripherals:
    def __init__(self, scene, assets):
        self.scene = scene
        self.assets = Path(assets)
        self.collection = bpy.data.collections.new("Assembled · peripherals")
        scene.collection.children.link(self.collection)
        self.built = {}

    def load(self, slug, select):
        path = self.assets / slug / "model.blend"
        with bpy.data.libraries.load(str(path), link=False) as (available, loaded):
            names = tuple(name for name in available.objects if select(name))
            if not names:
                raise ValueError(f"No required geometry in {path}")
            loaded.objects = list(names)
        return dict(zip(names, loaded.objects))

    def place(self, slug, objects, transform, lightgroup=""):
        for name, obj in objects.items():
            basis = obj.matrix_basis.copy()
            obj.name = f"Fitted {slug} / {name}"
            obj.parent = None
            obj.hide_render = obj.hide_viewport = False
            obj.lightgroup = lightgroup
            self.collection.objects.link(obj)
            obj.matrix_world = transform @ basis
        self.built[slug] = self.built.get(slug, 0) + len(objects)


def _hide(objects):
    for obj in objects:
        obj.hide_render = obj.hide_viewport = True


def _scale(x, y, z):
    return Matrix.Diagonal((x, y, z, 1))


def _origin(obj):
    return Matrix.Translation(obj.matrix_world.translation) @ obj.matrix_world.to_quaternion().to_matrix().to_4x4()


def _screens(kit, room):
    sets = {
        "minecraft-monitors": [f"Main monitor {c}.{r}" for r in (2, 1) for c in (1, 2, 3)]
        + ["Floor monitor left", "Floor monitor right"],
        "code-monitors": ["Right code monitor 1", "Right code monitor 2"],
    }
    stand_presets = [(1, .29), (2, .31), (3, 1.17), (4, 1.17), (5, 1.17), (6, 1.27)]
    stand_targets = ["Floor monitor left", "Floor monitor right"] + [f"Main monitor {i} rear support" for i in range(1, 4)] + ["Code monitor pole"]
    for slug, names in sets.items():
        geometry = kit.load(slug, lambda name: any(name.startswith(prefix+" ") and " display" not in name for prefix in names))
        for i, name in enumerate(names):
            anchor = room[name]
            if slug == "code-monitors":
                source = Vector((0, 0, (.342, .955)[i]))
            else:
                source = Vector(((i % 4 - 1.5) * .961, 0, (1.03, .35)[i // 4]))
            trim = {key: obj for key, obj in geometry.items() if key.startswith(name+" ")}
            # Fit the bevel on the existing emissive plane's back side.
            transform = _origin(anchor) @ _scale(1, .965, 1) @ Matrix.Translation(-source)
            kit.place(slug, trim, transform, room[name+" display"].lightgroup)
            _hide([room[name+" casing"]])
    for name, (index, height) in zip(stand_targets, stand_presets):
        prefix = f"Stand {index:02} "
        is_floor = index <= 2
        anchors = ("upright column", "cable channel insert")
        base_parts = ("weighted beveled base", "non-slip pad")
        objects = kit.load("monitor-stands", lambda key: key.startswith(prefix) and any(word in key for word in anchors + (base_parts if is_floor else ())))
        upright = {key: o for key, o in objects.items() if any(word in key for word in anchors)}
        support = room[name+" tilt neck"] if is_floor else room[name]
        x = (index-1-2.5)*.49
        depth = support.dimensions
        transform = _origin(support) @ _scale(depth.x/.072, depth.y/.060, depth.z/height) @ Matrix.Translation((-x, -.044, -height/2))
        kit.place("monitor-stands", upright, transform, support.lightgroup)
        _hide([support])
        if is_floor:
            base = room[name+" stand base"]
            parts = {key: o for key, o in objects.items() if any(word in key for word in base_parts)}
            # Compress the anti-slip pads into the fixed footprint without moving its bottom edge.
            transform = _origin(base) @ _scale(1, 1, .026/.029) @ Matrix.Translation((-x, 0, -.0115))
            kit.place("monitor-stands", parts, transform, base.lightgroup)
            _hide([base])


def _fit_mats(kit, room):
    for index, name, old_names, w, d, origin_y in (
        (1, "Desk - mat stitched perimeter", ("Desk - mat stitched perimeter", "Desk - woven mat surface"), 1.44, .29, .21),
        (2, "Floor keyboard mat", ("Floor keyboard mat",), .694, .273, -.13),
    ):
        base = room[name]
        old = [room[key] for key in old_names]
        top = max((obj.matrix_world @ Vector(point)).z for obj in old for point in obj.bound_box)
        thickness = top-min((obj.matrix_world @ Vector(point)).z for obj in old for point in obj.bound_box)
        prefix = f"Mat {index} "
        objs = kit.load("keyboard-mouse-mats", lambda key: key.startswith(prefix))
        origin = _origin(base)
        origin.translation.z = top-thickness
        scale_z = thickness/.0123
        transform = origin @ _scale(base.dimensions.x/w, base.dimensions.y/d, scale_z) @ Matrix.Translation((0,-origin_y,0))
        kit.place("keyboard-mouse-mats", objs, transform, base.lightgroup)
        _hide(old)


def _usb(kit, lead, socket, direction, scale, case_end=False):
    # USB-C male tip and cable-entry positions in the authored specimen.
    origin = Vector((-.144,-.0896,.005))
    align = Vector((0,-1,0)).rotation_difference(direction).to_matrix().to_4x4()
    transform = Matrix.Translation(socket) @ align @ _scale(scale,scale,scale) @ Matrix.Translation(-origin)
    end_parts = kit.load("usb-cable", lambda name: name.startswith("USB-C 1 "))
    kit.place("usb-cable", end_parts, transform, lead.lightgroup)
    points = lead.data.splines[0].bezier_points
    old = points[-1] if case_end else points[0]
    inlet = transform @ Vector((-.144,-.058,.005))
    delta = lead.matrix_world.inverted() @ inlet - old.co
    for point, fraction in zip(reversed(points) if case_end else points, (1,.61,.22)):
        offset = delta*fraction
        point.co += offset
        point.handle_left += offset
        point.handle_right += offset


def _keyboards(kit, room):
    for name, variant, oy, lead_name, group in (
        ("Desk RGB keyboard", "TKL A", .083, "Desk - keyboard lead", "Desk and chair"),
        ("Floor keyboard", "TKL B", -.083, "Floor keyboard USB cable", "Floor displays"),
    ):
        parent = room[name]
        old = list(parent.children_recursive)
        shell = room[name+" - lower case"]
        scale = _scale(shell.dimensions.x/.367, shell.dimensions.y/.137, .053/.0405)
        mat = _origin(parent) @ scale @ Matrix.Translation((0,-oy,.0008))
        templates = kit.load("keyboards", lambda key: key.startswith(variant+" "))
        kit.place("keyboards", templates, mat, group)
        _hide(old)
        lead = room[lead_name]
        transform = _origin(parent).to_3x3()
        socket = mat @ Vector((-.132,oy+.06935,.012))
        _usb(kit, lead, socket, transform @ Vector((0,-1,0)), shell.dimensions.x/.367)
        if name == "Floor keyboard":
            path = lead.data.splines[0].bezier_points
            tip = lead.matrix_world @ path[-1].co
            direction = (lead.matrix_world @ path[-1].co - lead.matrix_world @ path[-1].handle_left).normalized()
            _usb(kit, lead, tip, direction, 1.3, case_end=True)
        if lead_name == "Desk - keyboard lead":
            lead.location.z += .001


def _small_props(kit, room):
    mouse = room["Desk - low-profile graphite mouse"]
    center = mouse.matrix_world.translation.copy()
    center.z -= mouse.dimensions.z/2
    transform = Matrix.Translation(center) @ Matrix.Rotation(pi, 4, "Z") @ _scale(mouse.dimensions.x/.071,mouse.dimensions.y/.118,1.5)
    kit.place("mouse", kit.load("mouse", lambda name: name not in {"FRONT","BACK","RIGHT","LEFT","TOP","BUTTOM"} and "softbox" not in name.lower() and name not in {"Front fill","Underside fill"}), transform, mouse.lightgroup)
    _hide([mouse, room["Desk - mouse scroll wheel"]])

    originals = {
        "headphones": ("Desk - headphone", "Desk - headband rest", "Desk - sculpted headphone"),
        "beverage-can": ("Desk - beverage can", "Desk - soda can lower rim", "Desk - soda can lid", "Desk - wrapped drink can stripe", "Desk - can pull tab"),
    }
    for slug, prefixes in originals.items():
        old = [obj for obj in room if obj.name.startswith(prefixes)]
        parts = kit.load(slug, lambda key: key.startswith(prefixes + ("Stand underside", "Soft headband",
                         "Headphone volume", "Headphone size", "Headphone hinge", "Rolled aluminum",
                         "Oval aluminum", "Pull-tab", "Scored oval")))
        kit.place(slug, parts, Matrix.Identity(4), "Desk and chair")
        _hide(old)

    phone = room["Phone in hands"]
    transform = _origin(phone) @ _scale(phone.dimensions.x/.082, phone.dimensions.y/.0092, phone.dimensions.z/.158)
    transform @= Matrix.Translation((0,0,-.079))
    names = ("Graphite rounded", "Back matte", "Single laminated", "Screen dark", "Mock", "Cool grey", "Home gesture",
             "Single rear", "Rear LED", "Sound volume", "Single power", "Bottom")
    kit.place("phone", kit.load("phone", lambda key: key.startswith(names)), transform, phone.lightgroup)
    _hide([phone, *phone.children_recursive])


def apply_peripherals(scene, assets):
    """Install the standalone models and keep the mounted screen emission and posing."""
    kit = Peripherals(scene, assets)
    room = scene.objects
    _screens(kit, room)
    _fit_mats(kit, room)
    _keyboards(kit, room)
    _small_props(kit, room)
    bpy.context.view_layer.update()
    assert all(o.type in {"MESH", "CURVE", "FONT"} for o in kit.collection.objects)
    assert all(o.name == f"{name} display" and not o.hide_render
               for name in (root.name for root in room if root.get("screen_source"))
               for o in (room[name+" display"],))
    return {"replacement_parts": kit.built, "mounted_display_shaders": "original 10 panels retained"}
