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

def submesh_parse(mes_file):
    mesh_data = {
        "vertex_count":0,
        "vertex_positions":[],
        "uv_positions":[],
        "vertex_normals":[],
        "vertex_indices":[],
        "vertex_weights":[],
        "faces":[],
        "face_count":0,
        "weight_pallete":[]
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
    mhdr_length = struct.unpack("<I", mes_file.read(4))[0]
    mhdr_version = struct.unpack("<B", mes_file.read(1))[0]
    mesh_data["vertex_count"] = struct.unpack("<h", mes_file.read(2))[0]
    index_count = struct.unpack("<h", mes_file.read(2))[0]
    mesh_data["face_count"] = int(index_count / 3)
    
    primitive_type = struct.unpack("<b", mes_file.read(1))[0]
    material_hash = struct.unpack("<i", mes_file.read(4))[0]
    vertex_def_hash = struct.unpack("<i", mes_file.read(4))[0]

    mes_file.read(mhdr_length - 18)


    # MVTX - Vertex Data 
    mvtx_magic = mes_file.read(4)
    if mvtx_magic != b"MVTX":
        invalid_format("MVTX", offset)
    mvtx_length = struct.unpack("<i", mes_file.read(4))[0]

    
    weight_indices = []
    weight_values = []
    
    
    for _ in range(mesh_data["vertex_count"]):
        vertex_pos = mathutils.Vector(struct.unpack("<fff", mes_file.read(12)))
        mes_file.read(4)
        
        uv_pos = struct.unpack("<ff", mes_file.read(8))
        uv_pos = (uv_pos[0],-uv_pos[1]+1)
        vertex_nrm = mathutils.Vector(struct.unpack("<fff", mes_file.read(12)))
        
        vertex_index_raw = struct.unpack("<bbbb", mes_file.read(4))
        vertex_weight_raw = struct.unpack("<BBBB", mes_file.read(4))
        
        weight_indices.append(list(vertex_index_raw))
        weight_values.append(vertex_weight_raw)
        
        mesh_data["vertex_positions"].append(vertex_pos)
        mesh_data["uv_positions"].append(uv_pos)
        mesh_data["vertex_normals"].append(vertex_nrm)
    

    # MIDX - Face Index
    midx_magic = mes_file.read(4)
    if midx_magic != b'MIDX':
        invalid_format("MIDX", offset)
    midx_length = struct.unpack("<i", mes_file.read(4))[0]
    

    for _ in range(mesh_data["face_count"]):
        face = struct.unpack("<HHH", mes_file.read(6))
        mesh_data["faces"].append(face)
    
    if mesh_data["face_count"] % 2:
        mes_file.read(2)


    # MPAL - Weight pallete
    mpal_magic = mes_file.read(4)
    if mpal_magic != b'MPAL':
        invalid_format("MPAL", offset)
    mpal_length = struct.unpack("<i", mes_file.read(4))[0]
    weight_count = math.floor((mpal_length - 4) / 2)
    weight_pallete = []
    for _ in range(weight_count):
        bone_index = struct.unpack("<h", mes_file.read(2))[0]
        weight_pallete.append(bone_index)
    
    mesh_data["weight_pallete"] = weight_pallete
    
    '''
    # Pair vertices to bones
    for vertex in weight_indices:
        for i, group in enumerate(vertex):
            vertex[i] = weight_pallete[group]
    '''
    
    
    mesh_data["vertex_indices"] = weight_indices
    mesh_data["vertex_weights"] = weight_values
    

    return (mesh_data, smsh_length + 4)

def create_mesh(mesh_data, index, bones):
    # Create Mesh
    bm = bmesh.new()
    me = bpy.data.meshes.new(f"Submesh{index}")

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
    obj = bpy.data.objects.new(f"Submesh{index}", me)
    bpy.context.collection.objects.link(obj)

    # Select and make active
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)








    group_names = []
    for i in mesh_data["weight_pallete"]:
        group_names.append(bones[i].name)
    
    vertex_indices = []
    vertex_weights = []
    
    for i, vertex in enumerate(me.vertices):
        vertex_indices_sub = []
        vertex_weights_sub = []
        
        for j, weight in enumerate(mesh_data["vertex_weights"][i]):
            if weight > 0:
                temp_index = mesh_data["vertex_indices"][i][j]
                vertex_indices_sub.append(temp_index)
                temp_weight = mesh_data["vertex_weights"][i][j]
                temp_weight /= 255
                vertex_weights_sub.append(temp_weight)
        vertex_indices.append(vertex_indices_sub)
        vertex_weights.append(vertex_weights_sub)

        
    vertex_group_refs = []
    for group_name in group_names:
        temp_group = obj.vertex_groups.new(name=group_name)
        vertex_group_refs.append(temp_group)


    for vertex_i, temp_weights in enumerate(vertex_weights):
        for group_i, temp_weight in enumerate(temp_weights):
            ref_i = vertex_indices[vertex_i][group_i]
            vertex_group_refs[ref_i].add([vertex_i], temp_weight, 'REPLACE')
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
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


