"""Run in local Blender: build an isolated MPFB child design for visual review.

This is an authoring candidate, not automatic production promotion. Actual MPFB
facial targets and TalkingHead weights are used; private source GLBs are untouched.
"""
from pathlib import Path
import importlib.util
import json
import math
import struct
import sys
import bpy
from mathutils import Vector, Quaternion, Matrix

RUNTIME = Path(r'E:\Krishna-The GOD')
TOOLS = RUNTIME / 'tools'
AUTHOR = TOOLS / 'avatar-authoring'
OUTPUT = RUNTIME / 'dashboard/assets/avatar/candidates/child-identity-v1'
OUTPUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(TOOLS / 'mpfb2-src/src'))
original_extension_path = bpy.utils.extension_path_user
def isolated_extension_path(package, *args, **kwargs):
    if package == 'mpfb':
        return str(AUTHOR / 'mpfb-user')
    return original_extension_path(package, *args, **kwargs)
bpy.utils.extension_path_user = isolated_extension_path
import mpfb
bpy.context.preferences.addons.new().module = 'mpfb'
mpfb.register()
from mpfb.services import (HumanService, TargetService, AssetService, RigService,
                           FaceService, ExportService, ObjectService)
from mpfb.entities.rig import Rig

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
macro = TargetService.get_default_macro_info_dict()
macro.update(gender=1., age=0., muscle=.25, weight=.55, height=.45)
macro['race'] = {'asian': .7, 'caucasian': .2, 'african': .1}
body = HumanService.create_human(scale=.1, macro_detail_dict=macro)
body.name = 'KrishnaChild'
rig = Rig.from_json_file_and_basemesh(str(AUTHOR / 'talkinghead/talkinghead.mpfbskel'), body)
arm = rig.create_armature_and_fit_to_basemesh()
arm.name = arm.data.name = 'Armature'
body.parent = arm
RigService.load_weights(arm, body, str(AUTHOR / 'talkinghead/talkinghead.mhw'))
RigService.ensure_armature_modifier(body, arm)

def material(name, color, metallic=0., roughness=.65):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1.)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return mat

skin = next((AssetService.find_asset_absolute_path(name, asset_subdir='skins')
             for name in ('young_asian_male.mhmat', 'young_asian_female.mhmat')
             if AssetService.find_asset_absolute_path(name, asset_subdir='skins')), None)
if not skin:
    raise RuntimeError('Reference-quality skin assets missing; install system asset pack')
HumanService.set_character_skin(skin, body, skin_type='GAMEENGINE')
for mat in body.data.materials:
    mat.name='Krishna child skin'
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    socket = bsdf.inputs['Base Color']
    multiply = mat.node_tree.nodes.new('ShaderNodeMixRGB')
    multiply.blend_type='MULTIPLY'
    multiply.inputs[0].default_value=1.
    multiply.inputs[2].default_value=(.58,.42,.29,1.)
    if socket.links:
        mat.node_tree.links.new(socket.links[0].from_socket,multiply.inputs[1])
    else:
        multiply.inputs[1].default_value=socket.default_value
    mat.node_tree.links.new(multiply.outputs[0],socket)
assets = [('eyes','low-poly.mhclo','Eyes'), ('eyebrows','eyebrow001.mhclo','Eyebrows'),
          ('eyelashes','eyelashes01.mhclo','Eyelashes'), ('tongue','tongue01.mhclo','Tongue'),
          ('teeth','teeth_base.mhclo','Teeth'), ('hair','elvs_that_80s_babe_hair.mhclo','Hair'),
          ('clothes','toigo_harem_pants.mhclo','Clothes')]
