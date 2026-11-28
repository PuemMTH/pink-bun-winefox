"""Localized screen fill for the seated reader."""

from math import radians

import bpy
from mathutils import Vector

from sunset_city import area


def add_phone_light(scene):
    name = 'Phone - cool screen bounce on reader'
    if existing := scene.objects.get(name):
        return existing

    phone = scene.objects['Phone in hands'].evaluated_get(bpy.context.evaluated_depsgraph_get())
    normal = phone.matrix_world.to_quaternion() @ Vector((0, -1, 0))
    width, thickness, height = phone.dimensions
    position = phone.matrix_world.translation + normal * (thickness / 2 + .002)
    light = area(name, position, position + normal, .18, width * .84, (.67, .81, 1.0))
    light.data.shape = 'RECTANGLE'
    light.data.size_y = height * .84
    light.data.spread = radians(150)

    reader = scene.objects['On floor - Character root']
    receivers = bpy.data.collections.new('Phone screen bounce - floor reader only')
    receivers.objects.link(next(child for child in reader.children if child.type == 'MESH'))
    light.light_linking.receiver_collection = receivers
    return light
