"""Align the floor monitor feet, keyboard mat and USB lead with the floor surfaces."""
import math

import bpy
from mathutils import Vector


def _world_z(obj):
    heights = [(obj.matrix_world @ Vector(corner)).z for corner in obj.bound_box]
    return min(heights), max(heights)


def _split_at_rug_edge(outline, distance):
    """Split the desk mat at the rug's left edge while keeping the top level."""
    left, right = [], []
    for a, b in zip(outline, outline[1:] + outline[:1]):
        da, db = distance(a), distance(b)
        (right if da >= 0 else left).append(a)
        if da * db < 0:
            intersection = a.lerp(b, da / (da - db))
            left.append(intersection)
            right.append(intersection)
    return left, right


def _mat_mesh(pad, keyboard, rug, rug_height, top):
    rug_inverse = rug.matrix_world.inverted()
    left_edge = min(p[0] for p in rug.bound_box)
    keyboard_matrix = keyboard.matrix_world
    inverse = pad.matrix_world.inverted()

    def distance(point):
        return (rug_inverse @ point).x - left_edge

    outline = [
        keyboard_matrix @ Vector((x, y, 0))
        for x, y in [(-.347,-.127), (.347,-.127), (.347,.146), (-.347,.146)]
    ]
    left, right = _split_at_rug_edge(outline, distance)
    vertices, faces = [], []
    for shape, bottom in ((left, 0), (right, rug_height)):
        if not shape:
            continue
        first = len(vertices)
        count = len(shape)
        vertices.extend(inverse @ Vector((p.x, p.y, z)) for z in (bottom, top) for p in shape)
        faces.append(tuple(reversed(range(first, first + count))))
        faces.append(tuple(range(first + count, first + 2 * count)))
        for i in range(count):
            a, b = first + i, first + (i + 1) % count
            faces.append((a, b, b + count, a + count))
    mesh = bpy.data.meshes.new("Floor keyboard mat - level top and stepped underside")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(pad.data.materials[0])
    pad.data = mesh
    for mod in pad.modifiers:
        if mod.type == "BEVEL":
            mod.width = .00045
            mod.segments = 2


def _route_usb(lead, keyboard):
    """Guide the lead around the left monitor foot and into the case's rear."""
    start = keyboard.matrix_world @ Vector((0, .099, .022))
    data = lead.data
    data.bevel_depth = .0057
    data.resolution_u = 12
    data.splines.clear()
    path = [
        start, (-1.385,.227,.023), (-1.492,.243,.0184),
        (-1.531,.262,.0184), (-1.62,.281,.007),
        (-1.82,.318,.0068), (-1.99,.397,.0068), (-2.08,.468,.0068),
        (-2.105,.56,.0068), (-2.132,.70,.0068), (-2.16,.84,.0068),
        (-2.29,1.05,.010),
        (-2.31,1.24,.090),
    ]
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(path) - 1)
    path = [Vector(p) for p in path]
    for index, point in enumerate(spline.bezier_points):
        position = path[index]
        previous = path[max(0,index-1)]
        following = path[min(len(path)-1,index+1)]
        tangent = following - previous
        tangent.z = 0
        tangent.normalize()
        point.co = position
        # Horizontal handles keep the lead from dipping into the hardwood.
        point.handle_left_type = point.handle_right_type = "FREE"
        point.handle_left = position - tangent * (position - previous).length / 3
        point.handle_right = position + tangent * (following - position).length / 3


def apply_hardware_polish(scene):
    """Preserve both panel poses and ground their accessories on the correct surface."""
    objs = scene.objects
    rug = objs["Vintage woven area rug"]
    rug_height = _world_z(rug)[1]
    right_base = objs["Floor monitor right stand base"]
    base_shift = rug_height - _world_z(right_base)[0]
    right_base.location.z += base_shift
    neck = objs["Floor monitor right tilt neck"]
    if base_shift > .00001:
        zmin = min(v.co.z for v in neck.data.vertices)
        for vert in neck.data.vertices:
            if math.isclose(vert.co.z, zmin, abs_tol=.00001):
                vert.co.z += base_shift
        neck.data.update()

    keyboard = objs["Floor keyboard"]
    keyboard.location.y = .121
    pad_top = rug_height + .003
    keyboard.location.z = pad_top
    bpy.context.view_layer.update()
    _mat_mesh(objs["Floor keyboard mat"], keyboard, rug, rug_height, pad_top)
    _route_usb(objs["Floor keyboard USB cable"], keyboard)
    bpy.context.view_layer.update()
    left_z = _world_z(objs["Floor monitor left stand base"])[0]
    right_z = _world_z(right_base)[0]
    assert abs(left_z) < .0001 and abs(right_z - rug_height) < .0001
    assert abs(_world_z(objs["Floor keyboard - lower case"])[0] - pad_top) < .0001
    return {
        "left_monitor_base_bottom_z": round(left_z, 5),
        "right_monitor_base_bottom_z": round(right_z, 5),
        "rug_height": round(rug_height, 5),
        "panel_transforms_preserved": True,
        "keyboard_mat_dimensions": [.694, .273],
        "keyboard_mat_top_z": round(pad_top, 5),
        "keyboard_center": [round(v, 5) for v in keyboard.location],
        "usb_route": "Grounded sweep around the front-left monitor stand and back to the case",
    }
