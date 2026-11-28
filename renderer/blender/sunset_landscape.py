"""Voxel riverside landscape for the existing Minecraft city.

Geometry and texels remain block based. The caller supplies the reflective water,
lighting and sky; every solid here uses the locally extracted Minecraft atlas.
"""
from collections import defaultdict
import math
import random

import bpy


def build_landscape(scene, atlas, mapping, texture_dir=None):
    rng = random.Random(271127)
    blocks = {}
    lamps = []
    grass_positions = []

    def fill(x0, x1, y0, y1, z0, z1, state):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    blocks[x, y, z] = state

    # The original scene ends at y=56, with its walking surface at z=0.
    # Broad, distant terrain surrounds the walls without covering the old city.
    peaks = [(-102, -83, 40, 54), (-81, -133, 47, 55),
             (-26, -136, 38, 43), (28, -144, 54, 59),
             (86, -112, 43, 55), (116, -47, 36, 44),
             (-117, 7, 30, 49)]
    heights = {}
    for x in range(-135, 136):
        for y in range(-160, 111):
            if -59 <= x <= 59 and -85 <= y <= 56:
                continue
            if -90 <= x <= 90 and 57 <= y <= 73:
                h = -4
            else:
                mountain = max((height * max(0, 1 - math.hypot(x-px, y-py)/radius)
                                for px, py, height, radius in peaks), default=0)
                detail = (math.sin(x*.22+y*.11)*1.7 + math.sin(y*.33-x*.08)*1.3
                          + math.sin(x*.47)*math.sin(y*.38)*1.2)
                h = math.floor(mountain + detail * min(1, mountain/8)) - 1
                if y >= 74 and abs(x) < 90:
                    h = -1 + int(y > 84 and abs(x)>20) + int(y>99)
            heights[x, y] = h
            # Surface columns include just enough depth to join adjacent steps.
            # Undersides are closed below after adjacent heights are known.
    for (x, y), h in heights.items():
        neighbours = [heights.get((x+dx,y+dy), -6) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]]
        low = min(h-1, min(neighbours))
        if -90 <= x <= 90 and 57 <= y <= 73:
            top = 'dirt' if rng.random()<.6 else 'cobblestone'
        elif h > 23 and rng.random()<.58:
            top = 'cobblestone' if rng.random()<.72 else 'mossy_stone_bricks'
        else:
            top = 'grass_block'
        for z in range(low, h+1):
            blocks[x,y,z] = top if z==h else 'dirt' if h<5 else 'cobblestone'
        if top=='grass_block' and -70<x<70 and 35<y<103 and rng.random()<.14:
            if not (-6<x<7):
                grass_positions.append((x+.5,y+.5,h+1))

    # Dark wood bridge, supported by submerged piles and fenced along both edges.
    fill(-3,3,57,77,-1,-1,'spruce_planks')
    for x in [-3,3]:
        for y in [54,60,66,72,77]:
            fill(x,x,y,y,-4,-1,'oak_log')
    fill(-3,3,78,88,-1,-1,'cobblestone')

    # Natural, stepped shore pieces break up a perfectly rectangular canal edge.
    for x0,y0,w,d in [(-30,57,8,2),(-17,57,5,3),(15,57,7,2),(30,57,9,3),
                       (-50,72,10,3),(-20,72,8,3),(18,72,9,3),(43,72,7,3)]:
        fill(x0,x0+w,y0,y0+d,-3,-2,'dirt')
        fill(x0,x0+w,y0,y0+d,-1,-1,'grass_block')
        for i in range(max(4,w)):
            grass_positions.append((x0+rng.uniform(0,w),y0+rng.uniform(0,d),0))

    def tree(x,y,h,wide=3):
        ground=heights.get((x,y),-1)+1
        fill(x,x,y,y,ground,ground+h,'oak_log')
        for z,radius in [(h-2,wide),(h-1,wide+1),(h,wide+1),(h+1,wide),(h+2,wide-1)]:
            for dx in range(-radius,radius+1):
                for dy in range(-radius,radius+1):
                    if abs(dx)+abs(dy)<radius*1.65 and rng.random()>.05:
                        blocks[x+dx,y+dy,ground+z]='oak_leaves'
        blocks[x,y,ground+h+3]='oak_leaves'

    for x,y,h,w in [(-22,48,7,3),(22,47,7,3),(-37,50,8,3),(38,47,6,3),
                    (-18,83,7,3),(31,87,8,3),(-45,79,7,3),(55,81,7,3),
                    (-66,14,8,3),(68,-8,8,3),(-67,-34,7,3),(67,-57,8,3),
                    (-75,89,8,3),(80,90,8,3)]:
        tree(x,y,h,w)

    # Small lanterns preserve the reference's warm, dotted waterside rhythm.
    for x,y in [(-7,53),(7,53),(-23,76),(39,76),(-34,53),(35,53)]:
        fill(x,x,y,y,0,2,'stripped_dark_oak_log')
        blocks[x,y,3]='glowstone'
        fill(x-1,x+1,y-1,y+1,4,4,'dark_oak_planks')
        lamps.append((x+.5,y+.5,3.5))

    collection=bpy.data.collections.new('Sunset riverside - original voxel terrain')
    scene.collection.children.link(collection)
    groups=defaultdict(lambda: [[],[],[]])
    sides=[((1,0,0),[(1,0,0),(1,1,0),(1,1,1),(1,0,1)],'east'),
           ((-1,0,0),[(0,1,0),(0,0,0),(0,0,1),(0,1,1)],'west'),
           ((0,1,0),[(1,1,0),(0,1,0),(0,1,1),(1,1,1)],'south'),
           ((0,-1,0),[(0,0,0),(1,0,0),(1,0,1),(0,0,1)],'north'),
           ((0,0,1),[(0,0,1),(1,0,1),(1,1,1),(0,1,1)],'up'),
           ((0,0,-1),[(0,1,0),(1,1,0),(1,0,0),(0,0,0)],'down')]
    width,height=mapping['size']
    transparent={'oak_leaves','spruce_leaves'}
    for (x,y,z),state in blocks.items():
        verts,faces,uvs=groups[state]
        for (dx,dy,dz),corners,side in sides:
            if dz < 0:
                continue  # Terrain undersides never enter these ground-level views.
            neighbour=blocks.get((x+dx,y+dy,z+dz))
            if neighbour and (neighbour not in transparent or neighbour==state):
                continue
            first=len(verts)
            verts.extend((x+a,y+b,z+c) for a,b,c in corners)
            faces.append((first,first+1,first+2,first+3))
            tx,ty,_,_=mapping['tiles'][mapping['states'][state][side]]['pixel']
            uvs.extend(((tx+a)/width,1-(ty+b)/height)
                       for a,b in [(0.05,15.95),(15.95,15.95),(15.95,.05),(.05,.05)])
    faces_count=0
    for state,(verts,faces,uvs) in groups.items():
        mesh=bpy.data.meshes.new(state+' riverside faces')
        mesh.from_pydata(verts,[],faces)
        mesh.update()
        mesh.uv_layers.new(name='Minecraft atlas').data.foreach_set('uv',[n for pair in uvs for n in pair])
        material=bpy.data.materials.get('minecraft:'+state)
        if material is None:
            material=bpy.data.materials.new('minecraft:'+state)
            material.use_nodes=True
            texture=material.node_tree.nodes.new('ShaderNodeTexImage')
            texture.image=atlas
            texture.interpolation='Closest'
            shader=material.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Roughness'].default_value=.85
            material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
            if state in transparent:
                material.node_tree.links.new(texture.outputs['Alpha'],shader.inputs['Alpha'])
                material.surface_render_method='DITHERED'
        mesh.materials.append(material)
        obj=bpy.data.objects.new(state+' riverside',mesh)
        collection.objects.link(obj)
        obj['minecraft_block']='minecraft:'+state
        faces_count+=len(faces)

    # Fence rails use the same timber material, in vanilla fence-like proportions.
    def beam(name,location,scale):
        bpy.ops.mesh.primitive_cube_add(size=1,location=location)
        obj=bpy.context.object
        obj.name=name
        obj.scale=scale
        for old in list(obj.users_collection): old.objects.unlink(obj)
        collection.objects.link(obj)
        obj.data.materials.append(bpy.data.materials['minecraft:spruce_planks'])
        # UV scaling stretches less than an entire block per thin fence face.
        for loop in obj.data.uv_layers.active.data:
            tx,ty,_,_=mapping['tiles'][mapping['states']['spruce_planks']['north']]['pixel']
            loop.uv=((tx+loop.uv.x*15.9)/width,1-(ty+loop.uv.y*15.9)/height)
    for x in [-3,3]:
        for y in range(54,78,2):
            beam('Bridge fence post',(x+.5,y+.5,.575),(.25,.25,1.15))
        for z in [.5,1.1]:
            beam('Bridge horizontal fence',(x+.5,65.7,z),(.18,23.5,.18))

    # Vanilla cutout plants catch the warm rim light without smoothing the texels.
    vegetation_count = 0
    if texture_dir is not None:
        from pathlib import Path
        texture_dir = Path(texture_dir)
        plant_groups = defaultdict(list)
        for _ in range(420):
            x = rng.uniform(-52, 53)
            y = rng.choice([rng.uniform(49,56),rng.uniform(75,87)])
            if -7 < x < 8:
                continue
            ground = 0 if y <= 56 else heights.get((int(x),int(y)),-1)+1
            plant = rng.choices(['grass','fern','dandelion','poppy'],[.72,.15,.08,.05])[0]
            plant_groups[plant].append((x,y,ground,rng.uniform(.4,.65) if plant in ['poppy','dandelion'] else rng.uniform(.5,.95)))
        for side in [-1,1]:
            for _ in range(30):
                x = side*rng.uniform(9,50)
                y = rng.uniform(57,58.5) if rng.random()<.5 else rng.uniform(72,73.5)
                plant_groups['sugar_cane'].append((x,y,-.4,rng.uniform(.9,1.4)))
        for name,plants in plant_groups.items():
            path = texture_dir / (name+'.png')
            if not path.exists():
                continue
            tex=bpy.data.images.load(str(path),check_existing=True)
            tex.pack()
            material=bpy.data.materials.new('minecraft:'+name+' cutout')
            material.use_nodes=True
            nodes=material.node_tree.nodes
            shader=nodes.get('Principled BSDF')
            shader.inputs['Roughness'].default_value=.9
            shader.inputs['Specular IOR Level'].default_value=.1
            texture=nodes.new('ShaderNodeTexImage')
            texture.image=tex
            texture.interpolation='Closest'
            if name in ['grass','fern']:
                multiply=nodes.new('ShaderNodeMixRGB')
                multiply.blend_type='MULTIPLY'
                multiply.inputs[0].default_value=1
                multiply.inputs[2].default_value=(.48,.69,.12,1)
                material.node_tree.links.new(texture.outputs['Color'],multiply.inputs[1])
                material.node_tree.links.new(multiply.outputs[0],shader.inputs['Base Color'])
            else:
                material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
            material.node_tree.links.new(texture.outputs['Alpha'],shader.inputs['Alpha'])
            material.surface_render_method='DITHERED'
            verts,faces,uvs=[],[],[]
            for x,y,z,size in plants:
                angle=rng.uniform(0,math.pi)
                for rot in [angle,angle+math.pi/2]:
                    dx,dy=math.cos(rot)*size/2,math.sin(rot)*size/2
                    first=len(verts)
                    verts.extend([(x-dx,y-dy,z),(x+dx,y+dy,z),(x+dx,y+dy,z+size),(x-dx,y-dy,z+size)])
                    faces.append((first,first+1,first+2,first+3))
                    uvs.extend([(0,0),(1,0),(1,1),(0,1)])
            mesh=bpy.data.meshes.new(name+' crossed pixel plants')
            mesh.from_pydata(verts,[],faces)
            mesh.uv_layers.new(name='Vanilla full tile').data.foreach_set('uv',[n for pair in uvs for n in pair])
            mesh.materials.append(material)
            obj=bpy.data.objects.new(name+' bank vegetation',mesh)
            collection.objects.link(obj)
            vegetation_count+=len(plants)

    # Existing approach is dry; surface is provided by the caller for reflections.
    return {'blocks':len(blocks),'faces':faces_count,'water_bounds':[-90,91,57,74],
            'water_z':-.40,'riverbed_z':-3,'bridge_center_x':.5,
            'bridge_deck_z':0,'lamps':lamps,'grass_positions':grass_positions,
            'vegetation_count':vegetation_count}
