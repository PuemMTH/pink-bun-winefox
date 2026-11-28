"""Render and save a studio scene from a converted YSM Blender file."""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def add_light(name, location, power, size, color):
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = power
    light.shape = 'DISK'
    light.size = size
    light.color = color
    obj = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, (0, 0, 1))


def bounds(meshes):
    graph = bpy.context.evaluated_depsgraph_get()
    points = []
    for source in meshes:
        obj = source.evaluated_get(graph)
        points.extend(obj.matrix_world @ Vector(p) for p in obj.bound_box)
    low = Vector([min(p[i] for p in points) for i in range(3)])
    high = Vector([max(p[i] for p in points) for i in range(3)])
    return low, high


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--outfit', required=True)
    parser.add_argument('--only', nargs='*')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(args.out).resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    rig = next(o for o in scene.objects if o.type == 'ARMATURE')
    meshes = [o for o in scene.objects if o.type == 'MESH'
              and any(m.type == 'ARMATURE' for m in o.modifiers)]
    for obj in list(scene.objects):
        if obj.type in {'LIGHT', 'CAMERA'} or obj.get('ysm_studio'):
            bpy.data.objects.remove(obj, do_unlink=True)
    actions = {a.get('ysm_clip', a.name): a for a in bpy.data.actions}
    assert len(actions) == 47, f'Expected 47 actions, got {len(actions)}'
    sys.path.insert(0, str(Path(__file__).parent))
    from convert import select_action

    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 128
    scene.eevee.shadow_ray_count = 4
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    if scene.world is None:
        scene.world = bpy.data.worlds.new('Studio world')
    scene.world.color = (0.45, 0.45, 0.45)
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.73, 0.68, 0.8, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
    add_light('Key softbox', (-3.5, 4.5, 6), 450, 4, (1, 0.92, 0.87))
    add_light('Fill softbox', (4, 1.5, 3), 220, 3, (0.83, 0.86, 1))
    add_light('Rim softbox', (0, -4, 5), 350, 3, (1, 0.81, 0.91))
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.03))
    floor = bpy.context.object
    floor.name = 'Studio floor'
    floor['ysm_studio'] = True
    material = bpy.data.materials.new('Studio lavender')
    material.diffuse_color = (0.74, 0.7, 0.8, 1)
    floor.data.materials.append(material)
    camera_data = bpy.data.cameras.new('Review camera')
    camera_data.type = 'ORTHO'
    camera = bpy.data.objects.new('Review camera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    container = rig.parent or rig
    basis = container.matrix_world.copy()
    frames = []
    preferred_times = {'idle': 1, 'walk': 0.2, 'run': 0.3, 'jump': 0.32,
                       'extra0': 1.5, 'extra7': 4.8917, 'death': 0.99, 'attacked': 0.1667}
    for clip, action in actions.items():
        if args.only and clip not in args.only:
            continue
        container.matrix_world = basis
        select_action(rig, clip)
        t = preferred_times.get(clip, 0 if clip.startswith(('face_', 'studio_photo_')) else 0.2)
        frame = min(action.frame_range[1], 1 + t * scene.render.fps)
        scene.frame_set(math.floor(frame), subframe=frame % 1)
        if clip == 'sleep':
            # Match the web's chosen bed orientation without changing pose keys.
            rotation = Matrix.Rotation(math.pi / 2, 4, 'Y') @ Matrix.Rotation(3 * math.pi / 2, 4, 'Z')
            container.matrix_world = rotation @ basis
        bpy.context.view_layer.update()
        low, high = bounds(meshes)
        shift = Vector((-(low.x + high.x) / 2, -(low.y + high.y) / 2, -low.z))
        container.matrix_world.translation += shift
        bpy.context.view_layer.update()
        low, high = bounds(meshes)
        center = (low + high) / 2
        height = high.z - low.z
        face = clip.startswith('face_')
        if face:
            target = Vector((center.x, center.y, low.z + height * 0.83))
            camera.location = target + Vector((0, 6, 0.05))
            camera_data.ortho_scale = height * 0.5
        else:
            target = center
            camera.location = target + Vector((3.4, 6, 1.7))
            camera_data.ortho_scale = max(height, math.hypot(high.x - low.x, high.y - low.y)) * 1.16
        aim(camera, target)
        destination = output / f'{args.outfit}-{clip}.png'
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        frames.append({'clip': clip, 'frame': frame, 'time': (frame - 1) / scene.render.fps,
                       'file': destination.name, 'outfit': args.outfit})
    container.matrix_world = basis
    select_action(rig, 'idle')
    scene.frame_set(31)
    bpy.context.view_layer.update()
    low, high = bounds(meshes)
    target = (low + high) / 2
    camera.location = target + Vector((3.4, 6, 1.7))
    camera_data.ortho_scale = (high.z - low.z) * 1.16
    aim(camera, target)
    scene.render.filepath = str(output / f'{args.outfit}-idle.png')
    scene.frame_end = 1 + round(30 * scene.render.fps)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
            area.spaces.active.shading.type = 'MATERIAL'
        elif area.type == 'DOPESHEET_EDITOR':
            area.spaces.active.mode = 'ACTION'
    for image in bpy.data.images:
        if image.packed_file:
            image.filepath = '//textures/pink_bun.png'
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    (output / f'{args.outfit}-renders.json').write_text(json.dumps(frames, indent=2), encoding='utf-8')
    print('BLENDER_RENDER_DONE', args.outfit, len(frames), flush=True)


if __name__ == '__main__':
    main()
