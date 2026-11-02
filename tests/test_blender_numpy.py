import sys
import numpy as np
import pytest
import render_free3d as renderer

def test_existing_numpy_needs_no_install(monkeypatch,tmp_path):
    monkeypatch.setattr(renderer.importlib,'import_module',lambda name:np)
    monkeypatch.setattr(renderer.subprocess,'run',lambda *a,**k:pytest.fail('Unnecessary pip call'))
    assert renderer.ensure_numpy(tmp_path,(3,11)) is np

@pytest.mark.parametrize('version,abi,requirement',[((3,11),'cp311','numpy==1.26.4'),((3,12),'cp312','numpy==1.26.4'),((3,13),'cp313','numpy>=2.1,<3')])
def test_installs_for_blender_not_host_python(monkeypatch,tmp_path,version,abi,requirement):
    attempts=[];commands=[]
    def load(name):
        attempts.append(name)
        if len(attempts)==1: raise ModuleNotFoundError('numpy')
        return np
    monkeypatch.setattr(renderer.importlib,'import_module',load)
    monkeypatch.setattr(renderer,'clear_numpy',lambda:None)
    monkeypatch.setattr(renderer.sys,'path',list(sys.path))
    monkeypatch.setenv('REEL_STUDIO_HOST_PYTHON','/host/python')
    monkeypatch.setattr(renderer.subprocess,'run',lambda cmd,**kwargs:commands.append(cmd))
    assert renderer.ensure_numpy(tmp_path,version) is np
    command=commands[0]
    assert command[0]=='/host/python'
    assert command[command.index('--python-version')+1]==f'{version[0]}.{version[1]}'
    assert command[command.index('--abi')+1]==abi
    assert '--only-binary=:all:' in command and requirement in command


def test_check_deps_does_not_start_render(monkeypatch):
    calls=[]
    monkeypatch.setattr(renderer,'ensure_numpy',lambda:calls.append('numpy'))
    monkeypatch.setattr(renderer,'check_glb_import',lambda:calls.append('glb'))
    monkeypatch.setattr(renderer,'render_scene',lambda *a:pytest.fail('Unexpected render'))
    monkeypatch.setattr(renderer.sys,'argv',['blender','--','--check-deps'])
    renderer.main()
    assert calls==['numpy','glb']
