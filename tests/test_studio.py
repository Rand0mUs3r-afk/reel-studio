from types import SimpleNamespace
import socket
import pytest
from PIL import Image
import studio


def test_product_structured_gallery():
    html='<title>Store</title><script type="application/ld+json">{"@type":"Product","name":"Example bottle","image":["/one.jpg",{"url":"https://cdn.example.com/two.jpg"}]}</script>'
    title,images=studio.product(html,'https://shop.example.com/item')
    assert title=='Example bottle'
    assert images==['https://shop.example.com/one.jpg','https://cdn.example.com/two.jpg']


@pytest.mark.parametrize('url',['http://example.com','https://user:pass@example.com','https://example.com:444'])
def test_unsafe_url_shapes(url):
    with pytest.raises(ValueError): studio.target(url)


def test_local_ip_rejected(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(ValueError): studio.target('https://example.com')


def test_repository_traversal_rejected():
    with pytest.raises(ValueError): studio.local_path('../outside')


def test_voice_override_and_original_audio_plan():
    args=SimpleNamespace(input_mode='photo_urls',duration=15,style='minimal',instructions='',engine='basic',voice='off')
    result=studio.plan([], 'Example',[],args,0)
    assert result['voice'] is False and type(result['music']) is bool
    assert studio.plan([], 'Example',[],args,3)['music'] is False


def test_music_wave_duration(tmp_path):
    import wave
    path=tmp_path/'music.wav';studio.backing(path,1,'calm')
    with wave.open(str(path)) as audio: assert audio.getnframes()==22050


def test_portrait_card(tmp_path):
    photo=tmp_path/'photo.png';Image.new('RGB',(400,600),'red').save(photo)
    output=tmp_path/'card.png';studio.card(photo,'A closer look',None,240,426,output)
    assert Image.open(output).size==(240,426)


def test_ai_options_fail_without_secret(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(ValueError,match='OPENAI_API_KEY'): studio.api('images/generations',{})
