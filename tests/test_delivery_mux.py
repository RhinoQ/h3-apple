import subprocess
import pytest
from h3_apple.media import tool, validate, finish_native

@pytest.mark.parametrize("frames", [120,124,157,240,360])
def test_native_delivery_has_sample_accurate_endpoints(tmp_path,frames):
    count=((frames-5+16)//17)*17+5
    request=dict(width=64,height=64,model_width=96,model_height=64,num_frames=frames,
        model_num_frames=count,fps=24,audio_sample_rate=32000,audio_channels=2,duration=frames/24)
    source=tmp_path/"native.mp4"; output=tmp_path/"output.mp4"
    subprocess.run([tool("ffmpeg"),"-v","error","-nostdin","-n","-f","lavfi","-i",f"testsrc2=size=96x64:rate=24:duration={count/24}",
        "-f","lavfi","-i",f"sine=sample_rate=32000:duration={count/24}","-frames:v",str(count),"-c:v","libx264",
        "-preset","ultrafast","-c:a","aac","-ac","2","-t",str(count/24),str(source)],check=True,timeout=60)
    finish_native(source,output,request)
    validate(output,request)
