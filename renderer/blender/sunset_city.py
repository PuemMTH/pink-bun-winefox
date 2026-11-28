"""Relight the actual block city as a sunset river scene, without image generation.

Run inside Blender: blender -b --python sunset_city.py -- --hdri sky.exr --draft
"""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sunset_landscape import build_landscape


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def camera(name, position, target, lens):
    data = bpy.data.cameras.new(name)
    data.lens, data.clip_end = lens, 1500
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = position
    aim(obj, target)
    return obj


def area(name, position, target, power, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.size, data.color = power, size, color
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = position
    aim(obj, target)
    return obj


def river(scene, bounds):
    x0, x1, y0, y1, z = bounds
    mesh = bpy.data.meshes.new('River surface')
    mesh.from_pydata([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [], [(0, 1, 2, 3)])
    obj = bpy.data.objects.new('Reflective river - shader water', mesh)
    scene.collection.objects.link(obj)
    mat = bpy.data.materials.new('Water - sunset reflections and fine ripples')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (0.035, 0.09, 0.065, 1)
    shader.inputs['Roughness'].default_value = 0.11
    shader.inputs['IOR'].default_value = 1.333
    shader.inputs['Transmission Weight'].default_value = 0.85
    shader.inputs['Metallic'].default_value = 0
    shader.inputs['Specular IOR Level'].default_value = 0.6
    tex = nodes.new('ShaderNodeTexNoise')
    tex.inputs['Scale'].default_value = 2.2
    tex.inputs['Detail'].default_value = 3
    coordinates = nodes.new('ShaderNodeTexCoord')
    links.new(coordinates.outputs['Object'], tex.inputs['Vector'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.22
    bump.inputs['Distance'].default_value = 0.075
    links.new(tex.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    obj.data.materials.append(mat)
    return obj


def atmosphere(scene):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -35, 34))
    obj = bpy.context.object
    obj.name = 'Distant atmospheric haze'
    obj.scale = (390, 370, 80)
    material = bpy.data.materials.new('Thin sunset atmosphere')
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    volume = nodes.new('ShaderNodeVolumeScatter')
    volume.inputs['Density'].default_value = 0.00035
    volume.inputs['Color'].default_value = (0.72, 0.8, 1, 1)
    volume.inputs['Anisotropy'].default_value = 0.35
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(volume.outputs[0], output.inputs['Volume'])
    obj.data.materials.append(material)


def glow(scene):
    tree = bpy.data.node_groups.new('Sunset - gentle highlight bloom', 'CompositorNodeTree')
    scene.compositing_node_group = tree
    tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    render = tree.nodes.new('CompositorNodeRLayers')
    glare = tree.nodes.new('CompositorNodeGlare')
    glare.inputs['Type'].default_value = 'Fog Glow'
    glare.inputs['Quality'].default_value = 'High'
    glare.inputs['Threshold'].default_value = 1.0
    glare.inputs['Strength'].default_value = 0.4
    glare.inputs['Size'].default_value = 0.3
    output = tree.nodes.new('NodeGroupOutput')
    tree.links.new(render.outputs['Image'], glare.inputs['Image'])
    tree.links.new(glare.outputs['Image'], output.inputs['Image'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hdri', type=Path, required=True)
    parser.add_argument('--rotation', type=float, default=0)
    parser.add_argument('--character', type=Path, help='Newly converted character Blender file')
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--all', action='store_true', help='Render all three cameras')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    assert args.hdri.is_file(), args.hdri
    out = ROOT / 'output/blender-scenes/city-sunset'
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'output/blender-scenes/city-entrance/satou-minecraft-city.blend'))
    scene = bpy.context.scene
    character_source = args.character or ROOT / 'output/blender/latest/satou-school.blend'
    character_import = None
    if character_source.is_file():
        from refresh_character import replace_character
        character_import = replace_character(scene, character_source)
    for obj in list(scene.objects):
        if obj.type in {'CAMERA', 'LIGHT'} or obj.name == 'Studio floor':
            bpy.data.objects.remove(obj, do_unlink=True)
    atlas = next(image for image in bpy.data.images if image.name.startswith('minecraft-atlas'))
    mapping = json.loads((ROOT / 'dist/blender/minecraft-atlas.json').read_text(encoding='utf-8'))
    landscape = build_landscape(scene, atlas, mapping, ROOT / 'dist/blender/minecraft-textures')
    # Physical lighting replaces the diffuse emission used in the first preview.
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        shader = mat.node_tree.nodes.get('Principled BSDF')
        if shader and mat.name.startswith('minecraft:'):
            shader.inputs['Emission Strength'].default_value = 0
            shader.inputs['Specular IOR Level'].default_value = 0.25
            if 'glowstone' in mat.name:
                shader.inputs['Emission Strength'].default_value = 5
            elif 'yellow_stained_glass' in mat.name:
                shader.inputs['Emission Strength'].default_value = 0.6
    river(scene, [*landscape['water_bounds'], landscape['water_z']])
    atmosphere(scene)
    rig = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
    character = rig.parent
    character.location = (15, 75, 0)
    character.rotation_euler.z = math.radians(-18)
    body = next(obj for obj in scene.objects if obj.type == 'MESH' and any(m.type == 'ARMATURE' for m in obj.modifiers))
    bpy.context.view_layer.update()
    posed = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    character.location.z -= min((posed.matrix_world @ Vector(p)).z for p in posed.bound_box)
    nodes, links = scene.world.node_tree.nodes, scene.world.node_tree.links
    nodes.clear()
    environment = nodes.new('ShaderNodeTexEnvironment')
    environment.image = bpy.data.images.load(str(args.hdri.resolve()), check_existing=True)
    environment.image.pack()
    coordinates = nodes.new('ShaderNodeTexCoord')
    rotation = nodes.new('ShaderNodeMapping')
    rotation.inputs['Rotation'].default_value[2] = math.radians(args.rotation)
    links.new(coordinates.outputs['Generated'], rotation.inputs['Vector'])
    links.new(rotation.outputs['Vector'], environment.inputs['Vector'])
    background = nodes.new('ShaderNodeBackground')
    background.inputs['Strength'].default_value = 0.3
    tint = nodes.new('ShaderNodeMixRGB')
    tint.name = 'Warm sunset cloud highlights'
    tint.blend_type = 'MULTIPLY'
    tint.inputs[0].default_value = 1
    tint.inputs[2].default_value = (1.12, 1.0, 0.95, 1)
    # Cool the neutral/blue openings while retaining the photographed peach clouds.
    channels = nodes.new('ShaderNodeSeparateColor')
    links.new(environment.outputs['Color'], channels.inputs[0])
    ratio = nodes.new('ShaderNodeMath')
    ratio.operation = 'DIVIDE'
    links.new(channels.outputs['Red'], ratio.inputs[0])
    links.new(channels.outputs['Blue'], ratio.inputs[1])
    mask = nodes.new('ShaderNodeMapRange')
    mask.inputs['From Min'].default_value = 0.8
    mask.inputs['From Max'].default_value = 1.3
    mask.inputs['To Min'].default_value = 1
    mask.inputs['To Max'].default_value = 0
    links.new(ratio.outputs[0], mask.inputs['Value'])
    blue = nodes.new('ShaderNodeMixRGB')
    blue.name = 'Blue openings between the sunset clouds'
    blue.blend_type = 'MULTIPLY'
    blue.inputs[2].default_value = (0.4, 0.68, 1.25, 1)
    links.new(mask.outputs[0], blue.inputs[0])
    links.new(environment.outputs['Color'], blue.inputs[1])
    links.new(blue.outputs[0], tint.inputs[1])
    saturation = nodes.new('ShaderNodeHueSaturation')
    saturation.inputs['Saturation'].default_value = 1.05
    links.new(tint.outputs[0], saturation.inputs['Color'])
    links.new(saturation.outputs[0], background.inputs['Color'])
    output = nodes.new('ShaderNodeOutputWorld')
    links.new(background.outputs[0], output.inputs[0])
    sun = bpy.data.lights.new('Golden hour - low soft sun', 'SUN')
    sun.energy, sun.angle, sun.color = 3.8, math.radians(2.2), (1, 0.57, 0.24)
    obj = bpy.data.objects.new(sun.name, sun)
    scene.collection.objects.link(obj)
    obj.location = (-100, -110, 30)
    aim(obj, (0, 30, 0))
    bpy.ops.mesh.primitive_plane_add(size=15, location=(-145, -89, 43))
    square = bpy.context.object
    square.name = 'Minecraft square sunset sun'
    square.rotation_euler = (Vector((15, 84, 2)) - square.location).to_track_quat('Z', 'Y').to_euler()
    material = bpy.data.materials.new('Sun - golden emissive disc')
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (1, 0.57, 0.16, 1)
    shader.inputs['Emission Color'].default_value = (1, 0.6, 0.2, 1)
    shader.inputs['Emission Strength'].default_value = 18
    square.data.materials.append(material)
    area('Character - warm sky bounce', (16, 80, 4), (15, 75, 1), 180, 5, (1, 0.82, 0.63))
    area('Golden light bounced from the river', (-32, 75, 21), (0, 25, 3), 22000, 32, (1, 0.54, 0.21))
    area('Cool skylight over the approach', (15, 40, 28), (0, 28, 0), 8000, 35, (0.5, 0.65, 1))
    for i, position in enumerate(landscape['lamps']):
        data = bpy.data.lights.new(f'Riverside lantern {i+1}', 'POINT')
        data.energy, data.color, data.shadow_soft_size = 100, (1, 0.37, 0.08), 0.3
        obj = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(obj)
        obj.location = position
    views = [
        (camera('01 - Sunset at the city river', (15, 82, 1.65), (-2, 25, 6.3), 24), 'city-sunset-hero'),
        (camera('02 - Walled city in golden hour', (74, 110, 42), (-5, -5, 7), 39), 'city-sunset-wide'),
        (camera('03 - Satou at the riverside', (17.5, 80.5, 1.7), (14.9, 74.5, 1.4), 40), 'city-sunset-portrait'),
    ]
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'OPTIX'
    assert any(device.use for device in prefs.devices), 'An OptiX device is required for this render preset'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 32 if args.draft else 192
    scene.cycles.use_denoising = True
    scene.cycles.denoising_use_gpu = True
    scene.cycles.adaptive_threshold = 0.06 if args.draft else 0.015
    scene.cycles.max_bounces = 8
    scene.cycles.transparent_max_bounces = 16
    scene.cycles.transmission_bounces = 6
    scene.cycles.volume_bounces = 1
    scene.cycles.volume_step_rate = 2
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0.1
    scene.render.resolution_x, scene.render.resolution_y = (1008, 567) if args.draft else (2048, 1152)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False
    glow(scene)
    bpy.context.view_layer.update()
    posed = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    feet_z = min((posed.matrix_world @ Vector(p)).z for p in posed.bound_box)
    assert abs(feet_z - landscape['bridge_deck_z']) < 0.00002, feet_z
    assert 'Studio floor' not in scene.objects
    assert len(bpy.data.actions) >= 47
    assert len([obj for obj in scene.objects if obj.type == 'CAMERA']) == 3
    assert all(image.packed_file for image in bpy.data.images if image.source == 'FILE' and image.users)
    notes = bpy.data.texts.new('Sunset scene - rendering and credits')
    notes.write('Actual Minecraft 1.20.1 block textures, native Cycles lighting/reflections.\n'
                'Golden-hour art direction inspired by Minecraft shaders; no shader-pack code used.\n'
                'Sky: The Sky Is On Fire, Greg Zaal / Poly Haven, CC0, artistically graded.\n'
                'The original character rig and47 actions are preserved.\n')
    scene.camera = views[0][0]
    scene.render.filepath = '//city-sunset-hero.png'
    for viewport in bpy.context.screen.areas if bpy.context.screen else []:
        if viewport.type == 'VIEW_3D':
            viewport.spaces.active.region_3d.view_perspective = 'CAMERA'
            viewport.spaces.active.shading.type = 'MATERIAL'
            viewport.spaces.active.shading.use_scene_world = True
            viewport.spaces.active.shading.use_scene_lights = True
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'satou-minecraft-sunset.blend'))
    for cam, name in views if args.all else views[:1]:
        scene.camera = cam
        scene.render.filepath = str(out / (name + ('-draft' if args.draft else '') + '.png'))
        bpy.ops.render.render(write_still=True)
    scene.camera = views[0][0]
    scene.render.filepath = '//city-sunset-hero.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'satou-minecraft-sunset.blend'))
    (out / 'manifest.json').write_text(json.dumps({
        'renderer': 'Blender Cycles OptiX', 'samples': scene.cycles.samples,
        'resolution': [scene.render.resolution_x, scene.render.resolution_y],
        'minecraft_texture_version': mapping['source']['version'],
        'character_import': character_import,
        'hdri': args.hdri.name, 'hdri_rotation_degrees': args.rotation,
        'landscape': landscape, 'actions': len(bpy.data.actions),
        'checks': {'feet_z': feet_z, 'packed_textures': True, 'studio_floor_removed': True},
        'cameras': [cam.name for cam, name in views],
        'renders': [name + '.png' for cam, name in views],
    }, indent=2), encoding='utf-8')
    print('SUNSET_DONE', out, flush=True)


if __name__ == '__main__':
    main()
