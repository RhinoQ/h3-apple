"""Deterministic descriptive scores; no perceptual model or hidden weighting."""
import argparse
import json
import math
from pathlib import Path
import statistics


def score(data):
    required=data['primary']['case_ids'];arms=data['primary']['arms']
    expected_modes={'V768':'VSA','VX':'VSA','S768':'SOL','SX':'SOL'}
    if not required or set(arms)!=set(expected_modes) or len(arms)!=4:
        raise ValueError('Expected a nonempty four-route cohort')
    cases={c['id']:c for c in data['cases']}
    if len(cases)!=len(data['cases']) or len(set(required))!=len(required):
        raise ValueError('Duplicate case identity')
    selected={arm:[] for arm in arms}
    for cid in required:
        if cid not in cases:raise ValueError('Missing required case: '+cid)
        case=cases[cid]
        if case['cohort']!='main':raise ValueError('Required case is not in the primary cohort')
        paired_seed=None
        for arm in arms:
            rows=[r for r in case['runs'] if r['arm']==arm]
            if len(rows)!=1:raise ValueError(f'Expected exactly one {cid}/{arm}; missing or duplicated results invalidate the score')
            row=rows[0]
            if row['mode']!=expected_modes[arm]:raise ValueError('Mode does not match declared arm')
            if row['build_scope']!='current-frozen-product':raise ValueError('Historical/diagnostic output in primary cohort')
            if row['source_sha256']!=data['primary']['source_sha256']:raise ValueError('Mixed product sources in primary cohort')
            if row['model_identity']!=data['primary']['model_identities'][row['mode']]:raise ValueError('Unexpected prepared model identity')
            request=row['request'];fast=arm in ('VX','SX')
            if request['resolution']!=('544p' if fast else '768p') or request['x2'] is not fast:
                raise ValueError('Request does not match the frozen route')
            if request['duration']!=5 or request['fps']!=24 or request['num_steps']!=4:
                raise ValueError('Expected the frozen five-second four-step request')
            if request['prompt_file']!=case['prompt']['path'] or request['reference_images']!=[r['path'] for r in case['references']]:
                raise ValueError('Unpaired prompt/reference inputs')
            if request['seed']!=row['seed'] or (paired_seed is not None and paired_seed!=row['seed']):
                raise ValueError('Unpaired seeds')
            paired_seed=row['seed']
            if row['review']['status'] not in ('pass','fail','borderline'):raise ValueError('Primary result not fully adjudicated')
            if data['primary'].get('require_criterion_votes'):
                votes=row['review'].get('criteria_pass')
                if not isinstance(votes,list) or len(votes)!=len(case['criteria']) or not votes:
                    raise ValueError('Missing criterion-level judgments')
                if any(v is not True and v is not False and v is not None for v in votes):
                    raise ValueError('Invalid criterion judgment')
                expected='fail' if any(v is False for v in votes) else 'borderline' if any(v is None for v in votes) else 'pass'
                if row['review']['status']!=expected:
                    raise ValueError('Task status contradicts criterion judgments')
                required_dimensions={'action','count','detail','framing','geometry','identity','temporal'}
                if set(row['review'].get('severity',{}))!=required_dimensions:
                    raise ValueError('Incomplete quality dimensions')
            if row['seconds'] is None or not math.isfinite(row['seconds']) or row['seconds']<=0:raise ValueError('Missing full-call timing')
            selected[arm].append(row)
    def summarize(rows):
        counts={state:sum(r['review']['status']==state for r in rows) for state in ('pass','fail','borderline')}
        dimensions=sorted({k for r in rows for k in r['review'].get('severity',{})})
        quality={}
        for dim in dimensions:
            values=[r['review']['severity'][dim] for r in rows if dim in r['review'].get('severity',{})]
            if any(type(v) is not int or not 0<=v<=3 for v in values):raise ValueError('Invalid severity')
            quality[dim]=dict(evaluated=len(values),none_or_minor=sum(v<=1 for v in values),
                no_major_defect_percent=100*sum(v<=1 for v in values)/len(values),
                counts={str(i):values.count(i) for i in range(4)})
        memory=[r['peak_physical_gib'] for r in rows if r.get('peak_physical_gib') is not None]
        return dict(confirmed_passes=counts['pass'],total=len(rows),score=100*counts['pass']/len(rows),
            counts=counts,median_seconds=statistics.median(r['seconds'] for r in rows),
            physical_gib_range=[min(memory),max(memory)] if memory else None,quality=quality)
    routes={arm:summarize(rows) for arm,rows in selected.items()}
    modes={mode:summarize([r for rows in selected.values() for r in rows if r['mode']==mode]) for mode in ('VSA','SOL')}
    return dict(schema='h3-ref2va-score/v1',benchmark_version=data['version'],
        measure='Confirmed complete visual task success, 0–100; audio not assessed',
        evaluation=data.get('method',{}).get('score_evaluation',
            'Method-disclosed Agent visual judgments on exposed cases, two profiles per mode. Descriptive, not a blind/generalization result.'),
        coverage=dict(cases=len(required),profiles=len(arms),completed=sum(len(r) for r in selected.values()),expected=len(required)*len(arms)),
        quality_definition='Existing per-dimension severity: 0 none, 1 minor, 2 clear, 3 severe. Display fraction with severity <=1, plus all counts; do not combine with task score.',
        routes=routes,modes=modes)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('catalog',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=score(json.loads(args.catalog.read_text()))
    content=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        with args.output.open('x') as f:f.write(content)
    else:print(content,end='')
