import os
import re
import struct
import bpy
import bmesh
import math
import mathutils

class SanzaruGEOB:
    def __init__(self):
        self.name = ""
        self.bone_count = 0
        self.bone_transforms = []
        self.bone_names = []
        self.bone_parents = []
        self.hash = 0        

    def parse(self, file):
        
        # GEOB - GEOB Identifier 
        magic = file.read(4)
        if magic != b"GEOB":
            invalid_format("GEOB", file.tell(), magic) 
        geob_length = struct.unpack("<I", file.read(4))[0]


        # GEOH - Geo Header           
        magic = file.read(4)
        offset = file.tell()
        if magic != b"GEOH":
            invalid_format("GEOH", file.tell(), magic)
        geoh_length = struct.unpack("<I", file.read(4))[0]
        geoh_version = struct.unpack("<B", file.read(1))[0]
        file.read(0x18) # Bounding box min/max
        name_hash = struct.unpack("<i",file.read(4))[0]
        anim_hash = struct.unpack("<i",file.read(4))[0]
        file.read(4) # Light group
        self.name = file.read(0x2B).split(b'\x00')[0].decode() # Max string length found is 0x19, made longer just in case. May break with versions <6
        file.read(geoh_length - file.tell() + offset) # Adaptive read in case of longer headers
        
        magic = file.read(4)
        
        # SKEL - Skeleton Header
        if magic == b"SKEL":
            skel_length = struct.unpack("<I", file.read(4))[0]
            
            # SKHD - Skeleton Header
            magic = file.read(4)
            offset = file.tell()
            if magic != b"SKHD":
                invalid_format("SKHD", file.tell(), magic)
            skhd_length = struct.unpack("<I", file.read(4))[0]
            skhd_version = struct.unpack("<B", file.read(1))[0]
            self.bone_count = struct.unpack("<h", file.read(2))[0]
            file.read(skhd_length - file.tell() + offset) # Adaptive read in case of longer headers

            # BONS - Bones chunk
            magic = file.read(4)
            if magic != b"BONS":
                invalid_format("BONS", file.tell(), magic)
            bons_length = struct.unpack("<I", file.read(4))[0]
            
            bone_hashes = {}
            bone_parent_hashes = []
            
            for _ in range(self.bone_count):
                bone_name_hash, parent_name_hash = struct.unpack("<ii",file.read(8))
                x_basis = mathutils.Vector(struct.unpack("<fff",file.read(0xC)))
                z_basis = mathutils.Vector(struct.unpack("<fff",file.read(0xC)))
                position = mathutils.Vector(struct.unpack("<fff",file.read(0xC)))
                bone_name = file.read(0x20).split(b'\x00')[0].decode()

                bone_name_hash = str(bone_name_hash)
                parent_name_hash = str(parent_name_hash)

                y_basis = z_basis.cross(x_basis)
                quat = mathutils.Matrix((x_basis,y_basis,z_basis)).transposed().to_quaternion()
                transforms = (position, quat)
                
                self.bone_names.append(bone_name)
                self.bone_transforms.append(transforms)
                bone_hashes.update({bone_name_hash:bone_name})
                bone_parent_hashes.append(parent_name_hash)
            
            # Match hashes with indices
            for i in range(self.bone_count):
                if bone_parent_hashes[i] == "0":
                    parent_index = "@none"
                else:
                    parent_index = bone_hashes[bone_parent_hashes[i]]
                self.bone_parents.append(parent_index)
            
            magic = file.read(4)

            
        # GLOD - GLOD Identifier 
        if magic != b"GLOD":
            print(magic)
            invalid_format("GLOD or SKEL", file.tell(), magic)

        glod_length = struct.unpack("<I", file.read(4))[0]
        file.read(1) # Always 0, possibly version number
        self.hash = struct.unpack("<i",file.read(4))[0]
        switch_distance = struct.unpack("<f",file.read(4))[0]
        
        file.close()
        del file
        
    def make_skel(self):
        
        if bpy.context.active_object:
            bpy.ops.object.mode_set(mode='OBJECT')
            
        bpy.ops.object.add(type='ARMATURE',enter_editmode=1)
        obj = bpy.context.active_object
        obj.name = self.name + "_skel"
        obj.data.name = self.name + "_skel"
        
        # Create bones
        for i in range(self.bone_count):
            edit_bone = obj.data.edit_bones.new(self.bone_names[i])
            edit_bone.use_connect = False
            edit_bone.use_inherit_rotation = True
            edit_bone.use_inherit_scale = True
            edit_bone.use_local_location = False
            edit_bone.head = self.bone_transforms[i][0]
            edit_bone.tail = edit_bone.head + mathutils.Vector((0,0.1,0))

        bpy.ops.object.mode_set(mode='POSE')

        for i, pose_bone in enumerate(obj.pose.bones): # Apply Rotations | TODO: Orient bones without pose mode
            pose_bone.rotation_mode = 'QUATERNION'
            pose_bone.rotation_quaternion = self.bone_transforms[i][1]
        bpy.ops.pose.armature_apply()

        bpy.ops.object.mode_set(mode='EDIT')

        for i, bone in enumerate(obj.data.edit_bones): # Set parents
            if self.bone_parents[i] != "@none":
                parent_bone = self.bone_parents[i]
                bone.parent = obj.data.edit_bones[parent_bone]
            bone.use_local_location = True
        
        
        
        # Debug only
        #for i in range(len(obj.data.edit_bones)):
            #bone = obj.data.edit_bones[i]
            #print(f"{i} {bone.name}")
            
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.pose_bones = obj.pose.bones
        
        return obj

