"""Photo-preserving product ads. Local-only, no generative product reconstruction."""
import argparse
import json
import math
import re
import shutil
import subprocess
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

Image.MAX_IMAGE_PIXELS = 30_000_000
FPS = 24

def text(value, name, limit, required=False):
    value = ' '.join(str(value).split())
    if (required and not value) or len(value) > limit:
        raise ValueError(f'{name} must contain {1 if required else 0}–{limit} characters')
    return value

def make_plan(product, benefits=(), offer='', cta='Discover more', hook='', brand=''):
    product = text(product, 'Product name', 64, True)
    brand = text(brand, 'Brand', 48)
    hook = text(hook, 'Hook', 90) or product
    cta = text(cta, 'Call to action', 64, True)
    offer = text(offer, 'Offer', 140)
    if isinstance(benefits, str):
        benefits = benefits.splitlines()
    benefits = [text(v, 'Verified benefit', 96) for v in benefits if str(v).strip()]
    if len(benefits) > 3:
        raise ValueError('Use at most three verified benefits')
    scenes = [{'role': 'hook', 'text': hook}]
    scenes += [{'role': 'benefit', 'text': value} for value in benefits]
    if offer:
        scenes.append({'role': 'offer', 'text': offer})
    scenes.append({'role': 'cta', 'text': cta})
    return {'product': product, 'brand': brand, 'offer': offer, 'scenes': scenes,
            'claims_source': 'User-supplied text, not independently verified',
            'renderer': 'photo_preserving_2d', 'generative_product_edits': False}

def color(value):
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        raise ValueError('Use a six-digit hex color, for example #0F172A')
    return value

def photo_from_bytes(data):
    if len(data) > 15_000_000:
        raise ValueError('Maximum 15 MB per image')
    with Image.open(__import__('io').BytesIO(data)) as image:
        image.load()
        image = ImageOps.exif_transpose(image).convert('RGBA')
        if min(image.size) < 200:
            raise ValueError('Image must be at least 200 pixels on each side')
        image.thumbnail((2400, 2400))
        return image.copy()

def font(size):
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                 '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise RuntimeError('Install DejaVu Sans fonts before rendering')

def fitted_text(draw, value, box, maximum, fill):
    if not value:
        return
    x, y, width, height = box
    for size in range(maximum, 11, -1):
        face = font(size)
        lines, line = [], ''
        for word in value.split():
            candidate = (line + ' ' + word).strip()
            if draw.textlength(candidate, font=face) > width and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        step = math.ceil(size * 1.35)
        if lines and len(lines) * step <= height and all(draw.textlength(v, font=face) <= width for v in lines):
            top = y + (height - len(lines) * step) / 2
            for index, line in enumerate(lines):
                draw.text((x + width / 2, top + index * step), line, font=face, fill=fill, anchor='mt')
            return
    raise ValueError('Text cannot fit safely; shorten the wording')

def frame(photo, plan, scene, width, height, background='#0F172A', accent='#38BDF8', logo=None):
    color(background); color(accent)
    canvas = Image.new('RGB', (width, height), background)
    # Contain, never crop or reconstruct the original product photo.
    foreground = ImageOps.contain(photo.convert('RGBA'), (int(width*.80), int(height*.45)))
    canvas.paste(foreground, ((width-foreground.width)//2, int(height*.28)+(int(height*.45)-foreground.height)//2), foreground)
    if logo is not None:
        mark = ImageOps.contain(logo.convert('RGBA'), (int(width*.28), int(height*.065)))
        canvas.paste(mark, ((width-mark.width)//2, int(height*.05)), mark)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((int(width*.12), int(height*.745), int(width*.88), int(height*.75)), radius=3, fill=accent)
    fitted_text(draw, plan['brand'], (width*.1, height*.125, width*.8, height*.045), int(width*.04), '#FFFFFF')
    fitted_text(draw, plan['product'], (width*.1, height*.18, width*.8, height*.075), int(width*.065), '#FFFFFF')
    fitted_text(draw, scene['text'], (width*.1, height*.78, width*.8, height*.12), int(width*.065), '#FFFFFF')
    return canvas

def run(command):
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True, timeout=600)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError('Media command failed: ' + exc.stderr[-2000:]) from exc

def timecode(seconds):
    milliseconds = round(seconds*1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}'

def verify_video(path, width, height, duration, audio):
    probe = json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]).stdout)
    streams = probe.get('streams', [])
    video = next((v for v in streams if v.get('codec_type') == 'video'), {})
    if video.get('codec_name') != 'h264' or (video.get('width'),video.get('height')) != (width,height):
        raise RuntimeError('Output video dimensions or codec do not match the requested format')
    if abs(float(probe['format']['duration'])-duration) > .15:
        raise RuntimeError('Output duration does not match the storyboard')
    if audio and not any(v.get('codec_type')=='audio' for v in streams):
        raise RuntimeError('Requested audio is missing')
    return probe

