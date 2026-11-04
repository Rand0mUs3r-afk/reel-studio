import json
from pathlib import Path
import pytest
from PIL import Image
from inbox_video import discover,batch

def photo(path):Image.new('RGB',(200,240),'blue').save(path)

def test_discovers_all_requested_extensions_and_ignores_other_files(tmp_path):
    folder=tmp_path/'inbox';folder.mkdir()
    for name in ['d.jpg','B.JPEG','c.PNG','a.jpeg']:photo(folder/name)
    (folder/'.gitkeep').touch();(folder/'note.txt').write_text('not an image')
    (folder/'nested').mkdir();photo(folder/'nested'/'not-direct.jpg')
    assert [p.name for p in discover(tmp_path)]==['a.jpeg','B.JPEG','c.PNG','d.jpg']

def test_rejects_empty_invalid_and_symlink_images(tmp_path):
    folder=tmp_path/'inbox';folder.mkdir()
    with pytest.raises(ValueError):discover(tmp_path)
    (folder/'bad.jpg').write_text('not an image')
    with pytest.raises(Exception):discover(tmp_path)
    (folder/'bad.jpg').unlink()
    outside=tmp_path/'outside.png';photo(outside)
    (folder/'linked.png').symlink_to(outside)
    with pytest.raises(ValueError):discover(tmp_path)

def test_processes_every_file_and_retains_failures(tmp_path):
    folder=tmp_path/'inbox';folder.mkdir()
    for name in ['a.jpg','b.png','c.jpeg','d.jpg']:photo(folder/name)
    calls=[]
    def fake(root,image,output,extra):
        calls.append(image.name);output.mkdir(parents=True)
        if image.name=='b.png':raise RuntimeError('Test failure')
    result=batch(tmp_path,'separate_videos',['--rotation','180'],fake)
    assert calls==['a.jpg','b.png','c.jpeg','d.jpg']
    assert [r['status'] for r in result['sources']]==['completed','failed','completed','completed']
    assert result['source_count']==4 and result['multi_view_fusion'] is False
    assert json.loads((tmp_path/'output_free3d'/'inbox-manifest.json').read_text())==result
    with pytest.raises(ValueError):batch(tmp_path,'separate_videos',[],fake)

def test_combined_mode_never_silently_omits_failed_sources(tmp_path):
    folder=tmp_path/'inbox';folder.mkdir();photo(folder/'a.jpg')
    def fail(*args):raise RuntimeError('Test failure')
    result=batch(tmp_path,'combined_video',[],fail)
    assert result['combined_videos']==[] and result['combined_error_type']=='ValueError'


def test_real_combined_video_contains_both_clips(tmp_path):
    import shutil,subprocess
    from inbox_video import combine
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):pytest.skip('FFmpeg required')
    rows=[]
    for i,color in enumerate(['red','blue'],1):
        folder=tmp_path/f'source-{i:03d}'/'variant-01';folder.mkdir(parents=True)
        subprocess.run(['ffmpeg','-nostdin','-y','-f','lavfi','-i',f'color=c={color}:s=72x128:r=24:d=1','-c:v','libx264','-threads','2','-pix_fmt','yuv420p',str(folder/'reel.mp4')],capture_output=True,check=True)
        rows.append({'folder':f'source-{i:03d}','status':'completed'})
    outputs=combine(tmp_path,rows)
    assert outputs==['combined-variant-01.mp4']
    info=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(tmp_path/outputs[0])],capture_output=True,text=True,check=True)
    assert float(json.loads(info.stdout)['format']['duration'])==pytest.approx(2,abs=.15)