class SanzaruSubmesh:    
    class Vertex:
        def __init__(self):
            self.count = 0
            self.coord = []
            self.uv = []
            self.nrm = []
            self.idx = []
            self.color = []
            self.weight = []
            
        
    class Face:
        def __init__(self):
            self.count = 0
            self.idx = []
            
    class Weight:
        def __init__(self):
            self.pal = []

    def __init__(self):
        self.vertex = self.Vertex()
        self.face = self.Face()
        self.weight = self.Weight()
        self.length = 0
        self.vertex_scale = 1.0
        self.material_hash = 0
    
    def parse(self, file, geo):
        self.get_weights = False
        if geo.bone_count:
            self.get_weights = True
        
        # SMSH - Submesh Identifier 
        magic = file.read(4)
        if magic != b"SMSH":
            invalid_format("SMSH", file.tell(), magic)
        smsh_length = struct.unpack("<I", file.read(4))[0]
        self.length = smsh_length
        
        # MHDR - Model Header    
        magic = file.read(4)
        if magic != b"MHDR":
            invalid_format("MHDR", file.tell(), magic)
        offset = file.tell()
        
        mhdr_length = struct.unpack("<I", file.read(4))[0]
        mhdr_version = struct.unpack("<B", file.read(1))[0]
        self.vertex.count = struct.unpack("<h", file.read(2))[0]

        idx_count = struct.unpack("<h", file.read(2))[0]
        self.face.count = int(idx_count / 3)
        file.read(1) # primitive type
        self.material_hash = struct.unpack("<i", file.read(4))[0]
        file.read(4) # vertex_def_hash
        if mhdr_version:
            self.vertex_scale = struct.unpack("<f", file.read(4))[0]
            if mhdr_version >= 2:
                 file.read(1) # vis_group
                # GOTO: LABEL_6:
        else:
            self.vertex_scale = 1.0
        
        # LABEL_6:
        if mhdr_version >= 3:
            file.read(8) # vertex_pack_buf offset and size
        if mhdr_version >= 4:
            file.read(0xC) # bound sphere
            file.read(8) # idx_pack_buf offset and size
            file.read(4) # stream1_pack_buf_size
            
        if mhdr_version >= 5:
            name_hash = struct.unpack("<i", file.read(4))[0]

        file.read(mhdr_length - file.tell() + offset) # Unknown/Incomplete data, length still varies despite identical version numbers


        # MVTX - Vertex Data 
        magic = file.read(4)
        if magic != b"MVTX":
            invalid_format("MVTX", file.tell(), magic)
        mvtx_length = struct.unpack("<I", file.read(4))[0]
        
        for _ in range(self.vertex.count):
            vertex_pos = mathutils.Vector(struct.unpack("<fff", file.read(12)))
            #vertex_pos *= self.vertex_scale
            vertex_color = struct.unpack("<BBBB", file.read(4)) 
            uv_pos = struct.unpack("<ff", file.read(8))
            uv_pos = (uv_pos[0], -uv_pos[1] + 1) # Invert UVs
            vertex_nrm = mathutils.Vector(struct.unpack("<fff", file.read(12)))
            if self.get_weights:
                vertex_index_raw = struct.unpack("<bbbb", file.read(4))
                vertex_weight_raw = struct.unpack("<BBBB", file.read(4))
                self.vertex.idx.append(list(vertex_index_raw))
                self.vertex.weight.append(vertex_weight_raw)
            
            self.vertex.coord.append(vertex_pos)
            self.vertex.color.append(vertex_color)
            self.vertex.uv.append(uv_pos)
            self.vertex.nrm.append(vertex_nrm)

        # MIDX - Face Index
        magic = file.read(4)
        if magic != b'MIDX':
            invalid_format("MIDX", file.tell(), magic)
        midx_length = struct.unpack("<I", file.read(4))[0]
        
        for _ in range(self.face.count):
            face = struct.unpack("<HHH", file.read(6))
            self.face.idx.append(face)
        
        if self.face.count % 2:
            file.read(2) # Byte alignment

        if self.get_weights:
            # MPAL - Weight pallete
            magic = file.read(4)
            if magic != b'MPAL':
                invalid_format("MPAL", file.tell(), magic)
            mpal_length = struct.unpack("<I", file.read(4))[0]
            weight_count = int((mpal_length - 4) / 2)
            for _ in range(weight_count):
                bone_index = struct.unpack("<h", file.read(2))[0]
                self.weight.pal.append(bone_index)

    def make_mesh(self, geo, index):
        if geo.bone_count:
            bones = geo.pose_bones
        index = str(index).zfill(2)
        
        bm = bmesh.new()
        me = bpy.data.meshes.new(f"{geo.name}_submesh{index}")

        for vertex in self.vertex.coord:
            bm.verts.new(vertex)
        bm.verts.ensure_lookup_table()

        for face in self.face.idx:
            bm.faces.new([bm.verts[i] for i in face])
        bm.faces.ensure_lookup_table()
        
        bm.to_mesh(me) # Needed before applying UVs
        uv_layer = bm.loops.layers.uv.new("UVMap")
        uvs = self.vertex.uv
        for face in bm.faces:
            for loop in face.loops:
                loop[uv_layer].uv = uvs[loop.vert.index]
        
        vertex_colors_sub = []
        for color in self.vertex.color:
            vertex_colors_sub.append((color[0]/255, color[1]/255, color[2]/255, color[3]/255))
        
        
        color_layer = bm.loops.layers.color.new("Color")
        for f in bm.faces:
            for l in f.loops:
                l[color_layer]= vertex_colors_sub[l.vert.index]    
        
        bm.to_mesh(me)
        bm.free()

        # Add the mesh to the scene
        obj = bpy.data.objects.new(f"{geo.name}_submesh{index}", me)
        bpy.context.collection.objects.link(obj)

        # Select and make active
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        if self.get_weights:
            group_names = []
            for i in self.weight.pal:
                group_names.append(bones[i].name)
            
            vertex_indices = []
            vertex_weights = []
            
            for i, vertex in enumerate(me.vertices):
                vertex_indices_sub = []
                vertex_weights_sub = []
                
                for j, weight in enumerate(self.vertex.weight[i]):
                    if weight > 0:
                        temp_index = self.vertex.idx[i][j]
                        vertex_indices_sub.append(temp_index)
                        temp_weight = self.vertex.weight[i][j]
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
        
        vertex_normals = self.vertex.nrm
        loop_normals = []
        
        for polygon in me.polygons:
            for loop_i in polygon.loop_indices:
                loop = me.loops[loop_i]
                vertex_i = loop.vertex_index
                loop_normals.append(vertex_normals[vertex_i])
        
        me.normals_split_custom_set(loop_normals)
        me.update()
        
        return obj
    
