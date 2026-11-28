"""Editable surfaces, window and foreground for the library concept match."""

from array import array
import math
from pathlib import Path
import random

import bpy
from mathutils import Vector


def color_ramp(tree, source, stops):
    node = tree.nodes.new("ShaderNodeValToRGB")
    elements = node.color_ramp.elements
    for i, (position, rgb) in enumerate(stops):
        element = elements[i] if i < 2 else elements.new(position)
        element.position = position
        element.color = (*rgb, 1)
    tree.links.new(source, node.inputs["Fac"])
    return node.outputs["Color"]


def noise(tree, coordinate, stretch, scale=1, detail=2):
    vector = tree.nodes.new("ShaderNodeVectorMath")
    vector.operation = "MULTIPLY"
    vector.inputs[1].default_value = stretch
    tree.links.new(coordinate, vector.inputs[0])
    texture = tree.nodes.new("ShaderNodeTexNoise")
    texture.inputs["Scale"].default_value = scale
    texture.inputs["Detail"].default_value = detail
    tree.links.new(vector.outputs["Vector"], texture.inputs["Vector"])
    return texture.outputs["Fac"]


def bump(tree, shader, height, strength, distance):
    node = tree.nodes.new("ShaderNodeBump")
    node.inputs["Strength"].default_value = strength
    node.inputs["Distance"].default_value = distance
    tree.links.new(height, node.inputs["Height"])
    tree.links.new(node.outputs["Normal"], shader.inputs["Normal"])


def walnut_material(material):
    finish = material("Floor | hand-oiled walnut", (.123, .043, .024), .31)
    tree = finish.node_tree
    shader = tree.nodes["Principled BSDF"]
    position = tree.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    grain = noise(tree, position, (2.55, 104, 18), detail=4)
    tone = color_ramp(tree, grain, [
        (.18, (.017, .004, .002)),
        (.82, (.113, .032, .014)),
        (.49, (.054, .015, .008)),
    ])
    variation = tree.nodes.new("ShaderNodeObjectInfo").outputs["Random"]
    tint = color_ramp(tree, variation, [
        (0, (.62, .59, .54)),
        (1, (1, .92, .80)),
    ])
    multiply = tree.nodes.new("ShaderNodeMixRGB")
    multiply.blend_type = "MULTIPLY"
    multiply.inputs[0].default_value = 1
    tree.links.new(tone, multiply.inputs[1])
    tree.links.new(tint, multiply.inputs[2])
    tree.links.new(multiply.outputs[0], shader.inputs["Base Color"])
    roughness = color_ramp(tree, grain, [(0, (.21,) * 3), (1, (.41,) * 3)])
    tree.links.new(roughness, shader.inputs["Roughness"])
    shader.inputs["Specular IOR Level"].default_value = .15
    bump(tree, shader, grain, .14, .003)
    return finish


def fabric_material(material):
    finish = material("Wall | graphite acoustic linen", (.043, .037, .064), .82)
    tree = finish.node_tree
    shader = tree.nodes["Principled BSDF"]
    position = tree.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    threads = noise(tree, position, (166, 170, 175), detail=1)
    color = color_ramp(tree, threads, [
        (.21, (.033, .029, .044)),
        (.81, (.095, .072, .115)),
    ])
    tree.links.new(color, shader.inputs["Base Color"])
    shader.inputs["Sheen Weight"].default_value = .21
    bump(tree, shader, threads, .30, .0024)
    return finish


