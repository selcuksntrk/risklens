import runpy
from pathlib import Path
import pytest

EVAL = Path(__file__).resolve().parents[2] / 'eval'


def test_evaluation_rejects_room_leakage_and_unfrozen_observations():
    validate = runpy.run_path(str(EVAL/'run.py'))['validate_manifest']
    first = {'clip_id':'a','room_id':'one','split':'development','case':'A0','pre_model_observations_recorded':True}
    with pytest.raises(ValueError, match='Room leakage'):
        validate({'clips':[first, {**first,'clip_id':'b','split':'evaluation'}]})
    with pytest.raises(ValueError, match='Freeze observations'):
        validate({'clips':[{**first, 'pre_model_observations_recorded':False}]})


def test_metrics_preserve_denominators_and_exclude_unreviewed_or_uncalled_model():
    summarize = runpy.run_path(str(EVAL/'metrics.py'))['summarize']
    rows = [
        {'attempt_id':'a','variant':'full','case':'A0','completed':True,'independently_reviewed':True,
         'finding_tp':2,'finding_fp':1,'finding_fn':3,'seconds':10,'cost_usd':.2},
        {'attempt_id':'b','variant':'full','case':'B0','completed':True,'independently_reviewed':True,
         'verification_truth':'unchanged','model_verdict':None,'guarded_verdict':'cannot_verify','seconds':2,'cost_usd':0},
        {'attempt_id':'c','variant':'full','case':'B4','completed':True,'independently_reviewed':True,
         'verification_truth':'different_object','model_verdict':'fixed','guarded_verdict':'cannot_verify','seconds':8,'cost_usd':.1},
        {'independently_reviewed':False},
    ]
    out = summarize(rows); full=out['variants']['full']
    assert out['excluded_unreviewed_rows'] == 1
    assert full['precision'] == {'numerator':2,'denominator':3}
    assert full['recall'] == {'numerator':2,'denominator':5}
    assert full['before_guard']['false_confirmations'] == {'numerator':1,'denominator':1}
    assert full['before_guard']['not_assessed'] == 1
    assert full['after_guard']['false_confirmations'] == {'numerator':0,'denominator':2}
    assert full['seconds'] == {'n':3,'median':8,'min':2,'max':10}


def test_synthetic_protocol_rejects_physical_success_and_excess_repeats():
    validate=runpy.run_path(str(EVAL/'run.py'))['validate_manifest']
    row={'clip_id':'a','room_id':'one','split':'development','case':'B2',
         'baseline_clip_id':'base','pre_model_observations_recorded':True}
    with pytest.raises(ValueError,match='physical fix'):
        validate({'data_type':'synthetic','clips':[row]})
    with pytest.raises(ValueError,match='Repetitions'):
        validate({'clips':[{**row,'case':'A0','repetitions':{'full':4}}]})


def test_synthetic_summary_does_not_turn_findings_into_accuracy():
    summarize=runpy.run_path(str(EVAL/'summarize_synthetic.py'))['summarize']
    row={'clip_id':'room','case':'A0','variant':'full','status':'done','repetition':1,
         'assessment':'partial','seconds':12,'cost_usd':.2,'report':{'hazards':[{'tracking_supported':True}]}}
    failed={'clip_id':'other','case':'A0','variant':'full','status':'error','repetition':1,
            'recorded_call_cost_usd':.3,'unknown_usage_usd':.3}
    d=summarize({'version':'test','manifest_sha256':'hash','runs':[row,failed]})
    assert d['comparisons']['full']['complete_assessments']==0
    assert d['comparisons']['full']['returned_reports']==1
    assert d['comparisons']['full']['attempts']==2
    assert d['recorded_total_usd']==.5 and d['unknown_usage_usd']==.3
    assert d['physical_change_success_rate']=='not measured'
    assert 'not measured' in d['comparisons']['full']['finding_precision_recall']


def test_mutated_frozen_input_rejected_before_any_paid_call(tmp_path):
    import asyncio, hashlib, json
    run=runpy.run_path(str(EVAL/'run.py'))['run']
    video=tmp_path/'clip.mp4'; video.write_bytes(b'changed')
    manifest={'clips':[{'clip_id':'a','room_id':'one','split':'development','case':'A0',
        'video':'clip.mp4','sha256':hashlib.sha256(b'original').hexdigest(),
        'pre_model_observations_recorded':True}]}
    path=tmp_path/'manifest.json';path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='Video changed'):
        asyncio.run(run(path,tmp_path/'results'))
    assert not (tmp_path/'results').exists()


def test_service_failure_is_preserved_and_stops_further_paid_attempts(tmp_path, monkeypatch):
    import asyncio, hashlib, json
    run=runpy.run_path(str(EVAL/'run.py'))['run']
    calls=[]
    class Unavailable(Exception):
        status_code=401
    async def fail(src, context, *, scan_id, tracking):
        calls.append(scan_id)
        (tmp_path/scan_id/'model_calls.json').write_text(json.dumps([
            {'kind':'spark','cost_usd':.2,'usage_unknown':True}]))
        raise Unavailable('private provider error must not be exported')
    monkeypatch.setitem(run.__globals__,'run_scan',fail)
    video=tmp_path/'clip.mp4';video.write_bytes(b'fixture')
    row={'clip_id':'a','room_id':'one','split':'development','case':'A0','video':'clip.mp4',
         'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'pre_model_observations_recorded':True}
    path=tmp_path/'manifest.json';path.write_text(json.dumps({'clips':[row,{**row,'clip_id':'b'}]}))
    asyncio.run(run(path,tmp_path/'results'))
    saved=(tmp_path/'results/runs.private.json').read_text();d=json.loads(saved)
    assert len(calls)==1 and len(d['runs'])==1
    assert d['runs'][0]['status']=='error' and d['runs'][0]['unknown_usage_usd']==.2
    assert d['stopped_reason']=='model_service_or_budget_unavailable'
    assert 'private provider error' not in saved
