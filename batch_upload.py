"""Local mixed-input batch adapter. No GitHub writes, paid APIs, or external hosting."""
import fcntl,hashlib,importlib.util,json,os,shutil,signal,subprocess,sys,uuid,zipfile
from pathlib import Path
import studio
ROOT=Path(__file__).resolve().parent
MAX_INPUTS=8
MAX_VIDEOS=20
MAX_BYTES=15000000
CORE=('free3d.py','studio.py','creator.py','reconstruct_cpu.py','render_free3d.py')
CHOICES={'variants':('1','2','3','5','10'),'duration':('5','10','15'),'quality':('preview_360p','720p','1080p'),'mesh_resolution':('64','96','128'),'motion':('auto','turntable','orbit','float','reveal'),'captions':('none','offer','post_and_offer'),'music':('auto','off','on'),'voice':('off','on')}

def options(values):
    if set(values)-set(CHOICES)-{'main_words','reel_idea'}: raise ValueError('Unknown render option')
    for key,value in values.items():
        if key in CHOICES and str(value) not in CHOICES[key]: raise ValueError('Invalid '+key)
    if len(values.get('main_words',''))>180: raise ValueError('Offer words exceed 180 characters')
    return [item for key,value in values.items() for item in ('--'+key.replace('_','-')+'='+str(value),)]

def job_path(job_id):
    if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id): raise ValueError('Invalid batch ID')
    return ROOT/'.upload-jobs'/job_id

def prepare(uploads,url_text,product_pages=False,image_index=1):
    urls=list(dict.fromkeys(line.strip() for line in url_text.splitlines() if line.strip()))
    if not uploads and not urls: raise ValueError('Upload images, enter URLs, or use both')
    if len(uploads)+len(urls)>MAX_INPUTS: raise ValueError('Maximum 8 combined inputs per batch')
    if not 1<=image_index<=24: raise ValueError('Image index must be 1-24')
    job_id=uuid.uuid4().hex;folder=job_path(job_id);folder.mkdir(parents=True)
    queue=[];errors=[];seen=set()
    def accept(data,label):
        if len(data)>MAX_BYTES: raise ValueError('Image exceeds 15 MB')
        path=folder/f'input-{len(queue)+1:02d}.png';studio.normalized(data,path)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen: path.unlink();return
        seen.add(digest);queue.append({'label':label,'path':str(path)})
    for index,(_,data) in enumerate(uploads):
        try: accept(data,f'Upload {index+1}')
        except Exception as exc: errors.append({'input':f'Upload {index+1}','error':type(exc).__name__})
    for index,url in enumerate(urls):
        try:
            if product_pages:
                _,images=studio.product(studio.fetch(url,2000000),url)
                if len(images)<image_index: raise ValueError('Selected gallery image missing')
                url=images[image_index-1]
            accept(studio.fetch(url),f'URL {index+1}')
        except Exception as exc: errors.append({'input':f'URL {index+1}','error':type(exc).__name__})
    (folder/'inputs.json').write_text(json.dumps({'queue':queue,'errors':errors},indent=2))
    return job_id,queue,errors

def preflight():
    missing=[name for name in ('blender','ffmpeg','espeak-ng') if not shutil.which(name)]
    if importlib.util.find_spec('torch') is None: missing.append('CPU torch')
    if not (ROOT/'.triposr'/'tsr'/'system.py').is_file(): missing.append('TripoSR source')
    if missing: raise ValueError('Run setup_upload_ui.sh first; missing: '+', '.join(missing))

def render_batch(job_id,settings,progress=None):
    flags=options(settings);folder=job_path(job_id)
    state=json.loads((folder/'inputs.json').read_text());queue=state['queue']
    if not queue: raise ValueError('No usable input images')
    if len(queue)*int(settings.get('variants',1))>MAX_VIDEOS: raise ValueError('Maximum 20 output videos; reduce images or variants')
    preflight();results=[]
    with open(ROOT/'.upload-jobs'/'render.lock','a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('Another local batch is rendering; wait for it to finish')
        for index,item in enumerate(queue):
            runtime=folder/f'source-{index+1:02d}';runtime.mkdir()
            for name in CORE: shutil.copy(ROOT/name,runtime/name)
            (runtime/'.triposr').symlink_to((ROOT/'.triposr').resolve(),target_is_directory=True)
            shutil.copy(item['path'],runtime/'input.png')
            env={k:v for k,v in os.environ.items() if not k.endswith(('_KEY','_TOKEN'))}
            with open(runtime/'render.log','wb') as log:
                try:
                    process=subprocess.Popen([sys.executable,'free3d.py','--input-mode=repository_image','--source=input.png',*flags],cwd=runtime,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    success=process.wait(timeout=7200)==0
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGTERM)
                    try: process.wait(timeout=30)
                    except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL);process.wait()
                    success=False
            results.append({'label':item['label'],'directory':runtime.name,'success':success})
            (folder/'results.json').write_text(json.dumps(results,indent=2))
            if progress: progress(index+1,len(queue),results[-1])
    return results

def archive(job_id):
    folder=job_path(job_id);target=folder/'finished-reels.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as output:
        for path in sorted(folder.glob('source-*/output_free3d/**/*')):
            if path.is_file(): output.write(path,path.relative_to(folder))
        if (folder/'results.json').exists(): output.write(folder/'results.json','results.json')
    return target

def delete_job(job_id):
    folder=job_path(job_id)
    if folder.exists(): shutil.rmtree(folder)