def skeleton_parse(geo_file):
    
    skel_data = {
        "skel_name":0,
        "bone_count":0,
        "bone_transforms":[],
        "bone_names":[],
        "bone_parents":[],
        }

    # GEOB - Geo Identifier 
    geob_magic = geo_file.read(4)
    if geob_magic != b"GEOB":
        invalid_format("GEOB", offset)
    geob_length = struct.unpack("<i", geo_file.read(4))[0]


    # GEOH - Geo Header    
    geoh_magic = geo_file.read(4)
    if geoh_magic != b"GEOH":
        invalid_format("GEOH", offset)
    geoh_length = struct.unpack("<I", geo_file.read(4))[0]
    geoh_version = struct.unpack("<B", geo_file.read(1))[0]

    geo_file.read(0x18)
    skel_name_hash, anim_hash = struct.unpack("<ii",geo_file.read(8))
    geo_file.read(4)
    skel_name = str(geo_file.read(0x20).decode().rstrip('\x00'))
    geo_file.read(geoh_length - 0x49)
    
    
    # SKEL - Skeleton Header
    skel_magic = geo_file.read(4)
    if skel_magic != b"SKEL":
        invalid_format("SKEL", offset)
    skel_length = struct.unpack("<I", geo_file.read(4))[0]
    
    
    
    # SKHD - Skeleton Header
    skhd_magic = geo_file.read(4)
    if skhd_magic != b"SKHD":
        invalid_format("SKHD", offset)
    skhd_length = struct.unpack("<I", geo_file.read(4))[0]
    skhd_version = struct.unpack("<B", geo_file.read(1))[0]
    bone_count = struct.unpack("<h", geo_file.read(2))[0]
    
    geo_file.read(skhd_length - 7)
    
    
    
    # BONS - Bones chunk
    bons_magic = geo_file.read(4)
    if bons_magic != b"BONS":
        invalid_format("BONS", offset)
    bons_length = struct.unpack("<I", geo_file.read(4))[0]
    
    bone_names = []
    bone_transforms = []
    bone_hashes = {}
    bone_parent_hashes = []
    bone_parents = []
    
    # Get bones
    for _ in range(bone_count):
        name_hash, parent_name_hash = struct.unpack("<ii",geo_file.read(8))
        x_basis = mathutils.Vector(struct.unpack("<fff",geo_file.read(0xC)))
        z_basis = mathutils.Vector(struct.unpack("<fff",geo_file.read(0xC)))
        position = mathutils.Vector(struct.unpack("<fff",geo_file.read(0xC)))
        name = str(geo_file.read(0x20).decode().rstrip('\x00'))

        name_hash = str(name_hash)
        parent_name_hash = str(parent_name_hash)
        
        y_basis = z_basis.cross(x_basis)
        quat = mathutils.Matrix((x_basis,y_basis,z_basis)).transposed().to_quaternion()
        transforms = (position, quat)
        
        bone_names.append(name)
        bone_transforms.append(transforms)
        bone_hashes.update({name_hash:name})
        bone_parent_hashes.append(parent_name_hash)
        
    # Match hashes with indices
    for i in range(bone_count):
        if bone_parent_hashes[i] == "0":
            parent_index = "@none"
        else:
            parent_index = bone_hashes[bone_parent_hashes[i]]
        bone_parents.append(parent_index)
        
    
    skel_data["skel_name"] = skel_name
    skel_data["bone_count"] = bone_count
    skel_data["bone_transforms"] = bone_transforms
    skel_data["bone_names"] = bone_names
    skel_data["bone_parents"] = bone_parents
    
    return skel_data

def create_skel(skel_data):    
    
    skel_name = skel_data["skel_name"]
    bone_count = skel_data["bone_count"]
    bone_transforms = skel_data["bone_transforms"]
    bone_names = skel_data["bone_names"]
    bone_parents = skel_data["bone_parents"]
    
    if bpy.context.active_object:
        bpy.ops.object.mode_set(mode='OBJECT')
        
    bpy.ops.object.add(type='ARMATURE',enter_editmode=1)
    obj = bpy.context.active_object
    obj.name = skel_name
    obj.data.name = skel_name
    
    # Create bones
    for i in range(bone_count):
        edit_bone = obj.data.edit_bones.new(bone_names[i])
        edit_bone.use_connect = False
        edit_bone.use_inherit_rotation = True
        edit_bone.use_inherit_scale = True
        edit_bone.use_local_location = False
        edit_bone.head = bone_transforms[i][0]
        edit_bone.tail = edit_bone.head + mathutils.Vector((0,0.1,0))

    bpy.ops.object.mode_set(mode='POSE')

    for i, pose_bone in enumerate(obj.pose.bones): # Apply Rotations | TODO: Figure out math to do this in the previous loop or next loop without leaving edit mode
        pose_bone.rotation_mode = 'QUATERNION'
        pose_bone.rotation_quaternion = bone_transforms[i][1]
    bpy.ops.pose.armature_apply()

    bpy.ops.object.mode_set(mode='EDIT')

    for i, bone in enumerate(obj.data.edit_bones): # Set parents
        if bone_parents[i] != "@none":
            parent_bone = bone_parents[i]
            bone.parent = obj.data.edit_bones[parent_bone]
        bone.use_local_location = True
    
    

    # Debug only
    #for i in range(len(obj.data.edit_bones)):
        #bone = obj.data.edit_bones[i]
        #print(f"{i} {bone.name}")
        
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return obj


print("---------------START---------------")

mes_filepath = "C:/Users/Adel/Documents/Blender/boomtest/IGCCharacters/Sonic_Map/MESH_10.mes"
geo_filepath = "C:/Users/Adel/Documents/Blender/boomtest/IGCCharacters/Sonic_Map/GEOB_11.geo"

mes_file = open(mes_filepath, "rb")
geo_file = open(geo_filepath, "rb")



skel_data = skeleton_parse(geo_file)
skel_obj = create_skel(skel_data)
skel_bones = skel_obj.pose.bones


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
index = 0

#for _ in range(1):
while offset < file_length:
    mesh_data, mesh_length = submesh_parse(mes_file)
    create_mesh(mesh_data, index, skel_bones)
    offset += mesh_length
    index += 1



print("----------------END----------------")