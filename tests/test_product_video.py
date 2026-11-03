import array
import math
import shutil
import sys
import wave
import pytest
from product_video import rotation_config,audio_levels,humanoid_frame,add_presenter,probe

@pytest.mark.parametrize('motion,factor',[('turntable',1),('orbit',1),('float',1),('reveal',.3)])
def test_rotation_is_exact_even_for_reveal(motion,factor):
    original={'motion':motion,'angle':90}
    selected=rotation_config(original,180)
    assert selected['angle']*factor==pytest.approx(180)
    assert original['angle']==90

def test_visible_character_is_illustrated_and_mouth_moves():
    closed=humanoid_frame(120,240,0)
    opened=humanoid_frame(120,240,1)
    assert closed.size==(120,240) and closed.mode=='RGBA'
    assert closed.tobytes()!=opened.tobytes()

def voice_file(path):
    rate=22050
    values=array.array('h',(int(5000*math.sin(2*math.pi*220*i/rate)) for i in range(rate)))
    if sys.byteorder!='little':values.byteswap()
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate);stream.writeframes(values.tobytes())

def test_audio_energy(tmp_path):
    path=tmp_path/'voice.wav';voice_file(path)
    levels,seconds=audio_levels(path)
    assert seconds==1 and max(levels)>0

@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='FFmpeg required')
@pytest.mark.parametrize('music',[False,True])
@pytest.mark.parametrize('mode',['voiceover_only','visible_humanoid_illustrated'])
def test_real_presenter_mux_with_synthetic_audio(tmp_path,mode,music):
    import subprocess
    video=tmp_path/'reel.mp4';wav=tmp_path/'voice.wav';voice_file(wav)
    subprocess.run(['ffmpeg','-nostdin','-y','-f','lavfi','-i','color=c=green:s=360x640:r=24:d=2','-c:v','libx264','-threads','2','-pix_fmt','yuv420p',str(video)],capture_output=True,check=True)
    if music:
        with_music=tmp_path/'with-music.mp4'
        subprocess.run(['ffmpeg','-nostdin','-y','-i',str(video),'-i',str(wav),'-c:v','copy','-c:a','aac','-af','apad','-t','2',str(with_music)],capture_output=True,check=True)
        shutil.copyfile(with_music,video)
    result=add_presenter(video,wav,mode)
    assert result['presenter']==mode
    assert (tmp_path/'product-render.mp4').is_file()
    assert any(s['codec_type']=='audio' for s in probe(video)['streams'])