def render(photos, plan, output, duration=15, resolution='720p', background='#0F172A', accent='#38BDF8', logo=None, music=None, voice=False, preview_only=False):
    if not 1 <= len(photos) <= 8:
        raise ValueError('Supply one to eight photos of this product')
    if duration not in (15,30) or resolution not in ('720p','1080p'):
        raise ValueError('Use 15/30 seconds and 720p/1080p')
    color(background); color(accent)
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose an empty output folder to avoid overwriting previous ads')
    output.mkdir(parents=True, exist_ok=True)
    width = 1080 if resolution == '1080p' else 720
    height = width*16//9
    total_frames = duration*FPS
    scenes = plan['scenes']
    if not 2 <= len(scenes) <= 6:
        raise ValueError('Storyboard requires two to six scenes')
    counts = [total_frames//len(scenes) + (i < total_frames%len(scenes)) for i in range(len(scenes))]
    timeline, cursor = [], 0
    for i, (scene, count) in enumerate(zip(scenes, counts)):
        photo_index = i % len(photos)
        frame(photos[photo_index], plan, scene, width, height, background, accent, logo).save(output/f'scene-{i+1:02}.png')
        timeline.append({**scene, 'photo_index':photo_index, 'start':cursor/FPS, 'end':(cursor+count)/FPS})
        cursor += count
    shutil.copyfile(output/'scene-01.png', output/'cover.png')
    storyboard = {**plan, 'duration':duration, 'resolution':resolution, 'scenes':timeline, 'audio':{'voice':voice,'music':bool(music)}, 'publishing':'disabled'}
    (output/'storyboard.json').write_text(json.dumps(storyboard, indent=2), encoding='utf-8')
    (output/'caption.txt').write_text('\n'.join([plan['product'], *(s['text'] for s in scenes)]), encoding='utf-8')
    (output/'subtitles.srt').write_text('\n\n'.join(f"{i+1}\n{timecode(s['start'])} --> {timecode(s['end'])}\n{s['text']}" for i,s in enumerate(timeline)), encoding='utf-8')
    if preview_only:
        return output
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('Install FFmpeg and ffprobe to render video; previews were saved')
    import tempfile
    with tempfile.TemporaryDirectory(prefix='photo-ad-') as temp:
        work = Path(temp)
        narration = None
        if voice:
            if not shutil.which('espeak-ng'):
                raise RuntimeError('Install espeak-ng for optional English narration')
            narration = work/'voice.wav'
            script = '. '.join([plan['product'], *(s['text'] for s in scenes)])
            subprocess.run(['espeak-ng','-v','en-us','-s','165','-w',str(narration),'--stdin'],input=script, text=True, capture_output=True, check=True, timeout=120)
            with wave.open(str(narration)) as wav:
                if wav.getnframes()/wav.getframerate() > duration-.25:
                    raise ValueError('Narration exceeds the ad duration; shorten text, choose 30 seconds, or turn voice off')
        for i,count in enumerate(counts):
            z='min(zoom+0.00012,1.02)' if i%2==0 else 'if(eq(on,0),1.02,max(1,zoom-0.00012))'
            vf=f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={count}:s={width}x{height}:fps={FPS},format=yuv420p"
            run(['ffmpeg','-nostdin','-y','-i',str(output/f'scene-{i+1:02}.png'),'-vf',vf,'-frames:v',str(count),'-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','20',str(work/f'{i}.mp4')])
        listing = work/'concat.txt'
        listing.write_text(''.join(f"file '{i}.mp4'\n" for i in range(len(scenes))))
        silent = work/'silent.mp4'
        run(['ffmpeg','-nostdin','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(silent)])
        command = ['ffmpeg','-nostdin','-y','-i',str(silent)]
        if narration:
            command += ['-i',str(narration)]
        if music:
            command += ['-stream_loop','-1','-i',str(Path(music).resolve())]
        if narration and music:
            command += ['-filter_complex','[2:a]volume=0.18[m];[1:a][m]amix=inputs=2:duration=longest[a]','-map','0:v','-map','[a]']
        elif narration or music:
            command += ['-map','0:v','-map','1:a:0']
        command += ['-c:v','copy'] + (['-c:a','aac','-af','apad'] if (narration or music) and not (narration and music) else ['-c:a','aac'] if narration and music else ['-an'])
        command += ['-t',str(duration),'-movflags','+faststart',str(output/'ad.mp4')]
        run(command)
    report = verify_video(output/'ad.mp4',width,height,duration,bool(narration or music))
    (output/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return output

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--photos',nargs='+',required=True)
    p.add_argument('--product',required=True)
    p.add_argument('--brand',default='')
    p.add_argument('--hook',default='')
    p.add_argument('--benefit',action='append',default=[])
    p.add_argument('--offer',default='')
    p.add_argument('--cta',default='Discover more')
    p.add_argument('--duration',type=int,choices=(15,30),default=15)
    p.add_argument('--resolution',choices=('720p','1080p'),default='720p')
    p.add_argument('--background',default='#0F172A')
    p.add_argument('--accent',default='#38BDF8')
    p.add_argument('--logo')
    p.add_argument('--music',help='Local audio you have permission to use')
    p.add_argument('--voice',action='store_true')
    p.add_argument('--preview-only',action='store_true')
    p.add_argument('--output',default='output_ads')
    a = p.parse_args()
    if len(a.photos)>8:
        p.error('Maximum eight photos')
    photos = [photo_from_bytes(Path(v).read_bytes()) for v in a.photos]
    logo = photo_from_bytes(Path(a.logo).read_bytes()) if a.logo else None
    plan = make_plan(a.product,a.benefit,a.offer,a.cta,a.hook,a.brand)
    render(photos,plan,a.output,a.duration,a.resolution,a.background,a.accent,logo,a.music,a.voice,a.preview_only)

if __name__=='__main__':
    main()
