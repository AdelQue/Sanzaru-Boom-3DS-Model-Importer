import bpy
import struct
import mathutils

print("---------------START---------------")

if bpy.context.active_object:
    bpy.ops.object.mode_set(mode='OBJECT')

filepath = "C:/Users/Adel/Documents/Blender/boomtest/IGCCharacters/Sonic_Map/GEOB_11.geo"
geo_file = open(filepath, "rb")

geo_file.seek(0x35,0)
skel_name = geo_file.read(0x2B).decode().rstrip('\x00')

geo_file.seek(0x7D,0)
bone_count = struct.unpack("<h",geo_file.read(2))[0]

geo_file.seek(0x84,0) #BONS offset
geo_file.read(8) #BONS identifier + length

bpy.ops.object.add(type='ARMATURE',enter_editmode=1)
obj = bpy.context.active_object

bone_transforms = {}
name_hashes = {}
parent_hashes = {}

for _ in range(bone_count):
    name_hash, parent_name_hash = struct.unpack("<ii",geo_file.read(8))
    x_basis = mathutils.Vector(struct.unpack("<fff",geo_file.read(0xC)))
    z_basis = mathutils.Vector(struct.unpack("<fff",geo_file.read(0xC)))
    position = mathutils.Vector(struct.unpack("<fff",geo_file.read(0xC)))
    name = str(geo_file.read(0x20).decode().rstrip('\x00'))
    
    name_hash = str(name_hash)
    parent_name_hash = str(parent_name_hash)
    name_hashes.update({name_hash:name})
    parent_hashes.update({name:parent_name_hash})
    
    y_basis = z_basis.cross(x_basis)
    quat = mathutils.Matrix((x_basis,y_basis,z_basis)).transposed().to_quaternion()
    transforms = (position, quat)
    bone_transforms.update({name:transforms})
    
for i in bone_transforms:
    edit_bone = obj.data.edit_bones.new(i)
    edit_bone.use_connect = False
    edit_bone.use_inherit_rotation = True
    edit_bone.use_inherit_scale = True
    edit_bone.use_local_location = False
    edit_bone.head = bone_transforms[i][0]
    edit_bone.tail = edit_bone.head + mathutils.Vector((0,0.1,0))

bpy.ops.object.mode_set(mode='POSE')


for i in bone_transforms: # Apply Rotations | TODO: Figure out math to do this in the previous loop or next loop without leaving edit mode
    pose_bone = obj.pose.bones[i]
    pose_bone.rotation_mode = 'QUATERNION'
    pose_bone.rotation_quaternion = bone_transforms[i][1]
bpy.ops.pose.armature_apply()

bpy.ops.object.mode_set(mode='EDIT')

for bone in obj.data.edit_bones: # Set parents
    parent_name_hash = parent_hashes[bone.name]
    if parent_name_hash != "0":
        parent_bone = name_hashes[parent_name_hash]
        bone.parent = obj.data.edit_bones[parent_bone]
    bone.use_local_location = True
    
# Debug only
for i in range(len(obj.data.edit_bones)):
    bone = obj.data.edit_bones[i]
    print(f"{i} {bone.name}")
    

bpy.ops.object.mode_set(mode='OBJECT')




print("----------------END----------------")