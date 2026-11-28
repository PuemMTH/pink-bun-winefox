"""Frame-one hand poses for the furnished monitor room."""

from math import radians, sqrt

import bpy
from mathutils import Matrix, Quaternion, Vector

from monitor_room import bone_world, box, contact_min, material


def _character(scene, label):
    root = scene.objects[f'{label} - Character root']
    return {
        'root': root,
        'rig': next(child for child in root.children if child.type == 'ARMATURE'),
        'mesh': next(child for child in root.children if child.type == 'MESH'),
    }


def _rotate_bone(character, name, rotation):
    rig = character['rig']
    bone = rig.pose.bones[name]
    pivot = bone_world(character, name)
    rotation = Matrix.Translation(pivot) @ rotation.to_4x4() @ Matrix.Translation(-pivot)
    bone.matrix = rig.matrix_world.inverted() @ rotation @ rig.matrix_world @ bone.matrix
    bone.keyframe_insert(data_path='rotation_euler', frame=1)


def _reach(character, side, target, pole, palm_axis):
    upper, lower, hand = (side + part for part in ('Arm', 'ForeArm', 'Hand'))
    shoulder, elbow, wrist = (bone_world(character, bone) for bone in (upper, lower, hand))
    upper_length, lower_length = (elbow-shoulder).length, (wrist-elbow).length
    direction = (target-shoulder).normalized()
    distance = min((target-shoulder).length, upper_length+lower_length-.002)
    target = shoulder + direction*distance
    along = (upper_length**2-lower_length**2+distance**2)/(2*distance)
    bend = (pole-direction*pole.dot(direction)).normalized()
    elbow_target = shoulder + direction*along + bend*sqrt(max(0, upper_length**2-along**2))
    _rotate_bone(character, upper, (elbow-shoulder).rotation_difference(elbow_target-shoulder).to_matrix())
    elbow = bone_world(character, lower)
    wrist = bone_world(character, hand)
    pointing = (target-elbow).normalized()
    current_x = (character['rig'].matrix_world @ character['rig'].pose.bones[lower].matrix).to_3x3().col[0]
    reach = (wrist-elbow).rotation_difference(pointing)
    palm_x = reach @ current_x
    desired_x = (palm_axis-pointing*palm_axis.dot(pointing)).normalized()
    roll = palm_x.rotation_difference(desired_x)
    _rotate_bone(character, lower, (roll @ reach).to_matrix())


def _settle_legs(character):
    rig = character['rig']
    action = rig.animation_data.action
    if action.get('seated_legs_grounded'):
        return
    for side, turn in (('Left', 19.4), ('Right', 6.4)):
        thigh, knee, foot = (side + part for part in ('Leg', 'LowerLeg', 'Foot'))
        foot_bone = rig.pose.bones[foot]
        sole = rig.matrix_world @ foot_bone.matrix
        sole = Matrix.Rotation(radians(turn), 4, 'Z') @ sole
        thigh_bone = rig.pose.bones[thigh]
        thigh_bone.rotation_euler.x = radians(123)
        _rotate_bone(character, thigh, Matrix.Rotation(radians(turn), 3, 'Z'))
        rise = .014 - contact_min(character, [thigh])
        lift = Matrix.Translation((0, 0, rise))
        thigh_bone.matrix = rig.matrix_world.inverted() @ lift @ rig.matrix_world @ thigh_bone.matrix
        thigh_bone.keyframe_insert(data_path='location', frame=1)

        # Preserve the foot block's original level sole while finding the new ankle height.
        knee_bone = rig.pose.bones[knee]
        low, high = radians(-95), radians(-48)
        for _ in range(16):
            knee_bone.rotation_euler.x = (low + high) / 2
            if bone_world(character, foot).z < sole.translation.z:
                low = knee_bone.rotation_euler.x
            else:
                high = knee_bone.rotation_euler.x
        sole.translation = bone_world(character, foot)
        foot_bone.matrix = rig.matrix_world.inverted() @ sole
        for bone in (knee_bone, foot_bone):
            bone.keyframe_insert(data_path='rotation_euler', frame=1)
    action['seated_legs_grounded'] = True


def apply_pose_polish(scene):
    """Settle both characters' existing cuboid hands against their props."""
    scene.frame_set(1)
    player = _character(scene, 'At desk')
    reader = _character(scene, 'On floor')
    chest = player['rig'].pose.bones['UpperBody']
    chest.rotation_euler.x = radians(3)
    chest.rotation_euler.z = radians(-7)
    chest.keyframe_insert(data_path='rotation_euler', frame=1)
    _reach(player, 'Left', Vector((.075, 1.842, 1.078)), Vector((-.60,0,-.19)), Vector((-1,0,0)))
    _reach(player, 'Right', Vector((.958, 1.842, 1.068)), Vector((.5,0,-.55)), Vector((-1,0,0)))
    _settle_legs(reader)

    yaw = reader['root'].rotation_euler.to_matrix()
    side_axis = yaw @ Vector((1,0,0))
    forward = yaw @ Vector((0,1,0))
    reader_action = reader['rig'].animation_data.action
    if not reader_action.get('seated_hair_drape'):
        for strand, pitch in (('LongHair', 32), ('LongLeftHair', 10), ('LongRightHair', 10)):
            _rotate_bone(reader, strand, Quaternion(side_axis, radians(pitch)).to_matrix())
        reader_action['seated_hair_drape'] = True
    shoulder = (bone_world(reader, 'LeftArm')+bone_world(reader, 'RightArm'))/2
    grip = shoulder + forward*.285 + Vector((.02, 0, 0))
    grip.z = .407
    for side, sign, spread, drop in (('Left', -1, 1.25, -.38), ('Right', 1, 2.25, -1)):
        wrist = grip + side_axis*.075*sign
        pole = side_axis*spread*sign - 1.3*forward + Vector((0, 0, drop))
        _reach(reader, side, wrist, pole, Vector((-1, 0, 0)))

    phone = scene.objects['Phone in hands']
    phone.scale = (.90, .72, .795)
    phone.rotation_euler.x = radians(-23)
    phone.rotation_euler.z = reader['root'].rotation_euler.z + radians(8)
    phone.location = grip + forward*.094 + Vector((0,0,.038))
    if scene.objects.get('Phone in hands - rear lens') is None:
        lens = box('Phone in hands - rear lens', (-.036,.009,.065), (.012,.004,.012),
                   material('Phone rear lens glass', (.17,.20,.28), .25), .002)
        lens.parent = phone

    return {
        'floor_contact_z': {
            limb: round(contact_min(reader, [limb]), 6)
            for limb in ('LeftFoot', 'RightFoot', 'LeftLeg', 'RightLeg')
        },
        'phone_dimensions': tuple(round(value, 4) for value in phone.dimensions),
        'desk_left_wrist': tuple(round(value, 4) for value in bone_world(player, 'LeftHand')),
    }
