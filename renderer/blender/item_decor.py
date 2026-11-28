"""Standalone assets from the library and decor checklist."""

import math

import bpy
from mathutils import Matrix, Vector

from monitor_room import box, cylinder, material


GEOMETRY = {'MESH', 'CURVE', 'FONT'}
BANKS = ('West brick library and oak shelves', 'East brick library and oak shelves')
LEDGE = 'Library bridge shelf with trailing ivy'
SHELF_PARTS = ('Wide weathered walnut plank', 'Stained side stile', 'Forged ',
               'Uneven bonded terracotta brick', 'Recess mortar back')


def _parts(objects, prefixes=()):
    return [obj for obj in objects if obj.type in GEOMETRY and
            (not prefixes or obj.name.startswith(prefixes))]


def _clone(objects, scene, transform, label=None):
    result = []
    for original in objects:
        obj = original.copy()
        obj.parent = None
        obj.matrix_world = transform @ original.matrix_world
        if label:
            obj.name = f'{label} / {original.name}'
        scene.collection.objects.link(obj)
        result.append(obj)
    return result


def _bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (Vector(min(p[i] for p in points) for i in range(3)),
            Vector(max(p[i] for p in points) for i in range(3)))


def _pipe(scene, name, paths, radius, surface):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth, data.bevel_resolution = radius, 2
    data.materials.append(surface)
    for path in paths:
        spline = data.splines.new('POLY')
        spline.points.add(len(path) - 1)
        for point, position in zip(spline.points, path):
            point.co = (*position, 1)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    return obj


def _bookshelf(source, scene):
    result = []
    offset = 0
    hardware = material('Shelf screw · rubbed gunmetal', (.067, .061, .053), .42)
    slot = material('Shelf screw · recessed slot', (.014, .011, .010), .73)
    for bank in BANKS:
        parts = _parts(source.objects[bank].children, SHELF_PARTS)
        low, high = _bounds(parts)
        shift = Vector((offset - low.x, -low.y, -low.z))
        result.extend(_clone(parts, scene, Matrix.Translation(shift)))
        for wall_plate in (obj for obj in parts if obj.name.startswith('Forged wall plate')):
            center = wall_plate.matrix_world.translation + shift
            for dz in (-.057, .058):
                face = (center.x, center.y - .011, center.z + dz)
                screw = cylinder('Slotted shelf mounting screw', face, .007, .004, hardware, 12)
                screw.rotation_euler.x = math.pi / 2
                result.extend((screw, box('Screw slot', (face[0], face[1] - .0021, face[2]),
                                          (.010, .0004, .0014), slot)))
        offset += high.x - low.x + .15
    return result


def _bridge(source, scene):
    root = source.objects[LEDGE]
    originals = _parts(root.children, ('Long furniture bridge', 'Bridge inner back'))
    result = _clone(originals, scene, root.matrix_world.inverted())
    plank = next(obj for obj in result if obj.name.startswith('Long furniture bridge'))
    bpy.context.view_layer.update()
    wood = plank.data.materials[0]
    dark = bpy.data.materials['Library · stained oak frame']
    x, y, z = plank.matrix_world.translation
    for side in (-1, 1):
        end = x + side * 1.728
        result.extend((
            box('Flush walnut end cap', (end, y, z - .002), (.012, .46, .07), wood, .002),
            box('End grain join line', (end - side * .0065, y, z - .003),
                (.0012, .455, .067), dark, .0004),
        ))
    return result


