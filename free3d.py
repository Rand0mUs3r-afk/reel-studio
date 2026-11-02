"""Experimental no-paid-API image reconstruction and real mesh rendering."""
import argparse,json,math,os,shutil,struct,subprocess,sys,wave,textwrap
from pathlib import Path
from PIL import Image,ImageDraw
import studio
from creator import local_offer
ROOT=Path(__file__).resolve().parent

def check_model(data):
    if len(data)<20 or data[:4]!=b'glTF': raise ValueError('Expected a GLB model')
    version,total,size,kind=struct.unpack_from('<IIII',data,4)
    if version!=2 or total!=len(data) or kind!=0x4e4f534a or 20+size>len(data): raise ValueError('Invalid GLB')
    document=json.loads(data[20:20+size])
    if not document.get('meshes'): raise ValueError('No mesh in model')
    for item in document.get('images',[])+document.get('buffers',[]):
        if item.get('uri') and not item['uri'].startswith('data:'): raise ValueError('External model references blocked')
    return data

def interpret(idea,motion):
    value=idea.lower();selected=motion
    if motion=='auto':
        selected=next((word for word in ('orbit','float','reveal','turntable') if word in value),'turntable')
    return {'motion':selected,'angle':90 if 'slow' in value else 360 if 'fast' in value else 180,'light':'light' in value,'silence':'no music' in value,'no_voice':'no voice' in value or 'no narration' in value}

