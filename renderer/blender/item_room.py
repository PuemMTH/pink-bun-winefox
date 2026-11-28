"""Room item models, retaining the original scene shapes and materials."""
from math import pi

import bpy
from mathutils import Matrix, Vector

from monitor_room import box, material


def select(source, *prefixes):
    return [obj for obj in source.objects if obj.type in {'MESH', 'CURVE', 'FONT'}
            and obj.name.startswith(prefixes)]


def characters(source, scene):
    models = []
    rigs = []
    for label, x in (('At desk', -.38), ('On floor', .38)):
        root = source.objects[f'{label} - Character root']
        rotation = Matrix.Rotation(pi - root.rotation_euler.z, 4, 'Z')
        offset = Matrix.Translation((x, 0, root.location.z))
        transform = offset @ rotation @ Matrix.Translation(-root.location)
        originals = [root, *root.children_recursive]
        copies = {obj: obj.copy() for obj in originals}
        for obj, clone in copies.items():
            scene.collection.objects.link(clone)
            clone.hide_render = clone.hide_viewport = False
            clone.parent = copies.get(obj.parent)
            if obj == root:
                clone.matrix_world = transform @ obj.matrix_world
            for mod in clone.modifiers:
                if mod.type == 'ARMATURE' and mod.object in copies:
                    mod.object = copies[mod.object]
            if clone.type == 'MESH':
                rigs.append((copies[root], clone))
            models.append(clone)
        if label == 'On floor':
            phone = source.objects['Phone in hands']
            for original in (phone, *phone.children):
                clone = original.copy()
                clone.parent = None
                clone.matrix_world = transform @ original.matrix_world
                scene.collection.objects.link(clone)
                models.append(clone)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    for root, mesh in rigs:
        posed = mesh.evaluated_get(graph)
        height = min((posed.matrix_world @ Vector(point)).z for point in posed.bound_box)
        correction = Vector((0, 0, -height))
        root.location += correction
        if root.name.startswith('On floor'):
            for phone in models:
                if phone.name.startswith('Phone in hands'):
                    phone.location += correction
    return models


def acoustic(source):
    panels = select(source, 'Acoustic wall panel')
    graphite = material('Folded linen seams', (.024,.018,.035), .9)
    backs = [box(f'Folded backing seam {i+1}', (p.location.x, p.location.y+.029, p.location.z),
                 (.012,.005,1.74), graphite, .001) for i,p in enumerate(panels)]
    return panels + backs


def window(source):
    pieces = select(source, 'Timber window jamb', 'Window mullion', 'Window inner mullion')
    rubber = material('Dark glazing gasket', (.011,.012,.018), .92)
    metal = material('Black metal window latch', (.026,.032,.048), .32)
    # The narrow sections frame the window opening without obscuring its profile.
    for x in (-3.49, -2.88):
        pieces.append(box('Glazing rubber seal', (x,1.785,1.76), (.012,.017,3.39), rubber, .002))
    pieces.extend([box('Window latch mounting plate', (-3.079,1.809,1.32), (.055,.017,.111), metal, .004),
                   box('Window latch lever', (-3.062,1.775,1.33), (.087,.039,.016), metal, .005)])
    return pieces


def blinds(source):
    pieces = select(source, 'Venetian blind')
    rail_mat = source.objects['Venetian blind slat'].data.materials[0]
    pieces.extend([box('Headrail', (-3.184,1.75,3.66), (.715,.118,.064), rail_mat, .004),
                   box('Tilt wand', (-2.90,1.677,2.70), (.016,.016,1.72), rail_mat, .006)])
    for x in (-3.546,-2.822):
        pieces.append(box('Headrail end cap', (x,1.75,3.66), (.013,.121,.068), rail_mat, .003))
    return pieces


def pine(source, scene):
    original = source.objects['Pine treeline outside window']
    copy = original.copy()
    copy.data = original.data.copy()
    scene.collection.objects.link(copy)
    solid = copy.modifiers.new('Slim silhouette thickness', 'SOLIDIFY')
    solid.thickness = .014
    return [copy]


def bench(source):
    models = select(source, 'Near right upholstered bench', 'Near right upright silhouette')
    thread = material('Plum stitched welting', (.133,.106,.139), .85)
    for part in models[:]:
        minimum = min(v[0] for v in part.bound_box)
        maximum = max(v[0] for v in part.bound_box)
        front = min(v[1] for v in part.bound_box)
        top = max(v[2] for v in part.bound_box)
        line = [part.matrix_basis @ Vector((x, front-.002, top-.024)) for x in (minimum+.026, maximum-.026)]
        seam = bpy.data.curves.new(part.name+' seam', 'CURVE')
        seam.dimensions = '3D'
        seam.bevel_depth = .0027
        seam.materials.append(thread)
        knots = seam.splines.new('POLY')
        knots.points.add(1)
        for knot, location in zip(knots.points, line):
            knot.co = (*location, 1)
        obj = bpy.data.objects.new(part.name+' seam', seam)
        bpy.context.scene.collection.objects.link(obj)
        models.append(obj)
    return models


def build(item, source, scene):
    slug = item['id']
    callbacks = {'ysm-characters': lambda: characters(source, scene),
                 'acoustic-panels': lambda: acoustic(source), 'window': lambda: window(source),
                 'blinds': lambda: blinds(source), 'pine-trees': lambda: pine(source, scene),
                 'bench': lambda: bench(source)}
    if slug in callbacks:
        return callbacks[slug]()
    prefixes = {'woven-rug': ('Vintage woven area rug',),
                'wood-floor': ('Walnut floor plank','Floorboard subbase'),
                'brick-wall': ('Uneven bonded terracotta brick','Recess mortar back'),
                'distant-houses': ('Nearly dark distant house','Distant house light')}
    return select(source, *prefixes[slug])
