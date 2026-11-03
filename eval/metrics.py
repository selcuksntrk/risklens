"""Aggregate independently adjudicated counts. Exports no room text, media paths or observations.
Review JSON rows: variant, case, completed, seconds, cost_usd, finding_tp/fp/fn (A0 only),
verification_truth (changed|unchanged|insufficient|different_object), model_verdict, guarded_verdict.
One verification row per finding, one A0 row per clip. Unreviewed results are excluded, not assumed correct.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import median


def distribution(values):
    return {'n': len(values), 'median': median(values), 'min': min(values), 'max': max(values)} if values else {'n': 0}


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        if not row.get('independently_reviewed'): continue
        groups[row['variant']].append(row)
    output = {}
    for variant, items in groups.items():
        baseline = [r for r in items if r['case'] == 'A0']
        verification = [r for r in items if r['case'] != 'A0']
        tp, fp, fn = (sum(r.get('finding_'+k, 0) for r in baseline) for k in ('tp', 'fp', 'fn'))
        result = {'reviewed_rows': len(items), 'finding_counts': {'tp': tp, 'fp': fp, 'fn': fn},
                  'precision': {'numerator': tp, 'denominator': tp+fp}, 'recall': {'numerator': tp, 'denominator': tp+fn},
                  'completion': {'numerator': sum(bool(r['completed']) for r in items), 'denominator': len(items)}}
        # Deduplicate attempt-level duration/cost when several findings share an attempt.
        attempts = {r['attempt_id']: r for r in items}
        result['seconds'] = distribution([r['seconds'] for r in attempts.values() if r.get('seconds') is not None])
        result['cost_usd'] = distribution([r['cost_usd'] for r in attempts.values() if r.get('cost_usd') is not None])
        for stage, field in [('before_guard', 'model_verdict'), ('after_guard', 'guarded_verdict')]:
            assessed = [r for r in verification if r.get(field) in ('fixed', 'not_fixed', 'cannot_verify')]
            negative = [r for r in assessed if r['verification_truth'] != 'changed']
            positive = [r for r in assessed if r['verification_truth'] == 'changed']
            result[stage] = {
                'not_assessed': len(verification) - len(assessed),
                'false_confirmations': {'numerator': sum(r.get(field) == 'fixed' for r in negative), 'denominator': len(negative)},
                'true_confirmations': {'numerator': sum(r.get(field) == 'fixed' for r in positive), 'denominator': len(positive)},
                'abstentions': {'numerator': sum(r.get(field) == 'cannot_verify' for r in assessed), 'denominator': len(assessed)}}
        output[variant] = result
    return {'limitations': 'Small room sample; raw counts and descriptive ranges only. No safety guarantee or population performance claim.',
            'excluded_unreviewed_rows': sum(not r.get('independently_reviewed') for r in rows), 'variants': output}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('review', type=Path); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.write_text(json.dumps(summarize(json.loads(args.review.read_text())), indent=2)+'\n')
