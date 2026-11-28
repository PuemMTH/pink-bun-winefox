"""Build an editable scene from the approved room concept."""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from concept_architecture import build_concept_architecture
from concept_furniture import build_concept_furniture, build_keyboard
from concept_library import build_concept_library
from monitor_room import append_character, bone_world, box, material, phone_prop, pose_phone_reader
from pc_case import build_pc_case
from convert import select_action
from sunset_city import area, camera, glow

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT/'output/blender-scenes/monitor-room-concept'
SCREENS = ROOT/'assets/monitor-screens'
REFERENCE_SIZE = (1671, 941)


def empty(name, location):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    return obj


def cable(name, points, mat, radius=.008):
    spline_data = bpy.data.curves.new(name, 'CURVE')
    spline_data.dimensions = '3D'
    spline_data.bevel_depth = radius
    spline_data.bevel_resolution = 3
    spline = spline_data.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for point, location in zip(spline.bezier_points, points):
        point.co = location
        point.handle_left_type = point.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, spline_data)
    bpy.context.scene.collection.objects.link(obj)
    spline_data.materials.append(mat)
    return obj


def display(name, location, width, height, yaw, bezel, source, brightness, stand=False, sky_sample=None):
    parent = empty(name, location)
    parent.rotation_euler.z = math.radians(yaw)
    rim = .026 if stand else .030
    shell = box(name+' casing', (0, 0, 0), (width+rim, .047, height+rim), bezel, .009)
    shell.parent = parent
    mesh = bpy.data.meshes.new(name+' display mesh')
    mesh.from_pydata([(-width/2,0,-height/2), (width/2,0,-height/2),
                      (width/2,0,height/2), (-width/2,0,height/2)], [], [(0,1,2,3)])
    panel = bpy.data.objects.new(name+' display', mesh)
    bpy.context.scene.collection.objects.link(panel)
    panel.parent = parent
    panel.location.y = -.024
    screen = material(name+' screen light', (.01,.01,.01), .43)
    mesh.materials.append(screen)
    nodes, links = screen.node_tree.nodes, screen.node_tree.links
    tex = nodes.new('ShaderNodeTexImage')
    tex.label = 'Replaceable screen image'
    tex.image = bpy.data.images.load(str(source), check_existing=True)
    if not tex.image.packed_file:
        tex.image.pack()
    shader = nodes.get('Principled BSDF')
    display_color = tex.outputs['Color']
    if sky_sample:
        # Overlay the supplied sky on this monitor's UVs only. The lower part
        # of the game screen remains a distinct capture from the user's game.
        uv = nodes.new('ShaderNodeTexCoord').outputs['UV']
        coords = nodes.new('ShaderNodeVectorMath')
        coords.operation = 'MULTIPLY_ADD'
        coords.inputs[1].default_value = (1, 1/.55, 1)
        coords.inputs[2].default_value = (0, -.45/.55, 0)
        links.new(uv, coords.inputs[0])
        sky = nodes.new('ShaderNodeTexImage')
        sky.label = 'Sky texture sampled inside the reference monitor'
        sky.image = bpy.data.images.load(str(sky_sample), check_existing=True)
        sky.image.pack()
        sky.extension = 'EXTEND'
        links.new(coords.outputs['Vector'], sky.inputs['Vector'])
        separate = nodes.new('ShaderNodeSeparateXYZ')
        links.new(uv, separate.inputs[0])
        mask = nodes.new('ShaderNodeMapRange')
        mask.interpolation_type = 'SMOOTHSTEP'
        mask.inputs['From Min'].default_value = .45
        mask.inputs['From Max'].default_value = .61
        links.new(separate.outputs['Y'], mask.inputs['Value'])
        overlay = nodes.new('ShaderNodeMixRGB')
        links.new(mask.outputs['Result'], overlay.inputs[0])
        links.new(display_color, overlay.inputs[1])
        links.new(sky.outputs['Color'], overlay.inputs[2])
        display_color = overlay.outputs[0]
    links.new(display_color, shader.inputs['Base Color'])
    links.new(display_color, shader.inputs['Emission Color'])
    shader.inputs['Emission Strength'].default_value = brightness
    visible = nodes.new('ShaderNodeEmission')
    visible.inputs['Strength'].default_value = 1.03 if stand else 1.30 if 'Main' in name else .90
    color = nodes.new('ShaderNodeHueSaturation')
    color.inputs['Saturation'].default_value = 1.02 if stand else 1.15
    links.new(display_color, color.inputs['Color'])
    links.new(color.outputs['Color'], visible.inputs['Color'])
    ray = nodes.new('ShaderNodeLightPath')
    mix = nodes.new('ShaderNodeMixShader')
    links.new(ray.outputs['Is Camera Ray'], mix.inputs[0])
    links.new(shader.outputs[0], mix.inputs[1])
    links.new(visible.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], nodes.get('Material Output').inputs['Surface'])
    aspect = tex.image.size[0]/tex.image.size[1]
    u = min(1, (width/height)/aspect)
    v = min(1, aspect/(width/height))
    lo_u, lo_v = (1-u)/2, (1-v)/2
    mesh.uv_layers.new(name='Centered image').data.foreach_set(
        'uv', [lo_u,lo_v,1-lo_u,lo_v,1-lo_u,1-lo_v,lo_u,1-lo_v])
    parent['screen_source'] = source.name
    parent['screen_size'] = [width, height]
    if stand:
        # The bottom of the base sits on the hardwood. The neck meets the casing.
        base = box(name+' stand base', (0,.028,.013-location[2]), (.34,.21,.026), bezel, .012)
        base.parent = parent
        neck_height = location[2]-(height+rim)/2-.017
        neck = box(name+' tilt neck', (0,.035,.017+neck_height/2-location[2]),
                   (.075,.055,neck_height), bezel, .012)
        neck.parent = parent
    return parent


