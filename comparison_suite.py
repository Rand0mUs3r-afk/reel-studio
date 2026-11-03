"""Compare intact-photo ads, segmented-photo ads and optional approximate 3D."""
import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def attempt(results,name,folder,action,warning):
    started=time.monotonic()
    result={'name':name,'folder':folder,'warning':warning,'status':'failed'}
    try:
        action()
        result['status']='completed'
    except Exception as exc:
        # Do not copy external response bodies, user URLs or subprocess output into reports.
        result['error_type']=type(exc).__name__
    result['seconds']=round(time.monotonic()-started,2)
    results.append(result)
    return result

def write_report(folder,results,preview):
    folder=Path(folder)
    document={'preview_only':preview,'paid_api_calls':False,'publishing':'disabled',
              'generated_photographic_angles':'not implemented; requires separately approved backend',
              'results':results,'review':['Product shape and logo','Label readability','Cutout edges','Offer wording','Motion and pacing','Unknown sides in 3D are estimates']}
    (folder/'comparison.json').write_text(json.dumps(document,indent=2),encoding='utf-8')
    cards=[]
    for result in results:
        body='<h2>'+html.escape(result['name'])+'</h2><p>'+html.escape(result['status'])+'</p><p>'+html.escape(result['warning'])+'</p>'
        if result['status']=='completed':
            relative=result['folder']
            if (folder/relative/'ad.mp4').exists():
                body+=f'<video controls preload="metadata" src="{html.escape(relative)}/ad.mp4" style="max-width:300px"></video>'
            elif (folder/relative/'reel.mp4').exists():
                body+=f'<video controls preload="metadata" src="{html.escape(relative)}/reel.mp4" style="max-width:300px"></video>'
            if (folder/relative/'cover.png').exists():
                body+=f'<p><img src="{html.escape(relative)}/cover.png" style="max-width:220px" alt="Variant preview"></p>'
        elif result.get('error_type'):
            body+='<p>Failure type: '+html.escape(result['error_type'])+'</p>'
        cards.append('<section>'+body+'</section>')
    (folder/'comparison.html').write_text('<!doctype html><html><meta charset="utf-8"><title>Product ad comparison</title><body><h1>Product ad comparison</h1><p>Extract the entire archive, then open this file. Review product fidelity; completion is not a quality guarantee.</p>'+''.join(cards)+'</body></html>',encoding='utf-8')
    return document

def segment(photos):
    import numpy as np
    import rembg
    session=rembg.new_session('u2netp')
    output=[]
    for photo in photos:
        image=rembg.remove(photo.convert('RGBA'),session=session).convert('RGBA')
        alpha=np.asarray(image.getchannel('A'))
        retained=float((alpha>32).mean())
        if not .01<retained<.99:
            raise ValueError('Background removal did not produce a usable cutout')
        output.append(image)
    return output

def mesh_variant(photo,output):
    if not (ROOT/'.triposr').is_dir() or not shutil.which('blender'):
        raise RuntimeError('Install the optional pinned TripoSR and Blender dependencies')
    # Existing free3d writes under its script directory: isolate that directory per run.
    with tempfile.TemporaryDirectory(prefix='ad-mesh-') as temp:
        work=Path(temp)
        for name in ('free3d.py','studio.py','creator.py','reconstruct_cpu.py','render_free3d.py'):
            shutil.copyfile(ROOT/name,work/name)
        (work/'.triposr').symlink_to(ROOT/'.triposr',target_is_directory=True)
        photo.save(work/'source.png')
        environment={k:v for k,v in os.environ.items() if not k.endswith(('_KEY','_TOKEN'))}
        command=[sys.executable,str(work/'free3d.py'),'--input-mode','repository_image','--source','source.png','--variants','1','--duration','5','--quality','preview_360p','--mesh-resolution','64','--motion','orbit','--captions','none','--music','off','--voice','off']
        subprocess.run(command,cwd=work,env=environment,check=True,capture_output=True,timeout=10800)
        source=work/'output_free3d'
        video=source/'variant-01'/'reel.mp4'
        if not video.is_file() or video.stat().st_size==0:
            raise RuntimeError('3D workflow returned without a video')
        shutil.copytree(source,output)
        shutil.copyfile(video,output/'reel.mp4')
        if (source/'variant-01'/'cover.png').exists():
            shutil.copyfile(source/'variant-01'/'cover.png',output/'cover.png')
        (output/'warning.txt').write_text('Approximate single-image reconstruction. Hidden sides, shape, logos and labels are NOT verified. This is a five-second 360p silent showcase, not a complete offer ad.',encoding='utf-8')

