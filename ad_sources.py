"""Ordered direct-image URLs for one multi-angle product ad (maximum six)."""
import copy
import hashlib
from urllib.parse import urlsplit

MAX_ANGLES=6

def parse_urls(value):
    lines=[line.strip() for line in value.splitlines() if line.strip()]
    if len(lines)>MAX_ANGLES:
        raise ValueError('Use at most six direct image URLs')
    entries=[]
    for index,line in enumerate(lines,1):
        label,url=(part.strip() for part in line.split(' | ',1)) if ' | ' in line else (f'Angle {index}',line)
        if not label or len(label)>48:
            raise ValueError(f'URL {index}: angle label must contain 1–48 characters')
        try:
            p=urlsplit(url)
            valid=p.scheme=='https' and bool(p.hostname) and not p.username and not p.password and p.port in (None,443) and not p.fragment
        except ValueError:
            valid=False
        if not valid:
            raise ValueError(f'URL {index}: use a public HTTPS direct image URL on port 443')
        entries.append((label,url))
    return entries

def cover_angles(plan,count):
    if not 1<=count<=MAX_ANGLES:
        raise ValueError('Multi-angle mode supports one to six combined photos')
    result=copy.deepcopy(plan)
    scenes=result['scenes']
    if not 2<=len(scenes)<=6:
        raise ValueError('Expected a two-to-six-scene product-ad plan')
    insert_at=next((i for i,s in enumerate(scenes) if s['role']=='offer'),len(scenes)-1)
    while len(scenes)<count:
        scenes.insert(insert_at,{'role':'detail','text':result['product']})
        insert_at+=1
    result['input_mode']='ordered_multi_angle'
    result['all_input_angles_used']=True
    return result

def prepare_inputs(uploads,url_text):
    import product_ad as ads
    from studio import fetch
    entries=parse_urls(url_text)
    if not 1<=len(uploads)+len(entries)<=MAX_ANGLES:
        raise ValueError('Use one to six combined uploads and URLs in multi-angle mode')
    photos=[];manifest=[];seen=set()
    def add(data,label,kind):
        digest=hashlib.sha256(data).hexdigest()
        if digest in seen:
            raise ValueError('Duplicate image detected; remove repeated uploads or URLs')
        image=ads.photo_from_bytes(data)
        seen.add(digest);photos.append(image)
        manifest.append({'index':len(photos)-1,'label':label,'source_type':kind})
    for index,(_,data) in enumerate(uploads,1):
        add(data,f'Upload {index}','upload')
    for index,(label,url) in enumerate(entries,1):
        try:
            add(fetch(url,limit=15_000_000),label,'direct_image_url')
        except Exception as exc:
            raise ValueError(f'URL {index} failed or is a duplicate image. Use an accessible HTTPS image, not a product webpage; no angles were silently skipped.') from None
    # URLs, signed query parameters, and original filenames are not written to outputs.
    return photos,manifest