def characters(frame):
    library = ROOT/'output/blender/latest'
    player = append_character(library/'satou-school-square-eyes.blend', 'At desk')
    reader = append_character(library/'satou-white-square-eyes.blend', 'On floor')
    select_action(player, 'sit', 0)
    select_action(reader, 'sit', 0)
    player['root'].scale *= 1.08
    player['root'].location = (.61, 1.30, 0)
    player['root'].location.z += .72-bone_world(player, 'DownBody').z
    pose_desk_player(player)
    reader_action = reader['rig'].animation_data.action.copy()
    reader_action.name = 'Floor reader with phone'
    reader_action['ysm_clip'] = 'scene_floor_phone'
    reader_action.use_fake_user = True
    reader['rig'].animation_data.action = reader_action
    reader['rig'].animation_data.action_slot = next(iter(reader_action.slots))
    reader['root'].scale *= .89
    reader['root'].location = (-.52, .55, .012)
    reader['root'].rotation_euler.z = math.radians(148)
    bpy.context.scene.frame_set(1)
    pose_phone_reader(reader)
    rig = reader['rig']
    for name, angle in [('LeftLowerLeg', 10), ('RightLowerLeg', -8)]:
        bone = rig.pose.bones[name]
        pivot = bone_world(reader, name)
        rotation = Matrix.Rotation(math.radians(angle), 4, 'Z')
        transform = Matrix.Translation(pivot) @ rotation @ Matrix.Translation(-pivot)
        bone.matrix = rig.matrix_world.inverted() @ transform @ rig.matrix_world @ bone.matrix
        bone.keyframe_insert(data_path='rotation_euler', frame=1)
    for name, factor in [('LongLeftHair', .82), ('LongRightHair', .92), ('LongHair', .92)]:
        bone = rig.pose.bones[name]
        bone.scale *= factor
        bone.keyframe_insert(data_path='scale', frame=1)
    reader['root'].location.z += .012
    phone = phone_prop(reader, frame, material('Phone glass blue-white', (.27,.37,.70), .35, .70))
    phone.scale = (1.14, 1, .87)
    phone.location += Vector((-.012,-.062,.028))
    phone.rotation_euler.x = math.radians(-31)
    phone.data.materials[0] = material('Phone case soft graphite',(.069,.060,.068),.55)
    reading_light = area('Warm reflection on the reader from the shelf',(-1.60,-.20,1.42),
                         (-.54,.52,.38),11,.72,(1,.77,.59))
    reader_receiver = bpy.data.collections.new('Warm light on the reader and rug')
    reader_receiver.objects.link(reader['mesh'])
    reader_receiver.objects.link(bpy.data.objects['Vintage woven area rug'])
    reading_light.light_linking.receiver_collection = reader_receiver
    for character in (reader, player):
        tree = character['mesh'].data.materials[0].node_tree
        shader = next(node for node in tree.nodes if node.type == 'BSDF_PRINCIPLED')
        texture = shader.inputs['Base Color'].links[0].from_socket
        tint = tree.nodes.new('ShaderNodeHueSaturation')
        tint.inputs['Saturation'].default_value = 1.15
        tree.links.new(texture, tint.inputs['Color'])
        tree.links.new(tint.outputs['Color'], shader.inputs['Base Color'])
        relief = tree.nodes.new('ShaderNodeBump')
        relief.label = 'Subtle pixel surface relief'
        relief.inputs['Strength'].default_value = .13
        relief.inputs['Distance'].default_value = .003
        tree.links.new(texture, relief.inputs['Height'])
        tree.links.new(relief.outputs['Normal'], shader.inputs['Normal'])
    return player, reader


