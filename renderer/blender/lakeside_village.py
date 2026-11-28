"""Build a lakeside Minecraft village following the supplied landscape composition."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sunset_city import aim, area, camera, river, glow

OUT = ROOT / 'output/blender-scenes/lakeside-village'
ASSETS = ROOT / 'dist/blender/village-assets'
rng = random.Random(271127)
blocks = {}
extras = []
lights = []


def noise(x, y):
    ix, iy = math.floor(x), math.floor(y)
    a, b = x-ix, y-iy
    a, b = a*a*(3-2*a), b*b*(3-2*b)
    def h(i, j):
        return ((math.sin(i*127.1+j*311.7)*43758.5453)%1)*2-1
    return (h(ix,iy)*(1-a)+h(ix+1,iy)*a)*(1-b)+(h(ix,iy+1)*(1-a)+h(ix+1,iy+1)*a)*b


def shore(y):
    return 7-.16*y+2*math.sin(y*.07)


def surface(x, y):
    edge = shore(y)
    if y < 76 and x < edge:
        d=edge-x
        return 1+int(d>5)+int(d>13)+max(0,int(noise(x*.065,y*.065)*2))
    peaks=[(-37,106,35,43,37),(-10,146,49,39,41),(32,123,34,36,30),
           (123,122,43,37,35),(155,165,58,48,42),(82,191,36,40,41)]
    wx=x+noise(x*.025,y*.025)*14
    wy=y+noise(y*.035,x*.035)*13
    mountain=max(h*math.exp(-2.1*((wx-px)**2/rx**2+(wy-py)**2/ry**2)) for px,py,h,rx,ry in peaks)
    rough=(noise(x*.08,y*.08)*8+noise(x*.2,y*.2)*3+noise(x*.035,y*.035)*9)*min(1,mountain/10)
    bank=max(max(0,min(1,(y-78)/53)),max(0,min(1,(x-76)/58)))
    bank=bank*bank*(3-2*bank)
    bed=-3-int(min(4,max(0,x-edge)*.07))
    return math.floor(bed*(1-bank)+(mountain+rough-2)*bank)


def fill(x0,x1,y0,y1,z0,z1,state):
    for x in range(x0,x1+1):
        for y in range(y0,y1+1):
            for z in range(z0,z1+1):
                if state is None: blocks.pop((x,y,z),None)
                else: blocks[x,y,z]=state


def box(name, state, position, scale):
    extras.append((name,state,position,scale))


def house(cx,cy,w,d,height,tower=False):
    base=surface(cx,cy)
    x0,x1=cx-w//2,cx+w//2
    y0,y1=cy-d//2,cy+d//2
    fill(x0,x1,y0,y1,base-2,base-1,'cobblestone')
    for x in range(x0,x1+1):
        for y in range(y0,y1+1):
            if x in [x0,x1] or y in [y0,y1]:
                fill(x,x,y,y,base,base+height-1,'mossy_stone_bricks' if rng.random()<.12 else 'cobblestone')
    for x in [x0,x1]:
        for y in [y0,y1]:fill(x,x,y,y,base,base+height,'oak_log')
    for z in [base+height-1]+([base+5] if tower else []):
        for x in range(x0,x1+1):
            for y in [y0,y1]:blocks[x,y,z]='spruce_planks'
        for y in range(y0,y1+1):
            for x in [x0,x1]:blocks[x,y,z]='spruce_planks'
    # Warm windows face the lake, on the sunlit east wall.
    for y in [cy-2,cy+2] if d>7 else [cy]:
        for z in ([base+3,base+8] if tower else [base+2]):
            fill(x1,x1,y,y+1,z,z+1,'glass')
            box('Lit window interior','window_light',(x1-.35,y+1,z+1),(.12,1.7,1.7))
            box('Window oak sill','spruce_planks',(x1+.6,y+1,z-.15),(.5,2.5,.3))
    if tower:
        for z in [base+3,base+8,base+12]:
            fill(cx-1,cx,y0,y0,z,z+1,'glass')
            box('Tower warm window','window_light',(cx,y0+.4,z+1),(1.7,.1,1.7))
        for z in [base+5,base+10]:
            for y in [y0,y1]:fill(x0,x1,y,y,z,z,'spruce_planks')
            for x in [x0,x1]:fill(x,x,y0,y1,z,z,'spruce_planks')
    fill(x1,x1,cy,cy,base,base+1,'spruce_planks')
    roofbase=base+height+.1
    for step in range(w//2+2):
        for x in [x0-1+step,x1+1-step]:
            box('Stepped timber roof','spruce_planks',(x+.5,cy+.5,roofbase+step*.65),(1.03,d+3,.65))
        if step<w//2+1:
            for y in [y0,y1]:
                box('Stone gable','cobblestone',(cx+.5,y+.5,roofbase+step*.65),
                    (max(.2,w-2*step),1,.65))
    if tower:
        for y in [y0-1,y1+1]:
            box('Tower balcony rail','oak_planks',(cx+.5,y+.5,base+height-1),(w+3,.35,.4))
        fill(x0+1,x0+1,y0+1,y0+1,base+height,base+height+3,'bricks')
    else:
        fill(x0+2,x0+2,y1-2,y1-2,base+height,base+height+5,'cobblestone')
    return base


def tree(x,y,h=7,r=3):
    z=surface(x,y)
    fill(x,x,y,y,z,z+h,'oak_log')
    for dz,radius in [(h-2,r),(h-1,r+1),(h,r+1),(h+1,r),(h+2,r-1)]:
        for dx in range(-radius,radius+1):
            for dy in range(-radius,radius+1):
                if abs(dx)+abs(dy)<radius*1.7 and rng.random()>.045:
                    blocks[x+dx,y+dy,z+dz]='oak_leaves'


def lantern(x,y,z,post=False):
    if post:
        box('Lantern oak post','oak_log',(x,y,z+1.6),(.28,.28,3.2))
        box('Lantern cross arm','spruce_planks',(x+.4,y,z+3.3),(1.1,.3,.3))
        z+=2.5
        x+=.75
        for dx in [-.52,.52]:
            for dy in [-.45,.45]:box('Wooden lantern frame','spruce_planks',(x+dx,y+dy,z+.5),(.16,.16,1.1))
        for dz in [0,1.05]:box('Wooden lantern frame cap','spruce_planks',(x,y,z+dz),(1.25,1.1,.16))
    # Native Minecraft lantern geometry and its exact per-face texture UVs.
    model=json.loads((ASSETS/'lantern.json').read_text())
    for elem in model['elements']:
        a,b=elem['from'],elem['to']
        scale=1.8 if post else 1
        add_faces('Vanilla lantern','lantern',[(x+(a[0]-8)/16*scale,y+(a[2]-8)/16*scale,z+a[1]/16*scale),
                                             (x+(b[0]-8)/16*scale,y+(b[2]-8)/16*scale,z+b[1]/16*scale)],elem['faces'])
    lights.append((x,y,z+.28))


groups=defaultdict(lambda:[[],[],[]])
mapping=None
directions=[((1,0,0),'east'),((-1,0,0),'west'),((0,1,0),'south'),((0,-1,0),'north'),((0,0,1),'up'),((0,0,-1),'down')]


def add_faces(name,state,bounds,custom=None,visible=None):
    (x,y,z),(X,Y,Z)=bounds
    corners={'east':[(X,y,z),(X,Y,z),(X,Y,Z),(X,y,Z)],
             'west':[(x,Y,z),(x,y,z),(x,y,Z),(x,Y,Z)],
             'south':[(X,Y,z),(x,Y,z),(x,Y,Z),(X,Y,Z)],
             'north':[(x,y,z),(X,y,z),(X,y,Z),(x,y,Z)],
             'up':[(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],
             'down':[(x,Y,z),(X,Y,z),(X,y,z),(x,y,z)]}
    for side,coords in corners.items():
        if custom is not None and side not in custom:continue
        if visible is not None and side not in visible:continue
        actual='dirt_path_side' if state=='dirt_path_top' and side not in ['up','down'] else state
        verts,faces,uvs=groups[actual]
        first=len(verts);verts.extend(coords);faces.append((first,first+1,first+2,first+3))
        if custom is not None:
            u,v,U,V=custom[side]['uv'];tw,th=16,48
        elif state in mapping['states']:
            tile=mapping['states'][state][side];u,v,w,h=mapping['tiles'][tile]['pixel']
            U,V=u+w,v+h;tw,th=mapping['size']
        else:u,v,U,V,tw,th=.03,.03,15.97,15.97,16,16
        uvs.extend([(u/tw,1-V/th),(U/tw,1-V/th),(U/tw,1-v/th),(u/tw,1-v/th)])


def make_material(state,atlas):
    old=bpy.data.materials.get('minecraft:'+state)
    if old:return old
    mat=bpy.data.materials.new('minecraft:'+state);mat.use_nodes=True
    p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.83
    p.inputs['Specular IOR Level'].default_value=.25
    if state=='window_light':
        p.inputs['Base Color'].default_value=(1,.5,.1,1)
        p.inputs['Emission Color'].default_value=(1,.4,.07,1);p.inputs['Emission Strength'].default_value=3
        return mat
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image=atlas if state in mapping['states'] else bpy.data.images.load(str(ASSETS/(state+'.png')),check_existing=True)
    tex.image.pack();tex.interpolation='Closest'
    mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    mat.node_tree.links.new(tex.outputs['Alpha'],p.inputs['Alpha'])
    if state=='lantern':
        mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=2.8
    return mat


def plants():
    count=0
    for name in ['grass','fern','poppy','dandelion','azure_bluet','blue_orchid','oxeye_daisy','sugar_cane']:
        source=(ROOT/'dist/blender/minecraft-textures'/(name+'.png'))
        if not source.exists():source=ASSETS/(name+'.png')
        tex=bpy.data.images.load(str(source),check_existing=True);tex.pack()
        mat=bpy.data.materials.new(name+' native cutout');mat.use_nodes=True
        p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.9
        img=mat.node_tree.nodes.new('ShaderNodeTexImage');img.image=tex;img.interpolation='Closest'
        color=img.outputs['Color']
        if name in ['grass','fern']:
            mix=mat.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
            mix.inputs[2].default_value=(.5,.72,.2,1);mat.node_tree.links.new(color,mix.inputs[1]);color=mix.outputs[0]
        mat.node_tree.links.new(color,p.inputs['Base Color']);mat.node_tree.links.new(img.outputs['Alpha'],p.inputs['Alpha'])
        verts,faces,uv=[],[],[]
        for i in range(630 if name=='grass' else 90 if name=='fern' else 30 if name=='sugar_cane' else 65):
            y=rng.uniform(-24,71);edge=shore(y)
            x=edge-rng.uniform(.1,17)
            z=surface(math.floor(x),math.floor(y))
            if name=='sugar_cane':x=edge+.3;z=.1
            elif (math.floor(x),math.floor(y),z) in blocks:continue
            if abs(x-(edge-3))<1.3 and name!='sugar_cane':continue
            size=rng.uniform(.5,.95) if name in ['grass','fern'] else rng.uniform(.3,.55)
            if name=='sugar_cane':size=rng.uniform(.8,1.3)
            for angle in [rng.random()*math.pi, rng.random()*math.pi]:
                dx,dy=math.cos(angle)*size/2,math.sin(angle)*size/2
                k=len(verts);verts.extend([(x-dx,y-dy,z),(x+dx,y+dy,z),(x+dx,y+dy,z+size),(x-dx,y-dy,z+size)])
                faces.append((k,k+1,k+2,k+3));uv.extend([(0,0),(1,0),(1,1),(0,1)])
            count+=1
        mesh=bpy.data.meshes.new(name+' lakeside plants');mesh.from_pydata(verts,[],faces)
        mesh.uv_layers.new().data.foreach_set('uv',[c for pair in uv for c in pair]);mesh.materials.append(mat)
        obj=bpy.data.objects.new(name+' meadow',mesh);bpy.context.scene.collection.objects.link(obj)
    return count


def main():
    global mapping
    parser=argparse.ArgumentParser();parser.add_argument('--draft',action='store_true');parser.add_argument('--all',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'output/blender-scenes/city-sunset-latest/satou-minecraft-sunset.blend'))
    scene=bpy.context.scene
    rig=next(o for o in scene.objects if o.type=='ARMATURE');character=rig.parent
    retain={character,*character.children_recursive}
    for obj in list(scene.objects):
        if obj not in retain:bpy.data.objects.remove(obj,do_unlink=True)
    mapping=json.loads((ROOT/'dist/blender/minecraft-atlas.json').read_text())
    atlas=next(i for i in bpy.data.images if i.name=='minecraft-atlas.png')
    # World-space block columns: terraced meadow, wide lake bed and rough ridges.
    heights={(x,y):surface(x,y) for x in range(-72,175) for y in range(-42,204)}
    for (x,y),h in heights.items():
        low=min(h-1,min(heights.get((x+dx,y+dy),h-1) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]))
        top='grass_block' if h>=0 else 'sand' if x<shore(y)+4 else 'gravel'
        if h>24 and noise(x*.18,y*.18)>.05:top='stone'
        for z in range(low-1,h):blocks[x,y,z]=top if z==h-1 else 'dirt' if h<12 else 'stone'
    # Curving dirt path along the bank, rather than a town-wall composition.
    for y in range(-36,66):
        for x in range(math.floor(shore(y))-5,math.floor(shore(y))-2):
            h=surface(x,y);blocks[x,y,h-1]='dirt_path_top' if rng.random()<.97 else 'gravel'
    house(-11,8,10,12,5)
    house(-12,31,6,6,15,True)
    house(-14,31,8,10,5)
    house(-2,43,6,7,4)
    house(-24,48,7,10,6)
    for x,y,h,r in [(-14,-6,7,3),(-4,16,6,3),(-20,37,7,3),(-8,57,7,3),(-32,12,8,4),
                     (-33,61,7,3),(12,110,5,2),(97,104,6,3),(111,118,5,2)]:tree(x,y,h,r)
    for i in range(150):
        x=rng.randrange(-40,164);y=rng.randrange(75,191);z=surface(x,y)
        if 2<z<25 and noise(x*.11,y*.11)>.05:tree(x,y,rng.randrange(4,7),2)
    # Lake-facing timber dock and low vanilla-style fence.
    for x in range(1,17):
        for y in range(27,34):box('Timber dock','oak_planks',(x+.5,y+.5,.45),(1,1,.3))
    for x in [3,9,16]:
        for y in [27,33]:
            box('Dock pile','oak_log',(x+.5,y+.5,-.4),(.38,.38,2.9))
            box('Dock fence post','oak_planks',(x+.5,y+.5,1.1),(.25,.25,1.2))
    for y in [27,33]:
        for z in [.95,1.5]:box('Dock rail','oak_planks',(9.5,y+.5,z),(13,.14,.14))
    for x,y in [(-2,-9),(3,12),(-1,28),(-4,47)]:lantern(x,y,surface(x,y),True)
    for x,y in [(6,27),(15,33)]:lantern(x,y,.65)
    for (x,y,z),state in blocks.items():
        visible=[]
        for (dx,dy,dz),side in directions:
            if side=='down':continue
            neighbour=blocks.get((x+dx,y+dy,z+dz))
            if neighbour is None or (neighbour in ['glass','oak_leaves'] and neighbour!=state):visible.append(side)
        if visible:add_faces('Blocks',state,[(x,y,z),(x+1,y+1,z+1)],visible=visible)
    for name,state,pos,size in extras:
        add_faces(name,state,[tuple(p-s/2 for p,s in zip(pos,size)),tuple(p+s/2 for p,s in zip(pos,size))])
    for state,(verts,faces,uv) in groups.items():
        mesh=bpy.data.meshes.new(state+' village geometry');mesh.from_pydata(verts,[],faces);mesh.update()
        mesh.uv_layers.new().data.foreach_set('uv',[c for pair in uv for c in pair]);mesh.materials.append(make_material(state,atlas))
        obj=bpy.data.objects.new(state+' village',mesh);scene.collection.objects.link(obj)
    plant_count=plants()
    river(scene,[-72,176,-42,205,-.03])
    water=bpy.data.materials.get('Water - sunset reflections and fine ripples.001') or bpy.data.materials.get('Water - sunset reflections and fine ripples')
    for mat in bpy.data.materials:
        if mat.name.startswith('Water -'):
            p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.065
    scene.world.node_tree.nodes.get('Mapping').inputs['Rotation'].default_value[2]=math.radians(-85)
    scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.28
    scene.world.node_tree.nodes.get('Blue openings between the sunset clouds').inputs[2].default_value=(.25,.58,1.6,1)
    nodes,links=scene.world.node_tree.nodes,scene.world.node_tree.links
    background=nodes.get('Background');sky_color=background.inputs['Color'].links[0].from_socket
    # Remove the photographed ground/city in the HDRI while retaining its clouds.
    direction=nodes.new('ShaderNodeSeparateXYZ');links.new(nodes.get('Texture Coordinate').outputs['Generated'],direction.inputs[0])
    sky_mask=nodes.new('ShaderNodeMapRange');sky_mask.inputs['From Min'].default_value=.04;sky_mask.inputs['From Max'].default_value=.25
    links.new(direction.outputs['Z'],sky_mask.inputs['Value'])
    clean_sky=nodes.new('ShaderNodeMixRGB');clean_sky.inputs[1].default_value=(.28,.23,.25,1)
    links.new(sky_mask.outputs[0],clean_sky.inputs[0]);links.new(sky_color,clean_sky.inputs[2]);sky_color=clean_sky.outputs[0]
    dot=nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT'
    dot.inputs[1].default_value=Vector((102,211,29.7)).normalized()
    links.new(nodes.get('Texture Coordinate').outputs['Generated'],dot.inputs[0])
    halo=nodes.new('ShaderNodeMapRange');halo.inputs['From Min'].default_value=.88;halo.inputs['From Max'].default_value=1
    links.new(dot.outputs['Value'],halo.inputs['Value'])
    power=nodes.new('ShaderNodeMath');power.operation='POWER';power.inputs[1].default_value=3;links.new(halo.outputs[0],power.inputs[0])
    addition=nodes.new('ShaderNodeMixRGB');addition.name='Golden sunset halo reflected in lake';addition.blend_type='ADD'
    addition.inputs[2].default_value=(4,1,.12,1);links.new(power.outputs[0],addition.inputs[0]);links.new(sky_color,addition.inputs[1]);links.new(addition.outputs[0],background.inputs['Color'])
    sun=bpy.data.lights.new('Golden sunset over the lake','SUN');sun.energy=4.2;sun.color=(1,.58,.24);sun.angle=math.radians(1.8)
    obj=bpy.data.objects.new(sun.name,sun);scene.collection.objects.link(obj);obj.location=(90,175,30);aim(obj,(0,0,0))
    bpy.ops.mesh.primitive_plane_add(size=14,location=(110,185,33));disc=bpy.context.object;disc.name='Square sun above the mountain gap'
    disc.rotation_euler=(Vector((8,-26,3.3))-disc.location).to_track_quat('Z','Y').to_euler()
    disc.data.materials.append(bpy.data.materials['Sun - golden emissive disc'])
    sun_shader=disc.data.materials[0].node_tree.nodes.get('Principled BSDF')
    sun_shader.inputs['Emission Color'].default_value=(1,.38,.07,1)
    sun_shader.inputs['Emission Strength'].default_value=10
    area('Warm reflected lake light',(29,0,15),(-12,12,5),13500,30,(1,.65,.32))
    area('Gentle blue sky fill',(-8,-7,27),(-8,15,2),7000,35,(.5,.7,1))
    area('Character soft sky',(8,-19,7),(4,-11,2),100,6,(1,.85,.66))
    for i,pos in enumerate(lights):
        data=bpy.data.lights.new('Real lantern light '+str(i),'POINT');data.energy=45;data.color=(1,.42,.1);data.shadow_soft_size=.22
        obj=bpy.data.objects.new(data.name,data);scene.collection.objects.link(obj);obj.location=pos
    bpy.ops.mesh.primitive_cube_add(size=1,location=(50,110,8));haze=bpy.context.object;haze.name='Warm distant lake haze';haze.scale=(410,470,30)
    mat=bpy.data.materials.new('Thin golden atmosphere');mat.use_nodes=True;mat.node_tree.nodes.clear()
    v=mat.node_tree.nodes.new('ShaderNodeVolumeScatter');v.inputs['Color'].default_value=(.95,.82,.66,1);v.inputs['Anisotropy'].default_value=.35
    # A low homogeneous mist layer keeps the upper sky clear and renders analytically.
    v.inputs['Density'].default_value=.0011
    out=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(v.outputs[0],out.inputs['Volume']);haze.data.materials.append(mat)
    character.location=(4,-11,0);character.rotation_euler.z=math.radians(178)
    body=next(o for o in character.children if o.type=='MESH');bpy.context.view_layer.update()
    posed=body.evaluated_get(bpy.context.evaluated_depsgraph_get());character.location.z+=surface(4,-11)-min((posed.matrix_world@Vector(p)).z for p in posed.bound_box)
    views=[(camera('01 - Reference lakeside village',(8,-26,3.3),(7,35,10),24),'village-sunset'),
           (camera('02 - Satou by the lake',(6,-18,2.6),(3.7,-10.5,2.35),40),'village-character'),
           (camera('03 - Lakeshore wide view',(12,-42,6.5),(0,32,9),28),'village-overview')]
    scene.camera=views[0][0];scene.cycles.device='GPU';scene.cycles.use_denoising=True;scene.cycles.denoising_use_gpu=True
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    assert any(device.use for device in prefs.devices)
    print('RENDER_GPU',[(d.name,d.type) for d in prefs.devices if d.use],flush=True)
    scene.cycles.preview_samples=64;scene.cycles.use_preview_denoising=True;scene.cycles.samples=32 if args.draft else 192
    scene.cycles.adaptive_threshold=.06 if args.draft else .025
    scene.render.resolution_x,scene.render.resolution_y=(1120,630) if args.draft else (2560,1440)
    scene.view_settings.exposure=-.1
    scene.render.filepath='//village-sunset.png';scene.render.use_persistent_data=True
    for viewport in bpy.context.screen.areas if bpy.context.screen else []:
        if viewport.type=='VIEW_3D':viewport.spaces.active.region_3d.view_perspective='CAMERA';viewport.spaces.active.shading.type='MATERIAL'
    assert len([o for o in scene.objects if o.type=='ARMATURE'])==1
    assert len(bpy.data.actions)==47
    bpy.context.view_layer.update();posed=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    assert abs(min((posed.matrix_world@Vector(p)).z for p in posed.bound_box)-surface(4,-11))<.00002
    assert all(i.packed_file for i in bpy.data.images if i.source=='FILE' and i.users)
    for name in ['Minecraft city construction','Sunset scene - rendering and credits']:
        if name in bpy.data.texts:bpy.data.texts.remove(bpy.data.texts[name])
    notes=bpy.data.texts.new('Lakeside village - scene notes')
    notes.write('Original village scene built from Minecraft block textures and unit-block terrain.\n'
                'Lantern boxes and UVs originate from the local vanilla template_lantern model.\n'
                'Character imported from the previously validated school Blender file, with47 actions.\n'
                'Native Cycles OptiX lighting and water; sky uses graded CC0 Poly Haven HDRI.\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'satou-lakeside-village.blend'))
    for cam,name in views if args.all else views[:1]:
        scene.camera=cam;scene.render.filepath=str(OUT/(name+('-draft' if args.draft else '')+'.png'));bpy.ops.render.render(write_still=True)
    scene.camera=views[0][0];scene.render.filepath='//village-sunset.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'satou-lakeside-village.blend'))
    (OUT/'manifest.json').write_text(json.dumps({'blocks':len(blocks),'plants':plant_count,'actions':len(bpy.data.actions),'renders':[n+'.png' for c,n in views],'resolution':[scene.render.resolution_x,scene.render.resolution_y],'renderer':'Cycles OptiX GPU','samples':scene.cycles.samples},indent=2))
    print('VILLAGE_DONE',len(blocks),plant_count,flush=True)


if __name__=='__main__':main()