def suite(photos,plan,output,duration=15,resolution='720p',include_3d=False,preview=False):
    import product_ad as ads
    from ad_sources import cover_angles
    output=Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Comparison output must be empty')
    if not 1<=len(photos)<=6:
        raise ValueError('Compare one to six photos of the same product')
    output.mkdir(parents=True,exist_ok=True)
    plan=cover_angles(plan,len(photos))
    results=[]
    def save():write_report(output,results,preview)
    attempt(results,'Intact photo ad','01-intact',lambda:ads.render(photos,plan,output/'01-intact',duration,resolution,background='#0F172A',accent='#38BDF8',preview_only=preview),'Original image fitted into a designed layout. No new angles or generated product pixels.')
    save()
    cutouts=[]
    extraction=attempt(results,'Background removal','02-segmentation',lambda:cutouts.extend(segment(photos)),'Automatic segmentation may remove fine details or transparent product areas; inspect edges.')
    save()
    for name,folder,bg,accent in [('Cutout — dark','03-cutout-dark','#111827','#FBBF24'),('Cutout — light','04-cutout-light','#64748B','#F8FAFC')]:
        if extraction['status']=='completed':
            attempt(results,name,folder,lambda folder=folder,bg=bg,accent=accent:ads.render(cutouts,plan,output/folder,duration,resolution,background=bg,accent=accent,preview_only=preview),'Original photographed view with automatic background removal; not an invented new view.')
        else:
            results.append({'name':name,'folder':folder,'status':'skipped','warning':'Background removal failed; intact-photo results are retained.'})
        save()
    if include_3d and not preview:
        attempt(results,'Approximate 3D orbit','05-mesh',lambda:mesh_variant(photos[0],output/'05-mesh'),'Uses only the first image. Five-second silent 360p orbit; not multi-view fusion. Hidden sides, shape, logos and labels may be invented or wrong.')
    else:
        results.append({'name':'Approximate 3D orbit','folder':'05-mesh','status':'skipped','warning':'Not requested or preview-only run; use include_3d to attempt it.'})
    save()
    return results

def main():
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--urls-file',help='Text file of direct image URLs; one per line, optional labels')
    source.add_argument('--photos',nargs='+')
    p.add_argument('--product',required=True)
    p.add_argument('--brand',default='')
    p.add_argument('--hook',default='')
    p.add_argument('--benefit',action='append',default=[])
    p.add_argument('--offer',default='')
    p.add_argument('--cta',default='Discover more')
    p.add_argument('--duration',type=int,choices=(15,30),default=15)
    p.add_argument('--resolution',choices=('720p','1080p'),default='720p')
    p.add_argument('--include-3d',action='store_true')
    p.add_argument('--preview-only',action='store_true')
    p.add_argument('--output',default='output_comparison')
    a=p.parse_args()
    import product_ad as ads
    if a.urls_file:
        from ad_sources import prepare_inputs
        photos,_=prepare_inputs([],Path(a.urls_file).read_text())
    else:
        if not 1<=len(a.photos)<=6:p.error('Use one to six photos')
        photos=[ads.photo_from_bytes(Path(path).read_bytes()) for path in a.photos]
    plan=ads.make_plan(a.product,a.benefit,a.offer,a.cta,a.hook,a.brand)
    results=suite(photos,plan,a.output,a.duration,a.resolution,a.include_3d,a.preview_only)
    if not any(r['status']=='completed' and r['name']!='Background removal' for r in results):
        raise SystemExit('No render completed; see comparison.json for status')

if __name__=='__main__':main()