def pose_desk_player(player):
    rig = player['rig']
    action = rig.animation_data.action.copy()
    action.name = 'Desk player reaching for controls'
    action['ysm_clip'] = 'scene_desk_keyboard'
    action.use_fake_user = True
    rig.animation_data.action = action
    rig.animation_data.action_slot = next(iter(action.slots))
    bpy.context.scene.frame_set(1)

    def turn(bone_name, joint, target):
        start = bone_world(player, bone_name)
        vector = bone_world(player, joint)-start
        rotation = vector.rotation_difference(target-start).to_matrix().to_4x4()
        bone = rig.pose.bones[bone_name]
        around_joint = Matrix.Translation(start) @ rotation @ Matrix.Translation(-start)
        bone.matrix = rig.matrix_world.inverted() @ around_joint @ rig.matrix_world @ bone.matrix
        bone.keyframe_insert(data_path='rotation_euler', frame=1)

    for side, target, pole in [('Left', (.13,1.792,1.035), (-.8,0,-1)),
                                ('Right', (.82,1.81,1.046), (.5,0,-1))]:
        upper, lower, hand = (side+name for name in ('Arm', 'ForeArm', 'Hand'))
        shoulder = bone_world(player, upper)
        elbow, wrist = bone_world(player, lower), bone_world(player, hand)
        first, second = (elbow-shoulder).length, (wrist-elbow).length
        target = Vector(target)
        direction = (target-shoulder).normalized()
        distance = min((target-shoulder).length, first+second-.002)
        target = shoulder+direction*distance
        along = (first**2-second**2+distance**2)/(2*distance)
        pole = Vector(pole)
        down = (pole-direction*pole.dot(direction)).normalized()
        elbow = shoulder+direction*along+down*math.sqrt(max(0, first**2-along**2))
        turn(upper, lower, elbow)
        turn(lower, hand, target)


