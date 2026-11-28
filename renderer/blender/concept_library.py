"""Editable wood shelves, lighted brick recesses and library props."""

import math
import random
from array import array
from pathlib import Path

import bpy
from mathutils import Vector


def textured_surface(material, name, color, stretch, roughness, relief, scale=4):
    surface = material(name, color, roughness)
    nodes = surface.node_tree.nodes
    links = surface.node_tree.links
    shader = nodes.get("Principled BSDF")
    coords = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeVectorMath")
    mapping.operation = "MULTIPLY"
    mapping.inputs[1].default_value = stretch
    links.new(coords.outputs["Generated"], mapping.inputs[0])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 4.1
    noise.inputs["Roughness"].default_value = .73
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    colors = nodes.new("ShaderNodeValToRGB")
    for element, position, factor in zip(colors.color_ramp.elements, (.22, .80), (.58, 1.40)):
        element.position = position
        element.color = (*[min(1, channel * factor) for channel in color], 1)
    links.new(noise.outputs["Fac"], colors.inputs[0])
    links.new(colors.outputs[0], shader.inputs["Base Color"])
    pores = nodes.new("ShaderNodeBump")
    pores.inputs["Strength"].default_value = .28
    pores.inputs["Distance"].default_value = relief
    links.new(noise.outputs["Fac"], pores.inputs["Height"])
    links.new(pores.outputs["Normal"], shader.inputs["Normal"])
    return surface


