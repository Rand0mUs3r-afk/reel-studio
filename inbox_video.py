"""Discover all Inbox photos and run the existing product renderer for each."""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parent
EXTENSIONS={'.jpg','.jpeg','.png'}
Image.MAX_IMAGE_PIXELS=30_000_000

def discover(root):
    root=Path(root).resolve();folder=root/'inbox'
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError('Create a real inbox folder inside the repository')
    paths=sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS),key=lambda p:(p.name.casefold(),p.name))
    if not paths:raise ValueError('Inbox contains no .jpg, .jpeg or .png images')
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Inbox images must not be symlinks or point outside the repository')
        if path.stat().st_size>15_000_000:raise ValueError('An inbox image exceeds 15 MB: '+path.name)
        with Image.open(path) as image:
            if min(image.size)<200:raise ValueError('Inbox image is smaller than 200 pixels: '+path.name)
            image.verify()
    return paths

def render_one(root,image,folder,extra):
    folder.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='inbox-product-') as temporary:
        work=Path(temporary)
        for name in ('product_video.py','free3d.py','studio.py','creator.py','reconstruct_cpu.py','render_free3d.py'):
            shutil.copyfile(root/name,work/name)
        if (root/'.triposr').is_dir():
            (work/'.triposr').symlink_to(root/'.triposr',target_is_directory=True)
        source=work/('source'+image.suffix.lower());shutil.copyfile(image,source)
        command=[sys.executable,str(work/'product_video.py'),'--input-mode','repository_image','--source',source.name,*extra]
        environment={k:v for k,v in os.environ.items() if not k.endswith(('_KEY','_TOKEN'))}
        code=None
        try:
            with open(folder/'render.log','w',encoding='utf-8') as log:
                process=subprocess.Popen(command,cwd=work,env=environment,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
                try:code=process.wait(timeout=10800)
                except subprocess.TimeoutExpired:
                    if os.name=='posix':os.killpg(process.pid,signal.SIGKILL)
                    else:process.kill()
                    process.wait();raise
        finally:
            if (work/'output_free3d').is_dir():
                shutil.copytree(work/'output_free3d',folder,dirs_exist_ok=True)
        if code!=0:raise RuntimeError('Product render failed; see this source render.log')
        if not list(folder.glob('variant-*/reel.mp4')):
            raise RuntimeError('Renderer returned without any final videos')

def combine(output,rows):
    if any(row['status']!='completed' for row in rows):
        raise ValueError('Combined output requires every source to succeed; no failed images are omitted')
    sets=[{p.parent.name for p in (output/row['folder']).glob('variant-*/reel.mp4')} for row in rows]
    if not sets or not sets[0] or any(s!=sets[0] for s in sets):
        raise ValueError('All sources must contain the same completed variant set')
    results=[]
    with tempfile.TemporaryDirectory(prefix='inbox-concat-') as temporary:
        for variant in sorted(sets[0]):
            clips=[(output/row['folder']/variant/'reel.mp4').resolve() for row in rows]
            listing=Path(temporary)/'concat.txt'
            if any("'" in str(p) or '\n' in str(p) for p in clips):
                raise ValueError('Output path cannot contain quotes or newlines')
            listing.write_text(''.join("file '"+str(p)+"'\n" for p in clips),encoding='utf-8')
            target=output/('combined-'+variant+'.mp4')
            subprocess.run(['ffmpeg','-nostdin','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(target)],capture_output=True,check=True,timeout=600)
            if not target.is_file() or target.stat().st_size==0:raise RuntimeError('Combined MP4 is missing')
            results.append(target.name)
    return results

def batch(root,output_mode,extra,render_fn=None):
    root=Path(root).resolve();paths=discover(root);output=root/'output_free3d'
    if output_mode not in ('separate_videos','combined_video'):raise ValueError('Unsupported inbox output mode')
    if output.exists() and any(output.iterdir()):raise ValueError('Use an empty output_free3d folder')
    output.mkdir(exist_ok=True)
    render_fn=render_fn or render_one
    document={'input_mode':'inbox','inbox_output':output_mode,'source_count':len(paths),'order':'filename, case-insensitive','multi_view_fusion':False,'free_only':True,'sources':[],'combined_videos':[]}
    def save():(output/'inbox-manifest.json').write_text(json.dumps(document,indent=2),encoding='utf-8')
    save()
    print('Inbox images: '+str(len(paths)),flush=True)
    for i,path in enumerate(paths,1):
        print(f'{i}. {path.name}',flush=True)
        row={'source':path.name,'folder':f'source-{i:03d}','status':'running'}
        document['sources'].append(row);save()
        try:
            render_fn(root,path,output/row['folder'],extra)
            row['status']='completed'
        except Exception as exc:
            row.update(status='failed',error_type=type(exc).__name__)
        save()
    if output_mode=='combined_video':
        try:document['combined_videos']=combine(output,document['sources'])
        except Exception as exc:document['combined_error_type']=type(exc).__name__
        save()
    return document

def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--input-mode',choices=('inbox','image_url','repository_image','product_url','existing_glb','demo_3d'),default='inbox')
    parser.add_argument('--source',default='')
    parser.add_argument('--inbox-output',choices=('separate_videos','combined_video'),default='separate_videos')
    config,extra=parser.parse_known_args()
    if config.input_mode!='inbox':
        subprocess.run([sys.executable,str(ROOT/'product_video.py'),'--input-mode',config.input_mode,'--source',config.source,*extra],check=True)
        return
    document=batch(ROOT,config.inbox_output,extra)
    if any(row['status']!='completed' for row in document['sources']) or document.get('combined_error_type'):
        raise SystemExit('One or more Inbox outputs failed; inspect inbox-manifest.json and source render.log files')

if __name__=='__main__':main()
