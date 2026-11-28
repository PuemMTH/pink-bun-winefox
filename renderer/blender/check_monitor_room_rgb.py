"""Reopen the deliverable and verify screenshots, hardware and fresh model sources."""
from pathlib import Path
import hashlib
import json
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from import_all_characters import source_hashes
from monitor_room import contact_min
from mathutils import Vector


def main():
    folder=ROOT/'output/blender-scenes/monitor-room-rgb'
    library=ROOT/'output/blender/latest'
    imports=json.loads((library/'manifest.json').read_text(encoding='utf-8'))
    assert len(imports['variants'])==5
    for model in imports['variants']:
        assert source_hashes(ROOT/'dist'/model['model'])==model['source_hashes'],model['id']
        assert hashlib.sha256((library/model['blend']).read_bytes()).hexdigest()==model['blend_sha256']
        assert max(c['max_vertex_error'] for c in model['checks'])<2e-5
    bpy.ops.wm.open_mainfile(filepath=str(folder/'satou-monitor-room.blend'))
    s=bpy.context.scene
    assert s.render.engine=='CYCLES' and s.cycles.device=='GPU' and s.cycles.denoising_use_gpu
    assert (s.render.resolution_x,s.render.resolution_y)==(2560,1440)
    assert len([o for o in s.objects if o.type=='CAMERA'])==8
    pc=bpy.data.objects['PC - Aurora panoramic tower']
    for cam in [o for o in s.objects if o.type=='CAMERA']:
        point=pc.matrix_world.inverted()@cam.location
        assert not (-.5<point.x<.5 and -.4<point.y<.4 and 0<point.z<1.5),(cam.name,'inside PC case')
    rigs=[o for o in s.objects if o.type=='ARMATURE']
    assert len(rigs)==2 and len(bpy.data.actions)==95 and all(a.use_fake_user for a in bpy.data.actions)
    assert {r['ysm_source_model'] for r in rigs}=={'pink_bun_winefox_square_eyes','pink_bun_winefox_white_square_eyes'}
    for rig in rigs:
        v=next(v for v in imports['variants'] if v['model']==rig['ysm_source_model'])
        assert rig['ysm_source_fingerprint']==hashlib.sha256(json.dumps(v['source_hashes'],sort_keys=True).encode()).hexdigest()
    screens=sorted([o for o in s.objects if o.get('screen_index') is not None],key=lambda o:o['screen_index'])
    assert len(screens)==10
    assert [o['screen_index'] for o in screens]==list(range(10))
    hashes=[]
    for o in screens:
        m=o.data.materials[0];tex=m.node_tree.nodes['Minecraft screenshot']
        assert tex.image.packed_file
        hashes.append(hashlib.sha256(tex.image.packed_file.data).hexdigest())
        expected=45 if o['screen_index'] in (6,7) else 120
        assert m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value==expected
        assert m.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].links[0].from_node==tex
    assert len(set(hashes[:6]))==6 and len(set(hashes))==10
    assert screens[6]['screenshot']=='code-01.png' and screens[7]['screenshot']=='code-02.png'
    floor_screens=screens[8:]
    assert [o['screenshot'] for o in floor_screens]==['game-07.png','game-08.png']
    assert [o.parent.name for o in floor_screens]==['Low floor display left','Low floor display right']
    def seam_edge(panel,right):
        edge=(max if right else min)(v.co.x for v in panel.data.vertices)
        vertices=[panel.matrix_world@v.co for v in panel.data.vertices if abs(v.co.x-edge)<1e-6]
        return sum(vertices,Vector())/len(vertices)
    seam_left=seam_edge(floor_screens[0],True);seam_right=seam_edge(floor_screens[1],False)
    seam_gap_xy=(Vector((seam_left.x,seam_left.y))-Vector((seam_right.x,seam_right.y))).length
    assert seam_gap_xy<.08,('floor monitors are not joined',seam_gap_xy)
    floor_screen_back_y=max((o.matrix_world@v.co).y for o in floor_screens for v in o.data.vertices)
    pc_front_y=min((o.matrix_world@Vector(corner)).y for o in pc.children_recursive
                   if o.type in {'MESH','CURVE','FONT'} for corner in o.bound_box)
    assert pc_front_y>floor_screen_back_y+.025,('case must be behind the floor monitors',pc_front_y,floor_screen_back_y)
    shelf_roots=[o for o in s.objects if o.name.startswith('Library ') and o.get('shelf_levels')==6]
    assert len(shelf_roots)==2
    oak_shelves=[o for o in s.objects if o.name.startswith('Library ') and 'oak shelf ' in o.name]
    bricks=[o for o in s.objects if o.name.startswith('Library ') and 'handmade brick' in o.name]
    book_orientations={o['book_orientation'] for o in s.objects if o.get('book_orientation')}
    assert len(oak_shelves)==12 and len(bricks)>100
    assert {'upright','leaning','stacked'}<=book_orientations
    old_rack_names=('Left tall rack upright','Right tall rack upright','Left rack shelf','Right rack shelf',
                    'Left book','Right book','Left dark upper storage box','Right dark upper storage box')
    assert not any(o.name.startswith(old_rack_names) for o in s.objects)
    assert len([o for o in s.objects if o.name.startswith('PC - RAM DIMM')])==4
    assert len([o for o in s.objects if o.name.startswith('PC - 24 pin braided')])==10
    assert len([o for o in s.objects if o.name.startswith('PC - GPU braided')])==8
    assert bpy.data.objects.get('PC - tempered glass show panel')
    assert bpy.data.objects['PC - Aurora panoramic tower']['graphics_card']=='NVIDIA GeForce RTX 5070'
    assert bpy.data.objects['PC - GEFORCE RTX 5070'].data.body=='GEFORCE RTX 5070'
    assert bpy.data.objects['Phone in hands']['display_count']==1
    assert bpy.data.objects.get('Phone screen') is None
    assert all(im.packed_file for im in bpy.data.images if im.source=='FILE')
    floor=next(r for r in rigs if r.parent.name.startswith('On floor'))
    assert floor.animation_data.action['ysm_clip']=='scene_floor_phone'
    body=next(o for o in floor.parent.children if o.type=='MESH')
    posed=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    min_z=min((posed.matrix_world@Vector(v)).z for v in posed.bound_box)
    assert 0<=min_z<.08
    char=dict(rig=floor,root=floor.parent,mesh=body)
    contacts={name:contact_min(char,groups) for name,groups in [('thighs',['LeftLeg','RightLeg']),('feet',['LeftFoot','RightFoot'])]}
    assert all(abs(v-.002)<.00002 for v in contacts.values()),contacts
    result=dict(status='passed',fresh_model_variants=5,main_screens_unique=6,total_unique_screen_images=10,
                code_screens=2,rgb_ram_dimms=4,individual_power_cables=18,room_actions=95,
                source_models=[r['ysm_source_model'] for r in rigs],floor_min_z=min_z,
                image_driven_lighting=True,gpu='OptiX',resolution=[2560,1440],cameras=8,
                graphics_card='RTX 5070',phone_displays=1,floor_contacts=contacts,
                floor_monitors=2,floor_monitor_seam_gap_xy=seam_gap_xy,
                case_behind_floor_monitors=True,case_front_y=pc_front_y,floor_screen_back_y=floor_screen_back_y,
                timber_bookshelves=2,oak_shelves=len(oak_shelves),brick_count=len(bricks),
                book_orientations=sorted(book_orientations))
    (folder/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('RGB_ROOM_VALIDATION_PASSED',json.dumps(result),flush=True)


if __name__=='__main__':main()