def floor_setup(frame, texture_folder):
    case = build_pc_case(box, material, position=(-1.79,1.43,0), yaw=28)
    case.scale = (1.25,.92,.62)
    case['placement'] = 'Behind the two landscape floor monitors'
    case_side = material('PC - graphite case side',(.004,.004,.006),.66)
    case_side.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .12
    side = box('PC - powder coated left side panel', (-.465,0,.79), (.031,.713,1.31),case_side,.009)
    side.parent = case
    for part in case.children:
        if part.name.startswith(('PC - graphics card','PC - GPU backplate','PC - GPU cooling fin',
                                  'PC - GPU RGB edge','PC - GEFORCE RTX')):
            part.location.z += .26
            part.location.x += .06 if 'GEFORCE' not in part.name else .22
        elif part.name.startswith(('PC - GPU braided power lead','PC - cable comb')):
            part.location.z += .17
    for i in range(12):
        shader = bpy.data.materials[f'PC - RGB {i}'].node_tree.nodes.get('Principled BSDF')
        shader.inputs['Emission Strength'].default_value = 1.65
    coolant = material('PC - blue violet and green coolant edge',(.036,.21,.53),.48,.8)
    for part in case.children:
        if part.name.startswith(('PC - CPU RGB halo','PC - fan RGB ring')):
            part.data.materials[0] = coolant
    for name in ['PC - satin aluminum','PC - brushed graphite']:
        shader = bpy.data.materials[name].node_tree.nodes.get('Principled BSDF')
        color = shader.inputs['Base Color'].default_value
        shader.inputs['Base Color'].default_value = tuple(c*.63 for c in color[:3])+(1,)
        shader.inputs['Roughness'].default_value = .47
    glass = bpy.data.materials['PC - clear tempered glass'].node_tree.nodes.get('Principled BSDF')
    glass.inputs['Specular IOR Level'].default_value = .14
    glass.inputs['IOR'].default_value = 1.23
    glass.inputs['Roughness'].default_value = .09
    for part in case.children:
        if part.name.startswith('PC - vertical frame'):
            part.data.materials[0] = material('PC - powder coated dark frame',(.014,.016,.021),.66)
    for i in range(7):
        offset = i*.013
        stripe = material(f'PC - woven GPU harness {i}',(.025,.03,.056),.69)
        bund = cable('GPU rightward braided harness', [(-.15+offset,-.124,.91),
            (.04+offset,-.16,.91),(.14+offset,-.17,.96),(.20+offset,-.11,1.03),
            (.29+offset,.02,1.07)],stripe,.004)
        bund.parent = case
    gpu_shell = material('PC - textured GPU cast shroud', (.028,.027,.039), .53)
    gpu_fin = material('PC - inset GPU steel ribs', (.076,.081,.106), .41)
    for side in (-1, 1):
        cover = box('PC - GPU beveled shroud panel', (.22*side,-.095,.848),
                    (.179,.023,.118), gpu_shell, .020)
        cover.parent = case
        for i in range(5):
            fin = box('PC - slanted GPU shroud rib', (.22*side+(i-2)*.014,-.11,.848),
                      (.006,.004,.080), gpu_fin, .001)
            fin.parent = case
            fin.rotation_euler.y = math.radians(-17)
    for i, color in enumerate([(.12,.36,1), (.80,.075,.33), (.12,.78,.57)]):
        strip = material(f'PC - hardware edge accent {i+1}',color,.55,.7)
        z = .899+i*.017
        accent = cable('PC - bent illuminated GPU trim', [(-.32,-.121,z),(-.16,-.128,z),
            (-.12,-.128,z+.021),(.073,-.128,z+.021),(.10,-.12,z+.012)],strip,.0035)
        accent.parent = case
    case_fill = area('Neutral fill through the PC glass',(-2.30,.20,.76),(-1.78,1.40,.57),10,.53,(.93,.75,1))
    case_receivers = bpy.data.collections.new('PC interior reflected light')
    for part in case.children:
        if part.name.startswith(('PC - GPU','PC - graphics card','PC - motherboard','PC - RAM DIMM')):
            case_receivers.objects.link(part)
    case_fill.light_linking.receiver_collection = case_receivers
    for name, x, y, yaw in [('left', -1.89,.625,26), ('right',-1.224,.766,-5)]:
        display(f'Floor monitor {name}',(x,y,.317),.642,.642*9/16,yaw,frame,
                texture_folder/f'floor-{name}.png',2.8,stand=True)
    mat = material('Floor keyboard mat charcoal weave',(.020,.018,.028),.93)
    pad = box('Floor keyboard mat',(-1.29,.20,.006),(.81,.36,.012),mat,.019)
    pad.rotation_euler.z = math.radians(7)
    keyboard = build_keyboard(box,material,(-1.29,.178,.012),.55,'Floor keyboard')
    keyboard.rotation_euler.z = math.radians(7)
    sleeve = material('Keyboard and display cable rubber',(.012,.014,.019),.7)
    cable('Floor keyboard USB cable',[(-1.30,.292,.037),(-1.39,.362,.025),(-1.67,.40,.015),
          (-1.99,.53,.023),(-2.26,.88,.031),(-2.31,1.24,.09)],sleeve)


