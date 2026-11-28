"""Build a small, editable evening apartment around the converted YSM model."""

from pathlib import Path
import math
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/blender-scenes/cozy-room'
sys.path.insert(0, str(Path(__file__).parent))
from convert import select_action


def material(name, color, roughness=0.7, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    if emission:
        shader.inputs['Emission Color'].default_value = (*color, 1)
        shader.inputs['Emission Strength'].default_value = emission
    return mat


def box(name, location, dimensions, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft block edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return obj


def cylinder(name, location, radius, depth, mat, vertices=12, top_radius=None):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius,
                                  radius2=radius if top_radius is None else top_radius,
                                  depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def light(name, location, target, energy, size, color, kind='AREA'):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == 'AREA':
        data.shape = 'DISK'
        data.size = size
    else:
        data.shadow_soft_size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def camera(name, location, target, ortho=None, lens=48):
    data = bpy.data.cameras.new(name)
    data.type = 'ORTHO' if ortho else 'PERSP'
    data.lens = lens
    if ortho:
        data.ortho_scale = ortho
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def plant(name, x, y, z, size=1):
    cylinder(name + ' pot', (x, y, z + 0.11 * size), 0.15 * size, 0.22 * size, terracotta,
             vertices=8, top_radius=0.19 * size)
    for i, (dx, dy, dz) in enumerate([(-0.13, 0, 0.38), (0.12, 0.04, 0.5), (0, -0.1, 0.61)]):
        stem = cylinder(name + ' stem', (x + dx * size * 0.5, y + dy * size * 0.5,
                                        z + dz * size * 0.55), 0.018 * size, dz * size, leaf_dark, 6)
        leaf = box(name + f' leaf {i}', (x + dx * size, y + dy * size, z + dz * size),
                   (0.23 * size, 0.1 * size, 0.33 * size), leaf_light, 0.025 * size)
        leaf.rotation_euler = (0.25 * i, 0.45 * (-1 if i % 2 else 1), i * 1.2)


OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'output/blender/satou-white.blend'))
scene = bpy.context.scene
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
character = rig.parent
body = next(o for o in scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
for obj in list(scene.objects):
    if obj.type in {'LIGHT', 'CAMERA'} or obj.get('ysm_studio'):
        bpy.data.objects.remove(obj, do_unlink=True)
select_action(rig, 'studio_photo_shy', 0)
character.location = (0.62, 0.15, 0.015)
character.rotation_euler.z = math.radians(-10)

wall = material('Warm porcelain walls', (0.69, 0.64, 0.61))
wall_trim = material('Ivory window and trim', (0.89, 0.83, 0.72))
oak = [material(f'Maple plank {i}', (0.39 + i * 0.022, 0.25 + i * 0.016, 0.16 + i * 0.013)) for i in range(5)]
walnut = material('Walnut furniture', (0.2, 0.105, 0.065))
sofa = material('Dusty rose sofa', (0.43, 0.23, 0.24))
sofa_light = material('Sofa cushion', (0.59, 0.35, 0.35))
pillow = material('Sage pillow', (0.34, 0.46, 0.39))
cream = material('Linen and ceramic', (0.82, 0.72, 0.58))
rug = material('Woven pale rose rug', (0.57, 0.43, 0.43))
rug_border = material('Rug cream edging', (0.75, 0.64, 0.55))
metal = material('Warm dark metal', (0.055, 0.045, 0.044), 0.36)
terracotta = material('Clay plant pots', (0.43, 0.19, 0.12))
leaf_dark = material('Plant stems', (0.075, 0.19, 0.12))
leaf_light = material('Sage green leaves', (0.2, 0.36, 0.23))
paper = material('Warm paper', (0.86, 0.78, 0.62))
book_colors = [material('Book ' + str(i), col) for i, col in enumerate(
    [(0.23, 0.34, 0.34), (0.5, 0.24, 0.25), (0.6, 0.46, 0.25), (0.5, 0.48, 0.38)])]
sky = material('Evening blue through window', (0.19, 0.31, 0.53), emission=0.45)
city = material('Distant blue rooftops', (0.12, 0.19, 0.3), emission=0.18)
lamp_glow = material('Warm linen lamp glow', (1, 0.63, 0.28), emission=1.2)

# Two open walls form a dollhouse cutaway, with a true opening behind the window.
box('Foundation', (0, 0, -0.13), (7.25, 5.25, 0.22), walnut, 0.04)
for row in range(15):
    for col in range(4):
        x = -2.68 + col * 1.79
        y = -2.42 + row * 0.345
        box(f'Floor plank {row}-{col}', (x, y, -0.015), (1.778, 0.335, 0.06), oak[(row * 3 + col) % 5])
box('Left wall', (-3.62, 0, 1.68), (0.16, 5.25, 3.5), wall, 0.02)
box('Back wall left', (-1.5, -2.62, 1.68), (4.1, 0.16, 3.5), wall, 0.02)
box('Back wall right', (3.35, -2.62, 1.68), (0.55, 0.16, 3.5), wall, 0.02)
box('Below window', (1.82, -2.62, 0.54), (2.7, 0.16, 1.14), wall)
box('Above window', (1.82, -2.62, 3.14), (2.7, 0.16, 0.53), wall)
box('Back skirting', (0, -2.48, 0.09), (7.05, 0.09, 0.18), wall_trim)
box('Left skirting', (-3.49, 0, 0.09), (0.09, 5.05, 0.18), wall_trim)
box('Window view', (1.82, -2.79, 2), (2.7, 0.045, 1.72), sky)
for i in range(7):
    height = [0.33, 0.48, 0.3, 0.57, 0.37, 0.25, 0.46][i]
    box('Distant rooftop', (0.65 + 0.38 * i, -2.74, 1.18 + height / 2), (0.33, 0.04, height), city)
for x in [0.47, 1.82, 3.17]:
    box('Window upright', (x, -2.49, 2), (0.075, 0.12, 1.83), wall_trim, 0.01)
for z in [1.1, 2, 2.9]:
    box('Window horizontal', (1.82, -2.49, z), (2.79, 0.12, 0.075), wall_trim, 0.01)
box('Deep window sill', (1.82, -2.37, 1.07), (2.97, 0.48, 0.12), wall_trim, 0.025)
for side, x in enumerate([0.28, 3.34]):
    for i in range(4):
        box('Pleated linen curtain', (x + (i - 1.5) * 0.095, -2.35 + (i % 2) * 0.07, 2.03),
            (0.11, 0.13, 1.95), cream)
box('Curtain rail', (1.82, -2.3, 3.04), (3.65, 0.05, 0.05), metal)
plant('Window plant', 2.6, -2.27, 1.14, 0.7)

# Upholstery, a low table, and small lived-in details.
for x in [-2.4, -0.2]:
    for y in [-2.12, -1.4]:
        box('Sofa foot', (x, y, 0.16), (0.12, 0.12, 0.27), walnut)
box('Sofa base', (-1.3, -1.78, 0.41), (2.9, 1.07, 0.38), sofa, 0.07)
box('Sofa back', (-1.3, -2.19, 0.92), (2.92, 0.25, 1.07), sofa, 0.07)
for x in [-2.75, 0.15]:
    box('Sofa arm', (x, -1.76, 0.71), (0.25, 1.1, 0.72), sofa, 0.06)
for x in [-1.99, -0.62]:
    box('Seat cushion', (x, -1.7, 0.67), (1.32, 0.82, 0.2), sofa_light, 0.055)
    box('Back cushion', (x, -2.02, 1.03), (1.31, 0.23, 0.65), sofa_light, 0.055)
box('Sage throw pillow', (-2.17, -1.76, 1.01), (0.49, 0.23, 0.48), pillow, 0.04).rotation_euler.y = -0.15
box('Cream throw pillow', (-0.43, -1.77, 0.98), (0.47, 0.23, 0.44), cream, 0.04).rotation_euler.y = 0.15
box('Rug border', (-0.45, 0.15, 0.035), (3.85, 2.45, 0.018), rug_border, 0.035)
box('Rug center', (-0.45, 0.15, 0.049), (3.65, 2.25, 0.018), rug, 0.025)
for x in [-2.03, -1.06]:
    for y in [-0.1, 0.52]:
        box('Table leg', (x, y, 0.25), (0.08, 0.08, 0.42), walnut)
box('Coffee table', (-1.55, 0.2, 0.48), (1.42, 0.94, 0.12), walnut, 0.035)
box('Open book paper', (-1.6, 0.17, 0.558), (0.55, 0.35, 0.03), paper)
box('Book cover', (-1.6, 0.17, 0.541), (0.59, 0.38, 0.018), book_colors[0])
box('Book crease', (-1.6, 0.17, 0.575), (0.012, 0.33, 0.005), oak[1])
cylinder('Tea cup', (-1.07, -0.02, 0.62), 0.09, 0.15, cream)
cylinder('Tea surface', (-1.07, -0.02, 0.696), 0.071, 0.008, walnut)
cylinder('Cup saucer', (-1.07, -0.02, 0.55), 0.14, 0.025, cream)

# A compact bookcase on the left, a floor lamp and framed abstract art.
for z in [0.23, 0.85, 1.47, 2.09]:
    box('Bookcase shelf', (-3.25, -0.35, z), (0.56, 1.4, 0.075), walnut, 0.01)
for y in [-1.02, 0.32]:
    box('Bookcase side', (-3.25, y, 1.15), (0.56, 0.075, 2), walnut)
for shelf in range(3):
    for i in range(6):
        h = 0.32 + (i % 3) * 0.08
        box('Book spine', (-3.08, -0.85 + i * 0.18, 0.29 + shelf * 0.62 + h / 2),
            (0.31, 0.12, h), book_colors[(i + shelf) % 4], 0.005)
plant('Bookcase plant', -3.22, -0.34, 2.13, 0.75)
cylinder('Lamp foot', (-2.98, -1.67, 0.1), 0.25, 0.08, metal)
cylinder('Lamp upright', (-2.98, -1.67, 1.15), 0.025, 2.1, metal)
cylinder('Lamp shade', (-2.98, -1.67, 2.2), 0.37, 0.43, lamp_glow, 12, 0.26)
box('Wall art frame', (-1.35, -2.48, 2.32), (1.02, 0.075, 0.95), walnut, 0.015)
box('Wall art paper', (-1.35, -2.429, 2.32), (0.91, 0.02, 0.84), paper)
sun = cylinder('Art sunset disc', (-1.35, -2.407, 2.43), 0.23, 0.01, terracotta, 32)
sun.rotation_euler.x = math.pi / 2
box('Art horizon', (-1.35, -2.389, 2.13), (0.89, 0.012, 0.2), pillow)

bpy.context.view_layer.update()
posed = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
foot_z = min((posed.matrix_world @ Vector(p)).z for p in posed.bound_box)
character.location.z += 0.06 - foot_z

scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.32, 0.39, 0.55, 1)
background.inputs['Strength'].default_value = 0.14
light('Evening window soft light', (1.65, -2.18, 2.3), (0, 0.3, 0.7), 280, 1.8, (0.48, 0.67, 1))
light('Portrait warm key', (-1.5, 3.1, 4.4), (0.5, 0, 1), 180, 2.8, (1, 0.71, 0.52))
light('Gentle camera fill', (4, 4.5, 3), (0.3, 0, 1), 60, 4, (0.75, 0.8, 1))
light('Floor lamp practical', (-2.98, -1.58, 1.91), (-2, -1, 0.6), 90, 0.22, (1, 0.45, 0.16), 'POINT')
wide = camera('01 - Apartment overview', (7.7, 10.4, 8), (-0.2, -0.2, 1.25), ortho=9)
portrait = camera('02 - Evening portrait', (3.8, 6.8, 3.1), (0.38, -0.35, 1.27), lens=51)
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 128
scene.eevee.shadow_ray_count = 4
scene.eevee.use_fast_gi = True
scene.eevee.fast_gi_quality = 0.75
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0.4
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = False
for cam, size, name in [(wide, (1600, 1200), 'cozy-room-wide'),
                         (portrait, (1600, 1200), 'cozy-room-portrait')]:
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)
scene.camera = wide
scene.render.filepath = '//cozy-room-wide.png'
scene.frame_end = 901
for image in bpy.data.images:
    if image.packed_file:
        image.filepath = '//textures/pink_bun.png'
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type == 'VIEW_3D':
        area.spaces.active.region_3d.view_perspective = 'CAMERA'
        area.spaces.active.shading.type = 'MATERIAL'
notes = bpy.data.texts.new('Scene notes')
notes.write('Original block-style evening apartment. Cameras and lights are named in the Outliner.\n'
            'Character retains all 47 baked YSM actions and packed texture.\n'
            'Reference ideas: Poly Haven Art Studio, BlendSwap room galleries.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'cozy-room.blend'))
print('COZY_ROOM_DONE', OUT, flush=True)
