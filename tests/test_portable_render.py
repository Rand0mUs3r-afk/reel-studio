from types import SimpleNamespace as NS
import pytest
import render_free3d as renderer

def test_no_denoiser_is_required():
    layer=NS(cycles=NS(use_denoising=True))
    scene=NS(render=NS(),cycles=NS(use_denoising=True),view_layers=[layer,NS()],use_nodes=True)
    renderer.configure_cpu_render(scene)
    assert scene.render.engine=='CYCLES' and scene.cycles.device=='CPU'
    assert scene.cycles.use_denoising is False and layer.cycles.use_denoising is False
    assert scene.use_nodes is False and scene.render.use_compositing is False
    assert scene.cycles.samples==16

def info():
    return {'streams':[{'codec_type':'video','codec_name':'h264','width':72,'height':128},{'codec_type':'audio','codec_name':'aac'}],'format':{'duration':'0.084'}}

def test_valid_mp4_metadata(): renderer.validate_smoke_metadata(info())

@pytest.mark.parametrize('bad',[
    {'streams':[],'format':{'duration':'0'}},
    {'streams':[{'codec_type':'video','codec_name':'h264','width':72,'height':128}],'format':{'duration':'0.084'}},
    {'streams':[{'codec_type':'video','codec_name':'vp9','width':72,'height':128},{'codec_type':'audio','codec_name':'aac'}],'format':{'duration':'0.084'}}
])
def test_invalid_native_output_is_rejected(bad):
    with pytest.raises(RuntimeError): renderer.validate_smoke_metadata(bad)


def test_renderer_never_forces_denoising_on():
    import ast
    from pathlib import Path
    tree=ast.parse(Path(renderer.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='use_denoising' for t in node.targets):
            assert isinstance(node.value,ast.Constant) and node.value.value is False

@pytest.mark.parametrize('mode',['RGB','RGBA'])
def test_native_ffmpeg_overlay_audio_and_video(tmp_path,mode):
    import shutil
    from PIL import Image,ImageDraw
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'): pytest.skip('Native encoder not installed')
    frames=tmp_path/'frames';frames.mkdir()
    for i,color in ((1,'teal'),(2,'orange')):
        image=Image.new(mode,(72,128),'#222222');draw=ImageDraw.Draw(image)
        draw.rectangle((8*i,30,40+i*8,95),fill=color);image.save(frames/f'frame_{i:05d}.png')
    target=tmp_path/'smoke.mp4';renderer.encode_smoke(frames,target)
    assert target.stat().st_size>0