def walnut_face_swatch(reference):
    """Rectify a narrow wood-only sample, then normalize its grain as a relief map."""
    if reference is None or not Path(reference).is_file():
        return None
    photo = bpy.data.images.load(str(Path(reference).resolve()), check_existing=False)
    try:
        width, height = photo.size
        count = photo.channels
        source = array("f", [0]) * (width * height * count)
        photo.pixels.foreach_get(source)
        values = []
        for row in range(16):
            v = row / 15
            for col in range(376):
                u = col / 375
                x = round((165 + u*361) / 1671 * (width-1))
                top, bottom = 523-6*u, 534-7*u
                y = round((1-(bottom+(top-bottom)*v)/941) * (height-1))
                i = (y*width+x)*count
                values.append(.21*source[i] + .72*source[i+1] + .07*source[i+2])
    finally:
        bpy.data.images.remove(photo)
    ordered = sorted(values)
    lo = ordered[len(values)//16]
    hi = ordered[len(values)*15//16]
    pixels = []
    for value in values:
        t = min(1,max(0,(value-lo)/max(hi-lo,.025)))
        pixels.extend((t,t,t,1))
    grain = bpy.data.images.new("Walnut face detail | isolated grain sample", width=376, height=16)
    grain.colorspace_settings.name = "Non-Color"
    grain.pixels.foreach_set(pixels)
    grain.update()
    grain.pack()
    return grain


def binding_swatches(reference, material):
    """Sample only isolated book faces for their print, wear and paper pigments."""
    if reference is None or not Path(reference).is_file():
        return []
    crops = [
        ("Faded russet suede", (208,106,222,207)),
        ("Clothbound tan", (228,130,245,208)),
        ("Navy floral tooling", (254,136,269,209)),
        ("Gilt brown tooling", (280,116,293,208)),
        ("Blue volume, dark type", (302,145,317,209)),
        ("Dark red volume", (342,129,352,209)),
        ("Cream title label", (359,144,369,209)),
    ]
    photo = bpy.data.images.load(str(Path(reference).resolve()), check_existing=False)
    try:
        width, height = photo.size
        channels = photo.channels
        source = array("f", [0]) * (width * height * channels)
        photo.pixels.foreach_get(source)
        bindings = []
        for name,(left,top,right,bottom) in crops:
            out_w, out_h = 24, 126
            pixels = array("f")
            for row in range(out_h):
                y = round((1-(bottom-(bottom-top)*row/(out_h-1))/941)*(height-1))
                for col in range(out_w):
                    x = round((left+(right-left)*col/(out_w-1))/1671*(width-1))
                    i = (y*width+x)*channels
                    pixels.extend([min(.85,1.65*max(0,source[i+j])**2.15) for j in range(3)]+[1])
            image = bpy.data.images.new(name+" · isolated binding detail", width=out_w, height=out_h)
            image.colorspace_settings.name = "Non-Color"
            image.pixels.foreach_set(pixels)
            image.update()
            image.pack()
            finish = material("Library · " + name, (.10,.046,.021), .83)
            tree = finish.node_tree
            xyz = tree.nodes.new("ShaderNodeSeparateXYZ")
            uv = tree.nodes.new("ShaderNodeCombineXYZ")
            coords = tree.nodes.new("ShaderNodeTexCoord")
            tree.links.new(coords.outputs["Generated"],xyz.inputs[0])
            tree.links.new(xyz.outputs["X"],uv.inputs["X"])
            tree.links.new(xyz.outputs["Z"],uv.inputs["Y"])
            pattern = tree.nodes.new("ShaderNodeTexImage")
            pattern.image = image
            tree.links.new(uv.outputs[0],pattern.inputs["Vector"])
            tree.links.new(pattern.outputs["Color"],tree.nodes["Principled BSDF"].inputs["Base Color"])
            bindings.append(finish)
        return bindings
    finally:
        bpy.data.images.remove(photo)


def build_concept_library(box, material, area, reference=None):
    rng = random.Random(41332)
    scene = bpy.context.scene
    timber = textured_surface(material, "Library · worn walnut grain", (.204, .083, .034), (1.6, 38, 12), .67, .014)
    timber_nodes, timber_links = timber.node_tree.nodes, timber.node_tree.links
    timber_shader = timber_nodes.get("Principled BSDF")
    grain_colors = timber_shader.inputs["Base Color"].links[0].from_node
    grain_colors.color_ramp.elements[0].position = .36
    grain_colors.color_ramp.elements[0].color = (.033,.010,.004,1)
    grain_colors.color_ramp.elements[1].position = .77
    grain_colors.color_ramp.elements[1].color = (.34,.162,.073,1)
    figure = timber_nodes.new("ShaderNodeTexWave")
    figure.wave_type = "BANDS"
    figure.bands_direction = "Z"
    figure.inputs["Scale"].default_value = 3.8
    figure.inputs["Distortion"].default_value = 19
    figure.inputs["Detail Scale"].default_value = 2.3
    figure.inputs["Detail"].default_value = 7
    timber_links.new(timber_nodes.get("Texture Coordinate").outputs["Generated"], figure.inputs["Vector"])
    grain = timber_nodes.new("ShaderNodeMixRGB")
    grain.blend_type = "MULTIPLY"
    grain.inputs[0].default_value = .62
    timber_links.new(grain_colors.outputs["Color"], grain.inputs[1])
    timber_links.new(figure.outputs["Color"], grain.inputs[2])
    timber_links.new(grain.outputs[0], timber_shader.inputs["Base Color"])
    swatch = walnut_face_swatch(reference)
    lip = timber
    if swatch:
        lip = timber.copy()
        lip.name = "Library · distressed walnut front face"
        nodes, links = lip.node_tree.nodes, lip.node_tree.links
        shader = nodes.get("Principled BSDF")
        xyz = nodes.new("ShaderNodeSeparateXYZ")
        uv = nodes.new("ShaderNodeCombineXYZ")
        links.new(nodes["Texture Coordinate"].outputs["Generated"],xyz.inputs[0])
        links.new(xyz.outputs["X"],uv.inputs["X"])
        links.new(xyz.outputs["Z"],uv.inputs["Y"])
        photo_grain = nodes.new("ShaderNodeTexImage")
        photo_grain.image = swatch
        photo_grain.extension = "EXTEND"
        links.new(uv.outputs[0],photo_grain.inputs[0])
        stain = nodes.new("ShaderNodeValToRGB")
        stain.color_ramp.elements[0].color = (.070,.028,.010,1)
        stain.color_ramp.elements[1].color = (.228,.094,.034,1)
        links.new(photo_grain.outputs["Color"],stain.inputs[0])
        fiber = nodes.new("ShaderNodeTexNoise")
        bands = nodes.new("ShaderNodeVectorMath")
        bands.operation = "MULTIPLY"
        bands.inputs[1].default_value = (2.3,15,61)
        links.new(nodes["Texture Coordinate"].outputs["Generated"],bands.inputs[0])
        links.new(bands.outputs[0],fiber.inputs["Vector"])
        fiber.inputs["Scale"].default_value = 6
        fiber.inputs["Detail"].default_value = 2.8
        fiber_mix = nodes.new("ShaderNodeMixRGB")
        fiber_mix.blend_type = "MULTIPLY"
        fiber_mix.inputs[0].default_value = .24
        links.new(stain.outputs["Color"],fiber_mix.inputs[1])
        links.new(fiber.outputs["Color"],fiber_mix.inputs[2])
        pitted = nodes.new("ShaderNodeBump")
        pitted.inputs["Strength"].default_value = .20
        pitted.inputs["Distance"].default_value = .0031
        links.new(photo_grain.outputs["Color"],pitted.inputs["Height"])
        links.new(nodes["Bump"].outputs["Normal"],pitted.inputs["Normal"])
        links.new(pitted.outputs["Normal"],shader.inputs["Normal"])
        links.new(fiber_mix.outputs[0],shader.inputs["Base Color"])
    casing = textured_surface(material, "Library · stained oak frame", (.069, .026, .014), (2.8, 27, 1.8), .56, .009)
    mortar = textured_surface(material, "Library · irregular dark sand mortar", (.115, .066, .044), (2, 2, 4), .95, .006, 29)
    bricks = [
        textured_surface(material, f"Library · kiln brick {i+1}", rgb, (1.8, .7, .9), .89, .008, 17)
        for i, rgb in enumerate(((.219,.060,.036), (.293,.082,.047), (.232,.080,.064),
                                  (.275,.107,.071), (.200,.065,.053), (.253,.076,.054)))
    ]
    for masonry in bricks:
        nodes = masonry.node_tree.nodes
        ramp = nodes.get("Color Ramp").color_ramp
        ramp.elements[0].position = .319
        ramp.elements[1].position = .688
        for element in ramp.elements:
            color = element.color[:3]
            element.color = (*[channel * .74 for channel in color], 1)
        nodes["Bump"].inputs["Strength"].default_value = .47
    pages = textured_surface(material, "Library · aged laid paper", (.58,.44,.292), (3,4,29), .91, .002, 9)
    steel = material("Library · blackened steel", (.014,.016,.022), .39)
    brass = material("Library · antique brass", (.37,.198,.061), .33)
    brass.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = .64
    gold = textured_surface(material, "Library · rubbed gilt stamping", (.30,.176,.073), (8,4,9), .67, .001, 22)
    dark_ink = material("Library · dark book ink", (.020,.011,.007), .76)
    warm_strip = material("Library · warm linear shelf light", (1,.64,.32), .44, 8)
    lantern_glass = material("Library · frosted lantern", (1,.58,.245), .52, .85)
    covers = [
        textured_surface(material, f"Library · book cloth {name}", rgb, (3,3,10), .74, .002, 22)
        for name,rgb in (
            ("walnut",(.090,.040,.018)), ("oat",(.286,.205,.125)), ("linen",(.315,.233,.152)),
            ("oxblood",(.104,.016,.014)), ("plum",(.087,.017,.029)), ("ink blue",(.028,.034,.052)),
            ("slate",(.071,.071,.079)), ("olive",(.062,.076,.032)), ("sienna",(.184,.048,.019)),
        )
    ]
    bindings = binding_swatches(reference, material)
    for cover in covers:
        tree = cover.node_tree
        shader = tree.nodes["Principled BSDF"]
        cloth_ramp = shader.inputs["Base Color"].links[0].from_node
        coarse_wear = tree.nodes.new("ShaderNodeTexNoise")
        coarse_wear.inputs["Scale"].default_value = 7.4
        coarse_wear.inputs["Detail"].default_value = 4
        tree.links.new(tree.nodes["Texture Coordinate"].outputs["Generated"],coarse_wear.inputs["Vector"])
        dust = tree.nodes.new("ShaderNodeValToRGB")
        dust.color_ramp.elements[0].position = .38
        dust.color_ramp.elements[0].color = (.49,.48,.44,1)
        dust.color_ramp.elements[1].position = .72
        dust.color_ramp.elements[1].color = (.98,.93,.85,1)
        tree.links.new(coarse_wear.outputs["Fac"],dust.inputs[0])
        cloth = tree.nodes.new("ShaderNodeMixRGB")
        cloth.blend_type = "MULTIPLY"
        cloth.inputs[0].default_value = .52
        tree.links.new(cloth_ramp.outputs["Color"],cloth.inputs[1])
        tree.links.new(dust.outputs["Color"],cloth.inputs[2])
        tree.links.new(cloth.outputs["Color"],shader.inputs["Base Color"])
    labels = ("ATLAS", "THE STARS", "LETTERS", "BIRDS", "HERBARIUM", "WALKS", "TALES", "MOUNTAINS")
    storage = textured_surface(material, "Library · charcoal canvas storage", (.045,.034,.050), (3,4,5), .91, .004, 29)
    foliage = [
        textured_surface(material, f"Library · waxed heart leaf {i+1}", rgb, (2,2,1), .57, .001, 5)
        for i,rgb in enumerate(((.048,.107,.028),(.11,.16,.034),(.174,.186,.035),(.091,.137,.027)))
    ]
    stem_mat = material("Library · olive stems", (.086,.117,.021), .75)
    roots = []

    def root_object(name):
        obj = bpy.data.objects.new(name, None)
        scene.collection.objects.link(obj)
        roots.append(obj)
        return obj

    def part(root, name, pos, dim, surface, bevel=.003):
        obj = box(name, pos, dim, surface, bevel)
        obj.parent = root
        return obj

    def shelf_plank(root, name, pos, dim):
        plank = part(root,name,pos,dim,timber,.006)
        if lip != timber:
            plank.data.materials.append(lip)
            for face in plank.data.polygons:
                if face.normal.y < -.9:
                    face.material_index = 1
        return plank

    def tube(root, name, points, radius, surface, closed=False):
        curve = bpy.data.curves.new(name, "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth, curve.bevel_resolution = radius, 2
        spline = curve.splines.new("POLY")
        spline.points.add(len(points)-1)
        for point, coord in zip(spline.points, points):
            point.co = (*coord, 1)
        spline.use_cyclic_u = closed
        curve.materials.append(surface)
        obj = bpy.data.objects.new(name, curve)
        scene.collection.objects.link(obj)
        obj.parent = root
        return obj

    def beam(root, name, start, end, width, surface):
        delta = Vector(end) - Vector(start)
        obj = part(root, name, (Vector(start)+Vector(end))/2, (width,width,delta.length), surface, .002)
        obj.rotation_euler = delta.to_track_quat("Z","Y").to_euler()
        return obj

    def book(root, x, y, base, width, height, depth, cover, tilt=0, flat=False, print_title=False, binding=None):
        name = "Stacked volume" if flat else "Leather-bound volume"
        spine = bpy.data.objects.new(name, None)
        scene.collection.objects.link(spine)
        spine.parent = root
        angle = math.pi/2 if flat else math.radians(tilt)
        vertical = abs(height*math.cos(angle)) + abs(width*math.sin(angle))
        spine.location = (x,y,base+vertical/2)
        spine.rotation_euler.y = angle
        spine["orientation"] = "flat" if flat else "leaning" if tilt else "upright"
        part(spine, "Paper signatures", (0,.007,0), (width-.009,depth-.013,height-.014), pages, .002)
        for direction in [-1,1]:
            part(spine, "Cover board", (direction*(width/2-.002),0,0), (.004,depth,height), cover, .002)
        front = -depth/2-.003
        part(spine, "Rounded book spine", (0,front,0), (width,.013,height), binding or cover, .004)
        if binding:
            return vertical
        stamping = dark_ink if cover in covers[1:3] else gold
        face_y = front-.007
        for mark,z in enumerate((-height*.39,-height*.31,height*.31,height*.39)):
            if (int(width*1000)+mark)%9:
                part(spine, "Gilt raised band", (0,face_y,z), (width*(.70+.05*(mark%3)),.0024,.0033), stamping, .0005)
        if width > .063:
            for dx in [-width*.34,width*.34]:
                part(spine, "Fine spine border", (dx,face_y,0), (.0017,.0023,height*.72), stamping, .0003)
        for j in range(3):
            part(spine, "Embossed spine ornament", (0,face_y,-height*.18+j*.012),
                 (width*(.45-.07*abs(1-j)),.0025,.0028), stamping, .0005)
        if width > .064:
            diamond = part(spine, "Debossed gilt medallion", (0,face_y,-height*.25), (.014,.0026,.014), stamping, .001)
            diamond.rotation_euler.y = math.pi/4
            for dx in [-width*.25,width*.25]:
                part(spine, "Worn gilt border pip", (dx,face_y,height*.26), (.003,.0025,.003), stamping, .0005)
            for row in range(3):
                line_z = height*(.15 + row*.022)
                for j in range(4):
                    if (row+j)%4 != 0:
                        part(spine, "Rubbed print fragment", ((j-1.5)*width*.12,face_y,line_z),
                             (.0036,.0028,.0029), stamping, .0005)
        if print_title:
            title = bpy.data.curves.new("Spine title", "FONT")
            title.body = rng.choice(labels)
            title.size = height*.054
            title.align_x = "CENTER"
            title.align_y = "CENTER"
            title.materials.append(stamping)
            obj = bpy.data.objects.new(title.body, title)
            scene.collection.objects.link(obj)
            obj.parent = spine
            obj.location = (0,face_y-.001,.025)
            obj.rotation_euler = (math.pi/2,-math.pi/2,0)
        return vertical

    def book_row(root, start,end,y,z, stagger=True, palette=None, binding_order=()):
        cursor = start
        index = 0
        while cursor+.055 < end:
            width = rng.uniform(.052,.100)
            height = rng.uniform(.315,.46)
            tilt = rng.choice((-10,-6,6,10)) if stagger and index in (6,10) else 0
            angle = math.radians(tilt)
            footprint = width*math.cos(angle)+height*abs(math.sin(angle))
            if cursor+footprint > end:
                break
            y_offset, depth = rng.uniform(-.026,.042), rng.uniform(.23,.30)
            cover = rng.choice(covers)
            if palette:
                cover = covers[palette[index % len(palette)]]
            binding = None
            if bindings and binding_order:
                idx = binding_order[index % len(binding_order)]
                binding = bindings[idx] if idx is not None else None
            book(root,cursor+footprint/2,y+y_offset,z,width,height,depth,cover,tilt,
                 print_title=width>.073,binding=binding)
            cursor += footprint + rng.uniform(.001,.010)
            index += 1

    def stack(root, x,y,z,count=3):
        for j in range(count):
            z += book(root,x+rng.uniform(-.015,.015),y+rng.uniform(0,.017),z,
                      rng.uniform(.038,.061),rng.uniform(.31,.42),rng.uniform(.26,.32),
                      rng.choice(covers),flat=True,print_title=True) + .002
        return z

    def light_strip(root, left, right, front, z):
        x = (left+right)/2
        width = right-left-.078
        part(root,"Concealed warm light strip",(x,front+.031,z-.070),(width,.012,.007),warm_strip,.002)
        light = area("Warm linear library bounce", (x,front+.073,z-.090),
                     (x,front+.56,z-.40), 8.8*width, width, (1,.58,.30))
        light.parent = root
        light.data.shape = "RECTANGLE"
        light.data.size = width
        light.data.size_y = .030

    def shelf_bank(root, left, right, front, levels):
        back = 2.65
        x = (left+right)/2
        width = right-left
        low, high = levels[0]-.10, 3.55
        part(root,"Recess mortar back",(x,back+.018,(low+high)/2),(width,.07,high-low),mortar)
        rows = math.ceil((high-low)/.109)
        for row in range(rows):
            z = low+.055+row*.109
            offset = .151 if row%2 else 0
            for col in range(-1,math.ceil(width/.302)+1):
                a = max(left,left+col*.302+offset)
                b = min(right,left+col*.302+offset+.290)
                if b-a > .028:
                    part(root,"Uneven bonded terracotta brick",
                         ((a+b)/2,back-.032+rng.uniform(-.009,.009),z+rng.uniform(-.002,.002)),
                         (b-a,.049,rng.uniform(.093,.101)),rng.choice(bricks),.007)
        for edge in (left-.029,right+.027):
            part(root,"Stained side stile",(edge,(front+back)/2,1.77),(.057,back-front+.03,3.54),casing,.008)
        for i,z in enumerate(levels):
            shelf_plank(root,"Wide weathered walnut plank",(x,(front+back)/2,z-.035),
                        (width+.046,back-front,.070))
            if i:
                light_strip(root,left,right,front,z)
            for bracket_x in (left+.16,right-.153):
                beam(root,"Forged diagonal shelf bracket",(bracket_x,back-.10,z-.38),
                     (bracket_x,front+.14,z-.077),.020,steel)
                beam(root,"Forged wall plate",(bracket_x,back-.075,z-.38),
                     (bracket_x,back-.075,z-.082),.032,steel)
                beam(root,"Forged horizontal bracket",(bracket_x,front+.14,z-.11),
                     (bracket_x,back-.07,z-.11),.021,steel)

    def vine(root, x, y, z, length, drift, size=1, sidearm=.031):
        n = max(4,int(length/.106))
        points = [(x+drift*t+.037*math.sin(t*11),y-.04*t,z-length*t) for t in (i/n for i in range(n+1))]
        tube(root,"Trailing ivy stem",points,.0034,stem_mat)
        for i,(px,py,pz) in enumerate(points):
            side = -1 if i%2 else 1
            leaf_length = size*rng.uniform(.096,.143)
            leaf_width = leaf_length*rng.uniform(.56,.85)
            endpoint = (px+sidearm*side,py-.016,pz-.012)
            tube(root,"Leaf petiole",[(px,py,pz),endpoint],.0018,stem_mat)
            outline = [(0,0),(-.27,.12),(-.5,-.11),(-.44,-.36),(-.25,-.67),(0,-1),
                       (.25,-.67),(.44,-.36),(.5,-.11),(.27,.12)]
            vertices = [(leaf_width*a,abs(a)*.017,leaf_length*b) for a,b in outline]
            vertices.append((0,-.019,-leaf_length*.35))
            faces = [(10,(j+1)%10,j) for j in range(10)]
            mesh = bpy.data.meshes.new("Heart leaf")
            mesh.from_pydata(vertices,[],faces)
            mesh.update()
            for face in mesh.polygons:
                face.use_smooth = True
            leaf = bpy.data.objects.new("Ivy · heart leaf",mesh)
            scene.collection.objects.link(leaf)
            leaf.parent = root
            leaf.location = endpoint
            leaf.rotation_euler = (rng.uniform(-.40,.42),side*rng.uniform(.38,1.14),rng.uniform(-.50,.50))
            mesh.materials.append(rng.choice(foliage))
            tube(leaf,"Raised central vein",[(0,-.003,0),(0,-.023,-leaf_length*.35),(0,-.007,-leaf_length*.87)],.001,stem_mat)

    def armillary(root, x,y,z):
        part(root,"Armillary brass plinth",(x,y,z+.027),(.19,.18,.054),brass,.016)
        beam(root,"Armillary turned stem",(x,y,z+.048),(x,y,z+.142),.035,brass)
        hub = Vector((x,y,z+.239))
        for ex,ey,radius in (
            ((1,0,0),(0,0,1),.136),((1,0,0),(0,.82,.57),.116),
            ((.43,.90,0),(0,0,1),.097),((.79,0,.61),(0,1,0),.077),
        ):
            u,v = Vector(ex),Vector(ey)
            circle = [hub+radius*(u*math.cos(math.tau*k/48)+v*math.sin(math.tau*k/48)) for k in range(48)]
            tube(root,"Armillary engraved ring",circle,.0049,brass,closed=True)
        beam(root,"Armillary tilted axis",hub+Vector((-.052,0,-.142)),hub+Vector((.055,0,.142)),.006,brass)

    left = root_object("West brick library and oak shelves")
    shelf_bank(left,-2.78,-1.22,1.80,[1.08,1.67,2.277,2.876])
    book_row(left,-2.38,-1.52,2.07,1.08)
    book_row(left,-2.69,-1.64,2.08,1.67,palette=(1,2,1,5,5,3,3,4,3,5,6),
             binding_order=(0,6,1,2,4,5,5,3,5,2,4))
    book_row(left,-2.69,-1.48,2.08,2.277,palette=(1,2,1,0,5,3,5,0,2,1,0,3),
             binding_order=(0,6,1,2,3,4,3,5,6,4,5,5))
    book_row(left,-2.61,-1.33,2.10,2.876,palette=(0,1,3,4,5,3,4,5,3,7,0))
    stack(left,-1.44,2.07,2.277,3)
    frame = part(left,"Antiqued framed pixel print",(-2.53,1.99,1.243),(.252,.039,.326),casing,.008)
    part(frame,"Parchment mount",(0,-.021,0),(.200,.004,.269),pages,.002)
    print_palette = (material("Print · ochre",(.44,.36,.155),.9), material("Print · ink",(.024,.034,.018),.9),
                     material("Print · pale olive",(.24,.275,.116),.9))
    pattern = ("020102","021120","211112","210012","200102","021220")
    for row,line in enumerate(pattern):
        for col,idx in enumerate(line):
            part(frame,"Print · hand-cut pixel",((col-2.5)*.022,-.025,(2.5-row)*.023),
                 (.022,.003,.023),print_palette[int(idx)],0)
    frame.rotation_euler.x = -math.radians(6)
    for off, length in ((-.18,.21),(-.11,.30),(.01,.32),(.12,.48),(.20,.33)):
        vine(left,-2.49+off,1.865,3.18,length,off*.64,size=.90,sidearm=.033)
    lantern_base = stack(left,-1.53,2.06,1.67,2)
    lantern_x, lantern_y = -1.53,2.035
    part(left,"Lantern foot",(lantern_x,lantern_y,lantern_base+.021),(.178,.168,.042),steel,.004)
    part(left,"Lantern frosted amber body",(lantern_x,lantern_y,lantern_base+.131),(.142,.134,.19),lantern_glass,.003)
    part(left,"Lantern cap",(lantern_x,lantern_y,lantern_base+.232),(.167,.163,.020),steel,.004)
    for x in [-.073,.073]:
        for y in [-.071,.071]:
            part(left,"Lantern corner stile",(lantern_x+x,lantern_y+y,lantern_base+.13),(.010,.010,.203),steel,.0015)
    part(left,"Lantern thin window rim",(lantern_x,lantern_y-.069,lantern_base+.215),(.147,.008,.008),brass,.0015)
    part(left,"Lantern central dark leading",(lantern_x-.008,lantern_y-.07,lantern_base+.132),
         (.010,.008,.183),steel,.0015)
    lantern_bounce = area("Lantern's amber shelf reflection", (lantern_x,lantern_y-.081,lantern_base+.12),
                          (lantern_x+.12,2.30,lantern_base+.03), .52,.13,(1,.51,.23))
    lantern_bounce.parent = left

    right = root_object("East brick library and oak shelves")
    shelf_bank(right,2.22,3.38,1.95,[1.10,1.65,2.114,2.61])
    book_row(right,2.70,3.30,2.15,1.10)
    book_row(right,2.61,3.31,2.16,1.65)
    book_row(right,2.65,3.25,2.17,2.114)
    book_row(right,2.28,2.90,2.18,2.61)
    stack(right,2.53,2.19,1.10,3)
    stack(right,2.47,2.17,2.114,3)
    armillary(right,2.45,2.16,1.65)
    fascia = material("Library | right slate blue arch top",(.036,.040,.069),.67)
    part(right,"Right alcove upper fascia",(2.82,2.04,3.104),(1.25,.19,.17),fascia,.009).rotation_euler.y=math.radians(2)
    right_bounce = area("Soft glow across upper right books and ivy", (2.85,1.48,3.18),
                       (2.93,2.13,2.72), 6,.74,(1,.68,.36))
    right_bounce.parent = right
    for off,length in ((-.22,.24),(-.15,.32),(-.113,.26),(.016,.61),(.125,.57),(.063,.25),(.16,.25),(.21,.32)):
        vine(right,3.15+off,2.01,2.87,length,off*.74,size=.81)

    ledge = root_object("Library bridge shelf with trailing ivy")
    front, z = 2.40, 2.75
    shelf_plank(ledge,"Long furniture bridge",(.50,2.63,z-.037),(3.44,.46,.074))
    part(ledge,"Bridge inner back",(.50,2.872,3.02),(3.44,.05,.65),casing,.005)
    part(ledge,"Canvas archive box",(-.34,2.62,z+.176),(.465,.30,.352),storage,.009)
    part(ledge,"Archive box fitted lid",(-.34,2.62,z+.355),(.481,.313,.042),storage,.007)
    part(ledge,"Archive box label holder",(-.34,2.465,z+.173),(.106,.007,.048),brass,.003)
    part(ledge,"Archive box cream label",(-.34,2.460,z+.173),(.086,.004,.028),pages,.001)
    stack(ledge,.13,2.64,z,4)
    book_row(ledge,.34,.72,2.66,z,stagger=False,palette=(0,3,4,3,5))
    little_lamp = material("Library · amber voxel lantern", (1,.39,.13), .52, 3)
    part(ledge,"Pixel window keepsake",(.83,2.66,z+.112),(.207,.193,.224),casing,.005)
    holes = ("012001","010110","111010","001010","010111")
    for row,line in enumerate(holes):
        for col,idx in enumerate(line):
            if idx != "0":
                part(ledge,"Pixel lantern window",(.83+(col-2.5)*.026,2.561,z+.042+(4-row)*.031),
                     (.021,.004,.026),little_lamp,.001)
    part(ledge,"Olive ceramic pixel sculpture",(1.12,2.67,z+.10),(.202,.198,.200),foliage[2],.007)
    for x,zoff,w,h in ((-.045,.13,.037,.037),(.045,.13,.037,.037),(0,.064,.054,.049)):
        part(ledge,"Sculpture dark inlay",(1.12+x,2.569,z+zoff),(w,.005,h),dark_ink,.001)
    stack(ledge,1.48,2.65,z,2)
    book_row(ledge,1.77,2.18,2.66,z,stagger=True)
    vines = ((-.10,1.00,.07),(-.24,.38,-.10),(-.052,.38,-.05),(.079,.32,.09),
             (.17,.28,.22),(.29,.28,.16),(.12,.42,.46),(-.30,.26,-.05),
             (-.20,.32,.19),(.34,.21,.25),(.18,.17,.19))
    for off,length,drift in vines:
        if length > .85:
            off, drift = off+.096, drift+.025
        vine(ledge,-1.045+off,2.31+rng.uniform(-.11,.03),z+.39+rng.uniform(-.07,.061),
             length,drift,size=.95,sidearm=.046)
    vine_light = area("Soft amber ivy accent",(-.77,1.92,z+.59),(-1.0,2.3,z+.14),
                      5,.74,(1,.76,.39))
    vine_light.parent = ledge
    lamp_bounce = area("Bridge pixel light bounce",(.83,2.52,z+.11),(.83,2.60,z+.48),
                       4,.20,(1,.51,.18))
    lamp_bounce.parent = ledge
    ledge.rotation_euler.y = math.radians(2.1)
    pivot = Vector((.5,2.40,z))
    ledge.location = pivot-ledge.rotation_euler.to_matrix()@pivot+Vector((0,0,.054))
    for bank in (left,right):
        bank["material_notes"] = "Textured walnut grain, staggered terracotta masonry, detailed page blocks and gilt spines"
    return roots
