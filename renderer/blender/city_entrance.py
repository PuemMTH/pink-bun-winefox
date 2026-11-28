"""Render a block-built city entrance with local Minecraft client textures."""

from collections import defaultdict
from pathlib import Path
import json
import math
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/blender-scenes/city-entrance'
sys.path.insert(0, str(Path(__file__).parent))
from convert import select_action
from guild_blocks import build_city, city_entrance, PALETTE
from schematic import write_schematic


def pixel_atlas():
    source = ROOT / 'dist/blender/minecraft-atlas.png'
    mapping = json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
    atlas = bpy.data.images.load(str(source), check_existing=True)
    atlas.pack()
    atlas.filepath = '//minecraft-atlas.png'
    return atlas, mapping


def city_mesh(blocks):
    atlas, mapping = pixel_atlas()
    width, height = mapping['size']
    grouped = defaultdict(lambda: [[], [], []])
    transparent = {'glass', 'yellow_stained_glass', 'oak_leaves', 'spruce_leaves', 'water'}
    sides = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
             ((-1, 0, 0), [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)]),
             ((0, 1, 0), [(1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)]),
             ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
             ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
             ((0, 0, -1), [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)])]
    for (x, y, z), state in blocks.items():
        verts, faces, face_uvs = grouped[state]
        for (dx, dy, dz), corners in sides:
            neighbor = blocks.get((x + dx, y + dy, z + dz))
            if neighbor and (neighbor not in transparent or neighbor == state):
                continue
            start = len(verts)
            verts.extend([(x + a, y + b, z + c) for a, b, c in corners])
            faces.append((start, start + 1, start + 2, start + 3))
            side = 'up' if dz > 0 else 'down' if dz < 0 else 'east' if dx > 0 else 'west' if dx < 0 else 'south' if dy > 0 else 'north'
            tile = mapping['states'][state][side]
            tx, ty, _, _ = mapping['tiles'][tile]['pixel']
            face_uvs.extend([((tx + a) / width, 1 - (ty + b) / height)
                            for a, b in [(0.05, 15.95), (15.95, 15.95), (15.95, 0.05), (0.05, 0.05)]])
    collection = bpy.data.collections.new('Minecraft block city')
    bpy.context.scene.collection.children.link(collection)
    count = 0
    for name, (verts, faces, face_uvs) in grouped.items():
        mesh = bpy.data.meshes.new(name + ' exposed block faces')
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        uv = mesh.uv_layers.new(name='16px block tiles')
        uv.data.foreach_set('uv', [c for pair in face_uvs for c in pair])
        material = bpy.data.materials.new('minecraft:' + name)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        image = nodes.new('ShaderNodeTexImage')
        image.image = atlas
        image.interpolation = 'Closest'
        shader = nodes.get('Principled BSDF')
        shader.inputs['Roughness'].default_value = 0.87
        shader.inputs['Specular IOR Level'].default_value = 0.1
        material.node_tree.links.new(image.outputs['Color'], shader.inputs['Base Color'])
        material.node_tree.links.new(image.outputs['Color'], shader.inputs['Emission Color'])
        shader.inputs['Emission Strength'].default_value = 0.2
        if name in transparent:
            material.node_tree.links.new(image.outputs['Alpha'], shader.inputs['Alpha'])
            material.surface_render_method = 'DITHERED'
        if name in ['glowstone', 'yellow_stained_glass']:
            material.node_tree.links.new(image.outputs['Color'], shader.inputs['Emission Color'])
            shader.inputs['Emission Strength'].default_value = 1.1 if name == 'glowstone' else 0.25
        obj = bpy.data.objects.new(name + ' blocks', mesh)
        collection.objects.link(obj)
        mesh.materials.append(material)
        obj['minecraft_block'] = 'minecraft:' + name
        count += len(faces)
    return count


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def camera(name, location, target, lens):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_end = 700
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def area(name, location, target, energy, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.size, data.color = energy, size, color
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)


OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'output/blender/satou-school.blend'))
scene = bpy.context.scene
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
character = rig.parent
body = next(o for o in scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
for obj in list(scene.objects):
    if obj.type in {'CAMERA', 'LIGHT'} or obj.get('ysm_studio'):
        bpy.data.objects.remove(obj, do_unlink=True)
select_action(rig, 'studio_photo_hip', 0)
character.location = (1.6, 47.0, 0)
character.rotation_euler.z = math.radians(-6)
bpy.context.view_layer.update()
posed = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
character.location.z -= min((posed.matrix_world @ Vector(p)).z for p in posed.bound_box)
blocks, details = city_entrance(*build_city())
print('CITY_BLOCKS', len(blocks), flush=True)
faces = city_mesh(blocks)
schematic = write_schematic({(x, z, -y): 'minecraft:' + state for (x, y, z), state in blocks.items()},
                            OUT / 'minecraft-city.schem')
scene.world.use_nodes = True
nodes = scene.world.node_tree.nodes
nodes.clear()
sky = nodes.new('ShaderNodeTexSky')
sky.sky_type = 'HOSEK_WILKIE'
sky.sun_direction = Vector((-0.5, -0.4, 0.45)).normalized()
sky.turbidity = 2.4
background = nodes.new('ShaderNodeBackground')
background.inputs['Strength'].default_value = 0.7
output = nodes.new('ShaderNodeOutputWorld')
background.inputs['Color'].default_value = (0.37, 0.59, 0.9, 1)
scene.world.node_tree.links.new(background.outputs[0], output.inputs[0])
sun = bpy.data.lights.new('Late afternoon sun', 'SUN')
sun.energy = 1.8
sun.angle = math.radians(6)
sun.color = (1, 0.81, 0.59)
sun_obj = bpy.data.objects.new('Late afternoon sun', sun)
scene.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(-45), math.radians(-24), math.radians(-35))
area('Sky fill over square', (12, 22, 35), (0, -18, 7), 22000, 40, (0.68, 0.8, 1))
area('Character soft key', (-1, 51, 6), (1.6, 47, 1), 110, 5, (1, 0.9, 0.77))
for i, location in enumerate(details['lamps']):
    data = bpy.data.lights.new(f'Guild square lantern {i}', 'POINT')
    data.energy = 70
    data.color = (1, 0.43, 0.14)
    data.shadow_soft_size = 0.4
    obj = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(obj)
    obj.location = location

hero = camera('01 - Standing at the city entrance', (3, 52, 1.65), (0, 23, 8.0), 18)
overview = camera('02 - Grand Minecraft city', (75, 102, 62), (0, -8, 5.3), 37)
portrait = camera('03 - City entrance portrait', (3.7, 53, 2.35), (0.8, 42.7, 2.2), 33)
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 128
scene.eevee.shadow_ray_count = 4
scene.eevee.use_fast_gi = True
scene.eevee.fast_gi_quality = 0.5
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = -0.2
scene.render.resolution_x, scene.render.resolution_y = 1800, 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = False
for cam, name in [(hero, 'city-entrance-view'), (overview, 'minecraft-city-wide'), (portrait, 'city-character-view')]:
    scene.camera = cam
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)
scene.camera = hero
scene.frame_end = 901
scene.render.filepath = '//city-entrance-view.png'
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type == 'VIEW_3D':
        area.spaces.active.region_3d.view_perspective = 'CAMERA'
        area.spaces.active.shading.type = 'MATERIAL'
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
notes = bpy.data.texts.new('Minecraft city construction')
notes.write('Original 1m unit-block city. All city geometry uses the same coordinates as the supplied Sponge schematic.\n'
            'Block textures are extracted from the locally installed Minecraft client. Character remains editable with47 actions.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'satou-minecraft-city.blend'))
(OUT / 'manifest.json').write_text(json.dumps(dict(blocks=len(blocks), faces=faces, **details,
    schematic=schematic, renders=['city-entrance-view.png', 'minecraft-city-wide.png', 'city-character-view.png']), indent=2))
print('CITY_ENTRANCE_DONE', len(blocks), OUT, flush=True)
