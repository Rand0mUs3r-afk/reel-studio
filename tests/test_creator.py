from types import SimpleNamespace
import pytest
import creator

@pytest.mark.parametrize('words,sentence',[
    ('special deal, 2 or 3','There is a special deal on 2 or 3 items.'),
    ('2 for $30','Get 2 for $30.'),
    ('20% off today only','Enjoy 20% off today only.'),
    ('buy 2 get 1 free','Buy 2 and get 1 free.'),
])
def test_offer_sentence(words,sentence):
    assert creator.local_offer(words)==sentence

@pytest.mark.parametrize('sentence',['Buy 2 and get 1 free.','Get 2 for $30.','Offer on 2 or 3 today only.'])
def test_offer_guard(sentence):
    with pytest.raises(ValueError): creator.faithful_offer('deal 2 or 3',sentence)

def test_strict_idea_needs_cloud_direction():
    args=SimpleNamespace(engine='basic')
    config=SimpleNamespace(main_words='',reel_idea='Quiet unboxing',idea_mode='follow_my_idea')
    with pytest.raises(ValueError,match='cloud_ai'):
        creator.extend_plan([],'Product',[],args,0,config)
