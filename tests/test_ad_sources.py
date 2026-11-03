import copy
import pytest
from ad_sources import parse_urls,cover_angles

def test_preserves_order_labels_and_signed_query():
    result=parse_urls('Front | https://images.example/front.png?token=a,b\n\nBack | https://images.example/back.png')
    assert result==[('Front','https://images.example/front.png?token=a,b'),('Back','https://images.example/back.png')]

def test_default_labels_and_empty():
    assert parse_urls('')==[]
    assert parse_urls('https://images.example/side.png')[0][0]=='Angle 1'

@pytest.mark.parametrize('url',['http://example.com/x.png','https://user:pass@example.com/x.png','https://example.com:444/x.png','file:///tmp/x.png','https://example.com/x.png#secret'])
def test_rejects_unsafe_url_shapes(url):
    with pytest.raises(ValueError):parse_urls(url)

def test_limit():
    with pytest.raises(ValueError):parse_urls('\n'.join(f'https://example.com/{i}.png' for i in range(7)))

def test_every_angle_is_used_and_offer_stays_before_cta():
    original={'product':'Bottle','offer':'2 for $30','scenes':[{'role':'hook','text':'Bottle'},{'role':'offer','text':'2 for $30'},{'role':'cta','text':'Shop'}]}
    snapshot=copy.deepcopy(original)
    result=cover_angles(original,6)
    assert original==snapshot
    assert len(result['scenes'])==6
    assert [s['role'] for s in result['scenes']][-2:]==['offer','cta']
    assert {i%6 for i in range(len(result['scenes']))}==set(range(6))
    assert result['offer']=='2 for $30'
    assert result['all_input_angles_used']
    with pytest.raises(ValueError):cover_angles(original,7)