class SanzaruMaterial:
    def __init__(self, file):
        self.name = ""
        self.dif_color = (1, 1, 1)
        self.spec_color = (0.5, 0.5, 0.5)
        self.clamp_mode_uv = (0, 0)
        self.hash
        self.tex_hash = 0

class SanzaruTexture:
    "TEXR goes here"

def invalid_format(txt, loc, value):
    loc_hex = hex(loc)[:2] + hex(loc)[2:].upper() # For nicer readable hex offsets
    wrong_data = f"Unexpected magic bytes; expected {txt} chunk at {loc_hex}, actual value {value}"
    eof = "Unexpected end of file"
    if not value:
        raise ValueError(eof)
    else:
        raise ValueError(wrong_data)



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# # # # # # # # # # # # # # # # # BEGIN # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #     
        
print("----------------Start----------------")

folder = "C:/Users/adelj/Documents/Blender/modelsresource/SonicBoom/SC-ROM/Levels/IGCCharacters/Amy/"

#folder = "C:/Users/adelj/Documents/Blender/modelsresource/SonicBoom/FI-ROM/Levels/IGCStages/IGC_Cut04/"
filelist = os.listdir(folder)

#geo_filename = "GEOB_805.geo"
geo_filename = "GEOB_8.geo"
geo_file = open(folder + geo_filename, "rb")