def run(args,**kwargs): subprocess.run(args,check=True,timeout=7200,**kwargs)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input-mode',choices=('image_url','repository_image','product_url','existing_glb','demo_3d'),default='image_url')
    p.add_argument('--source',default='');p.add_argument('--image-index',type=int,choices=range(1,25),default=1)
    p.add_argument('--variants',type=int,choices=(1,2,3,5,10),default=1)
    p.add_argument('--duration',type=int,choices=(5,10,15),default=5)
    p.add_argument('--quality',choices=('preview_360p','720p','1080p'),default='preview_360p')
    p.add_argument('--mesh-resolution',type=int,choices=(64,96,128),default=64)
    p.add_argument('--motion',choices=('auto','turntable','orbit','float','reveal'),default='auto')
    p.add_argument('--main-words',default='');p.add_argument('--reel-idea',default='')
    p.add_argument('--captions',choices=('none','offer','post_and_offer'),default='post_and_offer')
    p.add_argument('--music',choices=('auto','off','on'),default='auto')
    p.add_argument('--voice',choices=('off','on'),default='off')
    a=p.parse_args();offer=local_offer(a.main_words);motion=interpret(a.reel_idea,a.motion)
    if not a.source and a.input_mode!='demo_3d': raise ValueError('Provide a source image URL or repository file')
    output=ROOT/'output_free3d';output.mkdir(exist_ok=True)
    if any(output.iterdir()): raise ValueError('Use an empty output_free3d directory')
    work=ROOT/'.free3d-work';work.mkdir(exist_ok=True);model=None;title='3D product showcase'
    env={k:v for k,v in os.environ.items() if not k.endswith(('_KEY','_TOKEN'))}
    if a.input_mode=='existing_glb':
        data=studio.fetch(a.source,160000000) if a.source.startswith('https://') else studio.local_path(a.source).read_bytes()
        model=output/'product.glb';model.write_bytes(check_model(data))
    elif a.input_mode!='demo_3d':
        if a.input_mode=='repository_image': data=studio.local_path(a.source).read_bytes()
        elif a.input_mode=='product_url':
            title,urls=studio.product(studio.fetch(a.source,2000000),a.source)
            if len(urls)<a.image_index: raise ValueError('No image at selected product gallery index')
            data=studio.fetch(urls[a.image_index-1])
        else: data=studio.fetch(a.source)
        photo=studio.normalized(data,work/'source.png');model=output/'product.glb'
        run([sys.executable,str(ROOT/'reconstruct_cpu.py'),str(photo.resolve()),str(model.resolve()),str(a.mesh_resolution)],env=env)
        check_model(model.read_bytes())
        shutil.copy(ROOT/'.triposr'/'LICENSE',output/'TripoSR-LICENSE.txt')
    provenance={'free_only':True,'paid_api_calls':False,'geometry_source':a.input_mode,'reconstruction':'TripoSR CPU, vertex colors' if a.input_mode not in ('existing_glb','demo_3d') else 'supplied model' if model else 'procedural demo, NOT image reconstruction','idea_interpretation':'keyword rules only; no general language-model director','reel_idea':a.reel_idea,'motion':motion}
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2))
    for index in range(a.variants):
        folder=output/f'variant-{index+1:02d}';folder.mkdir();temp=work/f'variant-{index}';temp.mkdir(exist_ok=True)
        duration=a.duration;voice=None
        if a.voice=='on' and not motion['no_voice']:
            voice=temp/'voice.wav';run(['espeak-ng','-v','en-us','-s','160','-w',str(voice),'--stdin'],input=(offer or title).encode())
            with wave.open(str(voice)) as f: duration=max(duration,math.ceil(f.getnframes()/f.getframerate())+1)
            if duration>30: raise ValueError('Narration exceeds 30 seconds')
        cfg={**motion,'model':str(model.resolve()) if model else None,'frames':str((temp/'frames').resolve()),'duration':duration,'quality':a.quality,'variant':index}
        scene=temp/'scene.json';scene.write_text(json.dumps(cfg))
        run(['blender','--background','--disable-autoexec','--python-exit-code','1','--python',str(ROOT/'render_free3d.py'),'--',str(scene.resolve())],env=env)
        frames=temp/'frames';video=temp/'render.mp4'
        cmd=['ffmpeg','-y','-framerate','24','-i',str(frames/'frame_%05d.png')]
        if offer and a.captions!='none':
            with Image.open(frames/'frame_00001.png') as first: size=first.size
            overlay=Image.new('RGBA',size);draw=ImageDraw.Draw(overlay);font=studio.font(max(16,int(size[0]*.045)));lines=textwrap.wrap(offer,28);step=int(size[0]*.07)
            for i,line in enumerate(lines): draw.text((size[0]*.06,size[1]*.94-step*(len(lines)-i)),line,font=font,fill='white',stroke_width=2,stroke_fill='black')
            overlay.save(temp/'offer.png');cmd+=['-loop','1','-i',str(temp/'offer.png'),'-filter_complex',f"[0:v][1:v]overlay=enable='gte(t,{duration*.5})'[v]",'-map','[v]']
        run(cmd+['-t',str(duration),'-c:v','libx264','-crf','20','-pix_fmt','yuv420p',str(video)])
        audios=[voice] if voice else []
        if a.music=='on' or (a.music=='auto' and not motion['silence']):
            music=temp/'music.wav';studio.backing(music,duration,'calm');audios.append(music)
        cmd=['ffmpeg','-y','-i',str(video)]
        for audio in audios: cmd+=['-i',str(audio)]
        if len(audios)==2: cmd+=['-filter_complex','[2:a]volume=0.25[m];[1:a][m]amix=inputs=2:duration=longest[a]','-map','0:v','-map','[a]']
        elif audios: cmd+=['-map','0:v','-map','1:a']
        cmd+=['-c:v','copy']+(['-c:a','aac'] if audios else ['-an'])+['-t',str(duration),'-movflags','+faststart',str(folder/'reel.mp4')]
        run(cmd);shutil.copy(frames/'frame_00001.png',folder/'cover.png')
        if a.captions=='post_and_offer': (folder/'caption.txt').write_text(title+(' — '+offer if offer else ''))
        (folder/'settings.json').write_text(json.dumps({'offer_sentence':offer,'actual_duration':duration,'quality':a.quality,'motion':motion,'real_mesh_render':True},indent=2))
        shutil.rmtree(temp)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f: f.write('# Free experimental 3D renderer\nDownload the free-3d artifact. No paid APIs or social posting.\n')

if __name__=='__main__': main()
