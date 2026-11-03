"""Real 3D product rotation with free narration and an optional illustrated humanoid."""
import argparse
import array
import json
import math
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from PIL import Image,ImageDraw


def rotation_config(config,degrees):
    if degrees not in (90,180,360):raise ValueError('Unsupported rotation')
    result=dict(config)
    # Existing reveal multiplies the rotation by .3; compensate explicitly.
    result['angle']=degrees/.3 if result['motion']=='reveal' else degrees
    return result

def audio_levels(path,fps=24):
    with wave.open(str(path)) as stream:
        if stream.getsampwidth()!=2 or stream.getnchannels()!=1:
            raise ValueError('Narration must be mono 16-bit PCM WAV')
        rate=stream.getframerate();samples=array.array('h',stream.readframes(stream.getnframes()))
        if sys.byteorder!='little':samples.byteswap()
    step=max(1,round(rate/fps));levels=[]
    for start in range(0,len(samples),step):
        chunk=samples[start:start+step]
        levels.append(min(1.,math.sqrt(sum(float(v)*v for v in chunk)/max(1,len(chunk)))/4500))
    return levels,len(samples)/rate

def humanoid_frame(width,height,mouth=0.,blink=False):
    image=Image.new('RGBA',(width,height));draw=ImageDraw.Draw(image)
    def box(coords):return tuple(int(v*(width if i%2==0 else height)) for i,v in enumerate(coords))
    draw.rounded_rectangle(box((.12,.53,.88,.98)),radius=max(2,width//8),fill='#1E3A5F')
    draw.rounded_rectangle(box((.25,.08,.75,.58)),radius=max(2,width//7),fill='#BDD7E7',outline='#38BDF8',width=max(1,width//40))
    for x in (.36,.59):
        draw.rectangle(box((x,.27,x+.07,.28 if blink else .30)),fill='#102030')
    opening=.006+.065*max(0.,min(1.,mouth))
    draw.ellipse(box((.38,.42-opening,.62,.43+opening)),fill='#16334A')
    draw.rectangle(box((.43,.58,.57,.65)),fill='#BDD7E7')
    draw.ellipse(box((.42,.73,.58,.81)),fill='#38BDF8')
    return image

def command(args):
    try:return subprocess.run(args,check=True,capture_output=True,text=True,timeout=600)
    except subprocess.CalledProcessError as exc:raise RuntimeError('Media processing failed: '+exc.stderr[-1500:]) from exc

def probe(path):
    return json.loads(command(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]).stdout)

def add_presenter(video,narration,presenter):
    info=probe(video);streams=info['streams'];v=next(s for s in streams if s['codec_type']=='video')
    width,height=v['width'],v['height'];duration=float(info['format']['duration'])
    levels,spoken=audio_levels(narration)
    if spoken>duration-.1:raise ValueError('Narration is longer than the render')
    music=any(s.get('codec_type')=='audio' for s in streams)
    with tempfile.TemporaryDirectory(prefix='product-presenter-') as temporary:
        work=Path(temporary);args=['ffmpeg','-nostdin','-y','-i',str(video)]
        filters=[];voice_index=1
        if presenter=='visible_humanoid_illustrated':
            aw=max(40,int(width*.24)//2*2);ah=max(80,int(height*.42)//2*2)
            frames=work/'frames';frames.mkdir()
            for i in range(math.ceil(duration*24)):
                humanoid_frame(aw,ah,levels[i] if i<len(levels) else 0.,i%96<3).save(frames/f'{i:05}.png')
            args+=['-framerate','24','-i',str(frames/'%05d.png')];voice_index=2
            pw=int(width*.72)//2*2;ph=int(height*.72)//2*2
            filters += [f'[0:v]scale={pw}:{ph}[product]',f'color=c=0x102030:s={width}x{height}:r=24:d={duration}[bg]',f'[bg][product]overlay=0:(H-h)/2[layout]',f'[layout][1:v]overlay=W-w-4:(H-h)/2[v]']
        args+=['-i',str(narration)]
        filters.append(f'[{voice_index}:a]apad[voice]')
        if music:
            filters += ['[0:a]volume=0.22[bed]','[bed][voice]amix=inputs=2:duration=longest[a]']
        else:filters.append('[voice]anull[a]')
        args+=['-filter_complex',';'.join(filters),'-map','[v]' if presenter=='visible_humanoid_illustrated' else '0:v','-map','[a]']
        args+=['-c:v','libx264','-threads','2','-preset','veryfast','-crf','20','-pix_fmt','yuv420p'] if presenter=='visible_humanoid_illustrated' else ['-c:v','copy']
        final=work/'final.mp4'
        args+=['-c:a','aac','-b:a','160k','-t',str(duration),'-movflags','+faststart',str(final)]
        command(args)
        checked=probe(final);video_stream=next(s for s in checked['streams'] if s.get('codec_type')=='video')
        if (video_stream['width'],video_stream['height'])!=(width,height) or not any(s.get('codec_type')=='audio' for s in checked['streams']):
            raise RuntimeError('Presenter output validation failed')
        if abs(float(checked['format']['duration'])-duration)>.2:raise RuntimeError('Presenter changed video duration')
        shutil.copyfile(video,video.with_name('product-render.mp4'))
        shutil.copyfile(final,video)
    return {'presenter':presenter,'voice_engine':'espeak-ng','presenter_is_photorealistic':False,'mouth_motion':'audio energy, not phoneme lip sync' if presenter=='visible_humanoid_illustrated' else 'none','video_validation':checked}

def main():
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument('--rotation',type=int,choices=(90,180,360),default=180)
    p.add_argument('--presenter',choices=('voiceover_only','visible_humanoid_illustrated'),default='voiceover_only')
    p.add_argument('--product-name',default='Product showcase')
    p.add_argument('--narration-text',default='')
    config,remaining=p.parse_known_args()
    base=argparse.ArgumentParser(add_help=False)
    base.add_argument('--voice',choices=('off','on'),default='on')
    base.add_argument('--duration',type=int,default=5)
    base.add_argument('--main-words',default='')
    known,_=base.parse_known_args(remaining)
    if config.presenter=='visible_humanoid_illustrated' and known.voice=='off':
        raise ValueError('Visible speaking humanoid requires voice=on; choose voiceover_only for music-only or silent video')
    import free3d
    from creator import local_offer
    script=' '.join((config.narration_text.strip() or (config.product_name+'. '+local_offer(known.main_words))).split())
    if not script or len(script)>500:raise ValueError('Use 1–500 narration characters')
    with tempfile.TemporaryDirectory(prefix='product-voice-') as temporary:
        narration=Path(temporary)/'voice.wav'
        if known.voice=='on':
            if not shutil.which('espeak-ng'):raise RuntimeError('Install espeak-ng for free local narration')
            subprocess.run(['espeak-ng','-v','en-us','-s','160','-w',str(narration),'--stdin'],input=script,text=True,capture_output=True,check=True,timeout=120)
            _,seconds=audio_levels(narration)
            if seconds>known.duration-.1:
                raise ValueError('Narration will not fit. Shorten it or choose a longer duration; render has not started.')
        original_argv=sys.argv;original_interpret=free3d.interpret
        try:
            free3d.interpret=lambda idea,motion:rotation_config(original_interpret(idea,motion),config.rotation)
            # Audio is added once after rendering; duplicate final flag overrides legacy voice input.
            sys.argv=[original_argv[0],*remaining,'--voice','off']
            free3d.main()
        finally:
            free3d.interpret=original_interpret;sys.argv=original_argv
        for folder in sorted((free3d.ROOT/'output_free3d').glob('variant-*')):
            result={'rotation_degrees':config.rotation,'free_only':True,'paid_api_calls':False,'voice':'off','presenter':'none','rotation_is_verified_product_geometry':False}
            if known.voice=='on':result.update(add_presenter(folder/'reel.mp4',narration,config.presenter),voice='on')
            result['product_name']=config.product_name
            (folder/'presentation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            if known.voice=='on':(folder/'narration.txt').write_text(script,encoding='utf-8')

if __name__=='__main__':main()
