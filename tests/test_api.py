import inspect
import json
import subprocess
import sys

from PIL import Image
import pytest

from h3_apple import generate, resolve
from h3_apple.cli import parser


@pytest.fixture
def images(tmp_path):
    paths = [tmp_path/'z.png', tmp_path/'a.png']
    for path, color in zip(paths, ('red','blue')):
        Image.new('RGB',(96,64),color).save(path)
    return paths


def test_default_request_is_one_ref2va_recipe(images):
    r = resolve('Picture 1 and Picture 2', reference_images=images, seed=0)
    assert r.reference_images == tuple(map(str, images))
    assert (r.width,r.height,r.num_frames,r.model_num_frames,r.num_steps) == (1024,576,360,362,4)
    assert r.audio_channels == 2 and r.audio_sample_rate == 32000
    for function in (resolve,generate):
        assert not {'preset','task','first_frame','last_frame','reference_video','reference_audio','reference_resize'} & set(inspect.signature(function).parameters)


@pytest.mark.parametrize('images_value',[None,[],[''],['missing.png']*10,'image.png'])
def test_requires_ordered_images(images_value):
    with pytest.raises(ValueError):
        resolve('Scene',reference_images=images_value)


@pytest.mark.parametrize('options',[{'duration':True},{'duration':4},{'duration':16},{'duration':float('nan')},
    {'duration':5.01},{'seed':True},{'seed':-1},{'seed':2**32},{'resolution':'1080p'},{'aspect_ratio':'1:1'}])
def test_rejects_invalid_delivery(images,options):
    with pytest.raises(ValueError):
        resolve('Scene',reference_images=images,**options)


@pytest.mark.parametrize('options',[{'prompt':''},{'prompt':'\0'},{'prompt':23},{'prompt':'text','prompt_file':'also.txt'}])
def test_rejects_invalid_prompt(images,options):
    with pytest.raises(ValueError):
        resolve(reference_images=images,**options)


def test_full_prompt_file_and_portrait(images,tmp_path):
    p=tmp_path/'prompt.txt';p.write_text('完整提示词\nMusic throughout.\n')
    r=resolve(prompt_file=p,reference_images=images,duration=124/24,resolution='768p',aspect_ratio='9:16')
    assert r.prompt==p.read_text()
    assert (r.width,r.height,r.model_width,r.model_height,r.num_frames,r.model_num_frames)==(768,1366,768,1376,124,124)


def test_rejects_animated_images(tmp_path):
    p=tmp_path/'animated.gif'
    Image.new('RGB',(32,32),'red').save(p,save_all=True,append_images=[Image.new('RGB',(32,32),'blue')],duration=100,loop=0)
    with pytest.raises(ValueError,match='still images'):
        resolve('Scene',reference_images=[p])


@pytest.mark.parametrize('flag',['--preset','--task','--first-frame','--reference-video','--reference-audio','--reference-resize'])
def test_removed_modes_are_not_silently_ignored(flag):
    with pytest.raises(SystemExit):
        parser().parse_args(['generate','--image','x.png','--prompt','Scene',flag,'unused'])


def test_import_does_not_load_heavy_frameworks():
    code="import h3_apple,sys,json;print(json.dumps(sorted(set(sys.modules)&{'torch','transformers','mlx','numpy'})))"
    r=subprocess.run([sys.executable,'-I','-c',code],capture_output=True,text=True,check=True)
    assert json.loads(r.stdout)==[]
