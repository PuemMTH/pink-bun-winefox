"""Move the floor station and keep its contact points on the new surfaces."""

import math

import bpy
from mathutils import Vector
from mathutils.geometry import interpolate_bezier

from polish_hardware import _split_at_rug_edge, _world_z


MAT_BOUNDS = ((-.347, .347), (-.127, .146))


def _outline(obj, bounds=None):
    if bounds is None:
        bounds = tuple((min(p[i] for p in obj.bound_box), max(p[i] for p in obj.bound_box))
                       for i in range(2))
    (xmin, xmax), (ymin, ymax) = bounds
    return [obj.matrix_world @ Vector((x, y, 0))
            for x, y in ((xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax))]


def _rug_regions(outline, rug_bounds):
    """Partition a footprint into the part on the rug and the parts off its four edges."""
    hardwood = []
    for axis, (low, high) in enumerate(rug_bounds):
        for bound, direction in ((low, 1), (high, -1)):
            off_rug, outline = _split_at_rug_edge(
                outline, lambda point: direction * (point[axis] - bound))
            if len(off_rug) >= 3:
                hardwood.append(off_rug)
    return outline if len(outline) >= 3 else [], hardwood


def _seat_stand(base, neck, height):
    shift = height - _world_z(base)[0]
    if abs(shift) < 1e-6:
        return
    base.location.z += shift
    bottom = min(vert.co.z for vert in neck.data.vertices)
    for vert in neck.data.vertices:
        if math.isclose(vert.co.z, bottom, abs_tol=1e-6):
            vert.co.z += shift
    neck.data.update()


