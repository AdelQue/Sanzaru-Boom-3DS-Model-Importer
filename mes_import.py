import struct
import bpy
import bmesh
import math
import mathutils

def invalid_format(txt, loc):
    wrong_data = f"Unexpected header; expected {txt} chunk"
    not_mesh = "Not a valid mesh file"
    if loc == 0:
        raise ValueError(not_mesh)
    else:
        raise ValueError(wrong_data)

def mes_parse(offset):
    
    mesh_data = {
        "vertex_count":0,
        "vertex_positions":[],
        "uv_positions":[],
        "vertex_normals":[],
        "vertex_weights":[],
        "faces":[],
        "face_count":0
        }

    
    # SMSH - Submesh Identifier 
    smsh_magic = mes_file.read(4)
    if smsh_magic != b"SMSH":
        invalid_format("SMSH", offset)
    smsh_length = struct.unpack("<i", mes_file.read(4))[0]


    # MHDR - Model Header
    mhdr_magic = mes_file.read(4)
    if mhdr_magic != b"MHDR":
        invalid_format("MHDR", offset)
    mhdr_length = struct.unpack("<i", mes_file.read(4))[0]
    mhdr_version = struct.unpack("<c", mes_file.read(1))[0]
    mesh_data["vertex_count"] = struct.unpack("<h", mes_file.read(2))[0]
    mes_file.read(mhdr_length - 7)


    # MVTX - Vertex Data 
    mvtx_magic = mes_file.read(4)
    if mvtx_magic != b"MVTX":
        invalid_format("MVTX", offset)
    mvtx_length = struct.unpack("<i", mes_file.read(4))[0]

    for _ in range(mesh_data["vertex_count"]):
        vertex_pos = mathutils.Vector(struct.unpack("<fff", mes_file.read(12)))
        mes_file.read(4)
        
        uv_pos = struct.unpack("<ff", mes_file.read(8))
        uv_pos = (uv_pos[0],-uv_pos[1]+1)
        vertex_nrm = mathutils.Vector(struct.unpack("<fff", mes_file.read(12)))
        
        vertex_index_raw = struct.unpack("<bbbb", mes_file.read(4))
        vertex_weight_raw = struct.unpack("<BBBB", mes_file.read(4))
        
        weight_add = ()
        weight_count = 0
        for i in vertex_index_raw:
            if sum(weight_add) <= 255:
                break
            weight_count += 1
            weight_add.append(vertex_weight_raw[i])
            
        vertex_index = ()
        vertex_weight = ()
        for i in range(weight_count):
            vertex_index.append(vertex_index_raw[i])
            vertex_weight.append(vertex_weight_raw[i]/255)
        
        mesh_data["vertex_positions"].append(vertex_pos)
        mesh_data["uv_positions"].append(uv_pos)
        mesh_data["vertex_normals"].append(vertex_nrm)
        mesh_data["vertex_weights"].append({vertex_index:vertex_weight})


    # MIDX - Face Index
    midx_magic = mes_file.read(4)
    if midx_magic != b'MIDX':
        invalid_format("MIDX", offset)
    midx_length = struct.unpack("<i", mes_file.read(4))[0]
    
    mesh_data["face_count"] = math.floor((midx_length - 4) / 6)

    for _ in range(mesh_data["face_count"]):
        face = struct.unpack("<HHH", mes_file.read(6))
        mesh_data["faces"].append(face)
    
    if mesh_data["face_count"] % 2:
        mes_file.read(2)


    # MPAL - Unknown
    mpal_magic = mes_file.read(4)
    if mpal_magic != b'MPAL':
        invalid_format("MPAL", offset)
    mpal_length = struct.unpack("<i", mes_file.read(4))[0]
    mes_file.read(mpal_length - 4)
    
    
    return (mesh_data, smsh_length + 4)

def create_mesh(mesh_data):
    # Create Mesh
    bm = bmesh.new()
    me = bpy.data.meshes.new("Mesh")

    for vertex in mesh_data["vertex_positions"]:
        bm.verts.new(vertex)
    bm.verts.ensure_lookup_table()

    for face in mesh_data["faces"]:
        bm.faces.new([bm.verts[i] for i in face])
    bm.faces.ensure_lookup_table()
    
    bm.to_mesh(me) # Needed before applying UVs
    uv_layer = bm.loops.layers.uv.new("UVMap")
    uvs = mesh_data["uv_positions"]
    for face in bm.faces:
        for loop in face.loops:
            loop[uv_layer].uv = uvs[loop.vert.index]
    
    bm.to_mesh(me)
    bm.free()

    # Add the mesh to the scene
    obj = bpy.data.objects.new("Object", me)
    bpy.context.collection.objects.link(obj)

    # Select and make active
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    me.use_auto_smooth = True
    
    vertex_normals = mesh_data["vertex_normals"]
    loop_normals = []
    
    for polygon in me.polygons:
        for loop_i in polygon.loop_indices:
            loop = me.loops[loop_i]
            vertex_i = loop.vertex_index
            loop_normals.append(vertex_normals[vertex_i])
    
    me.normals_split_custom_set(loop_normals)
    me.update()


print("---------------START---------------")

filepath = "C:/Users/Adel/Documents/Blender/boomtest/IGCCharacters/Sonic_Map/MESH_10.mes"
mes_file = open(filepath, "rb")

# Mesh File Identifier
mesh_magic = mes_file.read(4)
if mesh_magic != b"MESH":
    invalid_format("MESH", 0)
file_length = struct.unpack("<i", mes_file.read(4))[0]

# Mesh File Header (Unknown Data)
mshh_magic = mes_file.read(4)
if mshh_magic != b"MSHH":
    invalid_format("MSHH", 0)
mshh_length = struct.unpack("<i", mes_file.read(4))[0]
mes_file.read(mshh_length - 4)

offset = mshh_length + 16

while offset < file_length:
    mesh_data, mesh_length = mes_parse(offset)
    create_mesh(mesh_data)
    offset += mesh_length

print("----------------END----------------")