for directory, name, kind in assets:
    path = AssetService.find_asset_absolute_path(name, asset_subdir=directory)
    if not path:
        raise RuntimeError('Required appearance asset missing: ' + name)
    obj = HumanService.add_mhclo_asset(path, body, asset_type=kind, material_type='GAMEENGINE')
    if kind == 'Clothes':
        for mat in obj.data.materials:
            bsdf=mat.node_tree.nodes.get('Principled BSDF')
            for link in list(bsdf.inputs['Base Color'].links):mat.node_tree.links.remove(link)
            bsdf.inputs['Base Color'].default_value=(.94,.52,.025,1.)
            bsdf.inputs['Roughness'].default_value=.78
    if kind == 'Eyes':
        brown=AUTHOR/'mpfb-user/data/eyes/materials/brown_eye.png'
        if not brown.is_file():raise RuntimeError('Brown eye texture missing')
        image=bpy.data.images.load(str(brown),check_existing=True)
        for mat in obj.data.materials:
            for node in mat.node_tree.nodes:
                if node.type=='TEX_IMAGE' and node.image and 'normal' not in node.image.name.lower():
                    node.image=image
    if kind == 'Hair':
        for vertex in obj.data.vertices:
            co=vertex.co
            # Keep the cap away from the eyes; separate fitted curls supply length.
            if co.z<.42:
                co.z=.42-(.42-co.z)*.65
        for hair in arm.children:
            if hair == obj:
                for mat in hair.data.materials:
                    bsdf=mat.node_tree.nodes.get('Principled BSDF')
                    for link in list(bsdf.inputs['Base Color'].links):mat.node_tree.links.remove(link)
                    bsdf.inputs['Base Color'].default_value=(.012,.007,.004,1.)

gold = material('Restrained gold', (.6,.34,.035), .65, .32)
yellow = material('Yellow pitambara', (.94,.52,.025))
blue = material('Blue sash', (.018,.09,.35))
dark = material('Natural dark curls', (.015,.008,.005), 0., .7)
green = material('Peacock green', (.035,.3,.12), .1)
feather_blue = material('Peacock eye', (.01,.08,.4), .15)
ivory = material('Clean tilak', (.94,.86,.62))
red = material('Tilak center', (.55,.035,.02))

def mesh_object(name, verts, faces, mat, bone='Hips'):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    if bone:
        obj.parent = arm
        group = obj.vertex_groups.new(name=bone)
        group.add(list(range(len(verts))), 1., 'REPLACE')
        modifier = obj.modifiers.new('Armature', 'ARMATURE')
        modifier.object = arm
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj

def tube(name, centers, radii, mat, bone='Hips', sides=48, pleat=0.):
    verts = []
    for (cx,cy,z), (rx,ry) in zip(centers,radii):
        for i in range(sides):
            angle = i*math.tau/sides
            fold = 1.+pleat*math.cos(angle*12)
            verts.append((cx+rx*fold*math.cos(angle), cy+ry*fold*math.sin(angle), z))
    faces = [(r*sides+i,r*sides+(i+1)%sides,(r+1)*sides+(i+1)%sides,(r+1)*sides+i)
             for r in range(len(centers)-1) for i in range(sides)]
    faces += [tuple(reversed(range(sides))), tuple(range((len(centers)-1)*sides,len(verts)))]
    return mesh_object(name,verts,faces,mat,bone)

def ellipsoid(name, center, radius, mat, bone='Head', segments=20, rings=12):
    verts = []
    for j in range(rings+1):
        phi = math.pi*j/rings
        for i in range(segments):
            theta = math.tau*i/segments
            verts.append(tuple(center[k]+radius[k]*v for k,v in enumerate(
                (math.sin(phi)*math.cos(theta),math.sin(phi)*math.sin(theta),math.cos(phi)))))
    faces = [(j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i)
             for j in range(rings) for i in range(segments)]
    return mesh_object(name,verts,faces,mat,bone)

# The fitted CC0 harem garment provides continuous coverage and real skinning.
# The sash is restrained and follows the waist rather than becoming a barrel.
tube('Blue waist sash',[(0,-.039,.329),(0,-.039,.311)],[(.085,.098),(.088,.102)],blue)
mesh_object('Sash drape', [(-.055,-.142,.325),(-.023,-.145,.325),(-.045,-.10,.15),(-.075,-.095,.16)],[(0,1,2,3)],blue)
tube('Sash gold border',[(0,-.039,.332),(0,-.039,.329)],[(.086,.099),(.086,.099)],gold)

