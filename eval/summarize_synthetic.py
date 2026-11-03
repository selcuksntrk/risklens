"""Export measured operational results, never infer correctness from successful calls.
Usage: python eval/summarize_synthetic.py eval/results/RUN/runs.private.json
"""
import argparse
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]


def distribution(values):
    return {'n':len(values),'median':round(median(values),6),'min':min(values),'max':max(values)} if values else {'n':0}


def summarize(data):
    rows = data['runs']
    comparisons = {}
    for variant in ('spark_only','full'):
        primary = [r for r in rows if r['variant']==variant and r['case']=='A0' and r.get('repetition',1)==1]
        done = [r for r in primary if r['status']=='done']
        comparisons[variant] = {
            'attempts':len(primary),'returned_reports':len(done),
            'complete_assessments':sum(r.get('assessment')=='complete' for r in done),
            'reported_findings':sum(len(r['report']['hazards']) for r in done),
            'tracked_findings':sum(h.get('tracking_supported',False) for r in done for h in r['report']['hazards']),
            'seconds_successful':distribution([r['seconds'] for r in done]),
            'cost_usd_successful':distribution([r['cost_usd'] for r in done]),
            'finding_precision_recall':'not measured; human adjudication pending'}
    controls = []
    for r in rows:
        if r['case']=='A0': continue
        v=r.get('verification',{}); results=list(v.get('results',{}).values())
        controls.append({'case':r['case'],'status':r['status'],'description':r.get('control_description'),
                         'checked_findings':len(results),'confirmed':sum(x['verdict']=='fixed' for x in results),
                         'abstentions':sum(x['verdict']=='cannot_verify' for x in results),
                         'model_called_findings':sum(bool(x.get('model_called')) for x in results),
                         'model_false_confirmations':sum(bool(x.get('model_called')) and x.get('model_verdict')=='fixed' for x in results),
                         'seconds':r.get('seconds'),'cost_usd':r.get('cost_usd')})
    repeat=[r for r in rows if r['variant']=='full' and r['clip_id']=='ai_048_004_cam_00' and r['status']=='done']
    return {'release':data['version'],'manifest_sha256':data['manifest_sha256'],
            'data_type':data.get('data_type'),'evaluation_kind':data.get('evaluation_kind'),
            'human_review':'pending','physical_positive_cases':0,'physical_change_success_rate':'not measured',
            'comparisons':comparisons,'negative_controls':controls,
            'demo_repetitions':[{'repetition':r.get('repetition',1),'assessment':r.get('assessment'),
                                 'findings':len(r['report']['hazards']),'seconds':r['seconds'],'cost_usd':r['cost_usd']} for r in repeat],
            'attempts':len(rows),'failed_attempts':sum(r['status']=='error' for r in rows),
            'running_attempts':sum(r['status']=='running' for r in rows),
            'recorded_total_usd':round(sum(r.get('recorded_call_cost_usd',r.get('cost_usd',0)) for r in rows),6),
            'unknown_usage_usd':round(sum(r.get('unknown_usage_usd',0) for r in rows),6),
            'stopped_reason':data.get('stopped_reason'),
            'limitations':['Five synthetic scenes reused from development; not an independent benchmark.',
                          'Reported findings and exact-frame boxes are not correctness scores.',
                          'Re-encoding and cropping do not simulate a new real-camera recording.',
                          'No successful physical precaution or real-home performance has been demonstrated.',
                          'Costs are application accounting, including unknown reservations, not a provider invoice.']}


