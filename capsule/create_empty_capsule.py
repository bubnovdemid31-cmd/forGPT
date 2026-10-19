"""Lucid Corp / consciousness transfer pod — Blender 4.3+.

Run in Blender: Scripting > Open > Run Script.
The script creates a NEW scene and does not delete existing objects.
Animate Door_Hinge.rotation_euler.z: 0 closed, +75 degrees open.
CLI: blender -b --python create_capsule.py -- --output /path/to/folder
"""
import math

import bpy
import bmesh
from mathutils import Vector

scene = bpy.data.scenes.new('OFFWORLD — Lucid Transfer Capsule')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = False  # Works also in Blender builds without OpenImageDenoise.
scene.render.resolution_x = 1000
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world = bpy.data.worlds.new('Capsule Studio World')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.12, .16, .18, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .3
scene.view_settings.view_transform = 'AgX'

model = bpy.data.collections.new('CAPSULE — export this collection')
studio = bpy.data.collections.new('STUDIO — preview only')
scene.collection.children.link(model)
scene.collection.children.link(studio)

def material(name, color, metallic=0, roughness=.4, transmission=0, emission=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Metallic'].default_value = metallic
    node.inputs['Roughness'].default_value = roughness
    node.inputs['Transmission Weight'].default_value = transmission
    node.inputs['IOR'].default_value = 1.45
    if emission:
        node.inputs['Emission Color'].default_value = (*color, 1)
        node.inputs['Emission Strength'].default_value = emission
    mat.diffuse_color = (*color, 1)
    return mat

ceramic = material('LC | powder-coated warm white', (.64, .68, .66), .28, .33)
dark = material('LC | graphite housing', (.045, .06, .064), .55, .32)
steel = material('LC | brushed steel', (.32, .38, .39), .85, .27)
rubber = material('LC | rubber gaskets', (.012, .019, .02), 0, .7)
cushion = material('LC | medical upholstery', (.035, .065, .068), 0, .56)
glass = material('LC | smoked safety glass', (.52, .73, .72), 0, .075, .96)
light = material('LC | mint emission', (.24, .85, .65), .1, .25, emission=3)
amber = material('LC | amber indicator', (.95, .37, .065), .1, .3, emission=2)
ink = material('LC | dark print', (.018, .035, .035), 0, .53)
screen = material('LC | display background', (.015, .055, .06), .2, .2)
ground_mat = material('Studio | floor', (.075, .09, .095), .1, .6)

def move_to(obj, collection):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)

root = bpy.data.objects.new('LC_Capsule_ROOT', None)
model.objects.link(root)
root.empty_display_type = 'PLAIN_AXES'
root['description'] = 'Consciousness transfer capsule. Front is -Y; Z is up. Units: meters.'
root['approximate_dimensions'] = '1.95 m wide x 1.65 m deep x 2.95 m tall'

hinge = bpy.data.objects.new('Door_Hinge_ANIMATE_Z', None)
model.objects.link(hinge)
hinge.parent = root
hinge.location = (.77, -.695, 1.53)
hinge.empty_display_type = 'ARROWS'
hinge.empty_display_size = .23
hinge['instructions'] = 'Rotate local Z: 0 degrees closed; +75 degrees open. No keyframes supplied.'

def finish(obj, name, mat, parent=root, collection=model):
    obj.name = name
    move_to(obj, collection)
    if mat:
        obj.data.materials.append(mat)
    if parent:
        world = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = world
    return obj