# Fitted natural hair uses Elvaerwyn's CC-BY asset; attribution travels with the
# candidate. Scalp and curls deform with the actual imported head weights.
curl_vertices=[]
curl_faces=[]
for strand in range(28):
    theta=math.pi*(strand+.5)/28
    root_x=.065*math.cos(theta)
    root_y=.02+.032*math.sin(theta)
    root_z=.51-.035*math.sin(theta)+.008*math.sin(strand*1.7)
    length=.20+.045*(.5+.5*math.sin(strand*2.3))
    phase=strand*2.39996
    first=len(curl_vertices)
    for step in range(25):
        t=step/24
        wave=t**1.2
        cx=root_x*(1+.70*t)+.010*wave*math.sin(8*math.pi*t+phase)
        cy=root_y+.009*wave*math.cos(8*math.pi*t+phase)
        z=root_z-length*t
        radius=.0038*(1-.55*t)
        for side in range(8):
            angle=math.tau*side/8
            curl_vertices.append((cx+radius*math.cos(angle),cy+radius*math.sin(angle),z))
    for step in range(24):
        for side in range(8):
            here=first+step*8+side
            curl_faces.append((here,first+step*8+(side+1)%8,
                               first+(step+1)*8+(side+1)%8,first+(step+1)*8+side))
mesh_object('Long natural curls',curl_vertices,curl_faces,dark,'Head')
ellipsoid('Hair topknot',(0,.01,.635),(.028,.027,.026),dark)
ellipsoid('Single peacock feather',(.025,.005,.673),(.01,.002,.028),green)
ellipsoid('Peacock eye',(.025,.001,.679),(.006,.0015,.009),feather_blue)
ellipsoid('Peacock eye center',(.025,-.001,.679),(.002,.001,.004),gold)
for x in (-.004,.004):ellipsoid('Tilak', (x,-.085,.601),(.0018,.001,.009),ivory)
ellipsoid('Tilak center',(0,-.087,.6),(.001,.001,.006),red)

for i in range(22):
    theta=math.tau*i/22
    ellipsoid('Child necklace',(.051*math.cos(theta),-.014+.048*math.sin(theta),.485+.040*math.sin(theta)),
              (.003,.003,.003),gold,'Spine2',12,8)
# The flute is a real separate object; poses and hand placement still require review.
tube('Flute',[(0,0,0),(0,0,.25)],[(.0035,.0035),(.0035,.0035)],gold,'RightHand',20)
flute=bpy.data.objects['Flute']
flute.rotation_euler[1]=math.pi/2
flute.location=( -.125,-.085,.425)

export_arm=ExportService.create_character_copy(body,name_suffix='_export')
arm.name='AuthoringArmature'
export_arm.name='Armature'
export_body=ObjectService.find_object_of_type_amongst_nearest_relatives(export_arm,'Basemesh')
TargetService.bake_targets(export_body)
FaceService.load_targets(export_body,load_microsoft_visemes=False,load_meta_visemes=True,load_arkit_faceunits=True)
FaceService.interpolate_targets(export_body)
ExportService.bake_modifiers_remove_helpers(export_body,bake_masks=True,bake_subdiv=False,remove_helpers=True,also_proxy=True)
for obj in [export_arm,*export_arm.children_recursive]:
    if obj.type=='MESH' and obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks:
            if key.name.startswith('!ex-'):
                key.name=key.name[4:]
            if key.name in ('mouthSmileLeft','mouthSmileRight'):key.value=.24
            if key.name in ('cheekSquintLeft','cheekSquintRight'):key.value=.035
spec=importlib.util.spec_from_file_location('talkinghead_authoring',AUTHOR/'talkinghead/talkinghead-addon.py')
addon=importlib.util.module_from_spec(spec)
spec.loader.exec_module(addon)
addon.fix_bone_axes([export_arm])
review_scale=1./(export_arm.matrix_world @ export_arm.pose.bones['Hips'].head).z
addon.scale_character([export_arm],target_z=1.)

def reset_pose():
    for pb in export_arm.pose.bones:
        pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()

def hands_at(left,right):
    temporary=[]
    for side,point in [('Left',left),('Right',right)]:
        target=bpy.data.objects.new('Pose target',None)
        bpy.context.collection.objects.link(target)
        target.location=Vector(point)*review_scale
        bone=export_arm.pose.bones[side+'ForeArm']
        constraint=bone.constraints.new('IK')
        constraint.target=target;constraint.chain_count=2
        temporary.append((bone,constraint,target))
    bpy.context.view_layer.update()
    solved={name:export_arm.pose.bones[name].matrix.copy()
            for name in ('LeftArm','LeftForeArm','RightArm','RightForeArm')}
    for bone,constraint,target in temporary:
        bone.constraints.remove(constraint);bpy.data.objects.remove(target,do_unlink=True)
    for name,matrix in solved.items():export_arm.pose.bones[name].matrix=matrix
    bpy.context.view_layer.update()

