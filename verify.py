"""Verify all bundle bytes and recompute published scores without installing H3."""
import argparse
import json
from pathlib import Path
from package import contained,digest,local_paths
from score import score


def verify(root):
    checks=json.loads((root/'checksums.json').read_text())
    for name,item in checks.items():
        path=contained(root,name)
        if path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:
            raise ValueError('Changed bundle file: '+name)
    data=json.loads((root/'catalog.json').read_text())
    for name in set(local_paths(data)):
        if name not in checks:raise ValueError('Unchecked local asset: '+name)
    published=json.loads((root/'scores.json').read_text())
    if data.get('status')=='registered':
        if published is not None or any(r.get('video') or r['review']['status']!='pending' for c in data['cases'] for r in c['runs']):
            raise ValueError('Registration contains results or scores')
    elif score(data)!=published:raise ValueError('Published scores differ')
    return dict(files_verified=len(checks),cases=len(data['cases']),runs=sum(len(c['runs']) for c in data['cases']),status=data.get('status','complete'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',nargs='?',type=Path,default=Path(__file__).parent)
    print(json.dumps(verify(p.parse_args().directory),indent=2))