def setup_render(scene, draft):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'OPTIX'
    assert any(device.use for device in prefs.devices), 'OptiX GPU not found'
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.use_denoising = True
    scene.cycles.denoising_use_gpu = True
    scene.cycles.samples = 36 if draft else 144
    scene.cycles.adaptive_threshold = .055 if draft else .021
    scene.cycles.max_bounces = 8
    scene.render.resolution_x, scene.render.resolution_y = REFERENCE_SIZE
    scene.render.resolution_percentage = 100
    scene.render.use_persistent_data = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = .12
    glow(scene)
    glare = scene.compositing_node_group.nodes.get('Glare')
    glare.inputs['Threshold'].default_value = .85
    glare.inputs['Strength'].default_value = .22
    glare.inputs['Size'].default_value = .24


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--details', action='store_true')
    parser.add_argument('--save-only', action='store_true')
    parser.add_argument('--stem', default='room')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out = args.output.resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    bezel = material('Display graphite satin',(.012,.016,.029),.34)
    build_concept_architecture(box,material,area,reference=out/'reference.png')
    build_concept_library(box,material,area,reference=out/'reference.png')
    build_concept_furniture(box,material,area)
    characters(bezel)

    for col, (x,y,yaw,width, lower, upper) in enumerate([
        (-.55,2.64,10,.835,'game-01.png','game-02.png'),
        (.342,2.78,0,.899,'game-03.png','game-forest-clear.png'),
        (1.235,2.71,-7,.854,'game-05.png','game-06.png'),
    ], 1):
        for row, (z,texture) in enumerate([(1.423,lower),(1.992,upper)], 1):
            source = out/'textures'/texture if texture == 'game-forest-clear.png' else SCREENS/texture
            if not source.is_file() and texture == 'game-forest-clear.png':
                source = SCREENS/'game-04.png'
            sky_path = out/'textures/center-screen-sky.png'
            sky_sample = sky_path if col == row == 2 and sky_path.is_file() else None
            display(f'Main monitor {col}.{row}',(x,y,z),width,.521,yaw,bezel,source,4.2,
                    sky_sample=sky_sample)
        box(f'Main monitor {col} rear support',(x,y+.055,1.57),(.043,.065,1.17),bezel,.012)
    for i,z in enumerate([1.478,2.101],1):
        display(f'Right code monitor {i}',(2.024,2.43,z),.686,.548,-8,bezel,SCREENS/f'code-0{i}.png',1.8)
    box('Code monitor pole',(1.95,2.51,1.62),(.055,.065,1.22),bezel,.009)
    bar = material('Desk vertical violet bias light',(.31,.47,1),.35,3)
    box('Desk vertical bias light',(-1.002,2.37,1.69),(.019,.03,.59),bar,.006)
    floor_setup(bezel, out/'textures')
    area('Cool window reflection',(-3.0,-.15,2.77),(-1.02,1.1,.71),90,2.3,(.26,.43,1))
    area('Soft pink face and cloth bounce',(-1.05,-1.95,2.03),(-.45,.4,.59),32,2.3,(1,.45,.54))
    area('Soft blue-violet fill',(2.46,-1.15,2.41),(.65,1.35,1.15),38,2.9,(.43,.50,1))
    area('Low amber floor bounce',(-2.8,1.24,1.05),(-2.10,.56,.02),5,.85,(1,.50,.20))
    area('Amber pool under the left desk lip',(-.33,1.98,.89),(-.27,2.48,.69),5,.39,(1,.53,.27))
    floor_reflect = area('Small blue screen reflection on floorboards',(1.26,-.05,.65),
                         (1.22,-1.0,0),3,.56,(.18,.37,1))
    floor_reflect.data.spread = math.radians(70)
    edge_light = area('Cool rose bounce on the front walnut rail',(1.0,-.40,1.32),(1.1,1.92,.946),44,2,(.79,.55,1))
    edge_receivers = bpy.data.collections.new('Desk wood lit by reflected screen light')
    for name in ('Desk - walnut worktop','Desk - front edge rail'):
        edge_receivers.objects.link(bpy.data.objects[name])
    edge_light.light_linking.receiver_collection = edge_receivers
    area('Pink rim at seat',(.43,2.44,2.48),(.52,1.25,1.22),22,1.8,(1,.28,.50))
    area('Soft rim on reader hair',(-.10,1.15,1.55),(-.49,.55,.72),16,1.1,(1,.21,.37))
    world = bpy.data.worlds.new('Dim violet blue night')
    world.use_nodes = True
    scene.world = world
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (.055,.063,.122,1)
    bg.inputs['Strength'].default_value = .12
    hero = camera('01 Approved concept framing',(0,-6,1.25),(0,2.6,1.25),42)
    hero.data.dof.use_dof = True
    hero.data.dof.focus_distance = 7.3
    hero.data.dof.aperture_fstop = 1.25
    detail = camera('02 Floor computer and phone reader',(-.72,-3.35,1.28),(-1.19,.7,.51),46)
    angle = camera('03 Desk and library from right',(1.15,-5.0,2.10),(.29,1.99,1.23),36)
    scene.camera = hero
    setup_render(scene,args.draft)
    scene['approved_reference'] = 'reference.png'
    scene['scene_purpose'] = 'Editable reconstruction of the user-supplied room concept'
    assert len([o for o in scene.objects if o.get('screen_source')]) == 10
    assert len([o for o in scene.objects if o.type == 'ARMATURE']) == 2
    assert bpy.data.objects.get('Floor keyboard') and len(bpy.data.actions) == 96
    scene.render.filepath = '//room.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/f'{args.stem}.blend'))
    if args.save_only:
        return
    views = [(hero,args.stem)]
    if args.details:
        views += [(detail,'floor-detail'),(angle,'library-angle')]
    for cam, name in views:
        scene.camera = cam
        scene.render.filepath = str(out/f'{name}.png')
        bpy.ops.render.render(write_still=True)
    print('CONCEPT_ROOM_RENDER_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