def rotate(name,axis,angle):
    pb=export_arm.pose.bones[name]
    pb.rotation_mode='QUATERNION'
    pb.rotation_quaternion=pb.rotation_quaternion @ Quaternion(axis,angle)

reset_pose();hands_at((.085,-.12,.49),(-.075,-.12,.49))
prop=next(obj for obj in export_arm.children_recursive if obj.name.startswith('Flute'))
for modifier in list(prop.modifiers):prop.modifiers.remove(modifier)
prop.vertex_groups.clear()
prop.parent=export_arm;prop.parent_type='BONE';prop.parent_bone='RightHand'
bpy.context.view_layer.update()
prop.matrix_world=Matrix.Translation(Vector((-.125,-.128,.519))*review_scale) @ Matrix.Rotation(math.pi/2,4,'Y') @ Matrix.Diagonal((review_scale,review_scale,review_scale,1))
bpy.context.view_layer.update()

# Child-specific, genuinely keyed bone actions. No adult rest-pose overrides.
export_arm.animation_data_create()
clips=('idle','listen','think','talk','walk','wave','smile','flute','dhyan','sleep','wake','work','wisdom','playful','protection')
for index,clip in enumerate(clips):
    action=bpy.data.actions.new(clip);export_arm.animation_data.action=action
    for frame,phase in [(1,0.),(31,1.),(61,0.)]:
        reset_pose()
        left,right=(.09,-.045,.29),(-.09,-.045,.29)
        if clip=='flute':left,right=(.085,-.12,.49),(-.075,-.12,.49)
        elif clip in ('dhyan','sleep'):left,right=(.025,-.115,.385),(-.025,-.115,.385)
        elif clip in ('wave','protection'):left=(.16,-.08,.56)
        elif clip in ('think','work'):right=(-.035,-.11,.46)
        elif clip in ('talk','wisdom'):left=(.10,-.10,.39+phase*.025)
        elif clip=='playful':left,right=(.15,-.07,.44),(-.14,-.075,.42)
        hands_at(left,right)
        if clip=='flute':
            for side in ('Left','Right'):
                for finger in ('Index','Middle','Ring','Pinky'):
                    for segment,angle in ((1,.2),(2,.8),(3,.55)):
                        rotate(side+'Hand'+finger+str(segment),(1,0,0),angle)
        rotate('Head',(0,0,1),phase*(.045 if clip in ('listen','think') else .018))
        rotate('Head',(1,0,0),(.075 if clip in ('dhyan','sleep') else 0)+phase*.014)
        rotate('Spine2',(1,0,0),phase*.009)
        if clip=='walk':
            rotate('LeftUpLeg',(1,0,0),.22*(1-2*phase))
            rotate('RightUpLeg',(1,0,0),-.22*(1-2*phase))
        if clip=='wave':rotate('LeftHand',(0,0,1),phase*.3)
        if clip=='wake':rotate('Head',(1,0,0),.08*(1-phase))
        for pb in export_arm.pose.bones:
            pb.rotation_mode='QUATERNION'
            pb.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=pb.name)
            pb.keyframe_insert(data_path='location',frame=frame,group=pb.name)
    track=export_arm.animation_data.nla_tracks.new();track.name=clip
    track.strips.new(clip,1,action);track.mute=True
    export_arm.animation_data.action=None
reset_pose()

# Keep editable source hidden only in render; export remains an isolated duplicate.
for obj in [arm,*arm.children_recursive]:
    obj.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for obj in [export_arm,*export_arm.children_recursive]:
    obj.select_set(True)
