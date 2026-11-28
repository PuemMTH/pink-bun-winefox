"""Editable peripherals, modeled with front toward negative Y and Z up."""
from math import cos, pi, sin, tau

import bpy

from concept_furniture import cable, surface_grain
from monitor_room import box, cylinder, material


class Parts:
    def __init__(self, scene):
        self.scene = scene
        self.objects = []
        self.shell = surface_grain(material("Graphite satin ABS", (.028,.031,.038), .43), 150,.20,.0003)
        self.rubber = material("Black rubber", (.014,.015,.018), .71)
        self.metal = material("Satin connector alloy", (.31,.34,.38), .35)
        self.metal.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = .7
        self.void = material("Recess shadow", (.002,.0025,.004), .68)

    def add(self, obj):
        self.objects.append(obj)
        return obj

    def box(self, name, center, size, mat=None, bevel=0):
        return self.add(box(name, center, size, mat or self.shell, bevel))

    def disc(self, name, center, radius, thickness, mat, axis="Z"):
        obj = self.add(cylinder(name, center, radius, thickness, mat, 32))
        if axis == "Y":
            obj.rotation_euler.x = pi / 2
        elif axis == "X":
            obj.rotation_euler.y = pi / 2
        for face in obj.data.polygons:
            face.use_smooth = len(face.vertices) == 4
        return obj

    def mesh(self, name, vertices, faces, mat, smooth=False):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        mesh.materials.append(mat)
        obj = bpy.data.objects.new(name, mesh)
        self.scene.collection.objects.link(obj)
        for face in mesh.polygons:
            face.use_smooth = smooth
        return self.add(obj)

    def text(self, name, value, pos, size, mat, front=False):
        curve = bpy.data.curves.new(name, "FONT")
        curve.body, curve.size, curve.align_x, curve.align_y = value, size, "CENTER", "CENTER"
        curve.materials.append(mat)
        obj = bpy.data.objects.new(name, curve)
        self.scene.collection.objects.link(obj)
        obj.location = pos
        if front:
            obj.rotation_euler.x = pi / 2
        return self.add(obj)

    def port(self, name, pos, width, height, face, male=False):
        x,y,z = pos
        rim = height*.16
        def ring(w,h,depth):
            radius = h/2
            angles = [(-pi/2+i*pi/12+(pi if side<0 else 0),side)
                      for side in (1,-1) for i in range(13)]
            return [(x+side*(w/2-radius)+radius*cos(t),y+face*depth,z+radius*sin(t))
                    for t,side in angles]
        depth = .0056 if male else .0008
        verts = ring(width,height,0) + ring(width,height,depth)
        verts += ring(width-2*rim,height-2*rim,depth) + ring(width-2*rim,height-2*rim,-.001)
        n = 26
        faces = [(row*n+i,row*n+(i+1)%n,(row+1)*n+(i+1)%n,(row+1)*n+i)
                 for row in range(3) for i in range(n)]
        self.mesh(name+" metal rim",verts,faces,self.metal,True)
        self.box(name+" dark cavity",(x,y+face*.0003,z),(width-2*rim,.0003,height-2*rim),self.void,rim)
        self.box(name+" contact tongue",(x,y+face*(depth-.0011),z),
                 (width*.70,.0061 if male else .0018,height*.17),self.rubber,height*.06)


