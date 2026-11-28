"""The desk, chair and peripherals from the approved room concept."""

import math

import bpy
from mathutils import Vector


def grained_wood(material, name, low, high):
    """Give panels a warm, long-grain finish with visible pores and variation."""
    wood = material(name, high, .43)
    nodes, links = wood.node_tree.nodes, wood.node_tree.links
    shader = nodes.get("Principled BSDF")
    coord = nodes.new("ShaderNodeTexCoord")
    scale = nodes.new("ShaderNodeVectorMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = (.8, 30, 38)
    links.new(coord.outputs["Object"], scale.inputs[0])
    grain = nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 4
    grain.inputs["Detail"].default_value = 3.1
    grain.inputs["Roughness"].default_value = .72
    links.new(scale.outputs["Vector"], grain.inputs["Vector"])
    color = nodes.new("ShaderNodeValToRGB")
    color.color_ramp.elements[0].position = .18
    color.color_ramp.elements[0].color = (*low, 1)
    color.color_ramp.elements[1].position = .83
    color.color_ramp.elements[1].color = (*high, 1)
    links.new(grain.outputs["Fac"], color.inputs[0])
    links.new(color.outputs[0], shader.inputs["Base Color"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .18
    bump.inputs["Distance"].default_value = .015
    links.new(grain.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs[0], shader.inputs["Normal"])
    return wood


def surface_grain(mat, scale, strength, distance):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    tex = nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Roughness"].default_value = .63
    tex.inputs["Detail"].default_value = 2.0
    coords = nodes.new("ShaderNodeTexCoord")
    links.new(coords.outputs["Object"], tex.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs[0], nodes.get("Principled BSDF").inputs["Normal"])
    return mat


def cable(name, points, radius, mat):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 12
    data.bevel_depth = radius
    data.bevel_resolution = 3
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points)-1)
    for point, xyz in zip(spline.bezier_points, points):
        point.co = xyz
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    data.materials.append(mat)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _cylinder(name, position, radius, depth, mat, axis=(0,0,1)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, location=position)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = Vector(axis).to_track_quat("Z", "Y").to_euler()
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    obj.data.materials.append(mat)
    edge = obj.modifiers.new("Machined edge", "BEVEL")
    edge.width = min(.006, depth*.1)
    edge.segments = 2
    return obj


def _empty(name, position):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = position
    return obj


def _satin_metal(material, name, color, roughness=.33):
    mat = material(name, color, roughness)
    mat.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = .69
    return mat


def build_keyboard(box, material, location, width, name):
    """Return a moveable compact mechanical keyboard with individually modeled keys."""
    root = _empty(name, location)
    root["physical_width"] = width
    scale = width / .54

    def part(label, position, size, mat, bevel=.002):
        obj = box(f"{name} - {label}", tuple(v*scale for v in position),
                  tuple(v*scale for v in size), mat, bevel*scale)
        obj.parent = root
        return obj

    shell = material("Keyboard - graphite molded shell", (.019,.022,.028), .39)
    plate = _satin_metal(material, "Keyboard - brushed switch plate", (.031,.037,.058))
    cap = material("Keyboard - charcoal PBT", (.045,.046,.061), .53)
    pale = material("Keyboard - pale gray PBT", (.25,.24,.28), .57)
    legend = material("Keyboard - pale legend print", (.60,.61,.72), .46)
    colors = [
        (.06,.60,.66), (.18,.35,.85), (.46,.19,.85), (.74,.21,.69), (.86,.37,.16)
    ]
    rgb = [material(f"Keyboard - switch LED {i+1}", color, .32, 2.2) for i, color in enumerate(colors)]
    part("lower case", (0,0,.015), (.54,.193,.030), shell, .009)
    part("switch plate", (0,0,.031), (.523,.173,.010), plate, .006)
    part("illuminated front lip", (0,-.097,.022), (.495,.003,.0035), rgb[2], .001)
    key_rows = [
        [1]*13+[1.5],
        [1.35]+[1]*12+[1.15],
        [1.55]+[1]*11+[1.95],
        [1.75]+[1]*10+[1.75,1],
        [1.3,1.3,1.2,5.55,1.15,1,1,1,1],
    ]
    pitch = .0355
    for row, widths in enumerate(key_rows):
        x = -sum(widths)*pitch/2
        for i, units in enumerate(widths):
            key_width = units*pitch - .0046
            cx, cy = x+units*pitch/2, .065-row*.0325
            x += units*pitch
            hue = min(4, max(0, int((cx+.265)/.106)))
            part("switch housing", (cx,cy,.036), (key_width*.72,.022,.006), rgb[hue], .001)
            part(f"key {row+1}/{i+1}", (cx,cy,.044), (key_width,.0275,.012),
                 pale if units == 1 and row in (0,1) else cap, .0038)
            if units < 2.5:
                part("key legend", (cx-.003,cy+.0045,.0503), (.007,.0023,.0006), legend, .0004)
    return root


def build_concept_furniture(box, material, area):
    """Build the working desk and chair at the reference scene's scale."""
    wood = grained_wood(material, "Desk - warm walnut grain", (.027,.010,.007), (.33,.138,.060))
    wood.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .37
    cabinet = grained_wood(material, "Desk - dark walnut cabinet", (.005,.004,.006), (.032,.023,.026))
    drawer = grained_wood(material, "Desk - walnut drawer fronts", (.010,.005,.006), (.162,.080,.043))
    drawer_nodes = drawer.node_tree.nodes
    drawer_scale = next(node for node in drawer_nodes if node.type == "VECT_MATH")
    drawer_scale.inputs[1].default_value = (12,24,1.25)
    drawer_nodes["Principled BSDF"].inputs["Roughness"].default_value = .48
    metal = _satin_metal(material, "Desk - brushed muted brass hardware", (.40,.20,.06))
    black = material("Desk - graphite accessories", (.014,.016,.025), .44)
    violet = material("Desk - violet mat edge", (.19,.060,.12), .64)
    mat = surface_grain(material("Desk - woven black mat", (.021,.020,.042), .82), 280, .23, .002)
    warm = material("Desk - recessed amber strip", (1,.38,.10), .5, 3)

    box("Desk - walnut worktop", (.705,2.39,.949), (3.85,.98,.092), wood, .028)
    box("Desk - front edge rail", (.705,1.954,.882), (3.73,.09,.084), wood, .012)
    box("Desk - shadowed back panel", (.6,2.81,.449), (3.63,.076,.876), cabinet, .006)
    box("Desk - left side panel", (-1.14,2.45,.442), (.108,.79,.884), cabinet, .011)
    box("Desk - drawer case", (2.163,2.408,.443), (.691,.86,.884), cabinet, .011)
    box("Desk - drawer plinth", (2.163,2.386,.049), (.641,.79,.098), black, .008)
    for i, z in enumerate((.229,.474,.717), 1):
        box(f"Desk - walnut drawer {i}", (2.163,1.957,z), (.637,.055,.229), drawer, .013)
        for x in (2.047,2.279):
            box(f"Desk - brass handle posts {i}", (x,1.920,z+.054), (.023,.027,.023), metal, .004)
        box(f"Desk - brass pull {i}", (2.163,1.901,z+.054), (.254,.017,.023), metal, .006)

    box("Desk - amber lamp diffuser", (.32,1.993,.856), (2.67,.013,.009), warm, .003)
    area("Desk - under edge reflected amber", (.22,2.08,.840), (.225,2.48,.805), 16, .8, (1,.43,.20))
    area("Desk - reflected drawer amber", (2.19,1.872,.869), (2.19,1.94,.386), 5, .45, (1,.44,.18))
    box("Desk - mat stitched perimeter", (.58,2.16,1.002), (2.19,.477,.013), violet, .018)
    box("Desk - woven mat surface", (.58,2.16,1.009), (2.146,.444,.008), mat, .014)
    keyboard = build_keyboard(box, material, (-.165,2.105,1.037), .57, "Desk RGB keyboard")
    keyboard.rotation_euler = (.207,0,.053)
    for x in (-.37,.060):
        box("Desk - raised keyboard rear foot", (x,2.174,1.031), (.034,.032,.038), black, .003)
    cable("Desk - keyboard lead", [(-.165,2.205,1.070),(-.165,2.275,1.025),
                                   (-.30,2.45,1.015),(-.28,2.79,1.012)], .004, black)
    mouse_shell = _satin_metal(material, "Desk - satin gray mouse shell", (.094,.088,.120), .29)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=12, location=(1.332,2.105,1.041))
    mouse = bpy.context.object
    mouse.name = "Desk - low-profile graphite mouse"
    mouse.scale = (.065,.098,.027)
    mouse.data.materials.append(mouse_shell)
    for face in mouse.data.polygons:
        face.use_smooth = True
    box("Desk - mouse scroll wheel", (1.332,2.135,1.066), (.023,.023,.009), black, .005)

    # Left drink can with a readable foil top and diagonal band.
    can = _satin_metal(material, "Desk - midnight soda can", (.035,.060,.086), .37)
    aluminum = _satin_metal(material, "Desk - brushed aluminum", (.39,.42,.45), .34)
    _cylinder("Desk - beverage can", (-1.04,2.099,1.187), .075,.384,can)
    _cylinder("Desk - soda can lower rim", (-1.04,2.099,1.003), .075,.012,aluminum)
    _cylinder("Desk - soda can lid", (-1.04,2.099,1.379), .074,.015,aluminum)
    box("Desk - can pull tab", (-1.038,2.108,1.389), (.024,.045,.008), aluminum, .006)
    stripe = material("Desk - drink can diagonal stripe", (.45,.24,.22), .47)
    band_vertices, band_faces = [], []
    for i in range(49):
        t=2*math.pi*i/48
        z=1.19+.072*math.sin(t-.29)
        x,y=-1.04+.0756*math.cos(t),2.099+.0756*math.sin(t)
        band_vertices.extend(((x,y,z-.031),(x,y,z+.031)))
        if i:
            a=2*i
            band_faces.append((a-2,a,a+1,a-1))
    band_mesh=bpy.data.meshes.new("Desk - can diagonal band mesh")
    band_mesh.from_pydata(band_vertices,[],band_faces)
    band_mesh.update()
    band=bpy.data.objects.new("Desk - wrapped drink can stripe",band_mesh)
    bpy.context.scene.collection.objects.link(band)
    band_mesh.materials.append(stripe)

    # Headphones hanging from the stand at the right side of the workstation.
    rubber = material("Headphones - soft black ear cushions", (.022,.018,.028), .73)
    ring = material("Headphones - thin mint accent", (.14,.72,.54), .45, .55)
    xp, yp = 2.12, 2.28
    _cylinder("Desk - headphone stand base", (xp,yp,1.014), .111,.036, black)
    _cylinder("Desk - headphone stand post", (xp,yp+.036,1.194), .016,.346,metal)
    box("Desk - headband rest", (xp,yp+.014,1.367), (.101,.107,.026), black,.012)
    for dx in (-.033,.033):
        points = [(xp+.125*math.cos(t),yp+dx,1.212+.152*math.sin(t))
                  for t in (0,.30,.65,1,1.35,1.7,2.05,2.4,2.75,math.pi)]
        cable("Desk - sculpted headphone headband", points, .020, black)
    for s in (-1,1):
        x = xp + s*.113
        _cylinder("Desk - headphone ear cushion", (x-s*.015,yp,1.174), .066,.037,rubber,(1,0,0))
        _cylinder("Desk - headphone ear shell", (x,yp,1.174), .069,.038,black,(1,0,0))
        _cylinder("Desk - headphone thin accent ring", (x+s*.020,yp,1.174), .060,.006,ring,(1,0,0))
        _cylinder("Desk - headphone inset face", (x+s*.024,yp,1.174), .054,.006,black,(1,0,0))

    chair = _empty("Chair - ergonomic office chair", (.59,.95,0))
    chair.rotation_euler.z = .17
    cloth = surface_grain(material("Chair - charcoal grain upholstery", (.021,.017,.027), .62), 148, .35,.008)
    nodes, links = cloth.node_tree.nodes, cloth.node_tree.links
    grain = next(node for node in nodes if node.type == "TEX_NOISE")
    grain_tone = nodes.new("ShaderNodeValToRGB")
    grain_tone.color_ramp.elements[0].position = .19
    grain_tone.color_ramp.elements[0].color = (.010,.008,.015,1)
    grain_tone.color_ramp.elements[1].position = .81
    grain_tone.color_ramp.elements[1].color = (.038,.032,.047,1)
    links.new(grain.outputs["Fac"], grain_tone.inputs[0])
    links.new(grain_tone.outputs[0], nodes.get("Principled BSDF").inputs["Base Color"])
    trim = material("Chair - deep burgundy piping", (.105,.035,.045), .45)
    edge_trim = material("Chair - thin sunlit burgundy welt", (.154,.068,.079), .40, .13)
    graphite = _satin_metal(material, "Chair - graphite support hardware", (.050,.026,.031), .37)
    rubber = material("Chair - caster rubber", (.009,.009,.012), .61)

    def chair_part(name, pos, size, mat, bevel):
        obj = box("Chair - "+name,pos,size,mat,bevel)
        obj.parent = chair
        if obj.modifiers:
            obj.modifiers[0].segments = 5
        return obj

    chair_part("seat pan", (-.023,0,.546), (.73,.635,.107), graphite,.049)
    chair_part("padded seat", (-.023,.017,.612), (.76,.66,.132), cloth,.061)
    chair_part("seat piping", (-.023,-.295,.606), (.70,.028,.024), trim,.011)
    # The chair reference shows the flank of its beltline where the arm joins the pan.
    side = chair_part("left seat wing", (-.376,-.165,.559), (.231,.39,.147),graphite,.046)
    side.rotation_euler.y = -.17
    side = chair_part("left seat wing padded crest", (-.383,-.182,.615), (.220,.358,.044),trim,.020)
    side.rotation_euler.y = -.17

    def back_pad(name, width, height, depth, y, mat, bevel):
        # Broad shoulders and a narrower waist follow the tapered back in the concept.
        outline = [(-.37,-.5),(.37,-.5),(.46,-.43),(.49,.34),(.44,.47),(.32,.5),
                   (-.32,.5),(-.44,.47),(-.49,.34),(-.46,-.43)]
        verts = [(x*width, d*depth/2, z*height) for d in (-1,1) for x,z in outline]
        n = len(outline)
        faces = [tuple(range(n)), tuple(reversed(range(n,n*2)))]
        faces += [(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts,[],faces)
        mesh.update()
        obj = bpy.data.objects.new("Chair - "+name,mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = chair
        obj.location = (0,y,1.012)
        obj.rotation_euler = (.133,.087,0)
        obj.data.materials.append(mat)
        mod = obj.modifiers.new("Curved upholstered edges","BEVEL")
        mod.width, mod.segments = bevel,5
        return obj

    back_pad("tapered back frame", .745, .918, .169, -.30, graphite, .057)
    back_pad("sculpted dark leather pad", .626, .857, .132, -.373, cloth, .056)
    crown = chair_part("top burgundy piping", (.028,-.432,1.445), (.43,.020,.017), trim,.007)
    crown.rotation_euler.y = .066
    for s in (-1,1):
        obj=chair_part("side bolster", (s*.316,-.343,1.026), (.104,.14,.822),cloth,.047)
        obj.rotation_euler.x=.129
        obj.rotation_euler.y=.087+s*.057
        obj=chair_part("burgundy side seam", (s*.361,-.373,1.022), (.013,.021,.757),edge_trim,.006)
        obj.rotation_euler.x=.129
        obj.rotation_euler.y=.087+s*.057
        x = -.505 if s == -1 else .438
        width, length = (.192,.426) if s == -1 else (.153,.373)
        arm_post = chair_part("arm rest support", (x-s*.058,.027,.686), (.079,.108,.306),graphite,.019)
        arm_post.rotation_euler.y = s*.074
        arm_top = chair_part("padded arm rest", (x,.029,.850), (width,length,.066),cloth,.031)
        arm_top.rotation_euler.z = s*.045
        piping = chair_part("arm rest piping", (x,.029,.827), (width-.009,length-.022,.015),trim,.007)
        piping.rotation_euler.z = arm_top.rotation_euler.z
    badge = chair_part("rear fabric badge", (.040,-.443,.910), (.302,.024,.039),trim,.007)
    badge.rotation_euler.y = -.03
    for label,z,radius,height in [
        ("gas lift sleeve", .284,.073,.338),
        ("gas lift piston", .463,.038,.130),
        ("spider hub", .125,.111,.078),
    ]:
        obj=_cylinder("Chair - "+label,(-.018,0,z),radius,height,black if label=="gas lift sleeve" else graphite)
        obj.parent=chair
    for i in range(5):
        angle = -math.pi/2 + i*math.tau/5 - .115
        ux, uy = math.cos(angle), math.sin(angle)
        arm = chair_part("tapered spider leg", (-.018+.226*ux,.226*uy,.131), (.48,.085,.068), graphite,.019)
        arm.rotation_euler.z=angle
        chair_part("caster yoke", (-.018+.449*ux,.449*uy,.096), (.066,.072,.065), black,.016)
        for s in (-1,1):
            obj=_cylinder("Chair - caster wheel", (-.018+.449*ux-s*.028*uy,.449*uy+s*.028*ux,.061), .050,.029,rubber,(-uy,ux,0))
            obj.parent=chair
            pin=_cylinder("Chair - caster axle cap", (-.018+.449*ux-s*.045*uy,.449*uy+s*.045*ux,.061), .018,.006,graphite,(-uy,ux,0))
            pin.parent=chair
    chair_lighting = bpy.data.collections.new("Chair - warm upholstery light receivers")
    bpy.context.scene.collection.children.link(chair_lighting)
    for obj in chair.children:
        chair_lighting.objects.link(obj)
    rim = area("Chair - warm ruby rim", (-.47,.29,1.31), (.36,.57,1.06), 13, .55, (1,.46,.37))
    rim.light_linking.receiver_collection = chair_lighting
    rim = area("Chair - warm caster rim", (.46,1.74,.46), (.59,.94,.13), 7, .60, (1,.47,.27))
    rim.light_linking.receiver_collection = chair_lighting
    return {"chair": chair, "desk_keyboard": keyboard}
