"""Apply the annotated floor layout to a copy of the lighting scene."""

import argparse
import json
from math import atan2, degrees
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout_station import move_floor_station
from polish_room import configure_gpu, rig_dimensions, validate
from relight_room import OUTPUT as BASE_ROOM
from relight_room import TOP_CAMERA, render_view
from sunset_city import aim

OUTPUT = BASE_ROOM.with_name('monitor-room-layout')
HIDDEN_BENCH = ('Near right upholstered bench', 'Near right upright silhouette',
                'Soft lilac reflection beside camera', 'Cool highlight on near bench edge')


def arrange_rug(scene):
    rug = scene.objects['Vintage woven area rug']
    rug.scale.x *= 4.06 / rug.dimensions.x
    rug.scale.y *= 2.82 / rug.dimensions.y
    rug.rotation_euler.z = 0
    rug.location.x, rug.location.y = .47, .41
    bpy.context.view_layer.update()
    return rug


def verify_rug_support(scene, rug):
    inverse = rug.matrix_world.inverted()
    bounds = [(min(corner[i] for corner in rug.bound_box), max(corner[i] for corner in rug.bound_box))
              for i in range(3)]
    height = (rug.matrix_world @ Vector((0, 0, bounds[2][1]))).z
    reader = next(obj for obj in scene.objects['On floor - Character root'].children if obj.type == 'MESH')
    casters = [obj for obj in scene.objects['Chair - ergonomic office chair'].children
               if obj.name.startswith('Chair - caster wheel')]
    assert len(casters) == 10
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in [reader, *casters]:
        evaluated = obj.evaluated_get(depsgraph)
        points = (evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices)
        near_floor = [inverse @ point for point in points if point.z <= height + .004]
        assert near_floor and all(all(low <= p[axis] <= high for axis, (low, high) in enumerate(bounds[:2]))
                                  for p in near_floor), obj.name
    return {'width': round(rug.dimensions.x, 3), 'depth': round(rug.dimensions.y, 3),
            'top_z': round(height, 3), 'supports_reader': True, 'supported_chair_wheels': len(casters)}


def reframe_floor_setup(scene):
    detail = scene.objects['02 Floor computer and phone reader']
    detail.location = (1.2, -1.2, .58)
    detail.data.lens = 30
    aim(detail, (-1.11, .33, .48))
    library = scene.objects['03 Desk and library from right']
    library.data.lens = 32.5
    aim(library, (.10, 1.85, 1.14))

    reflection = scene.objects['Small blue screen reflection on floorboards']
    reflection.location = (-1.69, -.25, .42)
    aim(reflection, (-1.36, .06, .002))
    reflection.data.energy = 1.2


def verify_display_view(scene, eye_target, bezels=None):
    eye = Vector(eye_target).xy
    spans = []
    for side in ('left', 'right'):
        panel = scene.objects[f'Floor monitor {side} display']
        direction = (eye - panel.matrix_world.translation.xy).normalized()
        front = (panel.matrix_world.to_quaternion() @ Vector((0, -1, 0))).xy.normalized()
        assert front.dot(direction) > .999, panel.name
        bezel = bezels[side] if bezels else scene.objects[f'Floor monitor {side} casing']
        corners = [(bezel.matrix_world @ Vector(corner)).xy - eye for corner in bezel.bound_box]
        angles = [atan2(point.y, point.x) for point in corners]
        spans.append((min(angles), max(angles)))
    spans.sort()
    gap = degrees(spans[1][0] - spans[0][1])
    assert gap > 0, 'Floor displays overlap from the reader side'
    return {'panels_facing_reader': 2, 'gap_degrees_between_bezels': round(gap, 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--draft', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out = args.output.resolve()
    if out == BASE_ROOM.resolve():
        raise ValueError('Use a separate output folder for the layout revision')
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE_ROOM / 'room.blend'))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.frame_set(1)
    dimensions = rig_dimensions(scene)

    rug = arrange_rug(scene)
    station = move_floor_station(scene, floor_display_delta=(.08, -.78), case_delta=(-.34, -.01),
                                 case_yaw=0, face_reader=True)
    for name in HIDDEN_BENCH:
        obj = scene.objects[name]
        obj.hide_render = obj.hide_viewport = True
    reframe_floor_setup(scene)

    configure_gpu(scene, args.draft)
    report = validate(scene, dimensions)
    assert report['cameras'] == 4 and len(scene.view_layers[0].lightgroups) == 8
    report.update(rug=verify_rug_support(scene, rug), station=station,
                  reader_view=verify_display_view(scene, station['reader_eye_target']),
                  hidden_bench=list(HIDDEN_BENCH[:2]), devices=scene['optix_render_devices'])
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    scene['scene_purpose'] = 'Monitor room with the annotated floor layout'
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'room.blend'))

    for view, filename in [(scene.objects[TOP_CAMERA], 'top-view.png'), (scene.camera, 'room.png'),
                           (scene.objects['02 Floor computer and phone reader'], 'floor-detail.png'),
                           (scene.objects['03 Desk and library from right'], 'library-angle.png')]:
        render_view(scene, view, out / filename)


if __name__ == '__main__':
    main()
