"""Build a standalone Blender file and six orthographic renders per checklist entry."""
import argparse
import importlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout_room import OUTPUT as ROOM
from sunset_city import area

ROOT = ROOM.parents[2]
DATA = Path(__file__).with_name('item_specs')
OUTPUT = ROOT / 'output/scene-item-builds'
BUILDERS = {'room': 'item_room', 'peripherals': 'item_hardware', 'decor': 'item_decor', 'case': 'item_pc'}
VIEWS = {
    'RIGHT': (1, 0, 0), 'LEFT': (-1, 0, 0), 'FRONT': (0, -1, 0),
    'BACK': (0, 1, 0), 'BUTTOM': (0, 0, -1), 'TOP': (0, 0, 1),
}
MODEL_TYPES = {'MESH', 'CURVE', 'FONT', 'SURFACE', 'META'}


def export_models(source, studio, originals, graph):
    output = []
    for obj in dict.fromkeys(originals):
        if studio.objects.get(obj.name) == obj:
            output.append(obj)
        else:
            assert obj.type in MODEL_TYPES and source.objects.get(obj.name) == obj, obj.name
            evaluated = obj.evaluated_get(graph)
            mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=graph)
            if not mesh.vertices:
                bpy.data.meshes.remove(mesh)
                continue
            copy = bpy.data.objects.new(obj.name, mesh)
            copy.matrix_world = obj.matrix_basis if obj.hide_viewport and not obj.parent else obj.matrix_world
            studio.collection.objects.link(copy)
            output.append(copy)
    return output


def setup_studio(scene, objects, size, samples):
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    cloud = []
    for original in objects:
        if original.type not in MODEL_TYPES:
            continue
        obj = original.evaluated_get(graph)
        if obj.type == 'MESH':
            cloud.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
            continue
        # Blender can report placeholder boxes for unconverted text and curves.
        mesh = obj.to_mesh()
        if mesh:
            bounds = [(min(v.co[axis] for v in mesh.vertices), max(v.co[axis] for v in mesh.vertices))
                      for axis in range(3)] if mesh.vertices else []
            if bounds:
                cloud.extend(obj.matrix_world @ Vector((x,y,z))
                             for x in bounds[0] for y in bounds[1] for z in bounds[2])
            obj.to_mesh_clear()
    assert cloud, scene.name
    low = Vector(tuple(min(p[i] for p in cloud) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in cloud) for i in range(3)))
    center = (low + high) / 2
    longest = max(high - low)
    assert math.isfinite(longest) and longest > .0001, scene.name

    world = bpy.data.worlds.new('Neutral studio')
    world.use_nodes = True
    background = world.node_tree.nodes['Background']
    background.inputs['Color'].default_value = (.38,.42,.52,1)
    background.inputs['Strength'].default_value = .44
    scene.world = world
    for name, position, scale, color in [
        ('Key softbox', (-2,-3,3), 330, (1,.93,.84)),
        ('Front fill', (2,-3,1), 180, (.81,.89,1)),
        ('Back softbox', (1,3,2), 290, (1,.88,.76)),
        ('Underside fill', (-1,0,-2), 100, (.86,.91,1)),
    ]:
        area(name, center + Vector(position)*longest, center, longest**2*scale, longest*2, color)

    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.denoising_use_gpu = True
    scene.cycles.adaptive_threshold = .09
    scene.render.use_persistent_data = True
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'AgX'

    cameras = {}
    for name, direction in VIEWS.items():
        direction = Vector(direction)
        data = bpy.data.cameras.new(name)
        data.type = 'ORTHO'
        data.ortho_scale = longest*1.18
        data.clip_end = max(10, longest*12)
        data.clip_start = max(.0001, longest*.005)
        cam = bpy.data.objects.new(name, data)
        scene.collection.objects.link(cam)
        cam.location = center + direction * longest * 3.0
        if name in {'TOP','BUTTOM'}:
            cam.rotation_euler = (0 if name == 'TOP' else math.pi, 0, 0)
        else:
            cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
        cameras[name] = cam
    scene.camera = cameras['FRONT']
    return cameras, [round(length, 6) for length in high - low]


def build_entry(source, graph, item, builder, args):
    folder = args.output / item['id']
    folder.mkdir(parents=True, exist_ok=True)
    scene = bpy.data.scenes.new(item['id'])
    bpy.context.window.scene = scene
    objects = export_models(source, scene, builder(item, source, scene), graph)
    cameras, dimensions = setup_studio(scene, objects, args.size, args.samples)
    scene['item_title'] = item['title']
    scene['front_axis'] = '-Y'
    scene['bottom_view_file'] = 'BUTTOM.png'
    scene.render.filepath = '//FRONT.png'
    scene.frame_set(1)

    # Model, lights and six cameras form a complete scene datablock.
    dependencies = {scene}
    if item['id'] == 'ysm-characters':
        dependencies.update(bpy.data.actions)
        scene['model_attribution'] = 'Wine Fox 07_jk, CC BY-NC-SA 4.0. Satou adaptation by PuemMTH.'
    bpy.data.libraries.write(str(folder/'model.blend'), dependencies, path_remap='NONE',
                             fake_user=True, compress=True)
    for name, cam in cameras.items():
        scene.camera = cam
        scene.render.filepath = str(folder / f'{name}.png')
        bpy.ops.render.render(write_still=True)
    result = dict(id=item['id'], title=item['title'], size=dimensions, views=list(cameras),
                  model_objects=len(objects), checklist=item['details'])
    (folder/'item.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('ITEM_COMPLETE', item['id'], len(objects), dimensions, flush=True)
    bpy.context.window.scene = source
    bpy.data.batch_remove(ids=[*list(scene.objects), scene.world, scene])
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOM/'room.blend')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--group', choices=tuple(BUILDERS), action='append')
    parser.add_argument('--item', action='append')
    parser.add_argument('--size', type=int, default=900)
    parser.add_argument('--samples', type=int, default=16)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    args.output = args.output.resolve()
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    source = bpy.context.scene
    source.frame_set(1)
    graph = bpy.context.evaluated_depsgraph_get()
    engine = bpy.context.preferences.addons['cycles'].preferences
    engine.compute_device_type = 'OPTIX'
    engine.get_devices()
    for device in engine.devices:
        device.use = device.type == 'OPTIX'
    assert any(device.use for device in engine.devices), 'OptiX GPU is required'
    for group in args.group or BUILDERS:
        entries = json.loads((DATA / f'{group}.json').read_text(encoding='utf-8-sig'))
        for item in entries:
            if not args.item or item['id'] in args.item:
                builder = importlib.import_module(BUILDERS[group]).build
                build_entry(source, graph, item, builder, args)


if __name__ == '__main__':
    main()