bpy.context.view_layer.objects.active=export_arm
glb=OUTPUT/'krishna.child-candidate.glb'
for texture in bpy.data.images:
    if texture.size[0]>1024 or texture.size[1]>1024:
        ratio=1024/max(texture.size)
        texture.scale(max(1,round(texture.size[0]*ratio)),max(1,round(texture.size[1]*ratio)))
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_morph_normal=False)
# Blender's glTF exporter does not preserve the skin Multiply shader node.
# Store the same tint explicitly in the standard PBR material factor.
raw=glb.read_bytes()
json_length=struct.unpack_from('<I',raw,12)[0]
document=json.loads(raw[20:20+json_length])
document['asset'].setdefault('extras',{})['krishnaRuntimeProfile']='native-child-v1'
for mat in document.get('materials',[]):
    # MPFB's generic game shader marks even solid skin and trousers as BLEND.
    # In glTF this draws back faces through the face/body and breaks eye occlusion.
    name=mat.get('name','').lower()
    if any(part in name for part in ('hair','eyebrow','eyelash')):
        mat['alphaMode']='MASK';mat['alphaCutoff']=.35;mat['doubleSided']=True
    else:
        mat['alphaMode']='OPAQUE';mat.pop('alphaCutoff',None)
    if mat.get('name','').endswith('young_asian_male') or mat.get('name','')==body.data.materials[0].name:
        mat.setdefault('pbrMetallicRoughness',{})['baseColorFactor']=[.58,.42,.29,1.]
chunk=json.dumps(document,separators=(',',':')).encode()
chunk+=b' '*((-len(chunk))%4)
tail=raw[20+json_length:]
glb.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(chunk)+len(tail))+struct.pack('<I4s',len(chunk),b'JSON')+chunk+tail)

scene=bpy.context.scene
scene.render.fps=30
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=700
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.world.color=(.025,.025,.025)
for location,energy,size in [((-.7,-.9,1.2),28,1.),((.7,-.4,.7),14,.8),((0,.5,1.),30,.6)]:
    data=bpy.data.lights.new('Soft studio','AREA'); data.energy=energy;data.shape='DISK';data.size=size
    data.energy*=review_scale**2;data.size*=review_scale
    obj=bpy.data.objects.new('Soft studio',data);scene.collection.objects.link(obj);obj.location=Vector(location)*review_scale
    obj.rotation_euler=(Vector((0,0,.35))*review_scale-obj.location).to_track_quat('-Z','Y').to_euler()
camera_data=bpy.data.cameras.new('Review camera')
camera=bpy.data.objects.new('Review camera',camera_data);scene.collection.objects.link(camera);scene.camera=camera
camera_data.type='ORTHO';camera_data.ortho_scale=.79*review_scale
export_arm.animation_data.action=bpy.data.actions.get('idle')
scene.frame_set(1)
for view,position in ([] if '--skip-render' in sys.argv else [('front',(0,-1.5,.38)),('side',(1.5,0,.38)),('back',(0,1.5,.38))]):
    camera.location=Vector(position)*review_scale;camera.rotation_euler=(Vector((0,0,.35))*review_scale-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUTPUT/f'{view}.png');bpy.ops.render.render(write_still=True)
bpy.data.batch_remove(ids=[key for key in bpy.data.shape_keys if key.users==0 or key.user is None])
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'krishna.child-design.blend'))
(OUTPUT/'candidate-status.json').write_text(json.dumps({'stage':'visual-review-required',
    'production_promoted':False,'reference_identity_verified':False,'glb':str(glb),
    'real_face_targets':len(export_body.data.shape_keys.key_blocks)-1,'clips':list(clips),
    'limitations':['face likeness, curl placement, child clothing fit and flute pose require visual review',
                   'state animations and speech deformation require testing before promotion']},indent=2))
print('KRISHNA_CHILD_CANDIDATE',str(glb))
(OUTPUT/'ATTRIBUTION.md').write_text('Child base mesh, system textures, eyes and facial targets: MakeHuman Community, CC0.\n'
    'Hair cap: elvs_that_80s_babe_hair by Elvaerwyn, CC-BY; fitted to child proportions and darkened. Additional curls generated locally.\n'
    'Fitted trousers: toigo_harem_pants by MargaretToigo, CC0; recolored yellow.\n'
    'Source: https://static.makehumancommunity.org/assets/assetpacks/hair02.html\n'
    'TalkingHead rig/weights: Mika Suominen, CC0, https://github.com/met4citizen/TalkingHead/tree/main/blender/MPFB\n'
    'Costume, feather, tilak and necklace: generated locally by this authoring script.\n')