def _books(source, scene):
    standing = sorted((obj for obj in source.objects if obj.name.startswith('Leather-bound volume')),
                      key=lambda obj: obj.name)
    stacked = sorted((obj for obj in source.objects if obj.name.startswith('Stacked volume')),
                     key=lambda obj: obj.name)
    assert (len(standing), len(stacked)) == (84, 17)
    pages = bpy.data.materials['Library · aged laid paper'].copy()
    pages.name = 'Library · page block with visible layered edges'
    tree = pages.node_tree
    shader = tree.nodes['Principled BSDF']
    bump_input = shader.inputs['Normal']
    prior = bump_input.links[0].from_socket if bump_input.is_linked else None
    wave = tree.nodes.new('ShaderNodeTexWave')
    wave.bands_direction = 'X'
    wave.inputs['Scale'].default_value = 25.0
    wave.inputs['Distortion'].default_value = .50
    coords = tree.nodes.new('ShaderNodeTexCoord')
    tree.links.new(coords.outputs['Generated'], wave.inputs['Vector'])
    bump = tree.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .22
    bump.inputs['Distance'].default_value = .00065
    tree.links.new(wave.outputs['Fac'], bump.inputs['Height'])
    if prior is not None:
        tree.links.new(prior, bump.inputs['Normal'])
    tree.links.new(bump.outputs['Normal'], bump_input)

    band = material('Book · woven headband in warm ivory', (.34, .205, .127), .89)
    result, furthest = [], 0

    def place(spine, origin, label, add_band=False):
        parts = _parts(spine.children)
        low, high = _bounds(parts)
        move = Matrix.Translation(Vector(origin) - low)
        clones = _clone(parts, scene, move, label)
        for obj in clones:
            if 'Paper signatures' in obj.name:
                obj.data = obj.data.copy()
                obj.data.materials[0] = pages
                if add_band:
                    size = next(part.dimensions for part in parts if part.name.startswith('Paper signatures'))
                    for end in (-1, 1):
                        cloth = box('Book cloth headband', (0, 0, 0), (size.x * .97, .006, .003), band, .001)
                        cloth.matrix_world = obj.matrix_world @ Matrix.Translation(
                            (0, -size.y / 2 + .008, end * (size.z / 2 + .0007)))
                        result.append(cloth)
        result.extend(clones)
        return high - low

    for row in range(4):
        cursor = 0
        for column, spine in enumerate(standing[row * 21:(row + 1) * 21]):
            size = place(spine, (cursor, row * .365, 0), f'Upright book {row * 21 + column + 1:02}',
                         add_band=row == 0 and column % 3 == 0)
            cursor += size.x + .014
        furthest = max(cursor, furthest)
    for stack_index in range(4):
        height = 0
        division = stacked[stack_index * 5:stack_index * 5 + 5]
        for level, spine in enumerate(division):
            size = place(spine, (furthest + .15 + stack_index % 2 * .46 + (level % 3) * .012,
                                 stack_index // 2 * .46, height),
                         f'Flat book {stack_index * 5 + level + 1:02}', add_band=level == len(division) - 1)
            height += size.z + .002
    return result


def _archive(source):
    originals = _parts(source.objects[LEDGE].children, ('Canvas archive box', 'Archive box '))
    body = source.objects['Canvas archive box']
    matrix = body.matrix_world.copy()
    charcoal = material('Archive · doubled fabric seam', (.034, .025, .031), .88)
    for side in (-1, 1):
        for depth in (-1, 1):
            seam = box('Archive folded corner binding', (0, 0, 0), (.004, .004, .333), charcoal, .001)
            seam.matrix_world = matrix @ Matrix.Translation((side * .229, depth * .147, 0))
            originals.append(seam)
    lid = source.objects['Archive box fitted lid']
    for side in (-1, 1):
        hem = box('Archive lid horizontal seam', (0, 0, 0), (.456, .0018, .002), charcoal, .0005)
        hem.matrix_world = lid.matrix_world @ Matrix.Translation((0, side * .157, -.012))
        originals.append(hem)
    return originals


def _pixel_frame(source):
    body = source.objects['Antiqued framed pixel print']
    result = [body, *_parts(body.children_recursive)]
    back_surface = material('Frame · sealed wood backing', (.048, .030, .017), .8)
    back = box('Removable frame backing', (0, 0, 0), (.220, .006, .286), back_surface, .002)
    back.matrix_world = body.matrix_world @ Matrix.Translation((0, .021, 0))
    leg = box('Fold-out picture stand', (0, 0, 0), (.046, .010, .203), back_surface, .0025)
    leg.matrix_world = body.matrix_world @ Matrix.Translation((0, .074, -.058)) @ Matrix.Rotation(.44, 4, 'X')
    hinge = box('Picture stand hinge', (0, 0, 0), (.060, .013, .017),
                bpy.data.materials['Library · antique brass'], .002)
    hinge.matrix_world = body.matrix_world @ Matrix.Translation((0, .031, .034))
    return [*result, back, leg, hinge]


def _amber_lantern(source):
    result = _parts(source.objects[BANKS[0]].children, ('Lantern ',))
    glass = source.objects['Lantern frosted amber body']
    position = glass.matrix_world.translation
    steel = bpy.data.materials['Library · blackened steel']
    for sign in (-1, 1):
        z = position.z + sign * .087
        result.extend([
            box('Gasket along lantern glass', (position.x, position.y + side * .069, z),
                (.146, .004, .004), steel, .0008) for side in (-1, 1)
        ])
        result.extend([
            box('Gasket along lantern side glass', (position.x + side * .073, position.y, z),
                (.004, .139, .004), steel, .0008) for side in (-1, 1)
        ])
    return result


def _pixel_lantern(source):
    objects = _parts(source.objects[LEDGE].children, ('Pixel window keepsake', 'Pixel lantern window'))
    trim = bpy.data.materials['Library · blackened steel']
    for pixel in (part for part in tuple(objects) if part.name.startswith('Pixel lantern window')):
        for side in (-1, 1):
            bar = box('Recess side reveal', (0, 0, 0), (.002, .0048, .027), trim, .0004)
            bar.matrix_world = pixel.matrix_world @ Matrix.Translation((side * .0105, -.0024, 0))
            objects.append(bar)
            lip = box('Recess horizontal reveal', (0, 0, 0), (.021, .0048, .002), trim, .0004)
            lip.matrix_world = pixel.matrix_world @ Matrix.Translation((0, -.0024, side * .013))
            objects.append(lip)
    return objects


def _led_strip(source, scene):
    fixtures = sorted(_parts(source.objects, ('Concealed warm light strip',)), key=lambda obj: obj.name)
    assert len(fixtures) == 6
    aluminum = material('LED rail · satin anodized aluminum', (.19, .185, .17), .44)
    aluminum.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = .66
    black = material('LED strip · cable sleeve and end cap', (.016, .014, .014), .63)
    diffuser = fixtures[0].data.materials[0].copy()
    diffuser.name = 'LED strip · warm opal diffuser'
    diffuser.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 1.1
    result = []
    for index, fixture in enumerate(fixtures):
        length = fixture.dimensions.x
        y = index * .075
        result.extend((
            box('Anodized aluminum U-channel back', (0, y, .004), (length + .024, .023, .008), aluminum, .0017),
            box('Continuous opal diffuser', (0, y, .013), (length, .013, .009), diffuser, .002),
        ))
        for side in (-1, 1):
            result.extend((
                box('Aluminum extrusion rail', (0, y + side * .009, .011),
                    (length + .021, .0045, .013), aluminum, .0011),
                box('Fitted LED end cap', (side * (length / 2 + .006), y, .009),
                    (.012, .023, .018), black, .0017),
            ))
        tip = length / 2
        result.append(_pipe(scene, 'LED low-voltage input lead',
                            [[(tip + .010, y, .009), (tip + .043, y, .009),
                              (tip + .075, y + .008, .008), (tip + .124, y + .023, .006)]],
                            .003, black))
    return result


def _creeper(source, scene):
    root = source.objects[LEDGE]
    result = _clone(_parts(root.children, ('Olive ceramic pixel sculpture', 'Sculpture dark inlay')),
                    scene, root.matrix_world.inverted())
    body = next(obj for obj in result if obj.name.startswith('Olive ceramic pixel sculpture'))
    body.data = body.data.copy()
    glaze = body.data.materials[0].copy()
    glaze.name = 'Olive ceramic with blocky glaze mottling'
    body.data.materials[0] = glaze
    tree = glaze.node_tree
    coords = tree.nodes.new('ShaderNodeTexCoord')
    snap = tree.nodes.new('ShaderNodeVectorMath')
    snap.operation = 'SNAP'
    snap.inputs[1].default_value = (.125, .125, .125)
    tree.links.new(coords.outputs['Generated'], snap.inputs[0])
    pattern = tree.nodes.new('ShaderNodeTexWhiteNoise')
    tree.links.new(snap.outputs[0], pattern.inputs['Vector'])
    glaze_color = tree.nodes.new('ShaderNodeValToRGB')
    glaze_color.color_ramp.interpolation = 'CONSTANT'
    for pos, rgb in ((0, (.077, .106, .023)), (.25, (.115, .150, .026)),
                     (.52, (.164, .181, .044)), (1, (.201, .208, .059))):
        ramp = glaze_color.color_ramp
        stop = ramp.elements[0] if pos == 0 else ramp.elements[-1] if pos == 1 else ramp.elements.new(pos)
        stop.color = (*rgb, 1)
    tree.links.new(pattern.outputs['Value'], glaze_color.inputs['Fac'])
    tree.links.new(glaze_color.outputs['Color'], tree.nodes['Principled BSDF'].inputs['Base Color'])
    return result


def _armillary(source):
    parts = _parts(source.objects[BANKS[1]].children, ('Armillary ',))
    ring = next(obj for obj in parts if obj.name == 'Armillary engraved ring')
    center = sum((ring.matrix_world @ p.co.xyz for p in ring.data.splines[0].points), Vector()) / 48
    scale = material('Armillary · dark engraved scale', (.078, .041, .012), .54)
    for index in range(48):
        theta = index * math.tau / 48
        mark = box('Armillary engraved division', center + Vector((.136 * math.cos(theta), -.0049,
                   .136 * math.sin(theta))), (.0065 if index % 4 == 0 else .0038, .0007, .0015), scale, .0003)
        mark.rotation_euler.y = -theta
        parts.append(mark)
    axis = source.objects['Armillary tilted axis']
    brass = bpy.data.materials['Library · antique brass']
    for sign in (-1, 1):
        pin = cylinder('Armillary brass pivot cap', (0, 0, 0), .014, .008, brass, 18)
        pin.matrix_world = axis.matrix_world @ Matrix.Translation((0, 0, sign * axis.dimensions.z / 2))
        parts.append(pin)
    return parts


def _ivy(source, scene):
    result = []
    x = 0
    vein_surface = bpy.data.materials['Library · olive stems']
    underside_shaders = {}
    for cluster in (*BANKS, LEDGE):
        parts = _parts(source.objects[cluster].children_recursive, ('Ivy · ', 'Raised central vein',
                      'Trailing ivy stem', 'Leaf petiole'))
        lo, hi = _bounds(parts)
        shift = Matrix.Translation((x - lo.x, -lo.y, -hi.z))
        clones = _clone(parts, scene, shift)
        result.extend(clones)
        for leaf in (obj for obj in clones if obj.name.startswith('Ivy · heart leaf')):
            original = leaf.data.materials[0]
            if original.name not in underside_shaders:
                finish = original.copy()
                finish.name = original.name + ' with paler underside'
                tree = finish.node_tree
                base = tree.nodes['Principled BSDF'].inputs['Base Color']
                prior = base.links[0].from_socket
                sides = tree.nodes.new('ShaderNodeNewGeometry')
                factor = tree.nodes.new('ShaderNodeMath')
                factor.operation = 'MULTIPLY'
                factor.inputs[1].default_value = .25
                mix = tree.nodes.new('ShaderNodeMixRGB')
                mix.inputs[2].default_value = (.24, .32, .11, 1)
                tree.links.new(sides.outputs['Backfacing'], factor.inputs[0])
                tree.links.new(factor.outputs[0], mix.inputs[0])
                tree.links.new(prior, mix.inputs[1])
                tree.links.new(mix.outputs[0], base)
                underside_shaders[original.name] = finish
            leaf.data = leaf.data.copy()
            leaf.data.materials[0] = underside_shaders[original.name]
        paths = []
        for leaf in (obj for obj in parts if obj.name.startswith('Ivy · heart leaf')):
            transform = shift @ leaf.matrix_world
            center = leaf.data.vertices[10].co
            for index in (2, 4, 6, 8):
                edge = leaf.data.vertices[index].co
                points = [center.copy(), center.lerp(edge, .55), center.lerp(edge, .84)]
                for p in points:
                    p.y -= .0007
                paths.append([transform @ p for p in points])
        result.append(_pipe(scene, 'Ivy secondary leaf veins', paths, .00053, vein_surface))
        x += hi.x - lo.x + .12
    return result


def _potted_plant(source, scene):
    names = ('Foreground planter', 'Planter rim', 'Planter soil', 'Foreground olive plant', 'Foreground olive stems')
    parts = [source.objects[name] for name in names]
    rim = _clone([parts[1]], scene, Matrix.Identity(4))[0]
    rim.data = rim.data.copy()
    glaze = rim.data.materials[0].copy()
    glaze.name = 'Planter · glossy fired rim'
    glaze.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .38
    rim.data.materials[0] = glaze
    parts[1] = rim
    leaves = source.objects['Foreground olive plant']
    veins = bpy.data.materials['Foreground | olive stems']
    paths = []
    for i in range(46):
        path = [leaves.matrix_world @ leaves.data.vertices[i * 85 + row * 5 + 2].co for row in range(15)]
        paths.append([point + Vector((0, 0, .0014)) for point in path])
    parts.append(_pipe(scene, 'Planter raised leaf midribs', paths, .0008, veins))
    soil = source.objects['Planter soil'].matrix_world.translation
    loam = material('Planter · granular loam', (.034, .020, .011), .91)
    for i in range(32):
        theta = 2.399 * i
        distance = math.sqrt((i + 1) / 32)
        loc = soil + Vector((.244 * distance * math.cos(theta), .166 * distance * math.sin(theta), .0044))
        scale = .006 + .0017 * (i % 6)
        pebble = box('Planter grain of loam', loc, (scale, scale * .74, scale * .58), loam, .0015)
        pebble.rotation_euler.z = theta
        parts.append(pebble)
    return parts


def build(item, source, scene):
    """Select existing pieces or assemble extended details in the active destination scene."""
    slug = item['id'] if isinstance(item, dict) else item
    if slug == 'archive-box':
        return _archive(source)
    if slug == 'pixel-frame':
        return _pixel_frame(source)
    if slug == 'amber-lantern':
        return _amber_lantern(source)
    if slug == 'pixel-lantern':
        return _pixel_lantern(source)
    if slug == 'armillary':
        return _armillary(source)
    builders = {
        'bookshelf': _bookshelf, 'bridge-shelf': _bridge, 'books': _books,
        'led-strip': _led_strip, 'creeper-head': _creeper, 'ivy': _ivy,
        'potted-plant': _potted_plant,
    }
    return builders[slug](source, scene)
