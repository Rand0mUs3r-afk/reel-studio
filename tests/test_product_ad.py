import io
import os
import shutil
import pytest
from PIL import Image
import product_ad as ads

def image_bytes(size=(300,300)):
    data=io.BytesIO();Image.new('RGB',size,'red').save(data,format='PNG');return data.getvalue()

def test_exact_offer_and_no_invented_benefits():
    p=ads.make_plan('Bottle',offer='2 for $30. Ends Friday.',cta='Visit our store')
    assert p['offer']=='2 for $30. Ends Friday.'
    assert [s['role'] for s in p['scenes']]==['hook','offer','cta']
    assert not p['generative_product_edits']

def test_six_scene_limit():
    p=ads.make_plan('Bottle',['User fact 1','User fact 2','User fact 3'],'2 for $30')
    assert len(p['scenes'])==6
    with pytest.raises(ValueError):ads.make_plan('Bottle',['a','b','c','d'])

def test_input_validation():
    with pytest.raises(ValueError):ads.make_plan('')
    with pytest.raises(ValueError):ads.make_plan('Bottle',offer='a'*141)
    with pytest.raises(ValueError):ads.color('red; rm -rf /')
    with pytest.raises(ValueError):ads.photo_from_bytes(image_bytes((100,100)))
    with pytest.raises(Exception):ads.photo_from_bytes(b'not an image')

def test_preview_has_original_photo_and_timeline(tmp_path):
    image=ads.photo_from_bytes(image_bytes())
    p=ads.make_plan('Bottle',offer='2 for $30')
    folder=ads.render([image],p,tmp_path/'preview',preview_only=True)
    import json
    timeline=json.loads((folder/'storyboard.json').read_text())['scenes']
    assert timeline[0]['start']==0 and timeline[-1]['end']==15
    assert all(a['end']==b['start'] for a,b in zip(timeline,timeline[1:]))
    with Image.open(folder/'scene-01.png') as frame:
        assert frame.size==(720,1280)
        assert frame.getpixel((360,640))[:3]==(255,0,0)
    assert not (folder/'ad.mp4').exists()
    assert '00:00:15,000' in (folder/'subtitles.srt').read_text()
    with pytest.raises(ValueError):ads.render([image],p,folder,preview_only=True)

@pytest.mark.skipif(os.environ.get('PHOTO_AD_SMOKE')!='1' or not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='Set PHOTO_AD_SMOKE=1 with FFmpeg for a real 15-second encode')
def test_real_mp4(tmp_path):
    p=ads.make_plan('Test bottle')
    folder=ads.render([ads.photo_from_bytes(image_bytes())],p,tmp_path/'render')
    assert (folder/'ad.mp4').stat().st_size>0
    assert (folder/'validation.json').is_file()
