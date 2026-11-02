"""Portable CPU mesh renderer; native GLB/render/MP4 preflight."""
import importlib,json,math,os,platform,shutil,subprocess,sys,tempfile
from pathlib import Path

def clear_numpy():
    for name in list(sys.modules):
        if name=='numpy' or name.startswith('numpy.'): sys.modules.pop(name,None)

def ensure_numpy(cache_dir=None,python_version=None):
    version=tuple(python_version or sys.version_info[:2])
    cache=Path(cache_dir) if cache_dir is not None else Path.home()/'.cache'/'reel-studio'/f'blender-numpy-{version[0]}{version[1]}-{sys.platform}-{platform.machine()}'
    if cache.is_dir(): sys.path.insert(0,str(cache));importlib.invalidate_caches()
    def load():
        np=importlib.import_module('numpy')
        if int(np.arange(3,dtype=np.int64).sum())!=3: raise ImportError('NumPy native-array check failed')
        return np
    try: np=load()
    except (ImportError,AttributeError,OSError):
        host=os.environ.get('REEL_STUDIO_HOST_PYTHON') or shutil.which('python3') or shutil.which('python')
        if not host: raise RuntimeError('Blender needs NumPy and no host Python with pip was found')
        cache.mkdir(parents=True,exist_ok=True)
        requirement='numpy==1.26.4' if version<(3,13) else 'numpy>=2.1,<3'
        command=[host,'-m','pip','--isolated','--disable-pip-version-check','install','--upgrade','--no-cache-dir','--only-binary=:all:','--python-version',f'{version[0]}.{version[1]}','--implementation','cp','--abi',f'cp{version[0]}{version[1]}','--target',str(cache),'--index-url','https://pypi.org/simple',requirement]
        env=dict(os.environ);env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None)
        subprocess.run(command,check=True,timeout=300,env=env)
        clear_numpy();sys.path.insert(0,str(cache));importlib.invalidate_caches()
        np=load()
    print(f'Blender Python {version[0]}.{version[1]} | NumPy {np.__version__} | {np.__file__}',flush=True)
    return np

def configure_cpu_render(scene,samples=16):
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=samples
    scene.cycles.use_denoising=False
    for layer in scene.view_layers:
        cycles=getattr(layer,'cycles',None)
        if cycles is not None and hasattr(cycles,'use_denoising'): cycles.use_denoising=False
    scene.use_nodes=False
    scene.render.use_compositing=False
    print('Portable CPU render: denoising disabled; samples='+str(samples),flush=True)

def validate_smoke_metadata(info):
    video=next((s for s in info.get('streams',[]) if s.get('codec_type')=='video'),{})
    audio=next((s for s in info.get('streams',[]) if s.get('codec_type')=='audio'),{})
    if video.get('codec_name')!='h264' or (video.get('width'),video.get('height'))!=(72,128): raise RuntimeError('Smoke MP4 has invalid video format')
    if audio.get('codec_name')!='aac' or float(info.get('format',{}).get('duration',0))<=0: raise RuntimeError('Smoke MP4 has no valid audio/duration')

def encode_smoke(frames,target):
    graph="[0:v][1:v]overlay=enable='gte(t,0.04)'[v];[2:a][3:a]amix=inputs=2:duration=longest[a]"
    command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-framerate','24','-i',str(frames/'frame_%05d.png'),'-loop','1','-i',str(frames/'frame_00001.png'),'-f','lavfi','-i','anullsrc=r=22050:cl=mono','-f','lavfi','-i','anullsrc=r=22050:cl=mono','-filter_complex',graph,'-map','[v]','-map','[a]','-t',str(2/24),'-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(target)]
    subprocess.run(command,check=True,timeout=120)
    if not target.is_file() or target.stat().st_size==0: raise RuntimeError('Smoke MP4 missing')
    probe=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type,codec_name,width,height:format=duration','-of','json',str(target)],capture_output=True,text=True,check=True,timeout=30)
    validate_smoke_metadata(json.loads(probe.stdout))

