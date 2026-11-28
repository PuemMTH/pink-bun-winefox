"""Reopen the isolated files and save their standalone Workspaces."""
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / 'output/scene-item-builds'
CAMERAS = {'RIGHT', 'LEFT', 'FRONT', 'BACK', 'BUTTOM', 'TOP'}


def verify(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    assert len(bpy.data.scenes) == 1 and scene.name == path.parent.name, path
    assert len(scene.objects) > 6 and scene.camera.name == 'FRONT', path
    assert {obj.name for obj in scene.objects if obj.type == 'CAMERA'} == CAMERAS, path
    assert all(obj.data.type == 'ORTHO' for obj in scene.objects if obj.type == 'CAMERA'), path
    for image in bpy.data.images:
        if image.source == 'FILE':
            assert image.packed_files, (path, image.name)
    if scene.name == 'ysm-characters':
        assert len(bpy.data.actions) == 96
        assert sum(o.type == 'ARMATURE' for o in scene.objects) == 2
    if scene.name == 'keyboards':
        assert sum(' concave cap' in o.name for o in scene.objects) == 174
    bpy.context.preferences.filepaths.save_version = 0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_perspective = 'CAMERA'
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    return {'id':scene.name, 'objects':len(scene.objects), 'cameras':len(CAMERAS)}


if __name__ == '__main__':
    ids = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    files = sorted(PACK.glob('*/model.blend')) if not ids else [PACK / item / 'model.blend' for item in ids]
    assert (len(files) == 41) or ids, len(files)
    checks = [verify(path) for path in files]
    if not ids:
        (PACK/'file-validation.json').write_text(json.dumps(checks, indent=2)+'\n', encoding='utf-8')
    print('REOPENED_AND_SAVED', len(checks), flush=True)