def markdown(d):
    lines=['# Synthetic development regression — measured results','',
           f"Release: `{d['release']}`. Manifest: `{d['manifest_sha256']}`.",'',
           '**Five previously used synthetic scenes. Human adjudication is pending. These are operational measurements, not safety accuracy.**','',
           '| Variant | Reports / attempts | Complete assessments | Findings reported | Median seconds | Median recorded USD |',
           '|---|---:|---:|---:|---:|---:|']
    for name,r in d['comparisons'].items():
        lines.append(f"| {name} | {r['returned_reports']}/{r['attempts']} | {r['complete_assessments']} | {r['reported_findings']} | {r['seconds_successful'].get('median','n/a')} | {r['cost_usd_successful'].get('median','n/a')} |")
    lines += ['', 'The variants have different capabilities. Spark-only lacks tracking and automatically abstains in verification; it is not used as a verification competitor. More findings do not establish higher accuracy.', '',
              '## Negative controls', '', '| Case | Findings checked | Guarded confirmations | Model calls (findings) | Status |','|---|---:|---:|---:|---|']
    for r in d['negative_controls']:
        lines.append(f"| {r['case']} | {r['checked_findings']} | {r['confirmed']} | {r['model_called_findings']} | {r['status']} |")
    lines += ['',*[f"- {r['case']}: {r['description']}" for r in d['negative_controls']], '',
              'B0 is a deterministic same-file check. Other controls may also abstain before a verifier model call. Zero false confirmations in this small synthetic set is not a general reliability guarantee.', '',
              '## Repeat runs of the demo scene', '', '| Run | Assessment | Findings | Seconds | Recorded USD |','|---|---|---:|---:|---:|']
    for r in d['demo_repetitions']:
        lines.append(f"| {r['repetition']} | {r['assessment']} | {r['findings']} | {r['seconds']} | {r['cost_usd']} |")
    lines += ['',f"Recorded total: ${d['recorded_total_usd']}; unknown-usage component: ${d['unknown_usage_usd']}. Failed attempts: {d['failed_attempts']}. Running: {d['running_attempts']}.",'',
              '## Unmeasured', '', 'Finding precision/recall and positive physical-change verification are **not measured**. AI-assisted pre-run observations are available; Selçuk must review object/relationship matching before correctness metrics are published.', '',
              *['- '+x for x in d['limitations']], '',
              'See [qualitative review notes](QUALITY_NOTES.md) for an observed model overstatement and the limits of the UI wording. These notes are not human accuracy labels.', '',
              'Reproduce using `scripts/fetch_synthetic_eval.py`, `eval/prepare_synthetic.py`, `eval/run.py`, and `eval/summarize_synthetic.py`; see `eval/README.md`. Source media is excluded from Git.']
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('results',type=Path);args=p.parse_args()
    raw=json.loads(args.results.read_text())
    if raw.get('data_type')!='synthetic' or raw.get('evaluation_kind')!='development_regression':
        raise SystemExit('This exporter is only for the synthetic development protocol.')
    d=summarize(raw)
    if d['running_attempts']: raise SystemExit('Wait for all started attempts to finish before publishing.')
    (ROOT/'eval/synthetic-results.json').write_text(json.dumps(d,indent=2)+'\n')
    (ROOT/'docs/EVALUATION.md').write_text(markdown(d))
    keys=('clip_id','variant','case','repetition','status','assessment','seconds','cost_usd',
          'recorded_call_cost_usd','unknown_usage_usd','source_sha256','error_type','http_status')
    attempts=[]
    for r in raw['runs']:
        record={k:r[k] for k in keys if k in r}
        if r.get('report'):
            record['reported_findings']=len(r['report']['hazards'])
            record['tracked_findings']=sum(bool(h.get('tracking_supported')) for h in r['report']['hazards'])
        if r.get('verification'):
            record['verdicts']=[{'finding_id':hid,'model_called':v.get('model_called',False),
                                 'model_verdict':v.get('model_verdict'),'guarded_verdict':v['verdict']}
                                for hid,v in r['verification']['results'].items()]
        attempts.append(record)
    (ROOT/'eval/synthetic-attempts.json').write_text(json.dumps({'release':raw['version'],
        'manifest_sha256':raw['manifest_sha256'],'attempts':attempts},indent=2)+'\n')
    print('Operational summary exported; correctness review remains pending.')
