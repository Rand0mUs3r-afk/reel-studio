"""Local browser upload UI. Start with streamlit run upload_app.py."""
import json
from pathlib import Path
import streamlit as st
import batch_upload as batch

st.set_page_config(page_title='Reel Studio — Upload + URL',layout='wide')
st.title('Reel Studio — Upload + URL')
st.caption('Free experimental CPU 3D rendering. This app runs on your computer, not inside the GitHub Actions page.')
st.info('Use uploads, URLs, or both together. Maximum 8 inputs and 20 videos per batch. Each image creates its own model/video variants; images are not fused into one multi-view model.')
with st.form('sources'):
    left,right=st.columns(2)
    with left:
        uploads=st.file_uploader('Upload photos — select multiple or drag and drop',type=['jpg','jpeg','png','webp'],accept_multiple_files=True,help='Maximum 15 MB each. Uploads stay in this local app workspace.')
    with right:
        urls=st.text_area('Image or product URLs — one per line',height=160)
        product_pages=st.checkbox('These URLs are product pages rather than direct images')
        image_index=st.number_input('Product-page image number',min_value=1,max_value=24,value=1)
    st.subheader('Render settings')
    a,b,c=st.columns(3)
    values={}
    with a:
        values['variants']=st.selectbox('Videos per image',[1,2,3,5,10])
        values['duration']=st.selectbox('Target seconds',[5,10,15])
        values['quality']=st.selectbox('Video quality',['preview_360p','720p','1080p'])
    with b:
        values['mesh_resolution']=st.selectbox('Mesh resolution',[64,96,128])
        values['motion']=st.selectbox('Motion',['auto','turntable','orbit','float','reveal'])
        values['captions']=st.selectbox('Caption mode',['post_and_offer','offer','none'])
    with c:
        values['music']=st.selectbox('Music',['auto','off','on'])
        values['voice']=st.selectbox('Narration',['off','on'])
    values['main_words']=st.text_input('Main words / offer',max_chars=180,placeholder='2 for $30')
    values['reel_idea']=st.text_area('Reel idea — keyword direction',max_chars=1000,placeholder='slow orbit, light background, no music')
    st.caption('Idea interpretation is keyword-only in this version. Unrecognized details are not interpreted.')
    preview=st.form_submit_button('Preview combined inputs')
    generate=st.form_submit_button('Generate videos from all inputs')
if preview or generate:
    try:
        batch.options(values)
        with st.spinner('Validating uploads and downloading URL images…'):
            job_id,queue,errors=batch.prepare([(f.name,f.getvalue()) for f in uploads],urls,product_pages,int(image_index))
        st.session_state['upload_job']=job_id
        for error in errors: st.warning(error['input']+': could not load image ('+error['error']+')')
        if not queue: st.error('No usable images. Check URLs and uploaded file contents.')
        elif generate:
            progress=st.progress(0.0);status=st.empty()
            def update(done,total,result):
                progress.progress(done/total);status.write(result['label']+(' completed' if result['success'] else ' failed; inspect local render.log'))
            with st.spinner('Reconstructing and rendering locally. CPU processing can take a long time…'):
                batch.render_batch(job_id,values,update)
            batch.archive(job_id)
    except Exception as exc: st.error(str(exc))
job_id=st.session_state.get('upload_job')
if job_id:
    folder=batch.job_path(job_id)
    if (folder/'inputs.json').exists():
        queue=json.loads((folder/'inputs.json').read_text())['queue']
        st.subheader(f'Combined queue: {len(queue)} unique images')
        columns=st.columns(4)
        for index,item in enumerate(queue): columns[index%4].image(item['path'],caption=item['label'])
    for path in sorted(folder.glob('source-*/output_free3d/variant-*/reel.mp4')):
        label=str(path.relative_to(folder));st.write(label);st.video(str(path))
        with open(path,'rb') as data: st.download_button('Download this video',data,file_name=path.parent.parent.parent.name+'-'+path.parent.name+'.mp4',mime='video/mp4',key=label)
    archive=folder/'finished-reels.zip'
    if archive.exists():
        if archive.stat().st_size<=200000000:
            with open(archive,'rb') as data: st.download_button('Download all finished outputs',data,file_name='finished-reels.zip',mime='application/zip')
        else: st.warning('The combined archive exceeds the UI download limit; use the local batch folder or individual video downloads.')
    st.caption('Local batches persist until deleted. This UI does not commit uploads to GitHub. Earlier batches may remain in .upload-jobs until you remove them.')
    if st.button('Delete current local batch — uploads and outputs'):
        batch.delete_job(job_id);del st.session_state['upload_job'];st.rerun()
