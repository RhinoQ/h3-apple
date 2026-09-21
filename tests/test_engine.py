import os
from PIL import Image
import pytest
from h3_apple import resolve
from h3_apple.assets import RECIPE
from h3_apple import engine


def test_reference_order_and_fixed_acceleration(tmp_path):
    paths=[tmp_path/'z.png',tmp_path/'a.png']
    for path,color in zip(paths,('red','blue')):Image.new('RGB',(960,544),color).save(path)
    request=resolve('Picture 1 red, picture 2 blue',reference_images=paths).to_dict()
    prepared=engine.prepare_inputs(request,dict(image_paths=paths,pixel_budget=1024*576),tmp_path)
    assets=dict(native_model='/model',adapter=dict(path='/adapter'),recipe=RECIPE)
    stages={s['id']:s for s in engine.build_graph(request,assets,prepared,tmp_path/'out.mp4')['stages']}
    assert stages['video-ref-encoder']['config']['references']==[p['path'] for p in prepared]
    assert [Image.open(p['path']).getpixel((0,0)) for p in prepared]==[(255,0,0),(0,0,255)]
    config=stages['generate-video']['config']
    assert all(config[k] is True for k in ('i8_gemm','sol_attn','sage_attn'))
    assert config['steps']==5 and config['sol_tau']==1 and config['sol_dense_layers']==1
    assert config['sol_local_radius']==1 and config['sage_dense_layers']==0
    ports=stages['generate-video']['iports']
    assert [ports[n]['src'] for n in (0,7,8)]==['video-ref-encoder']*3
    assert ports[5]['src']==ports[6]['src']==''
    assert stages['save-video']['config']['enable_audio'] is True
    assert stages['text-prompt']['config']['text']==request['prompt']


@pytest.mark.parametrize('text',['','baked AdaLN for 4 steps','baked AdaLN for 4 steps\nSol-Attn ON\nSageAttention ON',
    'baked AdaLN for 4 steps\nSol-Attn ON\nSageAttention ON\nSol-Attn kept\nsage_attn is off at 200 rows'])
def test_acceleration_cannot_silently_fall_back(text):
    with pytest.raises(RuntimeError):engine.audit_log(text)


def test_native_progress_counts_four_forwards():
    assert engine.progress_event("[PROGRESS] 100% of 'denoise' completed (200/200)")==dict(phase='denoise',step=4,steps=4,block=50,blocks=50)
    assert engine.progress_event('diagnostic') is None


def test_runtime_drops_experimental_overrides(monkeypatch):
    for key in ('VPIPE_SAGE_ATTN','DYLD_INSERT_LIBRARIES','MTL_CAPTURE_ENABLED','MLX_METAL_GPU_ARCH','FASTVIDEO_EXPERIMENT'):
        monkeypatch.setenv(key,'bad')
    environment=engine.runtime_environment(dict(library=dict(path='/engine/libvpipe.0.dylib')))
    assert environment['DYLD_LIBRARY_PATH']=='/engine'
    assert not any(k in environment for k in ('VPIPE_SAGE_ATTN','DYLD_INSERT_LIBRARIES','MTL_CAPTURE_ENABLED','MLX_METAL_GPU_ARCH','FASTVIDEO_EXPERIMENT'))
