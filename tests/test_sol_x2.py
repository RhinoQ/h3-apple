"""Handoff contracts with independent markers and temporary inputs; no model weights."""
from pathlib import Path
from types import SimpleNamespace
import subprocess

import numpy as np
import pytest
from PIL import Image

from h3_apple import resolve, generate, DownloadApprovalRequired
from h3_apple import engine, compute, preparation, process, x2_assets
from h3_apple.assets import RECIPE


@pytest.mark.parametrize("aspect,canvas,delivery", [
    ("16:9", (960,544), (1920,1088)), ("9:16", (544,960), (1088,1920))])
def test_sol_x2_routes_only_latent_and_lossless_audio(tmp_path, aspect, canvas, delivery):
    image=tmp_path/'ref.png'; Image.new('RGB',(64,64),'blue').save(image)
    r=resolve('Picture 1', reference_images=[image], mode='SOL', x2=True,
              resolution='544p', duration=5, aspect_ratio=aspect).to_dict()
    assert (r['model_width'],r['model_height'])==canvas
    assert (r['width'],r['height'])==delivery
    graph=engine.build_graph(r,dict(native_model='/model',adapter=dict(path='/adapter'),recipe=RECIPE),[],tmp_path/'a.wav')
    stages={s['id']:s for s in graph['stages']}
    assert 'vae-decode' not in stages and 'rgb-to-video' not in stages
    assert stages['save-video']['iports']==[dict(src='audio-vae-decode',oport=0)]
    assert stages['save-video']['config']['audio_codec']=='pcm_f32le'
    assert not stages['save-video']['config']['enable_video']
    assert stages['generate-video']['config']['steps']==5


def test_sol_combined_download_uses_sol_bundle_before_preparing(monkeypatch,tmp_path):
    from h3_apple import vsa_preparation
    from h3_apple.runtime import backend
    image=tmp_path/'ref.png';Image.new('RGB',(32,32),'blue').save(image)
    monkeypatch.setattr(backend,'check_dependencies',lambda:None)
    monkeypatch.setattr(preparation,'plan',lambda *a,**kw:dict(download_bytes=18_000_000_000,additional_disk_bytes=30))
    monkeypatch.setattr(vsa_preparation,'plan',lambda *a,**kw:pytest.fail('VSA models requested for SOL'))
    monkeypatch.setattr(x2_assets,'plan',lambda *a,**kw:dict(download_bytes=5_000_000_000,additional_disk_bytes=40))
    monkeypatch.setattr(process,'ensure_ready',lambda *a,**kw:pytest.fail('download before approval'))
    with pytest.raises(DownloadApprovalRequired) as caught:
        generate('Picture 1',reference_images=[image],mode='SOL',x2=True,output=tmp_path/'o.mp4')
    assert caught.value.download_bytes==23_000_000_000


def marker_file(tmp_path):
    from h3_apple.runtime.sol_x2 import read_latent
    req=dict(model_num_frames=5,model_height=32,model_width=64)
    value=np.empty((24,2,2,4),dtype='<f4')
    for c,t,y,x in np.ndindex(value.shape):value[c,t,y,x]=c*1000+t*100+y*10+x
    path=tmp_path/'latent.f32';value.tofile(path)
    log=f"GenerateVideoStage('generate-video'): dumped latent [24, 2, 2, 4] to {path}\n"
    return req,value,path,log,read_latent


def test_native_grid_preserves_every_channel_time_and_pixel(tmp_path):
    req,value,path,log,read=marker_file(tmp_path)
    actual=read(path,req,log)
    for c,t,y,x in np.ndindex(value.shape):
        assert actual[0,c,t,y,x]==c*1000+t*100+y*10+x


@pytest.mark.parametrize('fault',['missing_confirmation','wrong_shape','wrong_path','truncated','nan'])
def test_native_handoff_rejects_invalid_exports(tmp_path,fault):
    req,value,path,log,read=marker_file(tmp_path)
    if fault=='missing_confirmation':log=''
    elif fault=='wrong_shape':log=log.replace('[24, 2, 2, 4]','[24, 2, 4, 2]')
    elif fault=='wrong_path':log=log.replace(str(path),'/unrelated')
    elif fault=='truncated':path.write_bytes(path.read_bytes()[:-4])
    else:value[0,0,0,0]=np.nan;value.tofile(path)
    with pytest.raises(ValueError):read(path,req,log)


