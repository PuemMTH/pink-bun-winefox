"""Install the standalone model revisions in the posed monitor room."""

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout_room import OUTPUT as BASE_ROOM
from layout_room import verify_display_view, verify_rug_support
from polish_room import configure_gpu, rig_dimensions, validate
from relight_room import TOP_CAMERA, render_view

PROJECT = BASE_ROOM.parents[2]
ASSETS = PROJECT / 'output/scene-item-builds'
OUTPUT = BASE_ROOM.with_name('monitor-room-assembled')
STRUCTURE = {
    'woven-rug': ('Vintage woven area rug',),
    'wood-floor': ('Walnut floor plank', 'Floorboard subbase'),
    'brick-wall': ('Uneven bonded terracotta brick', 'Recess mortar back'),
    'acoustic-panels': ('Acoustic wall panel',),
    'window': ('Timber window jamb', 'Window mullion', 'Window inner mullion'),
    'blinds': ('Venetian blind',),
    'pine-trees': ('Pine treeline outside window',),
    'distant-houses': ('Nearly dark distant house', 'Distant house light'),
    'bench': ('Near right upholstered bench', 'Near right upright silhouette'),
}
STUDIO_PREFIXES = ('Key softbox', 'Front fill', 'Back softbox', 'Underside fill')
VIEWS = {
    TOP_CAMERA:'top-view.png',
    '01 Approved concept framing':'room.png',
    '02 Floor computer and phone reader':'floor-detail.png',
    '03 Desk and library from right':'library-angle.png',
}


def apply_structure(scene, assets):
    destination = bpy.data.collections.new('Assembled room surfaces')
    scene.collection.children.link(destination)
    incoming = {}
    for item, prefixes in STRUCTURE.items():
        originals = [obj for obj in scene.objects if obj.name.startswith(prefixes)]
        assert originals, item
        with bpy.data.libraries.load(str(assets/item/'model.blend'), link=False) as (available, target):
            target.objects = [name for name in available.objects
                              if name not in {'RIGHT','LEFT','FRONT','BACK','BUTTOM','TOP'}
                              and not name.startswith(STUDIO_PREFIXES)]
        replacements = [obj for obj in target.objects if obj and obj.type in {'MESH','CURVE','FONT'}]
        assert replacements, item
        for obj in replacements:
            assert obj.parent is None, obj.name
            destination.objects.link(obj)
            obj.name = f'Assembled {item} · {obj.name}'
            obj['assembly_asset'] = item
            obj.hide_render = obj.hide_viewport = item == 'bench'
            if item == 'distant-houses':
                obj.lightgroup = 'Window and ambient'
        if item == 'woven-rug':
            receiver = scene.objects['Warm reflection on the reader from the shelf'].light_linking.receiver_collection
            receiver.objects.link(replacements[0])
        for obj in originals:
            obj.hide_render = True
            obj.hide_set(True)
        incoming[item] = replacements

    # The isolated YSM files and room share these meshes. Keep the posed rigs and animation slots.
    characters = [next(c for c in scene.objects[f'{name} - Character root'].children if c.type == 'MESH')
                  for name in ('At desk','On floor')]
    names = [obj.data.name for obj in characters]
    with bpy.data.libraries.load(str(assets/'ysm-characters/model.blend'), link=False) as (available, target):
        assert all(name in available.meshes for name in names), (names, available.meshes)
        target.meshes = names
    for character, mesh in zip(characters, target.meshes):
        character.data = mesh
        character['assembly_asset'] = 'ysm-characters'
    incoming['ysm-characters'] = characters
    return incoming


def validate_assembly(scene, baseline, dimensions=None):
    report = validate(scene, dimensions)
    assert report['cameras'] == len(VIEWS) and len(scene.view_layers[0].lightgroups) == 8
    assert scene.objects['Near right upholstered bench'].hide_render
    rug = next(obj for obj in scene.objects if obj.get('assembly_asset') == 'woven-rug')
    bezels = {side: scene.objects[f'Fitted minecraft-monitors / Floor monitor {side} graphite bezel']
              for side in ('left','right')}
    assert all(not obj.hide_render for obj in bezels.values())
    casing_back = max((obj.matrix_world @ Vector(corner)).y for obj in bezels.values()
                      for corner in obj.bound_box)
    case = scene.objects['PC - Aurora panoramic tower']
    case_front = min((obj.matrix_world @ Vector(corner)).y for obj in case.children
                     if obj.type in {'MESH','CURVE','FONT'} and not obj.hide_render for corner in obj.bound_box)
    assert case_front > casing_back
    report.update(rug=verify_rug_support(scene, rug), case_clearance_y=case_front-casing_back,
                  reader_view=verify_display_view(scene, baseline['station']['reader_eye_target'], bezels),
                  devices=scene['optix_render_devices'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--draft', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out = args.output.resolve()
    if out == BASE_ROOM.resolve():
        raise ValueError('The assembled room must use a separate output folder')
    out.mkdir(parents=True, exist_ok=True)

    from assemble_peripherals import apply_peripherals
    from assemble_decor import apply_decor
    from assemble_pc import apply_pc

    path = BASE_ROOM / 'room.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.frame_set(1)
    initial_pose = rig_dimensions(scene)
    structure = apply_structure(scene, ASSETS)
    receipt = {
        'room': {name: len(objects) for name, objects in structure.items()},
        'decor': apply_decor(scene, ASSETS),
        'computer': apply_pc(scene, ASSETS),
        'peripherals': apply_peripherals(scene, ASSETS),
    }
    installed = {*receipt['room'], *receipt['decor'], *receipt['computer']['installed_from_items'],
                 *receipt['peripherals']['replacement_parts']}
    expected = {entry.name for entry in ASSETS.iterdir() if (entry/'model.blend').is_file()}
    assert len(expected) == 41 and installed == expected, (expected-installed, installed-expected)
    bpy.context.view_layer.update()
    configure_gpu(scene, args.draft)
    baseline = json.loads((BASE_ROOM/'validation.json').read_text(encoding='utf-8'))
    report = validate_assembly(scene, baseline, initial_pose)
    report.update(assembly_item_count=len(installed), assembled=receipt)
    (out/'validation.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    scene['scene_purpose'] = 'Assembled standalone item models in the posed room layout'
    scene.render.filepath = '//room.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'room.blend'), compress=True)
    for name, filename in VIEWS.items():
        render_view(scene, scene.objects[name], out/filename)
    print('ROOM_ASSEMBLY_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
