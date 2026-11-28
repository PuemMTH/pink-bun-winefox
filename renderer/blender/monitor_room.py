"""Editable dark monitor room, composed from the user-supplied reference frame."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/blender-scenes/monitor-room'
SCREEN_DIR=ROOT/'assets/monitor-screens'
THEMES={'mixed':['game-01.png','game-02.png','game-03.png','game-04.png','game-05.png','game-06.png','code-01.png','code-02.png','game-07.png','game-08.png'],
        'daylight':['local-daylight.png']*9,'nether':['nether.jpg']*9,'warped':['warped.jpg']*9}
sys.path.insert(0,str(Path(__file__).parent))
from convert import select_action
from sunset_city import aim, camera, area, glow
from pc_case import build_pc_case
from bookshelves import build_bookshelves

VIEW_CONFIGS=[('01 - Reference composition',(0,-6,1.6),(0,2.6,2.15),32,'reference'),
 ('02 - Low seated character',(-.85,-1.45,1.10),(-.6,.75,.52),26,'character'),
 ('03 - Desk and screen arrangement',(2.4,-3.7,2.65),(.1,2.1,1.2),28,'layout'),
 ('04 - Panoramic RGB computer',(-2.6,-1.35,1.18),(-1.75,.85,.38),40,'pc'),
 ('05 - Left room overview',(-3.2,-3.4,2.6),(0,2,1.25),28,'room-left'),
 ('06 - Reverse room and characters',(-.3,3.8,3.75),(-.3,.6,.7),28,'room-reverse'),
 ('07 - RTX 5070 computer side',(-3.05,.2,1.15),(-1.73,1.0,.38),32,'pc-side'),
 ('08 - Seated phone side view',(-2.4,-.2,1.0),(-.7,.65,.48),26,'character-side')]


def material(name,color,rough=.65,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough
    if emission:
        p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    return m


def box(name,pos,size,mat,bevel=0):
    # Direct meshes avoid a full scene update for every book cover and brick.
    mesh=bpy.data.meshes.new(name+' mesh')
    mesh.from_pydata([(x*size[0]/2,y*size[1]/2,z*size[2]/2) for x,y,z in
        [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]],[],
        [(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)])
    mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);o.location=pos
    o.data.materials.append(mat)
    if bevel:
        b=o.modifiers.new('Small furniture edges','BEVEL');b.width=bevel;b.segments=2
    return o


def cylinder(name,pos,r,h,mat,vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=h,location=pos)
    o=bpy.context.object;o.name=name;o.data.materials.append(mat);return o


def append_character(file,label):
    with bpy.data.libraries.load(str(file),link=False) as (available,loaded):
        loaded.collections=list(available.collections);loaded.actions=list(available.actions);loaded.texts=list(available.texts)
    for c in loaded.collections:bpy.context.scene.collection.children.link(c)
    for a in loaded.actions:a.use_fake_user=True
    rig=next(o for c in loaded.collections for o in c.all_objects if o.type=='ARMATURE')
    body=next(o for o in rig.parent.children if o.type=='MESH')
    actions={a['ysm_clip']:(a,next(iter(a.slots))) for a in loaded.actions if a.get('ysm_clip')}
    rig.parent.name=label+' - Character root'
    return dict(root=rig.parent,rig=rig,mesh=body,actions=actions,fps=30)


def bone_world(character,name):
    bpy.context.view_layer.update()
    return character['rig'].matrix_world @ character['rig'].pose.bones[name].matrix.translation


def ground_min(character):
    bpy.context.view_layer.update()
    o=character['mesh'].evaluated_get(bpy.context.evaluated_depsgraph_get())
    return min((o.matrix_world@Vector(p)).z for p in o.bound_box)


def contact_min(character,groups):
    bpy.context.view_layer.update()
    body=character['mesh'];indices={body.vertex_groups[n].index for n in groups}
    posed=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=posed.to_mesh()
    try:return min((posed.matrix_world@v.co).z for v in mesh.vertices if any(g.group in indices for g in v.groups))
    finally:posed.to_mesh_clear()


def pose_phone_reader(girl):
    """Ground the seated thighs first, then bend the knees to ground both feet."""
    pose=girl['rig'].pose.bones
    rotations={'UpBody':(-8,0,0),'UpperBody':(8,0,0),'DownBody':(0,0,0),'MHead':(-18,0,0),
        'LeftLeg':(135,0,-5),'RightLeg':(135,0,5),'LeftLowerLeg':(-75,0,0),'RightLowerLeg':(-75,0,0),
        'LeftFoot':(-60,0,0),'RightFoot':(-60,0,0),'LeftArm':(28,0,-12),'RightArm':(28,0,12),
        'LeftForeArm':(100,0,0),'RightForeArm':(100,0,0),'LeftHand':(0,0,0),'RightHand':(0,0,0)}
    for name,angles in rotations.items():pose[name].rotation_euler=[math.radians(a) for a in angles]
    girl['root'].location.z+=.002-contact_min(girl,['LeftLeg','RightLeg'])
    low,high=-85.,-65.
    for _ in range(15):
        angle=(low+high)/2
        for side in ['Left','Right']:
            pose[side+'LowerLeg'].rotation_euler.x=math.radians(angle)
            pose[side+'Foot'].rotation_euler.x=math.radians(-(135+angle))
        if contact_min(girl,['LeftFoot','RightFoot'])<.002:low=angle
        else:high=angle
    for name in rotations:pose[name].keyframe_insert(data_path='rotation_euler',frame=1,group=name)
    report={name:contact_min(girl,groups) for name,groups in [('seated_thigh_contact',['LeftLeg','RightLeg']),('feet_contact',['LeftFoot','RightFoot'])]}
    assert all(abs(v-.002)<.00002 for v in report.values()),report
    girl['rig']['floor_contact_report']=json.dumps(report)
    return report


def phone_prop(girl,frame,screen_material):
    hand=(bone_world(girl,'LeftHand')+bone_world(girl,'RightHand'))/2
    forward=girl['root'].rotation_euler.to_matrix()@Vector((0,1,0))
    phone=box('Phone in hands',hand+forward*.025+Vector((0,0,.018)),(.12,.016,.18),frame,.006)
    phone.rotation_euler=(math.radians(-12),0,girl['root'].rotation_euler.z)
    phone.data.materials.append(screen_material)
    for face in phone.data.polygons:
        if face.normal.y<-.5:face.material_index=1
    phone['display_count']=1
    return phone


def apply_screens(scene,theme,strength=350,image_override=None):
    panels=sorted([o for o in scene.objects if o.get('screen_index') is not None],key=lambda o:o['screen_index'])
    for panel in panels:
        mat=panel.data.materials[0];node=mat.node_tree.nodes.get('Minecraft screenshot')
        images=THEMES[theme]
        source=Path(image_override) if image_override else SCREEN_DIR/images[panel['screen_index']%len(images)]
        if panel['screen_index'] in (6,7):source=SCREEN_DIR/f"code-{panel['screen_index']-5:02}.png"
        image=bpy.data.images.load(str(source.resolve()),check_existing=True);image.pack()
        node.image=image
        mat.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=45 if panel['screen_index'] in (6,7) else strength
        w,h=panel['display_width'],panel['display_height']
        image_aspect=image.size[0]/image.size[1];panel_aspect=w/h
        u=min(1,panel_aspect/image_aspect);v=min(1,image_aspect/panel_aspect)
        u0,v0=(1-u)/2,(1-v)/2
        panel.data.uv_layers.active.data.foreach_set('uv',[u0,v0,1-u0,v0,1-u0,1-v0,u0,1-v0])
        for vertex,co in zip(panel.data.vertices,[(-w/2,0,-h/2),(w/2,0,-h/2),(w/2,0,h/2),(-w/2,0,h/2)]):vertex.co=co
        panel['screenshot']=source.name
    scene['screen_theme']=theme;scene['screen_emission_strength']=strength


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--draft',action='store_true');parser.add_argument('--all',action='store_true')
    parser.add_argument('--theme',choices=list(THEMES),default='mixed');parser.add_argument('--variants',action='store_true')
    parser.add_argument('--image',type=Path);parser.add_argument('--brightness',type=float,default=120)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.output:OUT=args.output.resolve()
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    school=append_character(ROOT/'output/blender/latest/satou-school-square-eyes.blend','At desk')
    girl=append_character(ROOT/'output/blender/latest/satou-white-square-eyes.blend','On floor')
    select_action(school,'sit',0);select_action(girl,'sit',0)
    phone_pose=girl['rig'].animation_data.action.copy();phone_pose.name='Floor character - reading phone'
    phone_pose['ysm_clip']='scene_floor_phone';phone_pose.use_fake_user=True
    girl['rig'].animation_data.action=phone_pose;girl['rig'].animation_data.action_slot=next(iter(phone_pose.slots))
    school['root'].scale*=1.18;school['root'].location=(.24,1.55,0)
    school['root'].location.z+=1.02-bone_world(school,'DownBody').z
    girl['root'].scale*=.91;girl['root'].location=(-.67,.68,0);girl['root'].rotation_euler.z=math.radians(143)
    pose_phone_reader(girl)
    wall=material('Midnight blue wall',(.07,.075,.12))
    ceiling=material('Almost black ceiling',(.009,.011,.024))
    wood=material('Dark desaturated desk',(.06,.055,.07),.5)
    frame=material('Black monitor bezels',(.004,.005,.012),.28)
    steel=material('Cold blue-black steel',(.012,.016,.035),.35)
    chairmat=material('Deep violet chair upholstery',(.014,.008,.025),.75)
    accent=material('Chair violet seam',(.037,.017,.059))
    phoneglow=material('Soft phone screen',(.3,.43,1),.45,2)
    bookmats=[material('Shelf spine '+str(i),(.012+i*.005,.017+i*.004,.035+i*.008)) for i in range(5)]
    # High, mostly empty upper wall and dark aisles frame the lit desk below.
    box('Floor',(0,0,-.06),(8,10.5,.12),wood)
    box('Back wall',(0,4.25,2.45),(8,.16,4.9),wall)
    box('Ceiling',(0,.2,4.85),(8,8.2,.15),ceiling)
    box('Left wall',(-3.95,.2,2.4),(.12,8.2,4.8),wall)
    box('Right wall',(3.95,.2,2.4),(.12,8.2,4.8),ceiling)
    for x in [-.85,1.65]:box('Back panel seam',(x,4.155,2.6),(.025,.02,4.4),ceiling)
    box('High air conditioner',(-2.75,3.96,3.82),(1.65,.4,.73),wall,.035)
    box('Air conditioner violet lower lip',(-2.75,3.72,3.56),(1.57,.12,.16),accent,.015)
    box('Air conditioner control',(-2.07,3.72,3.49),(.1,.07,.27),steel)
    # Timber boards, brick backing and varied book arrangements from the shelf reference.
    build_bookshelves(box,material)
    # A second black monitor and stacked computer cases sit in the left darkness.
    box('Inactive left screen',(-2.02,2.62,1.7),(1.04,.09,.8),frame,.02).rotation_euler.z=math.radians(11)
    box('Left screen stand',(-2.02,2.7,1.14),(.11,.1,.45),steel)
    # Desktop and keyboard, mostly hidden by the silhouette of the chair.
    box('Main desk top',(0,2.78,.91),(4.8,1.65,.12),wood,.02)
    for x in [-2.15,2.15]:
        for y in [2.1,3.45]:box('Desk leg',(x,y,.44),(.065,.065,.88),steel)
    box('Desk rear support',(0,3.45,.62),(4.35,.07,.4),ceiling)
    box('Keyboard',(0,2.16,.99),(.68,.24,.035),frame,.012)
    for i in range(10):box('Dim keyboard key',(-.29+i*.064,2.16,1.012),(.045,.18,.008),steel)
    # Six main panels form the shallow arc, with an additional right-hand stack.
    screen_count=0
    def monitor(name,x,y,z,w,h,yaw):
        nonlocal screen_count
        parent=bpy.data.objects.new(name,None);scene.collection.objects.link(parent);parent.location=(x,y,z);parent.rotation_euler.z=math.radians(yaw)
        bezel=box(name+' bezel',(0,0,0),(w+.065,.085,h+.065),frame,.018);bezel.parent=parent;bezel.location=(0,0,0)
        box_panel=box(name+' black panel',(0,0,0),(w,.012,h),frame,.008);box_panel.parent=parent;box_panel.location=(0,-.05,0)
        mesh=bpy.data.meshes.new(name+' display UV plane')
        mesh.from_pydata([(-w/2,0,-h/2),(w/2,0,-h/2),(w/2,0,h/2),(-w/2,0,h/2)],[],[(0,1,2,3)])
        mesh.uv_layers.new(name='Full screenshot').data.foreach_set('uv',[0,0,1,0,1,1,0,1])
        panel=bpy.data.objects.new(name+' Minecraft screen',mesh);scene.collection.objects.link(panel);panel.parent=parent;panel.location=(0,-.059,0)
        mat=material(name+' image emission',(.01,.01,.01),emission=args.brightness)
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.name='Minecraft screenshot';tex.interpolation='Linear'
        shader=mat.node_tree.nodes.get('Principled BSDF')
        mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Emission Color'])
        # Keep the image readable to the camera while the same image supplies brighter GI.
        display=mat.node_tree.nodes.new('ShaderNodeEmission');display.name='Display - readable image';display.inputs['Strength'].default_value=.8
        mat.node_tree.links.new(tex.outputs['Color'],display.inputs['Color'])
        ray=mat.node_tree.nodes.new('ShaderNodeLightPath');mix=mat.node_tree.nodes.new('ShaderNodeMixShader')
        mat.node_tree.links.new(ray.outputs['Is Camera Ray'],mix.inputs[0]);mat.node_tree.links.new(shader.outputs[0],mix.inputs[1]);mat.node_tree.links.new(display.outputs[0],mix.inputs[2])
        mat.node_tree.links.new(mix.outputs[0],mat.node_tree.nodes.get('Material Output').inputs['Surface'])
        mesh.materials.append(mat);panel['screen_index']=screen_count;panel['display_width']=w;panel['display_height']=h;screen_count+=1
        return parent
    for col,(x,y,yaw,w) in enumerate([(-1.02,3.02,13,.93),(0,3.15,0,1.05),(1.05,3.04,-13,.93)]):
        for row,z in enumerate([1.34,2.02]):monitor(f'Main display {col+1}-{row+1}',x,y,z,w,.59,yaw)
        box('Monitor support pole',(x,y+.15,1.37),(.045,.045,1.0),steel)
    for row,z in enumerate([1.49,2.33]):monitor('Right display '+str(row+1),2.03,2.67,z,.75,.73,-37)
    # Can with a muted diagonal label, as on the left of the reference desk.
    can=cylinder('Drink can',(-1.03,2.26,1.22),.105,.48,steel)
    cylinder('Drink can rim',(-1.03,2.26,1.467),.09,.014,bookmats[3])
    label=box('Can diagonal label',(-1.03,2.151,1.23),(.15,.007,.07),material('Pale can label',(.45,.39,.35)))
    label.rotation_euler.y=math.radians(-23)
    # Chair back dominates the central silhouette; head and elbows show above it.
    cylinder('Chair central support',(.24,1.39,.35),.065,.57,steel)
    cylinder('Chair base hub',(.24,1.39,.12),.15,.08,frame)
    for i in range(5):
        theta=i*math.tau/5
        arm=box('Chair star foot',(.24+math.cos(theta)*.22,1.39+math.sin(theta)*.22,.13),(.5,.07,.065),frame,.02);arm.rotation_euler.z=theta
        cylinder('Chair caster',(.24+math.cos(theta)*.46,1.39+math.sin(theta)*.46,.07),.065,.09,frame,12)
    box('Chair seat',(.24,1.4,.76),(.88,.72,.14),chairmat,.065)
    box('Chair sculpted back',(.24,.99,1.31),(.96,.2,1.03),chairmat,.11)
    for x in [-.28,.76]:
        box('Chair back side', (x,1.02,1.35),(.13,.23,.94),chairmat,.06)
        box('Chair violet seam',(x,.88,1.34),(.017,.01,.8),accent,.005)
        box('Chair arm rest',(x,1.5,1.01),(.13,.65,.08),chairmat,.035)
    # The red annotation is a joined pair: taller left screen, shorter right screen.
    monitor('Low floor display left',-1.97,.55,.35,.49,.62,22)
    monitor('Low floor display right',-1.505,.61,.30,.48,.52,-8)
    for x,y in [(-1.97,.59),(-1.505,.66)]:
        box('Floor monitor foot',(x,y,.0075),(.31,.23,.015),steel,.006)
    cylinder('Floor monitor central hinge',(-1.743,.643,.29),.009,.56,steel)
    # Phone is a real prop held near the two animated hand bones.
    phone_prop(girl,frame,phoneglow)
    # Near-camera objects provide the out-of-focus framing of the still.
    # The green annotation is the case behind the two floor screens.
    pc=build_pc_case(box,material,position=(-1.78,1.08,0),yaw=0)
    pc.scale=(1,.85,.5)
    pc['placement']='behind joined floor monitor pair, as annotated in reference'
    for i,(x,y,z,size) in enumerate([(2.43,-2.12,.55,(1.7,1.2,1.05)),(2.7,-.8,.95,(1.2,.8,1.9))]):
        box('Soft foreground silhouette '+str(i),(x,y,z),size,ceiling,.025)
    frameob=box('Foreground leaning picture frame',(2.45,-.45,1.46),(.48,.07,.65),steel,.025);frameob.rotation_euler=(math.radians(-12),math.radians(8),math.radians(-25))
    picture=box('Very dim indigo picture',(2.45,-.497,1.46),(.4,.012,.56),material('Indigo picture',(.019,.011,.043),emission=.06),.005);picture.rotation_euler=frameob.rotation_euler
    # Screen lighting stays cold and directional; the rest of the room remains dark.
    for i,x in enumerate([-1.05,0,1.05]):area('Screen blue light '+str(i),(x,2.9,1.8),(0,1,1.05),38,1.15,(.25,.35,1))
    area('Right screen blue spill',(1.95,2.48,1.9),(.6,1.1,1.15),32,.9,(.23,.32,1))
    area('Floor screen glow',(-1.22,.27,.48),(-.55,.65,.7),13,.65,(.3,.38,1))
    area('Violet hair rim',(.2,2.48,2.6),(.24,1.5,1.8),13,.75,(.47,.2,1))
    area('Very faint front bounce',(-1.5,-1,2),(-.4,1,1),1.8,2,(.16,.19,.6))
    # Image emission supplies the light. Fixed blue area lights would conceal image-dependent changes.
    for obj in scene.objects:
        if obj.type=='LIGHT':obj.data.energy=0
    world=bpy.data.worlds.new('Night room world');world.use_nodes=True;scene.world=world
    world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.004,.005,.018,1)
    world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.08
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,.3,2.4));fog=bpy.context.object;fog.name='Subtle blue air around screens';fog.scale=(7.6,7.7,4.7)
    fm=material('Low density blue room air',(.1,.15,.3));nodes=fm.node_tree.nodes;nodes.clear()
    scatter=nodes.new('ShaderNodeVolumeScatter');scatter.inputs['Density'].default_value=.007;scatter.inputs['Anisotropy'].default_value=.18
    output=nodes.new('ShaderNodeOutputMaterial');fm.node_tree.links.new(scatter.outputs[0],output.inputs['Volume']);fog.data.materials.append(fm)
    views=[(camera(name,position,target,lens),'monitor-room-'+stem) for name,position,target,lens,stem in VIEW_CONFIGS]
    focus=bpy.data.objects.new('Focus on chair and seated characters',None);scene.collection.objects.link(focus);focus.location=(.15,1.25,1.25)
    for cam,name in views:
        cam.data.dof.use_dof=True;cam.data.dof.focus_object=focus;cam.data.dof.aperture_fstop=2.4 if cam==views[0][0] else 4
        point=pc.matrix_world.inverted()@cam.location
        assert not (-.5<point.x<.5 and -.4<point.y<.4 and 0<point.z<1.5),(cam.name,'inside PC case')
        for obj in scene.objects:
            if obj.name.startswith('Soft foreground silhouette'):
                point=obj.matrix_world.inverted()@cam.location
                assert not all(min(p[i] for p in obj.bound_box)<point[i]<max(p[i] for p in obj.bound_box) for i in range(3)),(cam.name,obj.name)
    near_focus=bpy.data.objects.new('Focus on floor character',None);scene.collection.objects.link(near_focus);near_focus.location=(-.65,.7,.7)
    views[1][0].data.dof.focus_object=near_focus;views[7][0].data.dof.focus_object=near_focus
    pc_focus=bpy.data.objects.new('Focus inside RGB computer',None);scene.collection.objects.link(pc_focus);pc_focus.location=pc.matrix_world@Vector((0,0,.85))
    views[3][0].data.dof.focus_object=pc_focus;views[3][0].data.dof.aperture_fstop=8
    views[6][0].data.dof.focus_object=pc_focus;views[6][0].data.dof.aperture_fstop=8
    views[0][0].data.dof.aperture_fstop=5.6
    views[5][0]['exposure_compensation']=-1.8
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    assert any(d.use for d in prefs.devices)
    scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.use_denoising=True;scene.cycles.denoising_use_gpu=True
    scene.cycles.samples=32 if args.draft else 192;scene.cycles.adaptive_threshold=.06 if args.draft else .025
    scene.cycles.max_bounces=8;scene.cycles.transparent_max_bounces=16;scene.cycles.volume_bounces=1
    scene.render.use_persistent_data=True
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.1
    scene.render.resolution_x,scene.render.resolution_y=(1280,720) if args.draft else (2560,1440)
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    glow(scene)
    glare=scene.compositing_node_group.nodes.get('Glare');glare.inputs['Threshold'].default_value=.15
    glare.inputs['Strength'].default_value=1.1;glare.inputs['Size'].default_value=.65
    glare.inputs['Tint'].default_value=(1,1,1,1)
    scene.camera=views[0][0];scene.frame_end=901;scene.render.filepath='//monitor-room-reference.png'
    notes=bpy.data.texts.new('Monitor room reference and construction')
    notes.write('Built from the supplied still and annotated correction: six main screens, two right code screens, TWO joined floor screens in front of the RTX 5070 case, and figure seated on the floor.\nTimber shelves with exposed brick backing follow the supplied shelf photograph.\nBoth characters use the user\'s freshly imported YSM outfits. Hidden areas are reconstructed. All props are editable geometry. Player/browser overlays are excluded.\n')
    assert len(bpy.data.actions)==95 and len([o for o in scene.objects if o.type=='ARMATURE'])==2
    assert ground_min(girl)>=-.00002
    apply_screens(scene,args.theme,args.brightness,args.image)
    if args.theme=='mixed' and not args.image:
        main_panels=[o for o in scene.objects if o.get('screen_index',99)<6]
        assert len({o['screenshot'] for o in main_panels})==6
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'satou-monitor-room.blend'))
    print('ROOM_GPU',[(d.name,d.type) for d in prefs.devices if d.use], 'POSE', {k:round(v,3) for k,v in {'chair_head_z':bone_world(school,'Head').z,'floor_hips_z':bone_world(girl,'DownBody').z,'floor_min_z':ground_min(girl)}.items()},flush=True)
    for cam,name in views if args.all else views[:1]:
        scene.camera=cam;scene.view_settings.exposure=.1+cam.get('exposure_compensation',0)
        scene.render.filepath=str(OUT/(name+('-draft' if args.draft else '')+'.png'));bpy.ops.render.render(write_still=True)
    scene.camera=views[0][0];scene.render.filepath='//monitor-room-reference.png'
    scene.view_settings.exposure=.1
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'satou-monitor-room.blend'))
    variant_renders=[]
    if args.variants:
        for theme in ['daylight','nether','warped']:
            apply_screens(scene,theme,args.brightness,args.image)
            scene.render.filepath='//monitor-room-'+theme+'.png'
            bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('satou-monitor-room-'+theme+'.blend')))
            scene.render.filepath=str(OUT/('monitor-room-'+theme+('-draft' if args.draft else '')+'.png'))
            bpy.ops.render.render(write_still=True);variant_renders.append('monitor-room-'+theme+'.png')
        apply_screens(scene,args.theme,args.brightness,args.image);scene.render.filepath='//monitor-room-reference.png'
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'satou-monitor-room.blend'))
    (OUT/'manifest.json').write_text(json.dumps({'scene':'satou-monitor-room.blend','renders':[n+'.png' for c,n in views]+variant_renders,'rigs':2,'actions':95,'source_actions_per_character':47,'scene_pose_actions':1,'screen_count':10,'floor_monitor_count':2,'pc_placement':'behind floor monitor pair','theme':args.theme,'screen_brightness':args.brightness,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'gpu':'RTX5070 OptiX','samples':scene.cycles.samples},indent=2))
    print('MONITOR_ROOM_DONE',flush=True)


if __name__=='__main__':main()