def monitor_set(p, source, code=False):
    if code:
        names = ["Right code monitor 1","Right code monitor 2"]
        centers = [(0,0,.342),(0,0,.955)]
    else:
        names = [f"Main monitor {column}.{row}" for row in (2,1) for column in (1,2,3)]
        names += ["Floor monitor left","Floor monitor right"]
        centers = [((i%4-1.5)*.961,0,(1.03,.35)[i//4]) for i in range(8)]
    status = material("Soft monitor status indicator", (.40,.69,.72), .44, .85)
    for name, center in zip(names, centers):
        width,height = source.objects[name]["screen_size"]
        x,y,z = center
        panel = source.objects[name+" display"].copy()
        panel.parent = None
        panel.rotation_euler = (0,0,0)
        panel.location = (x,y-.0243,z)
        panel.scale = (1,1,1)
        panel.lightgroup = ""
        p.scene.collection.objects.link(panel)
        p.add(panel)
        p.box(name+" graphite bezel",center,(width+.027,.048,height+.032),bevel=.008)
        p.box(name+" shallow back cover",(x,.032,z-.020),(width*.92,.051,height*.74),bevel=.020)
        p.box(name+" VESA plate",(x,.061,z),(.116,.008,.116),p.rubber,.004)
        for i in range(14):
            p.box(name+" vent groove",(x+(i-6.5)*.025,.058,z+height*.22),(.017,.002,.005),p.void,.001)
        for i, port in enumerate(("HDMI","DisplayPort","Power")):
            xx = x+(i-1)*.040
            p.box(name+" "+port+" shell",(xx,.059,z-height*.255),(.027,.004,.012),p.metal,.001)
            p.box(name+" "+port+" socket",(xx,.0612,z-height*.255),(.023,.0013,.0075),p.void,.001)
        p.box(name+" menu joystick",(x+width*.40,.056,z-height*.29),(.015,.009,.015),p.rubber,.004)
        p.box(name+" status light",(x+width*.43,-.025,z-height*.5-.008),(.012,.002,.003),status,.0008)
    if code:
        p.box("Shared code monitor mast",(0,.112,.642),(.055,.10,1.27),bevel=.009)
        p.box("Shared mast desk plate",(0,.103,.028),(.336,.245,.056),bevel=.024)


def monitor_stands(p):
    heights = (.29,.31,1.17,1.17,1.17,1.27)
    for i,height in enumerate(heights):
        x, name = (i-(len(heights)-1)/2)*.49, f"Stand {i+1:02}"
        p.box(name+" weighted beveled base",(x,0,.013),(.34,.21,.026),bevel=.012)
        for dx in (-.118,.118):
            for dy in (-.058,.058):
                p.box(name+" non-slip pad",(x+dx,dy,-.001),(.059,.041,.004),p.rubber,.002)
        p.box(name+" upright column",(x,.044,height/2),(.072,.060,height),bevel=.014)
        p.box(name+" cable channel insert",(x,.075,height*.45),(.028,.006,height*.46),p.rubber,.003)
        p.disc(name+" tilt pivot",(x,.02,height-.029),.042,.089,p.metal,"X")
        p.box(name+" four-hole VESA plate",(x,-.018,height-.023),(.113,.013,.113),bevel=.005)
        for dx in (-.044,.044):
            for dz in (-.044,.044):
                p.disc(name+" mounting socket",(x+dx,-.026,height-.023+dz),.004,.002,p.void,"Y")


def keyboard_rows():
    def units(labels):
        return [(label,1) for label in labels]
    x = (.5,2.,3.,4.,5.,6.45,7.45,8.45,9.45,10.9,11.9,12.9,13.9,16.,17.,18.)
    function_labels = ["ESC", *(f"F{i}" for i in range(1,13)), "PRT","SCR","PAU"]
    result = [(label,position,0,1) for label,position in zip(function_labels,x)]
    rows = [
        units((chr(96),"1","2","3","4","5","6","7","8","9","0","-","=")) + [("BKSP",2)],
        [("TAB",1.5)] + units((*"QWERTYUIOP","[","]")) + [("\\",1.5)],
        [("CAPS",1.75)] + units((*"ASDFGHJKL",";","'")) + [("ENTER",2.25)],
        [("SHIFT",2.25)] + units((*"ZXCVBNM",",",".","/")) + [("SHIFT",2.75)],
        [("CTRL",1.25),("WIN",1.25),("ALT",1.25),("SPACE",6.25),
         ("ALT",1.25),("WIN",1.25),("MENU",1.25),("CTRL",1.25)],
    ]
    for row, keys in enumerate(rows,1):
        edge = 0
        for label,size in keys:
            result.append((label,edge+size/2,row,size))
            edge += size
    for row,keys in ((1,("INS","HOME","PGUP")),(2,("DEL","END","PGDN")),
                     (4,("","UP","")),(5,("LEFT","DOWN","RIGHT"))):
        result.extend((label,16+i,row,1) for i,label in enumerate(keys) if label)
    assert len(result) == 87
    return result


def keyboards(p):
    caps = [material("PBT keycap graphite",(.036,.041,.056),.64),
            material("PBT blue-grey keycap",(.069,.084,.112),.68)]
    legends = material("Pale English legends",(.67,.72,.80),.48)
    leds = [material("RGB switch "+str(i),color,.53,1.2) for i,color in
            enumerate(((.047,.52,.55),(.17,.16,.66),(.58,.13,.43)))]
    pitch = .019
    layout = keyboard_rows()
    for variant, oy in (("TKL A",.083),("TKL B",-.083)):
        p.box(variant+" bottom shell",(0,oy,.0115),(.367,.137,.019),bevel=.0074)
        p.box(variant+" anodized plate",(0,oy,.022),(.351,.123,.005),p.metal,.004)
        p.box(variant+" front RGB diffuser",(0,oy-.0687,.013),(.338,.0016,.0022),leds[1],.0008)
        p.port(variant+" rear USB-C",(-.132,oy+.069,.012),.009,.0034,1)
        for x in (-.147,.147):
            for y in (-.045,.049):
                p.box(variant+" anti-slip pad",(x,oy+y,.0011),(.031,.019,.004),p.rubber,.002)
            foot = p.box(variant+" flip-out kickstand",(x,oy+.044,.003),(.030,.023,.004),bevel=.002)
            foot.rotation_euler.x = -.12
        for index,(label,column,row,width) in enumerate(layout,1):
            x,y = (column-9.25)*pitch,oy+(2.71-row-(.20 if row else 0))*pitch
            w,d = width*pitch-.00145,pitch-.00145
            name = f"{variant} key {index:02} {label}"
            p.box(name+" switch housing",(x,y,.0272),(min(.017,w),.0145,.0054),leds[(index//6)%3],.0012)
            verts = [(x+sx*(w/2-inset),y+sy*(d/2-inset),z)
                     for inset,z in ((0,.029),(.0016,.0385),(.0021,.0395))
                     for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1))]
            verts.append((x,y,.039))
            faces = [(3,2,1,0)] + [(i+k,(i+1)%4+k,(i+1)%4+k+4,i+k+4)
                                   for i in range(4) for k in (0,4)]
            faces += [(8+i,8+(i+1)%4,12) for i in range(4)]
            key = p.mesh(name+" concave cap",verts,faces,caps[int(index<17 or index in (29,75,87))])
            bevel = key.modifiers.new("Soft tooling edges","BEVEL")
            bevel.width,bevel.segments = .00034,2
            if label != "SPACE":
                p.text(name+" English legend",label,(x,y+.001,.0397),.0048 if len(label)<=1 else .0032,legends)


def mouse(p):
    def oval_shell(name, loops):
        verts = [(rx*cos(i*tau/64),center+ry*sin(i*tau/64),z)
                 for rx,ry,center,z in loops for i in range(64)]
        faces = [tuple(reversed(range(64)))]
        faces += [(i+k,(i+1)%64+k,(i+1)%64+k+64,i+k+64)
                  for k in range(0,len(verts)-64,64) for i in range(64)]
        faces.append(tuple(range(len(verts)-64,len(verts))))
        return p.mesh(name,verts,faces,p.shell,True)
    oval_shell("Wireless graphite lower shell",
          ((.032,.055,0,.002),(.035,.058,0,.007),(.0355,.059,0,.015),(.034,.058,0,.019)))
    # Click surfaces and palm shell share one crown profile. A shallow seam
    # separates their edges without lifting the buttons above the shell.
    nose = [
        (-.057,.007,.021,.00065),(-.054,.014,.0238,.00065),(-.048,.0192,.0256,.00065),
        (-.042,.0239,.0266,.001),(-.037,.027,.0273,.0045),(-.032,.029,.0280,.0062),
        (-.025,.0307,.0290,.0065),(-.018,.0322,.0301,.0062),(-.013,.0331,.0310,.0038),
        (-.008,.0336,.032,.00065),(-.00065,.034,.0332,.00065),
    ]
    palm = [
        (.00065,.034,.0334,0),(.008,.0338,.0349,0),(.016,.0328,.0365,0),
        (.024,.031,.0375,0),(.032,.0285,.0371,0),(.040,.0246,.0353,0),
        (.048,.0201,.0323,0),(.053,.0155,.0293,0),(.056,.011,.0266,0),
        (.058,.005,.0238,0),
    ]

    def cap(name, rows, side):
        columns = 17
        points = []
        for y, half_width, crown, split in rows:
            xmin = split if side > 0 else -half_width
            xmax = -split if side < 0 else half_width
            for column in range(columns):
                x = xmin + (xmax-xmin)*column/(columns-1)
                arch = max(0, 1-(x/half_width)**2)**.66
                points.append((x,y,.0188+(crown-.0188)*arch))
        count = len(points)
        lower = [(x,y,.01865) for x,y,_ in points]
        top = [(i,i+1,i+1+columns,i+columns)
               for i in range(count-columns) if i%columns != columns-1]
        rim = (list(range(columns)) + list(range(2*columns-1,count,columns))
               + list(range(count-2,count-columns-1,-1))
               + list(range(count-2*columns,0,-columns)))
        walls = [(b,a,a+count,b+count) for a,b in zip(rim,rim[1:]+rim[:1])]
        return p.mesh(name,points+lower,top+walls+[tuple(i+count for i in reversed(rim))],p.shell,True)

    cap("Rounded palm crown",palm,0)
    cap("Left click separate ABS button",nose,-1)
    cap("Right click separate ABS button",nose,1)
    p.box("Central scroll well",(0,-.025,.019),(.012,.029,.002),p.void,.001)
    p.disc("Rubber scroll wheel",(0,-.025,.0268),.0087,.0104,p.rubber,"X")
    for i in range(30):
        t = i*tau/30
        rib = p.box("Scroll tread",(0,-.025+.0085*cos(t),.0268+.0085*sin(t)),
                    (.0096,.0018,.0008),p.shell,.0003)
        rib.rotation_euler.x = t
    p.port("Front charging USB-C",(0,-.059,.012),.0093,.0036,-1)
    for y in (-.035,.036):
        p.box("Low-friction PTFE skate",(0,y,.001),(.041,.017,.0021),p.metal,.001)
    p.disc("Optical sensor recess",(0,.007,.0019),.0055,.0009,p.void)
    p.disc("Optical sensor glass",(0,.007,.0014),.0028,.00075,p.metal)
    p.box("Power switch cutout",(.012,.025,.0015),(.009,.007,.001),p.void,.00065)
    p.box("Wireless on-off slider",(.012,.026,.0008),(.0048,.0048,.0012),p.shell,.00055)


def usb_cable(p):
    sleeve = surface_grain(material("Black woven nylon cable sleeve",(.016,.018,.024),.73),420,.52,.00048)
    path = [(-.144,-.058,.005),(-.144,-.024,.005),(-.137,.062,.005),(-.096,.093,.005),
            (-.026,.079,.005),(.020,.022,.005),(.070,-.007,.005),(.118,.012,.005),
            (.144,.060,.005),(.144,.095,.005)]
    p.add(cable("Braided USB-C cable continuous lead",path,.00265,sleeve))
    for i,(x,y,face) in enumerate(((-.144,-.058,-1),(.144,.095,1)),1):
        for j in range(5):
            p.box(f"USB-C {i} relief rib {j+1}",(x,y+face*.0016*j,.005),
                  (.0062+j*.00065,.0013,.0060),p.rubber,.0005)
        p.box(f"USB-C {i} black molded grip",(x,y+face*.016,.005),(.013,.020,.0083),bevel=.0033)
        p.port(f"USB-C {i} male",(x,y+face*.026,.005),.0085,.00295,face,True)


def mats(p,source):
    for i,(name,y,w,d) in enumerate((("Desk - woven mat surface",.21,1.44,.29),
            ("Floor keyboard mat",-.13,.694,.273)),1):
        cloth = source.objects[name].data.materials[0]
        edge = source.objects["Desk - mat stitched perimeter"].data.materials[0] if i==1 else p.shell
        p.box(f"Mat {i} anti-slip rubber underside",(0,y,.004),(w,d,.008),p.rubber,.003)
        p.box(f"Mat {i} stitched perimeter",(0,y,.0085),(w,d,.0055),edge,.0026)
        p.box(f"Mat {i} woven top",(0,y,.011),(w-.012,d-.012,.0023),cloth,.0011)
        for k in range(1,int(w/.015)):
            for side in (-1,1):
                p.box(f"Mat {i} overlock stitch",(-w/2+k*.015,y+side*(d/2-.006),.0116),
                      (.008,.002,.0014),p.rubber,.0004)
        for k in range(1,int(d/.015)):
            for side in (-1,1):
                p.box(f"Mat {i} end seam",(side*(w/2-.006),y-d/2+k*.015,.0116),
                      (.002,.008,.0014),p.rubber,.0004)


def headphones(p,source):
    prefixes = ("Desk - headphone","Desk - headband rest","Desk - sculpted headphone")
    p.objects.extend(obj for obj in source.objects if obj.name.startswith(prefixes))
    p.disc("Stand underside non-slip ring",(2.12,2.28,.995),.100,.004,p.rubber)
    p.add(cable("Soft headband padding",[(2.12+.103*cos(t),2.28,1.212+.134*sin(t))
          for t in (0,.3,.6,.9,1.2,1.57,1.9,2.2,2.55,2.85,pi)],.017,p.rubber))
    p.disc("Headphone volume thumbwheel",(2.251,2.245,1.130),.017,.011,p.metal,"X")
    for side in (-1,1):
        p.box("Headphone size-adjust yoke",(2.12+side*.104,2.28,1.232),(.019,.038,.053),bevel=.006)
        p.disc("Headphone hinge pivot",(2.12+side*.118,2.28,1.22),.013,.008,p.metal,"X")


def beverage_can(p,source):
    names = ("Desk - beverage can","Desk - soda can lower rim","Desk - soda can lid","Desk - wrapped drink can stripe")
    p.objects.extend(source.objects[name] for name in names)
    x,y = -1.04,2.099
    p.add(cable("Rolled aluminum lid seam",[(x+.068*cos(t*tau/48),y+.068*sin(t*tau/48),1.387)
          for t in range(49)],.0027,p.metal))
    p.add(cable("Oval aluminum pull-tab loop",[(x+.011*cos(t*tau/36),y+.008+.017*sin(t*tau/36),1.392)
          for t in range(37)],.0031,p.metal))
    p.disc("Pull-tab rivet",(x,y-.007,1.391),.005,.004,p.metal)
    p.add(cable("Scored oval drink opening",[(x+.020*cos(t*tau/36),y-.028+.014*sin(t*tau/36),1.387)
          for t in range(37)],.00075,p.void))


def phone(p):
    glass = material("Dark phone front glass",(.012,.025,.047),.18)
    active = material("Muted blue screen cards",(.065,.25,.43),.32,.45)
    text = material("Blue white UI typography",(.40,.67,.91),.42,.70)
    lens = material("Blue coating on camera glass",(.025,.061,.11),.18)
    p.box("Graphite rounded phone body",(0,0,.079),(.082,.0092,.158),bevel=.0045)
    p.box("Back matte cover",(0,.0048,.079),(.080,.0010,.155),bevel=.00049)
    p.box("Single laminated dark display",(0,-.005,.079),(.077,.0011,.150),glass,.00052)
    p.box("Screen dark UI background",(0,-.00565,.079),(.070,.00045,.139),glass,.00020)
    p.text("Mock screen home time","09:41",(0,-.00616,.125),.0135,text,front=True)
    p.text("Mock screen status","SATURDAY",(0,-.00616,.111),.0045,text,front=True)
    for z in (.095,.082,.069):
        p.box("Cool grey notification card",(0,-.00620,z),(.057,.0006,.009),active,.00028)
        p.box("Mock notification content",(-.007,-.00656,z),(.025,.00045,.0012),text,.00021)
    p.box("Home gesture indicator",(0,-.00630,.020),(.028,.0005,.0015),text,.00024)
    p.disc("Single rear camera metal bezel",(-.024,.0061,.135),.0080,.0034,p.metal,"Y")
    p.disc("Single rear camera coated glass",(-.024,.0080,.135),.0064,.0010,lens,"Y")
    p.disc("Rear LED flash",(-.007,.0060,.135),.003,.0020,text,"Y")
    for z in (.094,.108):
        p.box("Sound volume button",(-.0416,0,z),(.0025,.005,.010),p.rubber,.0012)
    p.box("Single power button",(.0415,0,.090),(.0026,.0050,.013),p.rubber,.0011)
    start = len(p.objects)
    p.port("Bottom USB-C",(0,0,0),.0090,.0034,-1)
    for obj in p.objects[start:]:
        obj.rotation_euler.x = pi/2
        obj.location = (obj.location.x,-obj.location.z,obj.location.y)
    for side in (-1,1):
        for i in range(4):
            p.disc("Bottom microphone / speaker aperture",(side*(.012+i*.003),0,-.00008),.00075,.0007,p.void)


def build(item, source, scene):
    """Create new items and/or return the editable parts inherited from the source."""
    slug = item["id"] if isinstance(item,dict) else item
    parts = Parts(scene)
    actions = {
        "minecraft-monitors": lambda: monitor_set(parts,source),
        "code-monitors": lambda: monitor_set(parts,source,True),
        "monitor-stands": lambda: monitor_stands(parts),
        "keyboards": lambda: keyboards(parts),
        "mouse": lambda: mouse(parts),
        "keyboard-mouse-mats": lambda: mats(parts,source),
        "usb-cable": lambda: usb_cable(parts),
        "headphones": lambda: headphones(parts,source),
        "beverage-can": lambda: beverage_can(parts,source),
        "phone": lambda: phone(parts),
    }
    actions[slug]()
    assert parts.objects, slug
    return parts.objects
