"""CPU-only TripoSR adapter; substitutes scikit-image for compiled torchmcubes."""
import os,sys,types
from pathlib import Path

def marching_cubes(level,threshold):
    import numpy as np
    import torch
    from skimage.measure import marching_cubes as extract
    vertices,faces,_,_=extract(level.detach().cpu().numpy(),level=threshold)
    return torch.from_numpy(vertices[:,[2,1,0]].copy()),torch.from_numpy(faces.astype(np.int64).copy())

def main():
    import numpy as np
    import torch
    from PIL import Image
    import rembg
    root=Path(__file__).resolve().parent
    shim=types.ModuleType('torchmcubes');shim.marching_cubes=marching_cubes;sys.modules['torchmcubes']=shim
    sys.path.insert(0,str(root/'.triposr'))
    from tsr.system import TSR
    from tsr.utils import remove_background,resize_foreground
    torch.set_num_threads(min(4,os.cpu_count() or 1))
    model=TSR.from_pretrained('stabilityai/TripoSR',config_name='config.yaml',weight_name='model.ckpt').to('cpu').eval()
    model.renderer.set_chunk_size(1024)
    with Image.open(sys.argv[1]) as source:
        image=resize_foreground(remove_background(source.convert('RGBA'),rembg.new_session()),.85)
    rgba=np.asarray(image).astype(np.float32)/255
    rgb=rgba[:,:,:3]*rgba[:,:,3:4]+(1-rgba[:,:,3:4])*.5
    image=Image.fromarray((rgb*255).astype(np.uint8))
    with torch.inference_mode():
        codes=model([image],device='cpu')
        mesh=model.extract_mesh(codes,has_vertex_color=True,resolution=int(sys.argv[3]))[0]
    if not len(mesh.faces): raise ValueError('Reconstruction produced no mesh')
    mesh.export(sys.argv[2])

if __name__=='__main__': main()