def _build_mat(pad, regions, top):
    inverse = pad.matrix_world.inverted()
    vertices, faces = [], []
    for shape, bottom in regions:
        first, count = len(vertices), len(shape)
        lower = list(range(first, first + count))
        upper = [i + count for i in lower]
        vertices.extend(inverse @ Vector((p.x, p.y, z)) for z in (bottom, top) for p in shape)
        faces.extend((lower[::-1], upper))
        for a, b in zip(lower, lower[1:] + lower[:1]):
            faces.append((a, b, b + count, a + count))
    original = pad.data
    mesh = bpy.data.meshes.new(original.name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(original.materials[0])
    pad.data = mesh
    if original.users == 0:
        bpy.data.meshes.remove(original)


def _inside(point, bounds, margin=0):
    return all(low - margin <= point[axis] <= high + margin
               for axis, (low, high) in enumerate(bounds))


def _route_lead(lead, keyboard, floor_shift, case_transform, floor_at, stands, waypoints=None):
    inverse = lead.matrix_world.inverted()
    data = lead.data
    controls = [lead.matrix_world @ point.co for point in data.splines[0].bezier_points]
    if waypoints is None:
        waypoints = [point + floor_shift for point in controls[1:-2]]
    start = keyboard.matrix_world @ Vector((0, .099, .022))
    controls = [start, *waypoints, *(case_transform @ point for point in controls[-2:])]

    clearance = data.bevel_depth + .0011

    def ground(point):
        return floor_at(point, .012) + clearance

    path = [controls[0]]
    for index, (start, end) in enumerate(zip(controls, controls[1:]), 1):
        length = (end.xy - start.xy).length
        count = max(2, math.ceil(length / .010))
        previous = ground(start)
        # Add knots at surface changes so the last bend can follow the rug edge.
        for step in range(1, count + 1):
            factor = step / count
            height = ground(start.lerp(end, factor))
            if height != previous:
                high_factor = max(0, factor - 1 / count) if height > previous else factor
                low_factor = (max(0, high_factor - .025 / length) if height > previous
                              else min(1, high_factor + .025 / length))
                heights = [(low_factor, min(previous, height)), (high_factor, max(previous, height))]
                for knot, z in sorted(heights):
                    if 0 < knot < 1:
                        p = start.lerp(end, knot)
                        p.z = z
                        if (path[-1].xy - p.xy).length > .001:
                            path.append(p)
                previous = height
        end = end.copy()
        if index < len(controls) - 1:
            end.z = ground(end)
        path.append(end)

    data.splines.clear()
    spline = data.splines.new('BEZIER')
    spline.bezier_points.add(len(path) - 1)
    for i, (point, position) in enumerate(zip(spline.bezier_points, path)):
        before = path[max(0, i - 1)]
        after = path[min(len(path) - 1, i + 1)]
        tangent = (after - before).xy.to_3d().normalized()
        point.handle_left_type = point.handle_right_type = 'FREE'
        point.co = inverse @ position
        point.handle_left = inverse @ (position - tangent * (position.xy - before.xy).length / 3)
        point.handle_right = inverse @ (position + tangent * (after.xy - position.xy).length / 3)

    points = spline.bezier_points
    samples = [lead.matrix_world @ v for start, end in zip(points, points[1:])
               for v in interpolate_bezier(start.co, start.handle_right, end.handle_left, end.co, 32)]
    stand_gaps = {}
    for stand in stands:
        inverse = stand.matrix_world.inverted()
        bounds = tuple((min(p[i] for p in stand.bound_box), max(p[i] for p in stand.bound_box))
                       for i in range(3))
        gap = min(math.hypot(*(max(low - point[i], 0, point[i] - high)
                               for i, (low, high) in enumerate(bounds)))
                  for point in (inverse @ p for p in samples))
        stand_gaps[stand.parent.name] = round(gap - data.bevel_depth, 5)
    return {
        'keyboard_connector': [round(value, 5) for value in path[0]],
        'case_connector': [round(value, 5) for value in path[-1]],
        'minimum_surface_gap': round(min(p.z - data.bevel_depth - floor_at(p) for p in samples), 5),
        'minimum_stand_gaps': stand_gaps,
    }


def _face_reader(objs):
    root = objs['On floor - Character root']
    rig = next(child for child in root.children if child.type == 'ARMATURE')
    eyes = (rig.matrix_world @ rig.pose.bones['Eyes'].matrix).translation
    eye_target = eyes + root.matrix_world.to_quaternion() @ Vector((0, .10, 0))

    displays = [objs[f'Floor monitor {side}'] for side in ('left', 'right')]
    for display, position in zip(displays, ((-1.77, -.30), (-1.18, -.74))):
        display.location.xy = position
        to_reader = eye_target - display.location
        display.rotation_euler.z = math.atan2(to_reader.x, -to_reader.y)

    keyboard, pad = objs['Floor keyboard'], objs['Floor keyboard mat']
    keyboard.location.xy = (-1.19, -.25)
    keyboard.rotation_euler.z = sum(display.rotation_euler.z for display in displays) / len(displays)
    pad.location.xy = keyboard.location.xy
    pad.rotation_euler.z = keyboard.rotation_euler.z
    return eye_target


def move_floor_station(scene, *, floor_display_delta, case_delta, case_yaw=0.0, face_reader=False):
    """Translate the displays and relocate the case to its new yaw in degrees."""
    objs = scene.objects
    floor_shift = Vector((*floor_display_delta, 0))
    case_shift = Vector((*case_delta, 0))
    for name in ('Floor monitor left', 'Floor monitor right', 'Floor keyboard', 'Floor keyboard mat'):
        objs[name].location += floor_shift
    eye_target = _face_reader(objs) if face_reader else None
    case = objs['PC - Aurora panoramic tower']
    previous_case = case.matrix_world.copy()
    case.location += case_shift
    case.rotation_euler.z = math.radians(case_yaw)
    bpy.context.view_layer.update()
    case_transform = case.matrix_world @ previous_case.inverted()
    for name in ('Neutral fill through the PC glass', 'Small honey reflection beneath PC'):
        light = objs[name]
        light.matrix_world = case_transform @ light.matrix_world

    rug = objs['Vintage woven area rug']
    rug_corners = _outline(rug)
    rug_bounds = tuple((min(p[i] for p in rug_corners), max(p[i] for p in rug_corners)) for i in range(2))
    rug_height = _world_z(rug)[1]
    stands = {}
    bases = []
    for side in ('left', 'right'):
        base = objs[f'Floor monitor {side} stand base']
        neck = objs[f'Floor monitor {side} tilt neck']
        rug_region, exposed = _rug_regions(_outline(base), rug_bounds)
        _seat_stand(base, neck, rug_height if rug_region else 0)
        stands[side] = {'surface': 'rug' if rug_region else 'hardwood', 'crosses_rug_edge': bool(rug_region and exposed)}
        bases.append(base)

    keyboard = objs['Floor keyboard']
    pad = objs['Floor keyboard mat']
    rug_region, exposed = _rug_regions(_outline(keyboard, MAT_BOUNDS), rug_bounds)
    pad_top = (rug_height if rug_region else 0) + .003
    keyboard.location.z = pad_top
    regions = [(shape, 0) for shape in exposed]
    if rug_region:
        regions.append((rug_region, rug_height))
    _build_mat(pad, regions, pad_top)
    bpy.context.view_layer.update()

    keyboard_inverse = keyboard.matrix_world.inverted()

    def floor_at(point, margin=0):
        if _inside(keyboard_inverse @ point, MAT_BOUNDS, margin):
            return pad_top
        return rug_height if _inside(point, rug_bounds, margin) else 0

    waypoints = None
    if face_reader:
        # Go between the stands, around the left base and along the outside of the case.
        waypoints = [keyboard.matrix_world @ Vector((0, .172, 0)),
                     *(Vector((x, y, 0)) for x, y in ((-1.43, -.49), (-1.60, -.56),
                                                     (-1.87, -.57), (-2.03, -.47), (-2.10, -.26),
                                                     (-2.12, .03), (-2.20, .40), (-2.51, .79),
                                                     (-2.73, 1.01), (-2.78, 1.18)))]
    cable = _route_lead(objs['Floor keyboard USB cable'], keyboard, floor_shift, case_transform, floor_at, bases,
                        waypoints=waypoints)
    for side, contact in stands.items():
        contact['bottom_z'] = round(_world_z(objs[f'Floor monitor {side} stand base'])[0], 5)

    return {
        'floor_display_delta': list(floor_display_delta),
        'case_delta': list(case_delta),
        'case_yaw_degrees': case_yaw,
        'case_foot_contacts': [{'bottom_z': round(_world_z(foot)[0], 5),
                               'surface': 'rug' if _rug_regions(_outline(foot), rug_bounds)[0] else 'hardwood'}
                              for foot in case.children if foot.name.startswith('PC - rubber foot')],
        'monitor_stands': stands,
        'reader_eye_target': [round(value, 5) for value in eye_target] if eye_target is not None else None,
        'floor_displays': {side: {'center': [round(value, 5) for value in display.location],
                                 'yaw_degrees': round(math.degrees(display.rotation_euler.z), 3)}
                           for side, display in ((side, objs[f'Floor monitor {side}']) for side in stands)},
        'keyboard_center': [round(value, 5) for value in keyboard.location],
        'keyboard_yaw_degrees': round(math.degrees(keyboard.rotation_euler.z), 3),
        'keyboard_mat_top_z': round(pad_top, 5),
        'keyboard_bottom_z': round(_world_z(objs['Floor keyboard - lower case'])[0], 5),
        'keyboard_mat_underside_z': sorted({round(bottom, 5) for _, bottom in regions}),
        'case_fill_location': [round(value, 5) for value in objs['Neutral fill through the PC glass'].location],
        'usb_cable': cable,
    }
