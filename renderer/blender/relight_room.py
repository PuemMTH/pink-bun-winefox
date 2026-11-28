"""Rebalance the monitor-room lights and render the saved camera views."""

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from polish_room import OUTPUT as BASE_ROOM
from polish_room import configure_gpu, rig_dimensions, validate
from sunset_city import camera

OUTPUT = BASE_ROOM.with_name('monitor-room-lighting')
TOP_CAMERA = '04 High room overview'


def top_view(scene):
    if existing := scene.objects.get(TOP_CAMERA):
        return existing
    view = camera(TOP_CAMERA, (-.70, -3.78, 3.86), (.10, .75, .90), 20.9)
    roof = scene.objects['Ceiling']
    underside = min((roof.matrix_world @ Vector(corner)).z for corner in roof.bound_box)
    rotation = view.rotation_euler.to_quaternion()
    # Put this camera's near plane below the ceiling across the whole frame.
    slowest_descent = min(-(rotation @ (ray / -ray.z)).z for ray in view.data.view_frame(scene=scene))
    view.data.clip_start = (view.location.z - underside) / slowest_descent + .025
    return view


def render_view(scene, view, path):
    original_camera, original_path = scene.camera, scene.render.filepath
    try:
        scene.camera = view
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
    finally:
        scene.camera, scene.render.filepath = original_camera, original_path


def group_emitters(scene, phone_light):
    ambient = 'Window and ambient'
    groups = {
        ambient: ('Blue night exterior', 'Distant house light'),
        'Main game displays': ('Main monitor ',),
        'Code displays': ('Right code monitor ',),
        'Floor displays': ('Floor monitor ', 'Floor keyboard -'),
        'Library shelves': ('Concealed warm light strip', 'Lantern frosted', 'Pixel lantern window'),
        'Desk and chair': ('Desk -', 'Desk RGB keyboard -', 'Desk vertical bias light', 'Headphones -',
                           'Chair -', 'Cool rose bounce on the front walnut rail', 'Pink rim at seat'),
        'Reader and phone': ('Phone in hands', 'Warm reflection on the reader', 'Soft rim on reader hair',
                             'Soft pink face and cloth bounce', phone_light.name),
        'PC case and LEDs': ('PC -', 'Neutral fill through the PC glass'),
    }
    for view_layer in scene.view_layers:
        for name in groups:
            if name not in view_layer.lightgroups:
                view_layer.lightgroups.add(name=name)
    scene.world.lightgroup = ambient

    for obj in scene.objects:
        if obj.type == 'LIGHT' and obj.parent and 'library' in obj.parent.name.lower():
            obj.lightgroup = 'Library shelves'
        elif obj.type in {'LIGHT', 'MESH', 'CURVE', 'FONT'}:
            group = next((name for name, prefixes in groups.items() if obj.name.startswith(prefixes)), None)
            if group or obj.type == 'LIGHT':
                obj.lightgroup = group or ambient

    displays = [obj for obj in scene.objects if obj.parent and obj.parent.get('screen_source')
                and obj.name.endswith(' display')]
    assert len(displays) == 10 and all(obj.lightgroup.endswith('displays') for obj in displays)
    assert all(obj.lightgroup in groups for obj in scene.objects if obj.type == 'LIGHT')
    return list(groups)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=BASE_ROOM / 'room.blend')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--top-only', action='store_true', help='Add and render the overhead camera in the saved scene')
    parser.add_argument('--violet-power', type=float, default=27.0)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])

    out = args.output.resolve()
    target = out / 'room.blend'
    if args.top_only:
        bpy.ops.wm.open_mainfile(filepath=str(target))
        bpy.context.preferences.filepaths.save_version = 0
        scene = bpy.context.scene
        configure_gpu(scene, args.draft)
        view = top_view(scene)
        status = validate(scene)
        render_view(scene, view, out / 'top-view.png')
        bpy.ops.wm.save_as_mainfile(filepath=str(target))
        report_path = out / 'validation.json'
        report = json.loads(report_path.read_text(encoding='utf-8'))
        report['cameras'] = status['cameras']
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        return

    if args.source.resolve() == target:
        raise ValueError('Use a separate output folder for the lighting revision')
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.frame_set(1)
    dimensions = rig_dimensions(scene)
    exposure = scene.view_settings.exposure

    from relight_character import add_phone_light
    from relight_props import refine_props

    violet = scene.objects['Soft blue-violet fill'].data
    original_power = violet.energy
    violet.energy = args.violet_power
    phone_light = add_phone_light(scene)
    props = refine_props(scene)
    groups = group_emitters(scene, phone_light)
    glare = scene.compositing_node_group.nodes['Glare']
    glare.inputs['Strength'].default_value = .16
    glare.inputs['Threshold'].default_value = .96

    configure_gpu(scene, args.draft)
    overhead = top_view(scene)
    report = validate(scene, dimensions)
    assert scene.view_settings.exposure == exposure
    report.update(devices=scene['optix_render_devices'], exposure=exposure, light_groups=groups,
                  violet_fill_w={'before': original_power, 'after': violet.energy},
                  phone_light_w=phone_light.data.energy,
                  phone_receivers=[obj.name for obj in phone_light.light_linking.receiver_collection.objects],
                  props=props)
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    scene['scene_purpose'] = 'Lighting revision of the editable monitor room'
    scene.render.filepath = '//room.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(target))

    for view, filename in [(scene.camera, 'room.png'),
                           (scene.objects['02 Floor computer and phone reader'], 'floor-detail.png'),
                           (scene.objects['03 Desk and library from right'], 'library-angle.png'),
                           (overhead, 'top-view.png')]:
        render_view(scene, view, out / filename)


if __name__ == '__main__':
    main()