def check_glb_import():
    import bpy
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add()
    obj=bpy.context.object;obj.scale=(1,.6,1.3)
    colors=obj.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for color in colors.data: color.color=(.05,.4,.3,1)
    mat=bpy.data.materials.new('Smoke vertex color');mat.use_nodes=True
    node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name=colors.name
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    obj.data.materials.append(mat)
    with tempfile.TemporaryDirectory(prefix='reel-blender-check-') as temporary:
        folder=Path(temporary);model=folder/'cube.glb'
        bpy.ops.export_scene.gltf(filepath=str(model),export_format='GLB')
        cfg={'model':str(model),'frames':str(folder/'frames'),'duration':2/24,'quality':'preview_360p','variant':0,'motion':'orbit','angle':45,'light':False,'_smoke_test':True}
        render_scene(cfg)
        images=[]
        for index in (1,2):
            path=folder/'frames'/f'frame_{index:05d}.png'
            if not path.is_file(): raise RuntimeError('Native render did not save both smoke frames')
            image=bpy.data.images.load(str(path))
            if tuple(image.size)!=(72,128): raise RuntimeError('Wrong smoke image dimensions')
            pixels=list(image.pixels);rgb=[value for i,value in enumerate(pixels) if i%4!=3]
            if max(rgb)-min(rgb)<.0001: raise RuntimeError('Smoke render is a uniform blank image')
            images.append(rgb);bpy.data.images.remove(image)
        if not any(abs(a-b)>.0001 for a,b in zip(*images)): raise RuntimeError('Smoke camera motion did not change the rendered image')
        encode_smoke(folder/'frames',folder/'smoke.mp4')
    print('Blender GLB, CPU render, overlay/audio and H.264 MP4 smoke test passed',flush=True)

def render_scene(cfg):
    import bpy
    from mathutils import Vector,Matrix
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    if cfg['model']: bpy.ops.import_scene.gltf(filepath=cfg['model'])
    else:
        bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.45,depth=1.5,location=(0,0,.75))
        bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.22,depth=.3,location=(0,0,1.65))
    meshes=[o for o in scene.objects if o.type=='MESH']
    if not meshes: raise ValueError('No geometry to render')
    bpy.context.view_layer.update()
    points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
    lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
    span=max(hi-lo)
    if span<=0: raise ValueError('Degenerate geometry')
    center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    rig=bpy.data.objects.new('Product rig',None);scene.collection.objects.link(rig)
    transform=Matrix.Scale(2/span,4)@Matrix.Translation(-center)
    for obj in meshes:
        matrix=obj.matrix_world.copy();obj.parent=rig;obj.matrix_world=transform@matrix
        colors=obj.data.color_attributes
        if colors or not obj.data.materials:
            mat=bpy.data.materials.new('Product color');mat.use_nodes=True
            shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.035,.4,.32,1)
            if colors:
                node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name=colors[0].name
                mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
            obj.data.materials.clear();obj.data.materials.append(mat)
    for obj in list(scene.objects):
        if obj.type in ('CAMERA','LIGHT'): bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.03))
    mat=bpy.data.materials.new('Floor');mat.diffuse_color=(.7,.72,.75,1) if cfg['light'] else (.03,.04,.055,1);bpy.context.object.data.materials.append(mat)
    scene.world.color=(.15,.15,.15)
    def aim(obj): obj.rotation_euler=(Vector((0,0,.9))-obj.location).to_track_quat('-Z','Y').to_euler()
    for name,location,energy in [('Key',(3,-4,5),1000),('Fill',(-4,-2,3),650),('Rim',(2,3,4),1000)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.size=4
        obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=location;aim(obj)
    camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(camera);scene.camera=camera
    camera.data.type='ORTHO'
    smoke=cfg.get('_smoke_test',False)
    configure_cpu_render(scene,samples=1 if smoke else 16)
    width=72 if smoke else {'preview_360p':360,'720p':720,'1080p':1080}[cfg['quality']]
    scene.render.resolution_x=width;scene.render.resolution_y=width*16//9;scene.render.resolution_percentage=100;scene.render.fps=24
    scene.render.image_settings.file_format='PNG'
    folder=Path(cfg['frames']);folder.mkdir(parents=True,exist_ok=True)
    count=2 if smoke else round(cfg['duration']*24)
    for index in range(count):
        t=index/max(1,count-1);angle=cfg['variant']*.35+math.radians(cfg['angle'])*t
        rig.rotation_euler=(0,0,0);rig.location=(0,0,0);camera.location=(3,-5,2.8);camera.data.ortho_scale=4.8
        if cfg['motion']=='orbit': camera.location=(6*math.sin(angle),-6*math.cos(angle),2.8)
        elif cfg['motion']=='float': rig.location.z=.2+.12*math.sin(t*math.tau);rig.rotation_euler.z=angle
        elif cfg['motion']=='reveal': rig.rotation_euler.z=angle*.3;camera.data.ortho_scale=6-1.2*t
        else: rig.rotation_euler.z=angle
        aim(camera);bpy.context.view_layer.update();scene.render.filepath=str(folder/f'frame_{index+1:05d}.png');bpy.ops.render.render(write_still=True)

def main():
    ensure_numpy()
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if args==['--check-deps']: check_glb_import();return
    if len(args)!=1: raise ValueError('Pass a scene JSON path or --check-deps after --')
    render_scene(json.loads(Path(args[0]).read_text()))

if __name__=='__main__': main()
