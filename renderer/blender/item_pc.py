"""Isolated PC and furniture assemblies derived from the editable room scene."""

import math

import bpy
from mathutils import Matrix, Vector

from concept_furniture import _cylinder, surface_grain
from monitor_room import box, material


def _finish(name, color, roughness, metallic=0):
    finish = bpy.data.materials.get(name)
    if finish is None:
        finish = material(name, color, roughness)
        finish.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value = metallic
    return finish


def _block(frame, name, center, size, finish, bevel=0):
    obj = box(name, center, size, finish, bevel)
    obj.matrix_world = frame @ Matrix.Translation(center)
    return obj


def _round(frame, name, center, radius, depth, finish, axis=(0, 0, 1)):
    obj = _cylinder(name, center, radius, depth, finish, axis)
    obj.matrix_world = frame @ Matrix.Translation(center) @ obj.rotation_euler.to_matrix().to_4x4()
    return obj


def _named(objects, prefixes):
    return [obj for obj in objects if obj.name.startswith(prefixes)]


def _copy_parts(scene, objects, transform=None, parent=None, finish=None):
    copies = []
    for obj in objects:
        duplicate = obj.copy()
        if finish is not None:
            duplicate.data = obj.data.copy()
            duplicate.data.materials[0] = finish
        scene.collection.objects.link(duplicate)
        duplicate.parent = parent
        duplicate.matrix_parent_inverse = Matrix.Identity(4)
        duplicate.matrix_world = transform @ obj.matrix_world if transform is not None else obj.matrix_world.copy()
        copies.append(duplicate)
    return copies


