import json,struct
import pytest
import free3d

def glb(document):
    chunk=json.dumps(document).encode();chunk+=b' '*((-len(chunk))%4)
    return b'glTF'+struct.pack('<IIII',2,20+len(chunk),len(chunk),0x4e4f534a)+chunk

def test_mesh_validation():
    data=glb({'meshes':[{}]});assert free3d.check_model(data)==data

@pytest.mark.parametrize('uri',['https://example.com/image.png','../../file.png','file:///tmp/file'])
def test_external_resources_rejected(uri):
    with pytest.raises(ValueError): free3d.check_model(glb({'meshes':[{}],'images':[{'uri':uri}]}))

def test_keyword_direction():
    plan=free3d.interpret('slow orbit, light background, no music','auto')
    assert plan['motion']=='orbit' and plan['angle']==90 and plan['light'] and plan['silence']

def test_explicit_motion_wins():
    assert free3d.interpret('float','turntable')['motion']=='turntable'
