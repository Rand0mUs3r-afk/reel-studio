"""Run: streamlit run product_ad_app.py"""
import io
import json
import tempfile
import zipfile
from pathlib import Path
import streamlit as st
import product_ad as ads
from ad_sources import prepare_inputs, cover_angles

st.set_page_config(page_title='Reel Studio — Product Ads',layout='wide')
st.title('Product photo → product ad')
st.caption('Photo-preserving 2D ads. No reconstruction, paid API, invented claims, or posting.')
st.info('Multiple URLs are different angles of ONE product in ONE ad. Paste direct HTTPS image links in order, one per line. Optional labels: Front | https://example.com/front.jpg. This does not build a multi-view 3D model.')
with st.form('product-ad'):
    uploads=st.file_uploader('Product photos (up to 8 without URLs)',type=['png','jpg','jpeg','webp'],accept_multiple_files=True)
    image_urls=st.text_area('Product-angle image URLs (up to 6 combined images when URLs are used)',height=140)
    st.caption('Uploads appear first, then URLs in pasted order. URL downloads happen only when you click Preview or Generate. All supplied angles must load; failures stop the job.')
    logo_upload=st.file_uploader('Optional logo (at least 200 × 200)',type=['png','jpg','webp'])
    product=st.text_input('Product name',max_chars=64)
    brand=st.text_input('Brand',max_chars=48)
    hook=st.text_input('Opening hook (optional)',max_chars=90)
    benefits=st.text_area('Verified benefits — one per line, maximum three',help='Only facts you can substantiate; the app does not verify claims.')
    offer=st.text_input('Exact offer and conditions (optional)',max_chars=140)
    cta=st.text_input('Call to action',value='Discover more',max_chars=64)
    col1,col2=st.columns(2)
    with col1:
        duration=st.selectbox('Seconds',[15,30])
        resolution=st.selectbox('Resolution',['720p','1080p'])
        background=st.color_picker('Background','#0F172A')
    with col2:
        accent=st.color_picker('Accent','#38BDF8')
        voice=st.checkbox('Basic English narration (requires espeak-ng)',value=False)
        music_upload=st.file_uploader('Optional licensed music',type=['wav','mp3','m4a'])
    preview=st.form_submit_button('Preview storyboard')
    generate=st.form_submit_button('Generate ad')
if preview or generate:
    st.session_state.pop('ad_result',None)
    try:
        if image_urls.strip():
            with st.spinner('Loading all angles in order…'):
                photos,manifest=prepare_inputs([(v.name,v.getvalue()) for v in uploads],image_urls)
        else:
            if not 1<=len(uploads)<=8:
                raise ValueError('Upload one to eight photos, or supply image URLs')
            photos=[ads.photo_from_bytes(v.getvalue()) for v in uploads]
            manifest=[{'index':i,'label':f'Upload {i+1}','source_type':'upload'} for i in range(len(photos))]
        logo=ads.photo_from_bytes(logo_upload.getvalue()) if logo_upload else None
        plan=ads.make_plan(product,benefits,offer,cta,hook,brand)
        if image_urls.strip():
            plan=cover_angles(plan,len(photos))
        with tempfile.TemporaryDirectory(prefix='reel-ad-ui-') as temp:
            root=Path(temp);music=None
            if music_upload:
                if music_upload.size>30_000_000:
                    raise ValueError('Maximum 30 MB of licensed audio')
                music=root/('music'+Path(music_upload.name).suffix.lower())
                music.write_bytes(music_upload.getvalue())
            folder=root/'ad'
            with st.spinner('Preparing preview…' if preview else 'Rendering the product ad…'):
                ads.render(photos,plan,folder,duration,resolution,background,accent,logo,music,voice,preview_only=preview)
            (folder/'input-angles.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
            frames=[p.read_bytes() for p in sorted(folder.glob('scene-*.png'))]
            video=(folder/'ad.mp4').read_bytes() if (folder/'ad.mp4').exists() else None
            archive=io.BytesIO()
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
                for p in folder.iterdir():
                    if p.is_file():zipped.write(p,p.name)
            if archive.tell()>200_000_000:
                raise ValueError('Output exceeds the browser download limit; use the CLI')
            st.session_state['ad_result']={'frames':frames,'video':video,'zip':archive.getvalue(),'plan':json.loads((folder/'storyboard.json').read_text()),'angles':manifest}
    except Exception as exc:
        st.error(str(exc))
result=st.session_state.get('ad_result')
if result:
    st.subheader('Input angle order')
    st.json(result['angles'])
    st.subheader('Storyboard')
    columns=st.columns(3)
    for i,frame in enumerate(result['frames']):
        scene=result['plan']['scenes'][i]
        label=result['angles'][scene['photo_index']]['label']
        columns[i%3].image(frame,caption=scene['role']+' — '+label)
    st.json(result['plan'])
    if result['video']:
        st.video(result['video'])
        st.download_button('Download MP4',result['video'],'product-ad.mp4','video/mp4')
    st.download_button('Download output bundle',result['zip'],'product-ad.zip','application/zip')
    if st.button('Clear preview and downloads'):
        del st.session_state['ad_result'];st.rerun()
st.caption('Temporary render files are deleted after each job. Downloads stay in this session until cleared. Public deployments need authentication and resource limits. URL hosts receive network requests; do not paste private credentials.')
