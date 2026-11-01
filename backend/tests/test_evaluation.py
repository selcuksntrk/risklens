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