def bevel(obj, width=.015, segments=3):
    mod = obj.modifiers.new('Manufactured edge radii', 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod = obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    mod.keep_sharp = True

def cube(name, loc, dims, mat, radius=.015, parent=root, collection=model):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(obj, name, mat, parent, collection)
    if radius:
        bevel(obj, min(radius, min(dims) * .45))
    return obj

def cylinder(name, loc, radius, depth, mat, axis='Z', parent=root, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    if axis == 'Y':
        obj.rotation_euler.x = math.pi / 2
    elif axis == 'X':
        obj.rotation_euler.y = math.pi / 2
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(obj, name, mat, parent)
    bevel(obj, min(.004, depth * .12), 2)
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    return obj

def rounded_points(width, height, radius, center_z=1.53, steps=12):
    result = []
    for cx, cz, start in [
        (width/2-radius, height/2-radius, 0),
        (-width/2+radius, height/2-radius, 90),
        (-width/2+radius, -height/2+radius, 180),
        (width/2-radius, -height/2+radius, 270)
    ]:
        for i in range(steps):
            angle = math.radians(start + i * 90 / steps)
            result.append((cx + radius * math.cos(angle), center_z + cz + radius * math.sin(angle)))
    return result

def mesh_object(name, vertices, faces, mat, parent=root):
    mesh = bpy.data.meshes.new(name + '_mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    model.objects.link(obj)
    return finish(obj, name, mat, parent)

def slab(name, width, height, radius, z, y, depth, mat, parent=root):
    points = rounded_points(width, height, radius, z)
    count = len(points)
    verts = [(x, y-depth/2, zz) for x, zz in points] + [(x, y+depth/2, zz) for x, zz in points]
    faces = [tuple(reversed(range(count))), tuple(range(count, count*2))]
    faces += [(i, (i+1)%count, (i+1)%count+count, i+count) for i in range(count)]
    obj = mesh_object(name, verts, faces, mat, parent)
    bevel(obj, .005, 2)
    return obj

def frame(name, outer, inner, z, yfront, yback, mat, parent=root):
    a = rounded_points(*outer, center_z=z)
    b = rounded_points(*inner, center_z=z)
    n = len(a)
    vertices = []
    for points, y in [(a,yfront),(a,yback),(b,yback),(b,yfront)]:
        vertices += [(x,y,zz) for x,zz in points]
    faces=[]
    for ring in range(4):
        next_ring=(ring+1)%4
        for i in range(n):
            j=(i+1)%n
            faces.append((ring*n+i,ring*n+j,next_ring*n+j,next_ring*n+i))
    obj=mesh_object(name,vertices,faces,mat,parent)
    bevel(obj,.008,3)
    return obj

def tube(name, points, radius, mat, parent=root):
    curve=bpy.data.curves.new(name,'CURVE')
    curve.dimensions='3D'
    curve.resolution_u=12
    curve.bevel_depth=radius
    curve.bevel_resolution=3
    spline=curve.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for p,coord in zip(spline.bezier_points,points):
        p.co=coord
        p.handle_left_type='AUTO'
        p.handle_right_type='AUTO'
    obj=bpy.data.objects.new(name,curve)
    model.objects.link(obj)
    return finish(obj,name,mat,parent)

def text(name, content, loc, size, mat, parent=root):
    bpy.ops.object.text_add(location=loc, rotation=(math.pi/2,0,0))
    obj=bpy.context.object
    obj.data.body=content
    obj.data.size=size
    obj.data.extrude=.0003
    obj.data.space_character=1.15
    obj.data.align_x='CENTER'
    finish(obj,name,mat,parent)
    return obj

# Structural body. Front opening is real geometry, not a dark decal.
frame('Body_Outer_Shell', (1.76,2.62,.38), (1.55,2.40,.31), 1.53, -.61, .61, ceramic)
slab('Rear_Outer_Bulkhead',1.65,2.52,.35,1.53,.61,.1,dark)
slab('Rear_Inner_Liner',1.48,2.32,.29,1.53,.53,.055,dark)
frame('Front_Seal_Rubber', (1.59,2.43,.32), (1.48,2.31,.29),1.53,-.663,-.615,rubber)
frame('Front_Seal_Steel', (1.82,2.67,.4), (1.72,2.57,.36),1.53,-.625,-.56,steel)
cube('Base_Platform',(0,-.03,.15),(1.93,1.55,.27),dark,.085)
cube('Base_Top_Plate',(0,-.04,.294),(1.75,1.42,.045),steel,.015)
cube('Step_Threshold',(0,-.64,.315),(1.31,.27,.07),rubber,.025)
for x in [-.71,.71]:
    for y in [-.53,.52]:
        cylinder('Vibration_Isolation_Foot',(x,y,.035),.085,.07,rubber)
for i in range(12):
    cube('Step_AntiSlip_%02d'%i,(-.58+i*.105,-.665,.354),(.035,.20,.009),steel,.003)

# Visible rear utilities and external ribs.
for side in [-1,1]:
    x=side*.87
    cube('Side_Protective_Spine',(x,.16,1.54),(.10,.38,1.66),dark,.04)
    cube('Side_Service_Panel',(x+side*.025,-.08,1.34),(.075,.27,.72),ceramic,.025)
    for z in [.49,1.00,2.12,2.55]:
        cube('Shell_Clasp',(side*.825,-.26,z),(.11,.53,.055),steel,.01)
    tube('External_Utility_Hose',[(side*.77,.59,.48),(side*.93,.65,.85),(side*.96,.65,1.85),(side*.75,.61,2.48)],.026,rubber)
    for z in [.78,1.12,1.46,1.8,2.14]:
        cube('Hose_Retaining_Clip',(side*.94,.65,z),(.085,.10,.035),steel,.006)
for z in [.59,.67,.75,.83,.91]:
    cube('Rear_Cooling_Louver',(0,.683,z),(1.05,.04,.035),steel,.005)

# Empty standing chamber: no chair, headrest, armrests or footrest.
bpy.ops.mesh.primitive_torus_add(major_radius=.335,minor_radius=.037,major_segments=64,minor_segments=12,location=(0,.075,2.08),rotation=(math.pi/2,0,0))
finish(bpy.context.object,'Neural_Induction_Ring',steel)
for i in range(12):
    angle=i*2*math.pi/12
    x=.333*math.cos(angle)
    z=2.08+.333*math.sin(angle)
    cylinder('Neural_Contact_%02d'%i,(x,.018,z),.018,.035,dark,'Y',vertices=16)
    cylinder('Neural_Status_%02d'%i,(x,-.004,z),.009,.006,light,'Y',vertices=12)
for side in [-1,1]:
    tube('Neural_Data_Conduit',[(side*.32,.13,2.15),(side*.57,.27,2.35),(side*.66,.39,1.81),(side*.65,.40,.77)],.014,rubber)
    cube('Interior_Light_Channel',(side*.66,-.045,1.56),(.045,.055,1.45),dark,.014)
    cube('Interior_Diffuser',(side*.66,-.078,1.56),(.022,.013,1.36),light,.006)

# Door: ALL elements below belong to one hinge empty. No animation is baked.
frame('Door_Main_Frame',(1.54,2.36,.32),(1.29,2.09,.27),1.53,-.792,-.70,dark,hinge)
frame('Door_Outer_Trim',(1.57,2.39,.335),(1.50,2.32,.30),1.53,-.808,-.781,steel,hinge)
slab('Door_Glass',1.32,2.12,.28,1.53,-.756,.014,glass,hinge)
cube('Door_Lower_Armor',(0,-.82,.60),(1.23,.10,.31),ceramic,.045,hinge)
cube('Door_Upper_Brow',(0,-.82,2.51),(1.15,.09,.15),ceramic,.035,hinge)
text('Door_Identity','LUCID / CORP',(0,-.88,2.485),.057,ink,hinge)
text('Door_Model_Number','LC-07  /  TRANSFER UNIT',(0,-.881,.62),.035,ink,hinge)
text('Door_Glass_Instruction','CONSCIOUSNESS LINK',(0,-.77,1.91),.035,steel,hinge)
text('Door_Glass_Warning','KEEP CLEAR / AUTHORIZED ACCESS',(0,-.771,1.85),.021,steel,hinge)
for z in [.73,1.53,2.28]:
    cylinder('Door_Hinge_Knuckle',(.77,-.695,z),.048,.16,steel,'Z',hinge)
    cylinder('Body_Hinge_Pin',(.77,-.695,z),.024,.20,dark,'Z')
cube('Door_Handle_Base',(-.65,-.84,1.39),(.09,.07,.36),steel,.02,hinge)
cube('Door_Handle_Grip',(-.65,-.915,1.39),(.055,.075,.25),rubber,.02,hinge)
for z in [1.23,1.55]:
    cube('Door_Handle_Mount',(-.65,-.87,z),(.07,.13,.045),steel,.01,hinge)
for x in [-.54,.54]:
    cube('Door_Warning_Tab',(x,-.884,.60),(.055,.01,.18),amber,.006,hinge)
for x in [-.66,.66]:
    for z in [.49,2.56]:
        cylinder('Door_Frame_Fastener',(x,-.82,z),.016,.012,steel,'Y',hinge,16)

# Stationary controls deliberately sit outside the swing on the left side.
cube('Control_Console_Support',(-.99,-.37,1.39),(.16,.21,.50),dark,.04)
console=cube('Control_Console',(-1.02,-.56,1.53),(.28,.15,.45),ceramic,.035)
cube('Control_Screen',(-1.02,-.644,1.61),(.22,.018,.23),screen,.01)
text('Display_Title','LC / 07',(-1.02,-.66,1.665),.033,light)
text('Display_State','STANDBY',(-1.02,-.66,1.60),.025,light)
text('Display_Link','LINK : OFFLINE',(-1.02,-.66,1.55),.015,steel)
for i in range(3):
    cube('Display_Level_Bar',(-1.075+i*.05,-.661,1.51),(.032,.004,.012),light,.002)
cylinder('Emergency_Stop_Base',(-1.02,-.65,1.395),.047,.018,steel,'Y')
cylinder('Emergency_Stop_Button',(-1.02,-.67,1.395),.031,.028,amber,'Y')

# Small manufacturing details. All are geometry, so they survive FBX export.
for side in [-1,1]:
    for z in [.39,2.67]:
        for x in [.48,.61]:
            cylinder('Shell_Torx_Fastener',(side*x,-.638,z),.012,.012,dark,'Y',vertices=12)
for i in range(6):
    cube('Base_Exhaust_Slot',(-.30+i*.12,-.817,.15),(.07,.014,.045),rubber,.008)
text('Base_Service_Stencil','LUCID CORP / NEURAL SYSTEMS',(0,-.833,.217),.028,steel)

# Studio objects are placed in a separate collection and are not exported.
cube('Studio_Floor',(0,0,-.05),(200,200,.06),ground_mat,.0,None,studio)
def area(name, location, energy, color, size, target=(0,0,1.5)):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=energy
    data.color=color
    data.shape='DISK'
    data.size=size
    obj=bpy.data.objects.new(name,data)
    studio.objects.link(obj)
    obj.location=location
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj
area('Key_Softbox',(-3,-4,5),700,(.83,.94,1),4)
area('Rim_Softbox',(3,2,4),1000,(.58,.80,.75),3)
area('Front_Fill',(2,-4,2.3),250,(1,.86,.69),3)
camera_data=bpy.data.cameras.new('Preview_Camera')
camera=bpy.data.objects.new('Preview_Camera',camera_data)
studio.objects.link(camera)
camera.location=(4.4,-6.6,3.8)
camera.rotation_euler=(Vector((-.05,0,1.46))-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO'
camera_data.ortho_scale=4.0
scene.camera=camera

# Convert text and curves to meshes for reliable interchange, while keeping names and parents.
bpy.ops.object.select_all(action='DESELECT')
for obj in list(model.objects):
    if obj.type in {'CURVE','FONT'}:
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.convert(target='MESH')
        obj.select_set(False)

# Base UVs only. Regenerate/check a separate lightmap UV channel in Unity for baked GI.
meshes=[o for o in model.objects if o.type=='MESH']
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active=meshes[0]
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.02)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
hinge.select_set(True)
bpy.context.view_layer.objects.active=hinge
bpy.context.view_layer.update()

hinge.rotation_euler.z = 0
bpy.context.view_layer.update()
print("Empty capsule created. Animate Door_Hinge_ANIMATE_Z, local Z 0 to 75 degrees.")


