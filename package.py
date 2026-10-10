"""Create a self-contained static review bundle; never publish it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from score import score

CODE_FILES=('index.html','style.css','app.js','score.py','replay.py','package.py','verify.py','README.md','LICENSE')

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def local_paths(value):
    if isinstance(value,dict):
        for key,child in value.items():
            if key in ('path','poster') and isinstance(child,str) and (child.startswith(('assets/','prompts/','records/')) or child=='environment.txt'):
                yield child
            else:yield from local_paths(child)
    elif isinstance(value,list):
        for child in value:yield from local_paths(child)

def contained(root,name):
    path=(root/name).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Bundle path escapes root')
    return path

def export(catalog,destination,documented_only=False,*,registration_only=False):
    catalog=Path(catalog);destination=Path(destination)
    data=json.loads(catalog.read_text())
    for case in data['cases']:
        for run in case['runs']:
            review=run.get('review',{})
            if isinstance(review.get('summary'),str):
                review['summary']=re.sub(r'/(?:Users|home)/[^/\s"\\]+/', '<host>/', review['summary'])
    excluded=[]
    if documented_only:
        excluded=[c['id'] for c in data['cases'] if c['redistribution']!='documented']
        data['cases']=[c for c in data['cases'] if c['id'] not in excluded]
    if registration_only:
        if data.get('status')!='registered' or any(r.get('video') or r['review']['status']!='pending' for c in data['cases'] for r in c['runs']):
            raise ValueError('Registration export must have no outputs or judgments')
        result=None
    else:
        result=score(data)  # Reject incomplete or mixed primary cohorts before creating output.
    destination.mkdir(parents=True,exist_ok=False)
    data['export']=dict(documented_inputs_only=documented_only,excluded_cases=excluded,
        notice='Documented reference terms are retained. This export does not grant new model, image or personality rights, and performs no publication.')
    for name in sorted(set(local_paths(data))):
        source=contained(catalog.parent,name);target=contained(destination,name)
        target.parent.mkdir(parents=True,exist_ok=True)
        try:os.link(source,target)
        except OSError:shutil.copyfile(source,target)
    for name in CODE_FILES:shutil.copyfile(Path(__file__).parent/name,destination/name)
    (destination/'catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (destination/'data.js').write_text('window.BENCHMARK = '+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+';\n')
    (destination/'scores.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (destination/'scores.js').write_text('window.SCORES = '+json.dumps(result,ensure_ascii=False)+';\n')
    credits=['# Asset attribution','',
        'Original reference files are copied unchanged. Video outputs and JPEG posters are generated/reduced derivatives; the input license is not a blanket license for the whole bundle. Generated media remain subject to MiniMax H3 terms and any applicable source-image terms. CC BY-SA inputs and adaptations retain their stated ShareAlike obligations. Software LICENSE covers independently authored benchmark code only.',
        '', 'AI-generated project fixtures are identified as such, not assigned a third-party CC0 license. Publication does not establish redistribution rights for references with unresolved terms. `--documented-only` removes unscored cases with unresolved terms and refuses an export that would omit a required scored case.','']
    seen=set()
    for c in data['cases']:
        for ref in c['references']:
            if ref['sha256'] in seen:continue
            seen.add(ref['sha256']);a=ref['credit']
            credits.extend([f"## {a.get('title',ref['sha256'])}",'',
                f"- Author: {a.get('author','Not recorded')}",f"- Terms: {a.get('license','Unresolved')}",
                f"- Source: {a.get('page') or a.get('source') or a.get('url') or 'Project fixture; see original source records'}",
                *([f"- Source note: {a['source_note']}"] if a.get('source_note') else []),
                f"- License URL: {a.get('license_url','See source/terms above')}",
                f"- Original bytes: [{ref['path']}]({ref['path']})",f"- SHA256: `{ref['sha256']}`",
                f"- Redistribution record: {ref['redistribution']}",''])
    (destination/'ATTRIBUTION.md').write_text('\n'.join(credits))
    checks={str(p.relative_to(destination)):dict(bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination/'checksums.json').write_text(json.dumps(checks,indent=2)+'\n')
    return dict(cases=len(data['cases']),runs=sum(len(c['runs']) for c in data['cases']),
        files=len(checks),bytes=sum(i['bytes'] for i in checks.values()),excluded_cases=excluded,
        catalog_sha256=digest(destination/'catalog.json'),checksums_sha256=digest(destination/'checksums.json'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True);p.add_argument('--documented-only',action='store_true')
    a=p.parse_args();print(json.dumps(export(a.catalog,a.destination,a.documented_only),indent=2))
