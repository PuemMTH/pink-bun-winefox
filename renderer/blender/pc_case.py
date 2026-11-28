"""Editable panoramic PC case; real RGB meshes, braided cables and hardware."""
import colorsys
import math
import bpy
from mathutils import Vector


def build_pc_case(box, material, position=(-1.64, -1.28, 0), yaw=-12):
    scene = bpy.context.scene
    root = bpy.data.objects.new('PC - Aurora panoramic tower', None)
    scene.collection.objects.link(root)
    root.location = position
    root.rotation_euler.z = math.radians(yaw)
    metal = material('PC - brushed graphite', (.018, .024, .037), .28)
    silver = material('PC - satin aluminum', (.16, .19, .23), .3)
    black = material('PC - cable sleeve', (.006, .008, .014), .7)
    board = material('PC - motherboard graphite PCB', (.012, .025, .026), .65)
    rgb = [material('PC - RGB '+str(i), colorsys.hsv_to_rgb(i/12, .78, 1), .3, 6) for i in range(12)]
    def part(name, pos, size, mat=metal, bevel=.006):
        ob = box('PC - '+name, pos, size, mat, bevel)
        ob.parent = root
        return ob
    def curve(name, points, radius, mat):
        c = bpy.data.curves.new('PC - '+name, 'CURVE');c.dimensions='3D';c.resolution_u=16;c.bevel_depth=radius;c.bevel_resolution=3
        spline=c.splines.new('BEZIER');spline.bezier_points.add(len(points)-1)
        for p,co in zip(spline.bezier_points,points):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
        ob=bpy.data.objects.new('PC - '+name,c);scene.collection.objects.link(ob);ob.data.materials.append(mat);ob.parent=root
        return ob
    def disc(name, pos, radius, depth, mat):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=pos,rotation=(math.pi/2,0,0))
        ob=bpy.context.object;ob.name='PC - '+name;ob.data.materials.append(mat);ob.parent=root
        return ob
    # Wide show side faces the camera. A dark second chamber conceals cable returns.
    part('bottom chassis',(0,0,.13),(.94,.72,.15))
    part('vented roof',(0,0,1.45),(.94,.72,.075))
    part('rear steel panel',(0,.34,.8),(.94,.035,1.28))
    for x in [-.45,.45]:
        part('vertical frame',(x,-.335,.8),(.026,.028,1.28),silver)
        for y in [-.23,.23]:part('rubber foot',(x*.85,y,.035),(.13,.14,.07),black)
    part('PSU shroud',(0,.03,.26),(.86,.6,.18))
    part('motherboard',(-.08,.285,.87),(.64,.03,.91),board)
    for x in [-.35,.21]:
        for z in [.45,1.27]:disc('board standoff',(x,.26,z),.014,.02,silver)
    for i in range(7):part('VRM heatsink fin',(-.32+i*.021,.235,1.13),(.012,.09,.27),silver,.001)
    # CPU pump, four distinct DIMMs and diffused segmented RGB caps.
    disc('CPU cooling pump',(-.12,.15,1.02),.13,.17,metal)
    for i in range(12):
        a=i*math.tau/12;b=(i+1)*math.tau/12
        curve('CPU RGB halo', [(-.12+.115*math.cos(t),.052,1.02+.115*math.sin(t)) for t in [a,(a+b)/2,b]], .009,rgb[i])
    for ram in range(4):
        x=.075+ram*.039
        part('RAM DIMM '+str(ram+1),(x,.2,1.045),(.028,.11,.39),silver,.003)
        for j in range(8):part('RAM RGB '+str(ram+1)+' segment '+str(j),(x,.135,.88+j*.047),(.03,.025,.043),rgb[(j+ram*2)%12],.005)
    part('graphics card',(-.06,.08,.60),(.67,.29,.15),metal,.015)
    part('GPU backplate',(-.06,.08,.686),(.68,.29,.022),silver)
    for i in range(13):part('GPU cooling fin',(-.34+i*.044,-.074,.60),(.018,.023,.095),silver,.001)
    for i in range(12):part('GPU RGB edge',(-.34+i*.05,-.092,.66),(.046,.016,.016),rgb[i],.003)
    label=bpy.data.curves.new('RTX 5070 identification','FONT');label.body='GEFORCE RTX 5070';label.size=.034;label.align_x='CENTER';label.extrude=.0005
    badge=bpy.data.objects.new('PC - GEFORCE RTX 5070',label);scene.collection.objects.link(badge);badge.parent=root
    badge.location=(-.06,-.116,.585);badge.rotation_euler.x=math.pi/2
    label.materials.append(material('PC - RTX 5070 silver lettering',(.65,.8,.72),.3,.4))
    # Right intake fan column: housing, segmented luminous rings and seven blades.
    for fan,z in enumerate([.49,.88,1.27]):
        part('fan housing '+str(fan),(.335,.06,z),(.235,.13,.31),black,.014)
        for i in range(12):
            a=i*math.tau/12;b=(i+1)*math.tau/12
            curve('fan RGB ring',[(.335+.101*math.cos(t),-.021,z+.119*math.sin(t)) for t in [a,(a+b)/2,b]],.009,rgb[(i+fan*3)%12])
        disc('fan hub',(.335,-.028,z),.031,.027,metal)
        for i in range(7):
            a=i*math.tau/7
            blade=part('fan blade',(.335+.055*math.cos(a),-.016,z+.062*math.sin(a)),(.028,.013,.092),silver,.004)
            blade.rotation_euler.y=math.pi/2-a-.5
    # Visible individually sleeved power cables. Combs keep the bend parallel.
    for i in range(10):
        x=.20+i*.009
        curve('24 pin braided power lead '+str(i),[(x,.16,.83),(x+.03,.02,.79),(x+.07,-.08,.65),(x+.06,-.07,.40),(x-.10,.03,.35)],.004,rgb[(i+7)%12] if i in [0,9] else black)
    for i in range(8):
        x=-.20+i*.012
        curve('GPU braided power lead '+str(i),[(x,-.09,.61),(x,-.15,.48),(x+.05,-.12,.38),(x+.16,.08,.35)],.0045,silver if i%3==0 else black)
    for z in [.44,.52]:part('cable comb',(-.13,-.146,z),(.11,.018,.018),silver,.003)
    for i in range(2):
        curve('liquid cooling tube '+str(i),[(-.18+i*.11,.10,1.12),(-.28+i*.10,-.02,1.32),(-.11+i*.14,-.01,1.38),(.21+i*.06,.05,1.36)],.018,black)
    for i in range(18):part('top ventilation slot',(-.38+i*.043,-.02,1.491),(.018,.44,.004),black,.001)
    part('power button',(.34,-.12,1.494),(.06,.06,.008),rgb[6],.012)
    # Thin physical glass with a subtle cool tint; internal surfaces remain visible.
    glass=material('PC - clear tempered glass',(.92,.97,1),.018)
    p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=1;p.inputs['IOR'].default_value=1.46
    part('tempered glass show panel',(0,-.365,.81),(.87,.008,1.21),glass,.002)
    part('right glass return',(.455,-.03,.81),(.008,.61,1.21),glass,.002)
    for x in [-.412,.412]:
        for z in [.23,1.39]:disc('glass thumbscrew',(x,-.375,z),.012,.012,silver)
    root['features']='4 RGB RAM DIMMs; GPU; 3 RGB fans; CPU AIO; individually sleeved power cables; tempered glass'
    root['graphics_card']='NVIDIA GeForce RTX 5070'
    return root
