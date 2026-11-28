"""Timber shelves on exposed brick, with varied editable books and steel brackets."""
import math
import random

import bpy
from mathutils import Vector


def build_bookshelves(box, material):
    scene = bpy.context.scene
    rng = random.Random(271127)
    timber = material('Library - warm aged oak', (.26, .115, .043), .6)
    nodes, links = timber.node_tree.nodes, timber.node_tree.links
    coord = nodes.new('ShaderNodeTexCoord')
    stretch = nodes.new('ShaderNodeVectorMath'); stretch.operation = 'MULTIPLY'
    stretch.inputs[1].default_value = (2, 48, 36)
    links.new(coord.outputs['Generated'], stretch.inputs[0])
    grain = nodes.new('ShaderNodeTexNoise'); grain.inputs['Scale'].default_value = 2; grain.inputs['Detail'].default_value = 3
    links.new(stretch.outputs[0], grain.inputs['Vector'])
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (.085, .032, .012, 1)
    ramp.color_ramp.elements[1].color = (.37, .19, .075, 1)
    links.new(grain.outputs['Fac'], ramp.inputs[0])
    shader = nodes.get('Principled BSDF'); links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
    bump = nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .2; bump.inputs['Distance'].default_value = .008
    links.new(grain.outputs['Fac'], bump.inputs['Height']); links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    mortar = material('Library - warm lime mortar', (.24, .21, .175), .95)
    brick = [material('Library - terracotta brick '+str(i), c, .9) for i, c in enumerate([
        (.28, .095, .047), (.34, .13, .066), (.21, .073, .039), (.39, .17, .095), (.25, .125, .08), (.32, .16, .10)])]
    steel = material('Library - forged black brackets', (.022, .025, .029), .45)
    pages = [material('Library - paper '+str(i), c, .9) for i, c in enumerate([
        (.68, .61, .47), (.54, .47, .34), (.79, .73, .60)])]
    covers = [material('Library - cloth cover '+str(i), c, .75) for i, c in enumerate([
        (.24, .052, .038), (.40, .14, .09), (.10, .15, .11), (.05, .095, .14),
        (.45, .35, .21), (.61, .51, .35), (.11, .065, .052), (.24, .22, .15), (.18, .08, .12),
        (.72, .64, .47), (.62, .57, .45), (.80, .72, .57), (.55, .43, .27)])]
    gilt = material('Library - faded spine gold', (.45, .32, .14), .65)
    ink = material('Library - dark printed title', (.06, .052, .038), .8)
    reading_strip = material('Library - subtle warm shelf strip', (1, .69, .37), .5, 6)
    roots = []

    for side, x in [('Left', -2.9), ('Right', 3.05)]:
        root = bpy.data.objects.new('Library '+side+' - brick and timber shelves', None)
        scene.collection.objects.link(root); root.location = (x, 1.85, 0)
        roots.append(root)

        def part(name, pos, size, mat, bevel=.002, parent=None):
            ob = box('Library '+side+' - '+name, pos, size, mat, bevel)
            ob.parent = parent or root
            return ob

        def beam(name, start, end, width=.018):
            delta = Vector(end)-Vector(start)
            ob = part(name, (Vector(start)+Vector(end))/2, (width, width, delta.length), steel)
            ob.rotation_euler = delta.to_track_quat('Z', 'Y').to_euler()
            return ob

        def book(name, center_x, base_z, thickness, height, depth, cover, tilt=0, horizontal=False):
            ob = bpy.data.objects.new('Library '+side+' - '+name, None)
            scene.collection.objects.link(ob); ob.parent = root
            angle = math.pi/2 if horizontal else math.radians(tilt)
            ob.rotation_euler.y = angle
            vertical = thickness if horizontal else height*math.cos(angle)+thickness*abs(math.sin(angle))
            ob.location = (center_x, -.095+rng.uniform(-.012, .012), base_z+vertical/2)
            part(name+' page block', (0, .004, 0), (thickness-.009, depth-.016, height-.014), pages[rng.randrange(3)], .001, ob)
            for edge in [-1, 1]:
                part(name+' cloth cover', (edge*(thickness/2-.002), 0, 0), (.004, depth, height), cover, .001, ob)
            front = -depth/2-.002
            part(name+' rounded spine', (0, front, 0), (thickness, .009, height), cover, .002, ob)
            for z in [-height*.36, height*.36]:
                part(name+' spine band', (0, front-.005, z), (thickness*.78, .002, .006), gilt, .0004, ob)
            # A short label and fine lines read as print without repeating invented text.
            label = gilt if cover != covers[5] else ink
            for j in range(3):
                part(name+' spine title line', (0, front-.005, (j-1)*.011), (thickness*(.60-j*.09), .002, .003), label, .0002, ob)
            ob['book_orientation'] = 'stacked' if horizontal else 'leaning' if tilt else 'upright'
            return ob

        # A real staggered brick bond fills the mortar backing, not a flat red panel.
        part('mortar backing', (0, .355, 2.08), (1.35, .045, 4.16), mortar)
        for row in range(29):
            z = .08+row*.141
            offset = -.14 if row%2 else 0
            for column in range(6):
                left = -.675+offset+column*.282
                right = min(.675, left+.266); left = max(-.675, left)
                if right-left < .025: continue
                part('handmade brick', ((left+right)/2, .312+rng.uniform(-.002,.002), z),
                     (right-left, .052, .126+rng.uniform(-.003,.003)), rng.choice(brick), .003)
        levels = [.32, 1.00, 1.68, 2.36, 3.04, 3.72]
        for level, z in enumerate(levels):
            part('oak shelf '+str(level+1), (0, 0, z), (1.35, .60, .055), timber, .009)
            if level:
                part('under shelf reading strip', (0,-.29,z-.034), (1.18,.009,.008), reading_strip, .002)
            for bx in [-.46,.46]:
                part('wall bracket spine', (bx,.275,z-.12), (.026,.027,.26), steel)
                part('wall bracket shelf arm', (bx,.025,z-.037), (.026,.53,.022), steel)
                beam('wall bracket diagonal', (bx,.27,z-.235), (bx,-.21,z-.049))
                # Metallic screw heads are visible on the vertical wall plate.
                for bz in [z-.205,z-.045]:part('bracket screw', (bx,.258,bz), (.011,.007,.011), gilt, .003)
            base = z+.0275
            stack_right = (level+(side=='Right'))%3 != 1
            # Reserve one end for a horizontal pile; loose clusters break the picket-fence rhythm.
            stack_x = .42 if stack_right else -.42
            start, stop = (-.60,.20) if stack_right else (-.22,.61)
            cursor = start
            index = 0
            while cursor < stop-.04:
                thickness = rng.uniform(.038,.079)
                if cursor+thickness > stop:break
                height = rng.uniform(.29,.46)
                tilt = rng.choice([0,0,0,-9,7]) if index in [0,5] else 0
                angle=abs(math.radians(tilt))
                occupied=thickness*math.cos(angle)+height*math.sin(angle)
                if cursor+occupied>stop:break
                book(f'book {level+1}-{index+1}',cursor+occupied/2,base,thickness,height,rng.uniform(.24,.29),rng.choice(covers),tilt)
                cursor += occupied+rng.uniform(.004,.014)
                index += 1
            pile_z = base
            for j in range(rng.randint(2,4)):
                thickness=rng.uniform(.035,.054)
                book(f'pile {level+1}-{j+1}',stack_x+rng.uniform(-.022,.022),pile_z,thickness,rng.uniform(.30,.38),rng.uniform(.245,.285),rng.choice(covers),horizontal=True)
                pile_z+=thickness+.003

        # A few personal items on the broad bottom shelf echo the reference's lower display.
        z=levels[0]+.0275
        part('small framed print', (.42,.12,z+.15), (.24,.035,.30), steel, .006)
        part('print paper', (.42,.10,z+.15), (.21,.006,.267), pages[0], .001)
        part('print artwork', (.42,.096,z+.14), (.15,.002,.15), covers[2], .001)
        part('print pale horizon', (.42,.094,z+.18), (.15,.002,.03), pages[2], .001)
        # Place the frame behind the short horizontal stack; no floating ornaments.
        root['shelf_levels'] = len(levels)
        root['construction'] = 'Aged oak, exposed staggered brick, black wall brackets; varied cloth spines and horizontal stacks'
        root['reference_style'] = 'User supplied timber shelf on exposed brick wall'
    return roots
