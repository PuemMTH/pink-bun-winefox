"""Apply the approved reference refinements to a copy of the editable room."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from monitor_room import contact_min

ROOT = Path(__file__).resolve().parents[2]
SCENES = ROOT/'output/blender-scenes'
SOURCE = SCENES/'monitor-room-concept/room.blend'
OUTPUT = SCENES/'monitor-room-polish'


def rig_dimensions(scene):
    return {
        rig.parent.name: {
            'root_scale': list(rig.parent.scale),
            'pose_scale': {bone.name: tuple(bone.scale) for bone in rig.pose.bones},
            'bone_lengths': {bone.name: bone.length for bone in rig.data.bones},
        }
        for rig in scene.objects if rig.type == 'ARMATURE'
    }


def validate(scene, expected_rigs=None):
    scene.frame_set(1)
    assert scene.render.engine == 'CYCLES' and scene.cycles.device == 'GPU'
    assert (scene.render.resolution_x, scene.render.resolution_y) == (1671,941)
    rig_status = rig_dimensions(scene)
    assert len(rig_status) == 2
    if expected_rigs is not None:
        for name, actual in rig_status.items():
            for key in ('root_scale', 'bone_lengths'):
                assert actual[key] == expected_rigs[name][key], (name,key)
            assert all(max(abs(a-b) for a,b in zip(value,expected_rigs[name]['pose_scale'][bone])) < 1e-5
                       for bone,value in actual['pose_scale'].items()), name

    reader = next(r for r in scene.objects if r.type == 'ARMATURE' and r.parent.name.startswith('On floor'))
    mesh = next(o for o in reader.parent.children if o.type == 'MESH')
    contacts = {label: contact_min({'mesh': mesh}, [group]) for label, group in [
        ('left_thigh', 'LeftLeg'), ('right_thigh', 'RightLeg'),
        ('left_foot', 'LeftFoot'), ('right_foot', 'RightFoot')]}
    rug = bpy.data.objects['Vintage woven area rug']
    rug_top = max((rug.matrix_world@Vector(p)).z for p in rug.bound_box)
    assert all(0 <= z-rug_top <= .004 for z in contacts.values()), (contacts, rug_top)

    screens = [o for o in scene.objects if o.get('screen_source')]
    assert len(screens) == 10 and len({o['screen_source'] for o in screens}) == 10
    floor_screens = [bpy.data.objects[f'Floor monitor {side}'] for side in ('left','right')]
    assert floor_screens[0]['screen_size'][:] == floor_screens[1]['screen_size'][:]
    assert abs(floor_screens[0]['screen_size'][0]/floor_screens[0]['screen_size'][1] - 16/9) < 1e-5
    assert all(any('stand base' in child.name for child in screen.children) for screen in floor_screens)
    case = bpy.data.objects['PC - Aurora panoramic tower']
    assert case['graphics_card'] == 'NVIDIA GeForce RTX 5070'
    case_front = min((child.matrix_world@Vector(p)).y for child in case.children
                     if child.type in {'MESH','CURVE','FONT'} for p in child.bound_box)
    screens_back = max((child.matrix_world@Vector(p)).y for screen in floor_screens
                       for child in screen.children if child.type == 'MESH' and 'casing' in child.name
                       for p in child.bound_box)
    assert case_front > screens_back, (case_front, screens_back)
    assert all(bpy.data.objects.get(name) for name in ('Desk RGB keyboard','Floor keyboard','Phone in hands'))
    assert bpy.data.objects['Phone in hands']['display_count'] == 1
    assert len(bpy.data.actions) == 96 and all(action.use_fake_user for action in bpy.data.actions)
    images = [image for image in bpy.data.images if image.source == 'FILE']
    assert all(image.packed_file for image in images)
    return {
        'status': 'passed', 'renderer': 'Cycles / OptiX', 'rigs': len(rig_status),
        'rig_dimensions': {k: v['root_scale'] for k,v in rig_status.items()},
        'pose_preserves_scale': True, 'actions': len(bpy.data.actions),
        'floor_contacts': contacts, 'rug_height': rug_top, 'screen_count': len(screens),
        'floor_monitors': 'matching 16:9 panels, individual stands',
        'case_clearance_y': case_front - screens_back, 'keyboard_count': 2,
        'phone_count': 1, 'packed_file_images': len(images),
        'cameras': sum(o.type == 'CAMERA' for o in scene.objects),
    }


def configure_gpu(scene, draft):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'OPTIX'
    active_devices = [device.name for device in prefs.devices if device.use]
    assert active_devices, 'OptiX GPU not found'
    scene['optix_render_devices'] = ', '.join(active_devices)
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 36 if draft else 144
    scene.cycles.adaptive_threshold = .055 if draft else .021
    scene.cycles.use_denoising = True
    scene.cycles.denoising_use_gpu = True


def refine_chair_back(scene):
    chair = scene.objects['Chair - ergonomic office chair']
    chair.location.x += .028
    profiles = ('tapered back frame', 'sculpted dark leather pad', 'top burgundy piping',
                'side bolster', 'burgundy side seam', 'rear fabric badge')
    bottom = .55
    for part in chair.children:
        name = part.name.removeprefix('Chair - ')
        if name.startswith(profiles):
            part.location.z = bottom + (part.location.z-bottom) * .947
            part.scale.z *= .947
            part.location.x = .015 + part.location.x * .969
            part.scale.x *= .969
        if name.startswith(('left seat wing', 'arm rest', 'padded arm rest')):
            part.location.x *= .91
            if part.location.x > 0:
                part.location.x -= .054
        if name.startswith(('left seat wing', 'seat pan', 'padded seat')):
            part.location.x += .018


def refine_surface_lighting(scene):
    scene.camera.data.dof.aperture_fstop = 2.25
    scene.objects['Chair - warm caster rim'].data.energy *= 1.32
    scene.objects['Desk - reflected drawer amber'].data.energy *= 1.16
    scene.objects['Low amber floor bounce'].data.energy *= 1.20
    reading_light = scene.objects['Warm reflection on the reader from the shelf'].data
    reading_light.energy *= 1.26
    reading_light.color = (1, .73, .54)
    rug = scene.objects['Vintage woven area rug'].data.materials[0].node_tree
    shader = rug.nodes['Principled BSDF']
    base_color = shader.inputs['Base Color']
    weave = base_color.links[0].from_socket
    # Boost the thread signal in linear space while anchoring dark yarn.
    contrast = rug.nodes.new('ShaderNodeVectorMath')
    contrast.label = 'Lift dyed yarn highlights'
    contrast.operation = 'MULTIPLY_ADD'
    contrast.inputs[1].default_value = (1.40, 1.35, 1.35)
    contrast.inputs[2].default_value = (-.004, -.004, -.004)
    rug.links.new(weave, contrast.inputs[0])
    rug.links.new(contrast.outputs['Vector'], base_color)
    tuft_bump = shader.inputs['Normal'].links[0].from_node
    tuft_bump.inputs['Distance'].default_value *= 1.35


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--stem', default='room')
    parser.add_argument('--details', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.check_only:
        bpy.ops.wm.open_mainfile(filepath=str((out/f'{args.stem}.blend').resolve()))
        report = validate(bpy.context.scene)
        print(json.dumps(report, indent=2), flush=True)
        return
    if args.reference:
        shutil.copy2(args.reference, out/'reference.png')

    from polish_pose import apply_pose_polish
    from polish_hardware import apply_hardware_polish

    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.frame_set(1)
    initial = rig_dimensions(scene)
    pose_report = apply_pose_polish(scene)
    prop_report = apply_hardware_polish(scene)
    refine_chair_back(scene)
    refine_surface_lighting(scene)
    configure_gpu(scene, args.draft)
    scene['approved_reference'] = 'reference.png'
    scene['scene_purpose'] = 'Editable pose, prop and grounding refinement based on approved image edit'
    scene.render.filepath = '//room.png'
    report = validate(scene, initial)
    report.update(devices=scene['optix_render_devices'], pose=pose_report, props=prop_report)
    (out/('validation.json' if args.stem == 'room' else f'{args.stem}-validation.json')).write_text(
        json.dumps(report, indent=2)+'\n', encoding='utf-8')
    target = (out/f'{args.stem}.blend').resolve()
    if target == args.source.resolve():
        raise ValueError('Save the refinement as a separate scene')
    bpy.ops.wm.save_as_mainfile(filepath=str(target))

    views = [(scene.camera,args.stem)]
    if args.details:
        views.extend([(bpy.data.objects['02 Floor computer and phone reader'], 'floor-detail'),
                      (bpy.data.objects['03 Desk and library from right'], 'library-angle')])
    for camera, name in views:
        scene.camera = camera
        scene.render.filepath = str(out/f'{name}.png')
        bpy.ops.render.render(write_still=True)
    print('POLISH_ROOM_COMPLETE',flush=True)


if __name__ == '__main__':
    main()