def rug_swatch(reference, border=False):
    """Rectify and normalize a small open rug swatch from the supplied image."""
    if reference is None or not Path(reference).is_file():
        return None
    image = bpy.data.images.load(str(Path(reference).resolve()), check_existing=False)
    try:
        width, height = image.size
        source = array("f", [0]) * (width * height * image.channels)
        image.pixels.foreach_get(source)
        samples = []
        for row in range(37):
            v = row / 36
            for column in range(112):
                u = column / 111
                if border:
                    px = 1080 + 190*u
                    py = 915 - 8*u - 30*v
                else:
                    px = 1150 + 12*v + (152 + 14*v)*u
                    py = 824 + v*42
                x = round(px / 1671 * (width - 1))
                y = round((1 - py / 941) * (height - 1))
                i = (y * width + x) * image.channels
                samples.append(.21 * source[i] + .72 * source[i + 1] + .07 * source[i + 2])
    finally:
        bpy.data.images.remove(image)
    sorted_samples = sorted(samples)
    dark = sorted_samples[len(samples) // 16]
    light = sorted_samples[len(samples) * 15 // 16]
    spread = max(.025, light - dark)
    return [max(0, min(1, (value - dark) / spread)) for value in samples]


def carpet_pattern(reference, width=1024, height=768):
    """A mottled wool field framed by repeating geometric braid and fine piping."""
    swatch = rug_swatch(reference)
    border = rug_swatch(reference, border=True)
    pixels = []
    for row in range(height):
        v = (row + .5) / height
        for column in range(width):
            u = (column + .5) / width
            distance_x = min(u, 1 - u) * 1.50
            distance_y = min(v, 1 - v)
            edge = min(distance_x, distance_y)
            along = v if distance_x < distance_y else u * 1.50
            braid = math.cos(along * math.tau * 38 + math.sin(edge * 460) * 1.4)
            if edge < .010:
                rgb = (.054, .031, .043)
            elif edge < .016 or .053 < edge < .060 or .075 < edge < .082:
                rgb = (.245, .133, .137)
            elif edge < .022 or .061 < edge < .069 or .083 < edge < .090:
                rgb = (.040, .023, .040)
            elif edge < .090:
                tone = .55 + .23 * braid + .17 * math.sin(edge * 720)
                rgb = (.25 * tone, .132 * tone, .126 * tone)
            else:
                # Interleaved diamonds and irregular worn crests keep the large field from reading as solid cloth.
                scallop = 1.35 * math.sin(v * 96) + .70 * math.sin(v * 39 + u * 61)
                stitch = abs(math.sin(u * 126 + scallop) + .50 * math.sin(v * 122))
                crest = math.sin((u - v) * 57) * math.sin((u + v) * 53)
                mottling = .50 + .11 * math.cos(u * 41 + v * 63) + .13 * math.sin(u * 77 - v * 42)
                arabesque = 1.3 * max(0, .24 - stitch)
                tone = mottling + arabesque + .22 * max(0, crest)
                rgb = (.070 * tone, .054 * tone, .079 * tone)
                if swatch:
                    # Mirror the swatch at each repeat to preserve continuous yarn across joins.
                    sample_x = round((1 - abs((u * 14 % 2) - 1)) * 111)
                    sample_y = round((1 - abs((v * 10 % 2) - 1)) * 36)
                    detail = .43 + 1.20 * swatch[sample_y * 112 + sample_x]
                    rgb = tuple(channel * detail for channel in rgb)
            if border and edge < .090:
                sample_x = round((1-abs((along*12 % 2)-1))*111)
                sample_y = min(36, int(edge/.090*37))
                thread = border[sample_y*112+sample_x]
                rgb = (.051+.196*thread, .029+.110*thread, .040+.116*thread)
            yarn = .68 + .35 * math.sin(column * 2.7 + math.sin(row * .72)) ** 2
            yarn *= .73 + .38 * math.sin(row * 2.2 + math.sin(column * .88)) ** 2
            # A yarn spans multiple texture pixels so the contrasting threads
            # remain readable when foreshortened near the camera.
            tuft_x, tuft_y = column // 3, row // 2
            speckle = ((tuft_x * 77 + tuft_y * 137) ^ (tuft_x * tuft_y * 11)) % 53
            fleck = 2.05 if speckle < 6 else .37 if speckle < 20 else 1.0
            pixels.extend((rgb[0] * yarn * fleck, rgb[1] * yarn * fleck,
                           rgb[2] * yarn * fleck, 1))
    image = bpy.data.images.new(
        "Rug | woven aubergine and muted rose pattern", width=width, height=height,
    )
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(pixels)
    image.update()
    image.pack()
    return image


def rug_material(material, reference):
    finish = material("Rug | vintage woven wool", (.074, .048, .07), .86)
    tree = finish.node_tree
    shader = tree.nodes["Principled BSDF"]
    coords = tree.nodes.new("ShaderNodeTexCoord").outputs["Generated"]
    pattern = tree.nodes.new("ShaderNodeTexImage")
    pattern.image = carpet_pattern(reference)
    pattern.extension = "EXTEND"
    tree.links.new(coords, pattern.inputs["Vector"])
    tufts = noise(tree, coords, (147, 117, 1), detail=1)
    tufts_color = color_ramp(tree, tufts, [
        (.28, (.12, .11, .15)),
        (.70, (2.50, 2.25, 2.67)),
    ])
    mottled = tree.nodes.new("ShaderNodeMixRGB")
    mottled.blend_type = "MULTIPLY"
    mottled.inputs[0].default_value = .82
    tree.links.new(pattern.outputs["Color"], mottled.inputs[1])
    tree.links.new(tufts_color, mottled.inputs[2])
    tree.links.new(mottled.outputs[0], shader.inputs["Base Color"])
    tree.links.new(color_ramp(tree, tufts, [(0, (.59,) * 3), (1, (.97,) * 3)]),
                   shader.inputs["Roughness"])
    bump(tree, shader, tufts, .66, .0048)
    shader.inputs["Sheen Weight"].default_value = .035
    return finish


def window_and_blinds(box, material, area):
    frame = material("Window | dark blue oak", (.029, .026, .038), .42)
    blind = material("Window | midnight blue slats", (.022, .029, .052), .43)
    sky = material("Window | evening blue", (.009, .017, .061), .76, .54)
    forest = material("Window | distant blue-black pine canopy", (.004, .008, .016), .92)
    house = material("Window | far houses in shadow", (.008, .013, .026), .82)
    apartment = material("Window | distant house lights", (.38, .51, .76), .65, .86)
    center = -3.184
    box("Blue night exterior", (center, 2.06, 1.75), (.68, .035, 3.45), sky)
    rng = random.Random(26)
    tree_vertices, tree_faces = [], []
    pine_outline = [(-1, .02), (1, .02), (.91, .40), (.49, .38), (.69, .61),
                    (.31, .59), (.44, .78), (.17, .75), (0, 1), (-.17, .75),
                    (-.44, .78), (-.31, .59), (-.69, .61), (-.49, .38), (-.91, .40)]
    for index in range(12):
        x = center - .336 + index * .061
        width = rng.uniform(.09, .133)
        height = rng.uniform(.73, 1.63)
        start = len(tree_vertices)
        tree_vertices.extend((x + width * dx, 2.025 - index * .001, .24 + height * dz)
                             for dx, dz in pine_outline)
        tree_faces.append(tuple(range(start, len(tree_vertices))))
    mesh = bpy.data.meshes.new("Evening forest silhouettes")
    mesh.from_pydata(tree_vertices, [], tree_faces)
    mesh.materials.append(forest)
    mesh.update()
    trees = bpy.data.objects.new("Pine treeline outside window", mesh)
    bpy.context.scene.collection.objects.link(trees)
    for x, z in [(center - .248, 1.53), (center - .294, 1.33), (center - .12, 1.12)]:
        box("Nearly dark distant house", (x, 2.001, z), (.066, .012, .061), house, .005)
        for dx in (-.011, .010):
            box("Distant house light", (x + dx, 1.993, z - .008),
                (.009, .003, .013), apartment)
    for x in (center - .338, center + .338):
        box("Timber window jamb", (x, 1.87, 1.76), (.083, .20, 3.52), frame, .012)
    for z in (.24, 1.47, 3.49):
        box("Window mullion", (center, 1.88, z), (.72, .15, .060), frame, .009)
    box("Window inner mullion", (center + .105, 1.918, 1.64), (.036, .13, 2.80), frame, .006)
    for i in range(26):
        z = 2.063 + i * .062
        slat = box("Venetian blind slat", (center, 1.744, z), (.68, .105, .017), blind, .004)
        slat.rotation_euler = (math.radians(-23), 0, math.radians(14))
    for x in (center - .232, center + .242):
        box("Venetian blind ladder cord", (x, 1.689, 2.77), (.008, .005, 1.58), blind)
    area("Blue window spill", (-3.06, 1.55, 1.66), (-1.2, 1.05, .8),
         16, 1.0, (.19, .34, 1.0))


def foreground_plant(box, material):
    ceramic = material("Foreground | warm graphite planter", (.040, .036, .046), .73)
    soil = material("Foreground | dry planter soil", (.027, .015, .011), .97)
    foliage = [
        material("Foreground | olive leaf", (.032, .095, .010), .67),
        material("Foreground | deep green leaf", (.017, .057, .011), .66),
        material("Foreground | sage leaf", (.048, .110, .022), .65),
    ]
    center = Vector((-2.265, -1.03, 0))
    box("Foreground planter", center + Vector((0, 0, .245)), (.58, .44, .49), ceramic, .029)
    box("Planter rim", center + Vector((0, 0, .49)), (.588, .454, .027), ceramic, .014)
    box("Planter soil", center + Vector((0, 0, .504)), (.53, .38, .009), soil, .006)
    rng = random.Random(214)
    positions, faces, face_materials = [], [], []
    stems = bpy.data.curves.new("Planter stems and veins", "CURVE")
    stems.dimensions = "3D"
    stems.bevel_depth = .003
    stems.bevel_resolution = 1
    stems.materials.append(material("Foreground | olive stems", (.057, .082, .026), .63))

    def branch(start, middle, end):
        spline = stems.splines.new("BEZIER")
        spline.bezier_points.add(2)
        for point, coord in zip(spline.bezier_points, (start, middle, end)):
            point.co = coord
            point.handle_left_type = point.handle_right_type = "AUTO"
        spline.bezier_points[-1].radius = .40

    branch(center + Vector((0, 0, .514)), center + Vector((-.045, .012, .89)),
           center + Vector((.012, .05, 1.302)))
    for i in range(46):
        z = rng.uniform(.57, 1.302)
        outer = .27 - (z - .57) * .125
        base = center + Vector((rng.uniform(-outer, outer) + .057, rng.uniform(-.12, .16), z))
        angle = i * 2.40
        direction = Vector((math.cos(angle), math.sin(angle), rng.uniform(-.49, .18))).normalized()
        side = Vector((-direction.y, direction.x, .24)).normalized()
        length = rng.uniform(.18, .33)
        width = length * rng.uniform(.25, .36)
        trunk = center + Vector((-.02, .026, z - .10))
        branch(trunk, trunk.lerp(base, .55) + Vector((0, 0, .022)), base)
        index = len(positions)
        section_count = 16
        across = (-1, -.5, 0, .5, 1)
        for step in range(section_count + 1):
            section = step / section_count
            spread = .012 + .988 * math.sin(math.pi * section) ** .69
            mid = base + direction * (length * section)
            mid.z -= length * section**2 * .27
            for spread_ratio in across:
                point = mid + side * width * spread * spread_ratio
                point.z += width * spread * (.20 - .39 * spread_ratio**2)
                positions.append(point)
        for section in range(section_count):
            for j in range(4):
                a = index + section * len(across) + j
                b = a + len(across)
                faces.append((a, b, b + 1, a + 1))
        face_materials.extend([rng.randrange(len(foliage))] * (section_count * 4))
    mesh = bpy.data.meshes.new("Rounded foreground leaf mesh")
    mesh.from_pydata(positions, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Foreground olive plant", mesh)
    bpy.context.scene.collection.objects.link(obj)
    stem_object = bpy.data.objects.new("Foreground olive stems", stems)
    bpy.context.scene.collection.objects.link(stem_object)
    for mat in foliage:
        mesh.materials.append(mat)
    for polygon, index in zip(mesh.polygons, face_materials):
        polygon.material_index = index
        polygon.use_smooth = True


def build_concept_architecture(box, material, area, reference=None):
    """Build room surfaces around the established desk and library coordinates."""
    graphite = material("Architecture | dark graphite", (.026, .024, .035), .74)
    floor_subbase = material("Floor | shadow in plank seams", (.022, .009, .006), .85)
    floor = walnut_material(material)
    box("Floorboard subbase", (0, -1.18, -.043), (8.9, 10.2, .036), floor_subbase)
    rng = random.Random(217)
    y = -6.20
    while y < 3.81:
        width = min(rng.uniform(.173, .28), 3.81 - y)
        x = -4.45
        while x < 4.45:
            length = min(rng.uniform(1.42, 3.34), 4.45 - x)
            if length >= .006 and width >= .006:
                box("Walnut floor plank", (x + length / 2, y + width / 2, -.014),
                    (length - .0026, width - .0021, .028), floor, .0015)
            x += length
        y += width
    rug = box("Vintage woven area rug", (.284, .554, .006), (3.63, 2.31, .012),
              rug_material(material, reference), .004)
    rug.rotation_euler.z = math.radians(13)
    box("Back structure", (0, 3.02, 1.80), (8.55, .15, 3.61), graphite, .007)
    box("Ceiling", (0, -1.1, 3.53), (8.55, 8.4, .13), graphite, .012)
    box("Left room return", (-3.65, -1.31, 1.76), (.16, 8.8, 3.52), graphite, .006)
    box("Right room return", (3.79, -1.15, 1.76), (.16, 8.5, 3.52), graphite, .006)
    box("Rear oak skirting", (0, 2.907, .071), (7.41, .062, .142), floor, .007)
    fascia_mat = material("Architecture | deep warm violet fascia", (.056, .039, .052), .72)
    fascia = box("Ceiling fascia", (.36, 2.61, 3.33), (6.32, .29, .335), fascia_mat, .014)
    fascia.rotation_euler.y = math.radians(2.0)
    fascia_wash = area("Upper lintel violet bounce", (.18, 1.79, 3.38), (.18, 2.59, 3.32),
                       3.8, 3.0, (.76, .43, .58))
    fascia_wash.data.shape = "RECTANGLE"
    fascia_wash.data.size_y = .16
    fascia_wash.data.spread = math.radians(68)
    rim_mat = material("Architecture | upper slate-blue wall", (.030, .042, .093), .66)
    box("Dark blue wall above upper lintel", (.4, 2.428, 3.497),
        (6.05, .094, .12), rim_mat, .010)
    fabric = fabric_material(material)
    for panel in range(8):
        x = -1.25 + panel * .467
        box("Acoustic wall panel", (x + .225, 2.887, 1.855),
            (.455, .052, 1.81), fabric, .016)
    walnut_base = material("Shelf base | warm carbon stained wood", (.033, .021, .020), .57)
    for x0, x1 in [(-2.78, -1.23), (2.638, 3.38)]:
        box("Library lower cabinetry", ((x0 + x1)/2, 2.27, .483),
            (x1 - x0, .60, .966), walnut_base, .014)
        for n in range(3):
            width = (x1 - x0) / 3
            box("Stained shelf base panel", (x0 + width * (n + .5), 1.951, .493),
                (width - .013, .046, .887), walnut_base, .008)
    area("Warm right floor reflection", (2.12, 1.68, .62), (1.94, .44, .025),
         2.8, .68, (1, .44, .20))
    under_case = area("Small honey reflection beneath PC", (-2.14, .69, .25),
                      (-2.15, .65, .01), 2.3, .22, (1, .47, .18))
    under_case.data.spread = math.radians(69)
    area("Cool reading rug bounce", (1.54, -2.10, 1.36), (.51, .02, .03),
         5.2, 1.6, (.41, .52, 1))
    window_and_blinds(box, material, area)
    foreground_plant(box, material)
    leaf_glint = area("Soft light on olive leaf tips", (-2.71, -.47, 1.41),
                      (-2.18, -1.03, 1.02), 3.4, .6, (1, .80, .53))
    leaf_glint.data.spread = math.radians(74)
    upholstery = material("Foreground | muted plum-grey upholstery", (.092, .076, .096), .70)
    tree = upholstery.node_tree
    position = tree.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    threads = noise(tree, position, (130, 130, 163), detail=1)
    tree.links.new(color_ramp(tree, threads, [
        (.20, (.080, .065, .082)),
        (.80, (.104, .086, .101)),
    ]), tree.nodes["Principled BSDF"].inputs["Base Color"])
    bump(tree, tree.nodes["Principled BSDF"], threads, .13, .0014)
    bench = box("Near right upholstered bench", (1.983, -1.10, .477),
                (.70, .80, .954), upholstery, .029)
    bench.rotation_euler.z = math.radians(-18.4)
    upright = box("Near right upright silhouette", (2.203, -.831, 1.237),
                  (.155, .16, .563), upholstery, .020)
    upright.rotation_euler.z = bench.rotation_euler.z
    fabric_fill = area("Soft lilac reflection beside camera", (1.58, -2.39, 1.34),
                       (1.98, -1.46, .57), 1.55, 1.35, (.61, .56, 1))
    fabric_fill.data.spread = math.radians(64)
    edge_fill = area("Cool highlight on near bench edge", (1.89, -.69, 1.64),
                     (1.79, -1.25, .955), 2.3, .44, (.46, .48, 1))
    edge_fill.data.spread = math.radians(56)
    return rug
