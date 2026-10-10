"""Verify portable inputs and use the installed product's public API."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def input_path(root,item):
    path=(root/item['path']).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Input path escapes the benchmark')
    with path.open('rb') as f:checksum=hashlib.file_digest(f,'sha256').hexdigest()
    if checksum!=item['sha256']:raise ValueError('Input checksum differs: '+str(path))
    return path


def options(root,case,*,mode,profile,seed,output):
    request=case['runs'][0]['request']
    width=request.get('model_width') or request['width']
    height=request.get('model_height') or request['height']
    return dict(prompt_file=str(input_path(root,case['prompt'])),
        reference_images=[str(input_path(root,r)) for r in case['references']],
        mode=mode,resolution='768p' if profile=='standard' else '544p',x2=profile=='fast',
        duration=request['duration'],seed=seed,
        aspect_ratio='9:16' if width<height else '16:9',
        output=str(output))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=Path,default=Path(__file__).with_name('catalog.json'))
    parser.add_argument('--case',required=True);parser.add_argument('--mode',choices=('VSA','SOL'),required=True)
    parser.add_argument('--profile',choices=('standard','fast'),required=True)
    parser.add_argument('--seed',type=int);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--model-dir',type=Path);parser.add_argument('--x2-model-dir',type=Path)
    parser.add_argument('--execute',action='store_true',help='Without this flag, only verify inputs and print the request.')
    parser.add_argument('--allow-different-source',action='store_true',help='Evaluate a new product source; never claim this reproduces the recorded pixels.')
    args=parser.parse_args();data=json.loads(args.catalog.read_text());root=args.catalog.parent.resolve()
    cases=[c for c in data['cases'] if c['id']==args.case]
    if len(cases)!=1:raise ValueError('Unknown or duplicate case')
    case=cases[0];seed=args.seed if args.seed is not None else case['runs'][0]['seed']
    kw=options(root,case,mode=args.mode,profile=args.profile,seed=seed,output=args.output)
    if not args.execute:
        print(json.dumps(dict(action='validated_plan_only',kwargs=kw,
            notice='Use a dedicated Conda interpreter and --execute to generate. A new run requires a new visual judgment.'),indent=2));return
    if not args.model_dir:parser.error('--model-dir is required with --execute')
    if args.profile=='fast' and not args.x2_model_dir:parser.error('--x2-model-dir is required for fast execution')
    from h3_apple import generate
    from h3_apple.io import source_identity
    identity=source_identity()
    if identity!=data['primary']['source_sha256'] and not args.allow_different_source:
        raise ValueError('Installed source differs. Install the recorded build, or explicitly evaluate a new version with --allow-different-source.')
    # Preparation is deliberately separate: validate the selected bundle before
    # spending GPU time, without downloading anything through this replay helper.
    if args.mode=='VSA':
        from h3_apple.vsa_assets import load_assets
    else:
        from h3_apple.assets import load_manifest as load_assets
    bundle=load_assets(args.model_dir)
    model_matches=bundle['identity']==data['primary']['model_identities'][args.mode]
    if not model_matches and not args.allow_different_source:
        raise ValueError('Prepared model identity differs from the recorded benchmark.')
    x2_matches=None
    if args.profile=='fast':
        from h3_apple.x2_assets import plan
        spec=plan(args.x2_model_dir)
        if spec['download_bytes']:raise ValueError('Prepare X2 models separately before benchmark execution.')
        x2_matches=any(f['sha256']==data['primary']['x2_weights_sha256'] for f in spec['files'])
        if not x2_matches and not args.allow_different_source:raise ValueError('X2 weights differ from recorded benchmark.')
    if args.output.exists():raise FileExistsError(args.output)
    if args.output.with_suffix('.benchmark.json').exists():raise FileExistsError('Replay record already exists')
    started=time.monotonic()
    result=generate(**kw,model_dir=str(args.model_dir),x2_model_dir=str(args.x2_model_dir) if args.x2_model_dir else None,
        diagnostics=False,timeout=1200,allow_large_download=False,
        on_progress=lambda x:print(json.dumps(x),flush=True))
    elapsed=time.monotonic()-started
    record=dict(case=case['id'],benchmark_version=data['version'],mode=args.mode,profile=args.profile,seed=seed,
        seconds=elapsed,source_sha256=identity,source_matches_recorded=identity==data['primary']['source_sha256'],
        model_identity=bundle['identity'],model_matches_recorded=model_matches,x2_matches_recorded=x2_matches,
        metadata=str(result.metadata_path),output=str(result.video_path),judgment=None,
        notice='Generation success is not a task pass. Complete visual criteria require an explicit new judgment; retain failures and all planned seeds.')
    with args.output.with_suffix('.benchmark.json').open('x') as f:json.dump(record,f,indent=2)
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
