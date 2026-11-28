"""Build an editable, original sunset classroom around the school YSM rig."""

import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/blender-scenes/classroom"
sys.path.insert(0, str(Path(__file__).parent))
from convert import select_action


def material(name, color, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*color, 1)
    node.inputs["Roughness"].default_value = 0.85
    if emission:
        node.inputs["Emission Color"].default_value = (*color, 1)
        node.inputs["Emission Strength"].default_value = emission
    return mat


def box(name, location, size, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new("Small crafted edge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 1
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return obj


def cylinder(name, location, radius, depth, mat, vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def light(name, location, target, energy, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def desk(x, y, index, wood, edge, metal, blue, paper):
    box(f"Desk {index} tabletop", (x, y, 1.12), (1.27, 0.82, 0.095), wood, 0.02)
    box(f"Desk {index} shelf", (x, y, 0.91), (1.1, 0.59, 0.075), edge)
    for sx in [-0.5, 0.5]:
        for sy in [-0.27, 0.27]:
            box(f"Desk {index} leg", (x + sx, y + sy, 0.53), (0.055, 0.055, 1.06), metal)
    cy = y + 0.8
    box(f"Chair {index} seat", (x, cy, 0.63), (0.64, 0.62, 0.095), wood, 0.018)
    box(f"Chair {index} back", (x, cy + 0.28, 1.02), (0.64, 0.065, 0.48), wood, 0.018)
    for sx in [-0.25, 0.25]:
        for sy in [-0.23, 0.23]:
            box(f"Chair {index} leg", (x + sx, cy + sy, 0.3), (0.045, 0.045, 0.6), metal)
    if index % 2:
        book = box(f"Notebook {index}", (x - 0.2, y, 1.19), (0.43, 0.32, 0.035), blue)
        book.rotation_euler.z = math.radians(9)
        box(f"Notebook paper {index}", (x - 0.2, y, 1.212), (0.4, 0.3, 0.008), paper)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "output/blender/satou-school.blend"))
    scene = bpy.context.scene
    rig = next(obj for obj in scene.objects if obj.type == "ARMATURE")
    for obj in list(scene.objects):
        if obj.type in {"LIGHT", "CAMERA"} or obj.get("ysm_studio"):
            bpy.data.objects.remove(obj, do_unlink=True)
    container = rig.parent
    select_action(rig, "studio_photo_shy", 0)
    container.location = (0.35, 1.25, 0)
    container.rotation_euler.z = math.radians(-10)

    plaster = material("Warm cream plaster", (0.7, 0.63, 0.52))
    trim = material("Cream window trim", (0.88, 0.78, 0.58))
    wood = material("Honey desk wood", (0.47, 0.26, 0.105))
    wood_light = material("Desk top light grain", (0.63, 0.39, 0.17))
    wood_edge = material("Dark wood edge", (0.28, 0.15, 0.08))
    floor_colors = [material(f"Floor plank {i}", c) for i, c in enumerate([(0.41,0.25,0.14),(0.46,0.29,0.16),(0.51,0.32,0.18),(0.44,0.27,0.14)])]
    metal = material("Warm gray desk steel", (0.19, 0.22, 0.2))
    board = material("Chalkboard green", (0.035, 0.115, 0.092))
    chalk = material("Warm chalk", (0.78, 0.81, 0.7))
    navy = material("Navy notebook", (0.12, 0.21, 0.32))
    coral = material("Coral book", (0.6, 0.24, 0.22))
    paper = material("Ivory paper", (0.88, 0.82, 0.65))
    leaf = material("Plant leaf", (0.14, 0.32, 0.17))
    pot = material("Terracotta planter", (0.5, 0.22, 0.12))
    window_sky = material("Golden late afternoon sky", (0.95, 0.56, 0.25), 0.65)

    box("Classroom foundation", (0, 0, -0.16), (10.1, 8.1, 0.28), wood_edge)
    for row in range(20):
        x = -4.75 + row * 0.5
        for j in range(4):
            box("Individual oak floor plank", (x, -3 + j * 2, -0.015), (0.486, 1.985, 0.06), floor_colors[(row + j) % 4])
    box("Back classroom wall", (0, -4.04, 1.75), (10.1, 0.16, 3.5), plaster)
    box("Left wall under windows", (-5.04, 0, 0.55), (0.16, 8.1, 1.1), plaster)
    box("Left wall above windows", (-5.04, 0, 3.3), (0.16, 8.1, 0.4), plaster)
    for y in [-4, -1.45, 1.15, 4]:
        box("Window pillar", (-5.04, y, 2.05), (0.16, 0.2, 2), plaster)
    for y in [-2.73, -0.15, 2.57]:
        box("Window sunset panel", (-5.13, y, 2.07), (0.035, 2.32, 1.85), window_sky)
        box("Window sill", (-4.94, y, 1.13), (0.35, 2.5, 0.11), trim)
        for yy in [y - 1.2, y, y + 1.2]:
            box("Window vertical mullion", (-4.92, yy, 2.08), (0.13, 0.075, 1.95), trim)
        box("Window horizontal mullion", (-4.91, y, 2.08), (0.13, 2.43, 0.065), trim)
    box("Back skirting", (0, -3.92, 0.13), (10, 0.1, 0.22), wood_edge)
    box("Left skirting", (-4.92, 0, 0.13), (0.1, 8, 0.22), wood_edge)
    box("Chalkboard frame", (-0.7, -3.9, 2.12), (5.65, 0.15, 1.66), wood_edge, 0.02)
    box("Chalkboard surface", (-0.7, -3.8, 2.12), (5.42, 0.055, 1.45), board)
    box("Chalk tray", (-0.7, -3.68, 1.35), (5.65, 0.24, 0.075), wood)
    for x, length, z in [(-2.5,1.1,2.5),(-2.2,1.65,2.25),(-1.9,2.2,2.0),(-2.45,1.2,1.75)]:
        box("Quiet chalk notation", (x, -3.763, z), (length, 0.007, 0.018), chalk)
    for x in [0.5, 0.9, 1.3]:
        box("Chalk diagram vertical", (x, -3.76, 2.24), (0.014,0.008,0.75), chalk)
    box("Chalk diagram horizontal", (0.9, -3.76, 2.24), (1.1,0.008,0.014), chalk)
    for x in [-1.8, -0.8]:
        box("Chalk stick", (x, -3.66, 1.41), (0.14, 0.035, 0.035), chalk)
    box("Board eraser", (1.25, -3.64, 1.43), (0.3,0.12,0.08), navy)

    clock = cylinder("Wall clock rim", (3.3, -3.87, 2.7), 0.32, 0.1, wood_edge)
    clock.rotation_euler.x = math.pi / 2
    face = cylinder("Clock face", (3.3,-3.79,2.7),0.275,0.025,paper)
    face.rotation_euler.x = math.pi / 2
    box("Clock hour hand", (3.23,-3.77,2.72),(0.16,0.02,0.025),metal)
    hand = box("Clock minute hand", (3.32,-3.76,2.8),(0.025,0.02,0.23),metal)
    hand.rotation_euler.y = -0.3
    box("Notice board", (3.65,-3.9,1.65),(1.65,0.13,0.95),wood)
    for x,z,angle in [(3.2,1.72,7),(3.7,1.6,-5),(4.1,1.74,3)]:
        note=box("Pinned notice",(x,-3.81,z),(0.38,0.02,0.47),paper)
        note.rotation_euler.y=math.radians(angle)

    index=0
    for y in [-2.1, -0.05]:
        for x in [-2.85, -0.5, 2.3]:
            index+=1
            desk(x,y,index,wood_light,wood_edge,metal,navy,paper)
    # Foreground desk gives the portrait depth without crossing the character.
    desk(3.1,2.35,7,wood_light,wood_edge,metal,coral,paper)
    box("Teacher table top", (-2.1,-3.1,1.12),(1.65,0.75,0.12),wood_light,0.025)
    for x in [-2.75,-1.45]:
        box("Teacher desk pedestal", (x,-3.1,0.54),(0.3,0.62,1.05),wood)
    box("Teacher books",(-1.8,-3.1,1.23),(0.5,0.34,0.12),coral)
    box("Plant stand top",(-4.43,-2.7,1.11),(0.65,0.65,0.09),wood_light,0.018)
    for sx in [-0.24,0.24]:
        for sy in [-0.24,0.24]:
            box("Plant stand leg",(-4.43+sx,-2.7+sy,0.53),(0.055,0.055,1.06),wood_edge)
    cylinder("Window plant pot",(-4.43,-2.7,1.33),0.23,0.35,pot,8)
    for x,y,z in [(-4.45,-2.7,1.7),(-4.29,-2.67,1.62),(-4.6,-2.62,1.65)]:
        stem=box("Plant stem",(x,y,1.62),(0.035,0.035,0.45),leaf)
        foliage=box("Blocky plant leaf",(x,y,z),(0.32,0.16,0.24),leaf,0.035)
        foliage.rotation_euler.z=(x+5)*2

    # Window key and cooler opposing fill retain the original atlas colors.
    light("Sunset window key",(-4.65,-0.4,2.8),(0.5,0,1),680,(1,0.59,0.31),2.4)
    light("Cool classroom fill",(3.5,4.5,4.8),(0,0,1),420,(0.68,0.78,1),5)
    light("Character soft face light",(1,5,3.5),(0.35,1.25,1),150,(1,0.88,0.78),3)
    sun_data=bpy.data.lights.new("Low sunset through windows","SUN")
    sun_data.energy=1.4
    sun_data.angle=math.radians(4)
    sun_data.color=(1,0.7,0.4)
    sun=bpy.data.objects.new("Low sunset through windows",sun_data)
    scene.collection.objects.link(sun)
    sun.location=(-9,-1,7)
    aim(sun,(0,1,0))
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.35,0.43,0.65,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.35
    scene.render.engine='BLENDER_EEVEE'
    scene.eevee.taa_render_samples=128
    scene.eevee.shadow_ray_count=4
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.resolution_x=1600
    scene.render.resolution_y=1200
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA'
    scene.render.film_transparent=False

    cameras=[]
    for name,position,target,scale in [
        ('Classroom wide',(10,13,9),(0,-0.1,1.1),11.5),
        ('Classroom portrait',(4.8,8.5,3.8),(0.3,1.1,1.05),4.5),
        ('Classroom cinematic',(3.7,7.6,2.5),(0.35,1.25,1.05),3.4),
    ]:
        data=bpy.data.cameras.new(name)
        data.type='ORTHO'
        data.ortho_scale=scale
        camera=bpy.data.objects.new(name,data)
        scene.collection.objects.link(camera)
        camera.location=position
        aim(camera,target)
        cameras.append(camera)
    scene.camera=cameras[0]
    scene['Scene design']='Original cutaway classroom with warm sunset windows and cool fill'
    scene['Character source']='Satou school YSM conversion; Wine Fox credits retained'
    notes=bpy.data.texts.new('Classroom - scene notes')
    notes.write('Original classroom geometry and lighting created for this project.\nTwo named orthographic cameras.\nCharacter remains the actual editable YSM armature with all 47 baked actions.\n')
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.type='MATERIAL'
    blend=OUT/'satou-sunset-classroom.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    renders=[]
    for camera in cameras:
        scene.camera=camera
        file=OUT/(camera.name.lower().replace(' ','-')+'.png')
        scene.render.filepath=str(file)
        bpy.ops.render.render(write_still=True)
        renders.append(file.name)
    scene.camera=cameras[0]
    scene.render.filepath='//classroom-wide.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    (OUT/'manifest.json').write_text(json.dumps(dict(scene=blend.name,renders=renders,actions=len([a for a in bpy.data.actions if a.get('ysm_clip')]),lights=4,cameras=[c.name for c in cameras]),indent=2))


if __name__ == '__main__':
    build()