def _mesh(frame, name, vertices, faces, finish):
    mesh = bpy.data.meshes.new(name + ' mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = frame
    obj.data.materials.append(finish)
    return obj


def _ports(frame, roof):
    graphite = _finish('I/O housing · graphite plastic', (.018, .020, .024), .43)
    steel = _finish('I/O bezel · satin nickel', (.18, .20, .23), .34, .65)
    recess = _finish('I/O port · shadow', (.003, .004, .006), .72)
    blue = _finish('USB-A · blue contact tongue', (.018, .104, .33), .41)
    z = 1.491
    items = [_block(frame, 'Top I/O trim and panel seam', (.234, -.295, z), (.337, .077, .014), graphite, .007)]
    for label, x, width, depth, plug in [('USB-C', .127, .060, .024, graphite),
                                          ('USB-A', .224, .080, .033, blue),
                                          ('USB-A', .327, .080, .033, blue)]:
        items.extend([
            _block(frame, f'{label} bezel', (x, -.295, z+.010), (width, depth, .006), steel, depth*.24),
            _block(frame, f'{label} inner cavity', (x, -.295, z+.013), (width-.007, depth-.006, .002),
                   recess, (depth-.006)*.24),
            _block(frame, f'{label} contact tongue', (x, -.295, z+.014), (.58*width, .005, .002), plug, .001),
        ])
    items.extend([
        _round(frame, 'Headphone jack rim', (.382, -.292, z+.011), .013, .005, steel),
        _round(frame, 'Headphone jack cavity', (.382, -.292, z+.014), .009, .003, recess),
    ])
    return [*roof, *items]


GPU_NAMES = ('PC - graphics card', 'PC - GPU backplate', 'PC - GPU cooling fin', 'PC - GPU RGB edge',
             'PC - GEFORCE RTX', 'PC - GPU beveled shroud', 'PC - slanted GPU shroud', 'PC - bent illuminated GPU')


def _graphics(frame, case):
    items = _named(case.children, GPU_NAMES)
    steel = _finish('GPU expansion bracket · brushed steel', (.22, .24, .27), .39, .7)
    dark = _finish('I/O port · shadow', (.003, .004, .006), .72)
    board = _finish('GPU card edge · FR4', (.012, .055, .048), .53)
    gold = _finish('Card edge contacts · gold', (.48, .29, .064), .31, .75)
    items.extend([
        _block(frame, 'Dual-slot I/O retention plate', (-.350,.068,.856), (.023,.34,.148), steel, .006),
        _block(frame, 'PCIe edge PCB', (-.110,.139,.766), (.332,.011,.040), board, .002),
        _block(frame, '12V power socket housing', (.203,.14,.960), (.111,.042,.027), dark, .004),
    ])
    for i in range(20):
        for y in (.1329, .1451):
            items.append(_block(frame, 'PCIe gold edge finger', (-.264+i*.013,y,.754),
                                (.007,.0018,.022), gold))
    for i, label in enumerate(('HDMI', 'DisplayPort', 'DisplayPort', 'DisplayPort')):
        y = -.050+i*.071
        items.extend([
            _block(frame, label+' plated port edge', (-.365,y,.866), (.010,.056,.037), steel, .006),
            _block(frame, label+' black cavity', (-.371,y,.866), (.004,.045,.027), dark, .004),
            _block(frame, label+' inner tongue', (-.374,y,.863), (.005,.030,.006), steel, .001),
        ])
    for z in (.805,.912):
        items.append(_round(frame, 'Bracket retention screw', (-.367,.192,z), .009,.007,steel,(1,0,0)))
    return items


def _motherboard(frame, case):
    items = _named(case.children, ('PC - motherboard','PC - board standoff','PC - VRM heatsink fin'))
    molded = _finish('DIMM and ATX sockets · black nylon', (.011,.014,.017), .5)
    black = _finish('I/O port · shadow', (.003,.004,.006), .72)
    steel = _finish('Motherboard socket · satin steel', (.19,.22,.24), .4, .62)
    mask = _finish('PCB printed conductors · muted jade', (.047,.19,.135), .55)
    silk = _finish('PCB silkscreen · chalk', (.44,.48,.46), .65)
    items.extend([
        _block(frame, 'CPU socket frame', (-.118,.255,1.019), (.170,.024,.161), molded, .007),
        _block(frame, 'CPU metal load plate', (-.118,.235,1.019), (.148,.018,.139), steel, .006),
        _block(frame, 'CPU pin field', (-.118,.223,1.019), (.123,.013,.116), black, .005),
        _block(frame, 'Socket latch arm', (-.015,.230,1.016), (.010,.016,.154), steel, .004),
        _block(frame, 'PCIe x16 slot body', (-.185,.247,.709), (.365,.055,.026), molded, .005),
        _block(frame, 'PCIe x16 entry slot', (-.185,.217,.709), (.337,.008,.009), black, .002),
        _block(frame, 'PCIe latch', (.019,.231,.711), (.038,.030,.025), steel, .003),
        _block(frame, 'ATX 24-pin socket', (.219,.245,.898), (.041,.060,.219), molded, .004),
        _block(frame, 'Chipset heatsink', (-.065,.239,.545), (.167,.066,.135), steel, .006),
        _block(frame, 'Rear I/O block', (-.362,.239,1.097), (.075,.070,.227), steel, .006),
    ])
    for i,x in enumerate((.015,.067,.119,.171)):
        items.extend([
            _block(frame, f'DIMM {i+1} slot body', (x,.249,1.067), (.025,.043,.420), molded, .004),
            _block(frame, 'DIMM guide channel', (x,.224,1.067), (.007,.008,.374), black, .001),
        ])
        for z in (.846,1.288):
            items.append(_block(frame, 'DIMM flip-lock', (x,.233,z), (.029,.024,.028), steel, .004))
    for x in (.210,.227):
        for i in range(12):
            items.append(_block(frame, 'ATX pin socket cavity', (x,.213,.804+i*.017),
                                (.011,.008,.011), black, .0015))
    for i in range(12):
        x = -.363+i*.012
        items.extend([
            _block(frame, 'PCB routed conductor', (x,.268,.653), (.003,.002,.129), mask),
            _block(frame, 'Solder landing pad', (x,.265,.583), (.006,.004,.007), steel, .001),
        ])
    for i in range(7):
        items.append(_block(frame, 'PCB white silkscreen reference', (-.371+i*.011,.268,.499),
                            (.002,.004,.012), silk))
    return items


def _ram(frame, case):
    items = _named(case.children, ('PC - RAM DIMM','PC - RAM RGB'))
    graphite = _finish('DIMM heat spreader edge', (.063,.079,.099), .39,.52)
    board = _finish('GPU card edge · FR4', (.012,.055,.048), .53)
    gold = _finish('Card edge contacts · gold', (.48,.29,.064), .31,.75)
    frost = _finish('DIMM translucent cap · opal', (.70,.79,.83), .38)
    frost.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value = .88
    for row in range(4):
        x = .075 + row*.039
        items.extend([
            _block(frame, f'DIMM {row+1} continuous opal light diffuser',
                   (x,.120,1.045), (.029,.007,.384), frost, .002),
            _block(frame, 'DIMM upper heat spreader rail', (x,.165,1.251), (.028,.072,.013), graphite,.003),
            _block(frame, 'Slotted DIMM PCB edge left', (x,.179,.836), (.013,.045,.030), board,.002),
            _block(frame, 'Slotted DIMM PCB edge right', (x,.231,.836), (.013,.036,.030), board,.002),
        ])
        for side in (-1,1):
            for y in (.163,.172,.181,.190,.222,.231,.240):
                items.append(_block(frame, 'DIMM plated contact', (x+side*.0074,y,.830),
                                    (.002,.005,.015), gold))
    return items


def _fan_frame(frame, finish):
    vertices = []
    for y in (-.026,.026):
        for outer in (True,False):
            for i in range(64):
                a = math.tau*i/64
                x,z = math.cos(a),math.sin(a)
                radius = .136 / (abs(x)**9+abs(z)**9)**(1/9) if outer else .107
                vertices.append((x*radius,y,z*radius))
    faces = []
    for i in range(64):
        j = (i+1)%64
        faces.extend([(i,j,j+64,i+64),(i+128,i+192,j+192,j+128),
                      (i,i+128,j+128,j),(i+64,j+64,j+192,i+192)])
    obj = _mesh(frame, 'Open-through fan chassis', vertices, faces, finish)
    mod = obj.modifiers.new('Rounded molded chassis edge', 'BEVEL')
    mod.width, mod.segments = .003, 2
    return obj


def _fans(scene):
    black = _finish('Fan chassis · textured black', (.012,.016,.023), .58)
    steel = _finish('Fan blade · graphite polymer', (.076,.086,.108), .44)
    rubber = _finish('Fan corner cushions · black rubber', (.026,.028,.032), .81)
    silver = _finish('Fan fastener · steel', (.24,.265,.30), .37,.55)
    glow = bpy.data.materials.get('PC - blue violet and green coolant edge')
    items = []
    for i,z in enumerate((.14,.44,.74),1):
        frame = Matrix.Translation((0,0,z))
        items.append(_fan_frame(frame, black))
        # Low-poly tubes along the real fan opening, using independent RGB segments.
        for segment in range(12):
            curve = bpy.data.curves.new('Fan ring segment', 'CURVE')
            curve.dimensions = '3D'
            curve.bevel_depth, curve.bevel_resolution = .0045, 3
            spline = curve.splines.new('POLY')
            spline.points.add(9)
            for j,p in enumerate(spline.points):
                a = math.tau*(segment+.016+.968*j/9)/12
                p.co = (.114*math.cos(a), -.029, .114*math.sin(a), 1)
            rim = bpy.data.objects.new('RGB ring segment',curve)
            scene.collection.objects.link(rim)
            rim.matrix_world = frame
            curve.materials.append(glow)
            items.append(rim)
        for x in (-.110,.110):
            for v in (-.110,.110):
                items.extend([
                    _block(frame, 'Anti-vibration corner pad', (x,-.027,v), (.037,.009,.037), rubber,.008),
                    _round(frame, 'Steel fan screw head', (x,-.034,v), .009,.006,silver,(0,1,0)),
                    _block(frame, 'Slotted screw head recess', (x,-.038,v), (.013,.002,.002), black,.0004),
                ])
        for a in (0, math.tau/3, 2*math.tau/3):
            brace_frame = frame @ Matrix.Rotation(-a,4,'Y')
            items.append(_block(brace_frame, 'Rear motor strut', (.073,.021,0), (.143,.014,.012), black,.004))
        rotor = bpy.data.objects.new(f'Fan {i} rotor · local Y axis', None)
        scene.collection.objects.link(rotor)
        rotor.matrix_world = frame
        items.append(rotor)
        blades = [_round(frame,'Fan motor hub',(0,0,0),.034,.047,steel,(0,1,0))]
        for blade in range(7):
            angle = math.tau*blade/7
            points = []
            for j in range(9):
                t = j/8
                radius, sweep = .029 + t*.074, angle + t*.66
                half = (.25 + math.sin(t*math.pi)*.10 - t*.10)
                points.extend([(radius*math.cos(sweep-half), -.017+t*.013, radius*math.sin(sweep-half)),
                               (radius*math.cos(sweep+half), .014-t*.010, radius*math.sin(sweep+half))])
            faces = [(2*j,2*j+1,2*j+3,2*j+2) for j in range(8)]
            shell = _mesh(frame, 'Swept fan blade', points, faces, steel)
            shell.modifiers.new('Blade shell thickness', 'SOLIDIFY').thickness = .003
            blades.append(shell)
        for part in blades:
            world = part.matrix_world.copy()
            part.parent = rotor
            part.matrix_world = world
        items.extend(blades)
        items.append(_block(frame, 'Recessed PWM and ARGB cable outlet', (.122,.032,-.092),
                            (.023,.020,.017), rubber,.003))
    return items


def _pump(frame, case, scene):
    items = _named(case.children, ('PC - CPU cooling pump','PC - CPU RGB halo'))
    tubes = _named(case.children, 'PC - liquid cooling tube')
    braided = _finish('AIO tube · woven black sheath', (.018,.020,.024), .71)
    if not any(node.type == 'BUMP' for node in braided.node_tree.nodes):
        surface_grain(braided, 385, .32, .002)
    items.extend(_copy_parts(scene, tubes, finish=braided))
    steel = _finish('AIO rail and ferrule · dark brushed steel', (.072,.083,.103), .37,.62)
    graphite = _finish('Fan chassis · textured black', (.012,.016,.023), .58)
    for point in ((-.18,.10,1.12),(-.07,.10,1.12),(.21,.05,1.36),(.27,.05,1.36)):
        items.extend([
            _round(frame,'AIO metal crimp ferrule',point,.025,.034,steel),
            _round(frame,'AIO rubber strain collar',(point[0],point[1],point[2]-.020),.023,.021,graphite),
        ])
    for y in (-.036,.154):
        items.append(_block(frame,'Radiator long side rail',(.15,y,1.414),(.530,.024,.072),steel,.007))
    for x in (-.126,.426):
        items.append(_block(frame,'Radiator rounded end header',(x,.059,1.414),(.046,.214,.077),graphite,.008))
    for j in range(36):
        items.append(_block(frame,'Radiator fin',(-.105+j*.014,.059,1.415),(.004,.164,.035),steel,.0006))
    for x in (-.09,.39):
        for y in (-.036,.154):
            items.append(_round(frame,'Radiator rail mounting screw',(x,y,1.455),.010,.007,steel))
    return items


def _cables(frame, case, scene):
    groups = [_named(case.children, prefix) for prefix in ('PC - 24 pin braided power lead',
                                                            'PC - GPU braided power lead',
                                                            'GPU rightward braided harness')]
    sheath = _finish('Woven cable sleeve · black nylon', (.023,.023,.028), .65)
    if not any(node.type == 'BUMP' for node in sheath.node_tree.nodes):
        surface_grain(sheath, 560, .45, .0013)
    dark = _finish('DIMM and ATX sockets · black nylon', (.011,.014,.017), .5)
    latch = _finish('Fan corner cushions · black rubber', (.026,.028,.032), .81)
    items = _named(case.children, 'PC - cable comb')
    for group in groups:
        items.extend(_copy_parts(scene, group, finish=sheath))
        for index in (0,-1):
            endpoints = [obj.matrix_local @ obj.data.splines[0].bezier_points[index].co for obj in group]
            midpoint = sum(endpoints, Vector((0,0,0))) / len(endpoints)
            width = max(point.x for point in endpoints) - min(point.x for point in endpoints) + .028
            items.extend([
                _block(frame,'Keyed cable connector shell',midpoint,(width,.027,.031),dark,.005),
                _block(frame,'Connector retention latch',(midpoint.x,midpoint.y,midpoint.z+.020),
                       (width*.52,.020,.011),latch,.002),
                _block(frame,'Braided sleeve strain relief',(midpoint.x,midpoint.y+.020,midpoint.z),
                       (width*.92,.019,.025),latch,.004),
            ])
    return items


def _desk(source, scene):
    objects = source.objects
    prefixes = ('Desk - walnut worktop','Desk - front edge rail','Desk - shadowed back panel',
                'Desk - left side panel','Desk - drawer plinth','Desk - amber lamp diffuser')
    items = _named(objects, prefixes)
    steel = _finish('Drawer slide · galvanized steel', (.24,.25,.27), .42,.57)
    cabinet = objects['Desk - drawer case'].data.materials[0]
    front = objects['Desk - walnut drawer 1'].data.materials[0]
    frame = Matrix.Identity(4)
    for x in (1.829,2.497):
        items.append(_block(frame,'Hollow cabinet side', (x,2.408,.443), (.020,.86,.884), cabinet,.005))
    items.append(_block(frame,'Hollow cabinet back', (2.163,2.826,.443), (.69,.021,.884), cabinet,.005))
    for i in range(1,4):
        face = objects[f'Desk - walnut drawer {i}']
        z = face.location.z
        drawer = bpy.data.objects.new(f'Drawer {i} · slide along local Y',None)
        scene.collection.objects.link(drawer)
        drawer.location = (2.163,1.957,z)
        bpy.context.view_layer.update()
        items.append(drawer)
        handles = _named(objects,(f'Desk - brass handle posts {i}',f'Desk - brass pull {i}'))
        items.extend(_copy_parts(scene,[face,*handles],parent=drawer))
        basket = [_block(frame,'Drawer interior floor',(2.163,2.350,z-.086),(.589,.724,.018),front,.003),
                  _block(frame,'Drawer inside back',(2.163,2.703,z-.008),(.601,.020,.166),front,.005)]
        for x in (1.868,2.458):
            basket.append(_block(frame,'Drawer inside side',(x,2.348,z-.006),(.020,.707,.172),front,.005))
        for x in (1.85,2.476):
            basket.append(_block(frame,'Sliding inner rail',(x,2.345,z-.054),(.011,.637,.023),steel,.002))
        for part in basket:
            world = part.matrix_world.copy()
            part.parent = drawer
            part.matrix_world = world
        items.extend(basket)
        for x in (1.843,2.483):
            items.append(_block(frame,'Fixed outer rail',(x,2.369,z-.053),(.008,.676,.036),steel,.002))
            items.append(_block(frame,'Cabinet rail travel stop',(x,2.694,z-.053),(.014,.016,.037),steel,.003))
    return items


def _chair(source, scene):
    chair = source.objects['Chair - ergonomic office chair']
    world = chair.matrix_world.copy()
    position = world.translation
    rotate = Matrix.Translation(position) @ Matrix.Rotation(math.pi-chair.rotation_euler.z,4,'Z')
    rotate @= Matrix.Translation(-position)
    items = _copy_parts(scene,chair.children,transform=rotate)
    graphite = bpy.data.materials['Chair - graphite support hardware']
    rubber = bpy.data.materials['Chair - caster rubber']
    frame = rotate @ world
    items.extend([
        _block(frame,'Height control mechanism cover', (-.023,.025,.482), (.215,.259,.081), graphite,.018),
        _round(frame,'Pneumatic height adjustment lever', (.166,.007,.478), .012,.243, graphite,(1,0,0)),
        _block(frame,'Height lever padded thumb grip', (.297,.007,.478), (.108,.044,.029), rubber,.011),
    ])
    return items


def build(item, source, scene):
    slug = item['id'] if isinstance(item,dict) else item
    case = source.objects['PC - Aurora panoramic tower']
    frame = case.matrix_world
    if slug == 'pc-case':
        return _ports(frame, [obj for obj in case.children if obj.type in {'MESH','CURVE','FONT'}])
    if slug == 'graphics-card':
        return _graphics(frame,case)
    if slug == 'motherboard':
        return _motherboard(frame,case)
    if slug == 'rgb-ram':
        return _ram(frame,case)
    if slug == 'rgb-fans':
        return _fans(scene)
    if slug == 'cooling-pump':
        return _pump(frame,case,scene)
    if slug == 'braided-power-cables':
        return _cables(frame,case,scene)
    if slug == 'walnut-desk':
        return _desk(source,scene)
    if slug == 'rolling-chair':
        return _chair(source,scene)
    raise KeyError(slug)
