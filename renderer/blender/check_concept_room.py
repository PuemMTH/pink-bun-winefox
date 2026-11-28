"""Open the final blend and verify its physical setup and packed textures."""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from monitor_room import contact_min


def main():
    scene = bpy.context.scene
    scene.frame_set(1)
    assert scene.render.engine == 'CYCLES' and scene.cycles.device == 'GPU'
    screens = [obj for obj in scene.objects if obj.get('screen_source')]
    assert len(screens) == 10 and len({obj['screen_source'] for obj in screens}) == 10
    left, right = [bpy.data.objects[f'Floor monitor {side}'] for side in ('left', 'right')]
    assert all(abs(obj['screen_size'][0]/obj['screen_size'][1] - 16/9) < 1e-5 for obj in (left, right))
    assert left.location.z == right.location.z
    assert all(any('stand base' in child.name for child in obj.children) for obj in (left, right))
    case = bpy.data.objects['PC - Aurora panoramic tower']
    front_y = min((child.matrix_world @ Vector(corner)).y for child in case.children
                  if child.type in {'MESH','CURVE','FONT'} for corner in child.bound_box)
    rear_y = max((child.matrix_world @ Vector(corner)).y for obj in (left, right)
                 for child in obj.children if child.type == 'MESH' and 'casing' in child.name
                 for corner in child.bound_box)
    assert front_y > rear_y, (front_y, rear_y)
    assert case['graphics_card'] == 'NVIDIA GeForce RTX 5070'
    assert all(bpy.data.objects.get(name) for name in ('Floor keyboard','Desk RGB keyboard','Phone in hands'))
    assert bpy.data.objects['Phone in hands']['display_count'] == 1
    rigs = [o for o in scene.objects if o.type == 'ARMATURE']
    assert len(rigs) == 2 and len(bpy.data.actions) == 96 and all(a.use_fake_user for a in bpy.data.actions)
    rig = next(r for r in rigs if r.parent.name.startswith('On floor'))
    body = next(o for o in rig.parent.children if o.type == 'MESH')
    contacts = {label: contact_min({'mesh': body}, groups) for label, groups in [
        ('thighs', ['LeftLeg', 'RightLeg']), ('left_foot', ['LeftFoot']), ('right_foot', ['RightFoot'])]}
    assert all(abs(z-.014) < .002 for z in contacts.values()), contacts
    file_images = [image for image in bpy.data.images if image.source == 'FILE']
    assert all(image.packed_file for image in file_images)
    result = dict(status='passed', editable_objects=len(scene.objects), cameras=sum(o.type=='CAMERA' for o in scene.objects),
                  actions=len(bpy.data.actions), screen_count=len(screens), unique_screen_images=len({o['screen_source'] for o in screens}),
                  floor_displays='two 16:9 monitors on separate stands', case_clearance_y=round(front_y-rear_y, 4),
                  keyboard_count=2, floor_contacts=contacts, packed_file_images=len(file_images), engine='Cycles / OptiX')
    report = Path(bpy.data.filepath).with_name('validation.json')
    report.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
