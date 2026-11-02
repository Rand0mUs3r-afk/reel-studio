import io
from PIL import Image
import pytest
import batch_upload as batch

def photo(color='red'):
    out=io.BytesIO();Image.new('RGB',(400,600),color).save(out,format='PNG');return out.getvalue()

@pytest.fixture
def workspace(tmp_path,monkeypatch):
    monkeypatch.setattr(batch,'ROOT',tmp_path)
    return tmp_path

def test_uploads_and_urls_combine(workspace,monkeypatch):
    monkeypatch.setattr(batch.studio,'fetch',lambda *a,**k:photo('blue'))
    job,queue,errors=batch.prepare([('one.png',photo())],'https://example.com/two.png')
    assert len(queue)==2 and not errors
    assert [item['label'] for item in queue]==['Upload 1','URL 1']

def test_duplicates_removed(workspace,monkeypatch):
    monkeypatch.setattr(batch.studio,'fetch',lambda *a,**k:photo())
    _,queue,_=batch.prepare([('one.png',photo())],'https://example.com/one.png')
    assert len(queue)==1

def test_names_cannot_escape(workspace):
    _,queue,_=batch.prepare([('../../outside.png',photo())],'')
    assert len(queue)==1 and not (workspace/'outside.png').exists()

def test_limits_and_invalid_inputs(workspace):
    with pytest.raises(ValueError): batch.prepare([('a',photo())]*9,'')
    _,queue,errors=batch.prepare([('bad.jpg',b'not an image')],'')
    assert not queue and len(errors)==1

def test_option_and_batch_id_validation():
    with pytest.raises(ValueError): batch.options({'source':'/etc/passwd'})
    with pytest.raises(ValueError): batch.job_path('../escape')
    assert batch.options({'variants':2})==['--variants=2']


def test_isolated_runtimes_and_outputs_only_archive(workspace,monkeypatch):
    import zipfile
    for name in batch.CORE: (workspace/name).write_text('')
    monkeypatch.setattr(batch,'preflight',lambda:None)
    class Process:
        def __init__(self,*a,**kwargs):
            assert kwargs['start_new_session'] is True
            output=kwargs['cwd']/'output_free3d'/'variant-01';output.mkdir(parents=True)
            (output/'reel.mp4').write_bytes(b'unit-test-placeholder')
        def wait(self,**kwargs): return 0
    monkeypatch.setattr(batch.subprocess,'Popen',Process)
    job,_,_=batch.prepare([('a.png',photo()),('b.png',photo('blue'))],'')
    results=batch.render_batch(job,{'variants':1})
    assert len(results)==2 and all(item['success'] for item in results)
    with zipfile.ZipFile(batch.archive(job)) as archive:
        assert len([name for name in archive.namelist() if name.endswith('.mp4')])==2
        assert not any(name.endswith(('.py','input.png','render.log')) for name in archive.namelist())
