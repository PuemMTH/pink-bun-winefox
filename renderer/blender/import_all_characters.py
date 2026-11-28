"""Refresh every local project variant and save a five-character comparison scene."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
VARIANTS=[('school','pink_bun_winefox'),('white','pink_bun_winefox_white'),
          ('school-square-eyes','pink_bun_winefox_square_eyes'),
          ('white-square-eyes','pink_bun_winefox_white_square_eyes'),('aunt','satou_aunt')]
OUT=ROOT/'output/blender/latest'
PREP=ROOT/'dist/blender/latest'
sys.path.insert(0,str(Path(__file__).parent))


def source_hashes(model):
    return {p.relative_to(model).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(model.rglob('*')) if p.is_file()}


def main():
    from convert import prepare_model, CLIPS
    OUT.mkdir(parents=True,exist_ok=True);PREP.mkdir(parents=True,exist_ok=True)
    if '--prepare' in sys.argv:
        for variant,dirname in VARIANTS:
            prepare_model(ROOT,ROOT/'dist'/dirname,PREP/(variant+'.json'))
        print('PREPARED_ALL_5_VARIANTS');return
    import bpy
    from convert import build_character,validate_character,select_action
    from sunset_city import camera,area
    from monitor_room import append_character,material,box
    variants=[]
    for variant,dirname in VARIANTS:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        char=build_character(PREP/(variant+'.json'),ROOT)
        checks=validate_character(char)
        path=OUT/f'satou-{variant}.blend'
        for a in bpy.data.actions:a.use_fake_user=True
        hashes=source_hashes(ROOT/'dist'/dirname)
        char['rig']['ysm_source_fingerprint']=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
        bpy.ops.wm.save_as_mainfile(filepath=str(path))
        bpy.ops.wm.open_mainfile(filepath=str(path))
        expected=json.loads((PREP/(variant+'.json')).read_text(encoding='utf-8'))['clip_ids']
        assert len(bpy.data.actions)==len(expected)
        assert all(im.packed_file for im in bpy.data.images if im.source=='FILE')
        report=dict(id=variant,model=dirname,blend=path.name,actions=len(expected),action_ids=expected,source_hashes=hashes,
                    blend_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),checks=checks)
        path.with_suffix('.validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        variants.append(report)
    manifest=dict(description='All five current project YSM variants, freshly converted from dist',
                  geometry_validation_threshold=2e-5,
                  validation_scope='Numerical Blender vs YSM adapter at the recorded per-model poses; rendered previews are not Minecraft runtime testing',variants=variants)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s=bpy.context.scene
    for i,(variant,dirname) in enumerate(VARIANTS):
        char=append_character(OUT/f'satou-{variant}.blend',variant)
        select_action(char,'idle',1)
        char['root'].location.x=(i-2)*1.25
        char['root'].rotation_euler.z=3.14159265
        char['rig']['library_variant']=variant
    s.camera=camera('All five current YSM models',(4,-11,4),(0,0,1),48)
    area('Studio key',(-3,-4,6),(0,0,1),600,5,(.85,.92,1))
    area('Studio fill',(4,-1,4),(0,0,1),350,4,(1,.78,.86))
    box('Studio floor',(0,0,-.075),(15,12,.1),material('Studio floor',(.09,.12,.18)))
    w=bpy.data.worlds.new('Studio');w.use_nodes=True;s.world=w;w.node_tree.nodes['Background'].inputs['Strength'].default_value=.18
    s.render.engine='CYCLES';s.cycles.device='GPU';s.cycles.samples=96;s.cycles.use_denoising=True;s.cycles.denoising_use_gpu=True
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    s.view_settings.view_transform='AgX';s.render.resolution_x=2560;s.render.resolution_y=1080;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.filepath='//all-characters.png'
    assert len([o for o in s.objects if o.type=='ARMATURE'])==5 and len(bpy.data.actions)==sum(v['actions'] for v in variants)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'satou-all-characters.blend'))
    s.render.filepath=str(OUT/'all-characters.png');bpy.ops.render.render(write_still=True)
    print('REFRESHED_ALL_5_CHARACTERS',[(v['id'],v['actions']) for v in variants],flush=True)


if __name__=='__main__':main()
