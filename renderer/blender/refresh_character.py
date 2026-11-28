"""Replace a scene character with a newer converted YSM, retaining the scene."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from convert import select_action


def floor_z(body):
    bpy.context.view_layer.update()
    posed = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return min((posed.matrix_world @ Vector(point)).z for point in posed.bound_box)


def replace_character(scene, source):
    source = Path(source).resolve()
    assert source.is_file(), source
    old_rig = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
    old_root = old_rig.parent
    old_body = next(obj for obj in old_root.children if obj.type == 'MESH')
    ground = floor_z(old_body)
    location, rotation = old_root.location.copy(), old_root.rotation_euler.copy()
    clip = old_rig.animation_data.action.get('ysm_clip', 'idle')
    time = (scene.frame_current_final - 1) / scene.render.fps
    frame_range = scene.frame_start, scene.frame_end
    previous_clips = {action['ysm_clip'] for action in bpy.data.actions if action.get('ysm_clip')}
    previous_materials = set(old_body.data.materials)
    previous_images = {node.image for material in previous_materials if material and material.use_nodes
                       for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image}
    collections = list(old_root.users_collection)
    for obj in [*old_root.children_recursive, old_root]:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data and not data.users:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Armature):
                bpy.data.armatures.remove(data)
    for action in list(bpy.data.actions):
        if action.get('ysm_clip'):
            bpy.data.actions.remove(action, do_unlink=True)
    for collection in collections:
        if not collection.objects and not collection.children:
            bpy.data.collections.remove(collection)
    for material in previous_materials:
        if material and not material.users:
            bpy.data.materials.remove(material)
    for image in previous_images:
        if not image.users:
            bpy.data.images.remove(image)
    with bpy.data.libraries.load(str(source), link=False) as (available, imported):
        imported.collections = list(available.collections)
        imported.actions = list(available.actions)
        imported.texts = list(available.texts)
    for collection in imported.collections:
        scene.collection.children.link(collection)
    # Appending clears fake users; retain clips that are not the active pose.
    for action in imported.actions:
        action.use_fake_user = True
    rigs = [obj for obj in scene.objects if obj.type == 'ARMATURE']
    assert len(rigs) == 1, 'Expected one refreshed character'
    rig = rigs[0]
    root = rig.parent
    body = next(obj for obj in root.children if obj.type == 'MESH')
    clips = {action['ysm_clip'] for action in bpy.data.actions if action.get('ysm_clip')}
    assert clips == previous_clips, (clips - previous_clips, previous_clips - clips)
    select_action(rig, clip, time)
    root.location, root.rotation_euler = location, rotation
    root.location.z += ground - floor_z(body)
    scene.frame_start, scene.frame_end = frame_range
    assert abs(floor_z(body) - ground) < 0.00002
    fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()
    rig['ysm_imported_blend_sha256'] = fingerprint
    rig['ysm_imported_blend'] = source.name
    report = dict(source=source.name, sha256=fingerprint, model=rig.get('ysm_source_model'),
                  actions=len(clips), pose=clip, time=time, feet_z=floor_z(body),
                  vertices=len(body.data.vertices), triangles=len(body.data.polygons))
    scene['ysm_character_import'] = json.dumps(report)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--character', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.scene, args.character, args.out = args.scene.resolve(), args.character.resolve(), args.out.resolve()
    bpy.ops.wm.open_mainfile(filepath=str(args.scene))
    scene = bpy.context.scene
    report = replace_character(scene, args.character)
    scene.cycles.device = 'GPU'
    scene.cycles.denoising_use_gpu = True
    args.out.parent.mkdir(parents=True, exist_ok=True)
    original_camera, original_filepath = scene.camera, scene.render.filepath
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out.resolve()))
    if args.render:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = device.type == 'OPTIX'
        for camera, name in zip(sorted((obj for obj in scene.objects if obj.type == 'CAMERA'), key=lambda obj: obj.name),
                                ['city-sunset-hero.png', 'city-sunset-wide.png', 'city-sunset-portrait.png']):
            scene.camera = camera
            scene.render.filepath = str(args.out.parent / name)
            bpy.ops.render.render(write_still=True)
    scene.camera, scene.render.filepath = original_camera, original_filepath
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(args.out))
    report['saved_action_count'] = len([action for action in bpy.data.actions if action.get('ysm_clip')])
    assert report['saved_action_count'] == report['actions']
    args.out.with_suffix('.import.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('CHARACTER_REFRESHED', json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