geo = SanzaruGEOB()
geo.parse(geo_file)
if geo.bone_count:
    skel_obj = geo.make_skel()
else:
    skel_obj = 0

mes_file = 0
mat_file = 0
tex_file = 0


for file in filelist:
    if file.endswith(".mes"):
        mes_file_test = open(folder + file, "rb")
        mes_file_test.read(0x21)
        mes_hash = struct.unpack("<i", mes_file_test.read(4))[0]
        if mes_hash == geo.hash:
            print(file)
            mes_file = mes_file_test
            break
        else:
            mes_file_test.close()

if not mes_file:
    raise ValueError("Could not find associated .mes file")
    

# No submesh count found in files. Find based on submesh header count instead
mes_file.seek(0)
mesh_count = len(re.findall(b'SMSH', mes_file.read()))
mes_file.seek(0)


# Mesh File Identifier
magic = mes_file.read(4)
if magic != b"MESH":
    invalid_format("MESH", mes_file.tell(), magic)
mesh_length = struct.unpack("<i", mes_file.read(4))[0]

# Mesh File Header
magic = mes_file.read(4)
if magic != b"MSHH":
    invalid_format("MSHH", file.tell(), magic)
mshh_length = struct.unpack("<i", mes_file.read(4))[0]
mshh_version = struct.unpack("<B", mes_file.read(1))[0]
mes_file.read(0x10) # 4 Unknown floats
mesh_hash = struct.unpack("<i", mes_file.read(4))[0]
mes_file.read(3) # Byte alignment

for i in range(mesh_count):
    submesh = SanzaruSubmesh()
    submesh.parse(mes_file, geo)
    mesh_obj = submesh.make_mesh(geo, i)
    if skel_obj:
        mesh_obj.parent = skel_obj
        bpy.ops.object.modifier_add(type='ARMATURE')
        bpy.data.objects[mesh_obj.name].modifiers["Armature"].object = skel_obj

geo_file.close()
mes_file.close()

'''
for filename in filelist:
    if filename.endswith(".geo"):
        geo_file_test = open(folder + filename, "rb")
        geo_file_test.read(0x35)
        geo_file_name = geo_file_test.read(0x2B).split(b'\x00')[0].decode()
        print(filename + " : " + geo_file_name)
'''

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# # # # # # # # # # # # # # # # # TESTS # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #     

print()

print("---GEOB TESTS---")

print(f"Name: {geo.name}")
if geo.bone_count:
    print(f"Bone Count: {geo.bone_count}")
    print(f"Bone Transforms: {geo.bone_transforms[1]}")
    print(f"Bone Name: {geo.bone_names[1]}")
    print(f"Bone Parent: {geo.bone_parents[1]}")
print(f"Hash: {geo.hash}")
print()





print("----------------End----------------")