def test_shared_decoder_matches_previous_normalization_and_rgb_conversion(monkeypatch):
    mx=pytest.importorskip('mlx.core')
    from h3_apple.runtime import x2_vae
    from h3_apple._vendor.fastvideo_mlx.minimax_h3_pipeline import MiniMaxH3MLXPipeline as Old
    from h3_apple._vendor.fastvideo_mlx.minimax_h3 import patchify_video_latents
    z=np.arange(24*2*2*4,dtype=np.float32).reshape(1,24,2,2,4)/1000
    calls=[]
    class Decoder:
        spatial_compression_ratio=16
        latent_channels=24
        def denormalize_latents(self,latent):calls.append(np.asarray(latent));return latent*2+3
        def decode(self,latent,**kwargs):
            np.testing.assert_array_equal(np.asarray(latent),z*2+3)
            assert kwargs==dict(tiled=True,tile_sample_min_height=32,tile_sample_min_width=64)
            return mx.array(np.linspace(-.2,1.2,3*5*64*128,dtype=np.float32).reshape(1,3,5,64,128))
        def denormalize_pixels(self,pixels):return pixels
    old=SimpleNamespace(resolve_geometry=Old.resolve_geometry,video_decode_backend='h3-vae',
        _dit_in_channels=24,_dit_patch_size=(1,2,2),_load_video_vae=lambda:Decoder(),observer=None)
    expected=Old.decode_video(old,patchify_video_latents(z,(1,2,2)),height=32,width=64,num_frames=5)
    monkeypatch.setattr(x2_vae,'load_x2',lambda *a,**kw:Decoder())
    actual=x2_vae.decode_latents(z,'unused',height=32,width=64,num_frames=5)
    np.testing.assert_array_equal(actual,expected)
    assert len(calls)==2
    for call in calls:np.testing.assert_array_equal(call,z)


def test_sol_x2_policy_requires_sampling_but_not_unused_video_decoder(monkeypatch,tmp_path):
    monkeypatch.setattr(compute,'hardware_identity',lambda *a:dict(native=dict(cpu='Apple M5 Max',matrix_cores=True),gpus=[dict(cores='40')]))
    assets=dict(engine_capabilities=['stable-compute-v1'],identity='model',adapter=dict(sha256='a'),
                recipe=RECIPE,binary=dict(sha256='b'),library=dict(sha256='c'))
    plan,_=compute.prepare(dict(x2=True),assets,[],tmp_path,{})
    assert plan['video_decoder']=='mlx-x2'
    assert 'VPIPE_H3_VVAE_INT8' not in plan['environment']
    log='replayed research qmm plan: test\n[h3-plan] dit M=10 N=20 K=30 route=u8-w8-cm1 split=2\n'
    assert compute.complete(plan,None,log,tmp_path)['actual_routes']
    with pytest.raises(RuntimeError):compute.complete(plan,None,'',tmp_path)


def test_float_audio_handoff_preserves_channels_and_sample_accurate_trim(tmp_path):
    from h3_apple.media import tool
    from h3_apple.runtime.sol_x2 import read_audio
    value=np.arange(7000,dtype=np.float32)/10000
    stereo=np.stack((value,-value/2),axis=1)
    path=tmp_path/'audio.wav'
    subprocess.run([tool('ffmpeg'),'-v','error','-nostdin','-n',
        '-f','f32le','-ar','32000','-ac','2','-i','pipe:0',
        '-c:a','pcm_f32le',str(path)],input=stereo.tobytes(),check=True,timeout=30)
    req=dict(num_frames=5,audio_sample_rate=32000,fps=24)
    actual=read_audio(path,req)
    np.testing.assert_array_equal(actual,stereo[:6667].T)
    with pytest.raises(ValueError,match='insufficient'):
        read_audio(path,dict(req,num_frames=6))
    with pytest.raises(ValueError,match='float32 stereo'):
        read_audio(path,dict(req,audio_sample_rate=48000))
