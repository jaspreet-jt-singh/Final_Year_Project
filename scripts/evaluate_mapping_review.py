"""Score mapping candidates only against a completed independent review.

Template contains no algorithm answers. Reviewers must not copy current mappings
as ground truth. Existing heuristic VERIFIED labels are not independent review.
"""
import argparse
import csv
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
METHODS = ('normalized_exact', 'automatic_without_precomputed', 'current_mapping')


def evaluate(comparisons, reviews):
    expected = {row['class'] for row in comparisons}
    if len(reviews) != len(expected) or {row['class'] for row in reviews} != expected:
        raise ValueError('Require exactly one reviewed row for every class, without duplicates')
    accepted = {}
    for row in reviews:
        if not row.get('reviewer', '').strip() or not row.get('evidence', '').strip():
            raise ValueError('Independent reviewer and evidence are required for every row')
        try:
            names = json.loads(row['acceptable_database_names_json'])
        except (ValueError, KeyError) as exc:
            raise ValueError('Complete acceptable_database_names_json; use [] only for reviewed unsupported foods') from exc
        if not isinstance(names, list) or not all(isinstance(name, str) and name.strip() for name in names):
            raise ValueError('Accepted records must be a JSON list of database names')
        accepted[row['class']] = set(names)
    results = {}
    for method in METHODS:
        counts = {'correct_match': 0, 'wrong_match': 0, 'correct_abstention': 0, 'missed_supported': 0}
        for row in comparisons:
            names = accepted[row['class']]
            prediction = row[method]
            outcome = ('correct_match' if prediction in names else 'wrong_match') if prediction is not None else ('missed_supported' if names else 'correct_abstention')
            counts[outcome] += 1
        results[method] = {**counts, 'cases': len(comparisons),
                           'decision_accuracy': (counts['correct_match'] + counts['correct_abstention']) / len(comparisons)}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--audit', type=Path, default=ROOT / 'research/evidence/audit.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'research/evidence/mapping_review_results.json')
    args = parser.parse_args()
    if args.template:
        names = yaml.safe_load((ROOT / 'data/food_dataset/data.yaml').read_text(encoding='utf-8'))['names']
        args.template.parent.mkdir(parents=True, exist_ok=True)
        with args.template.open('x', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['class', 'acceptable_database_names_json', 'reviewer', 'evidence'])
            writer.writeheader()
            writer.writerows({'class': name} for name in names)
        print('Created blank independent-review template; no judgments were invented.')
        return
    if not args.review:
        parser.error('Use --template PATH or --review PATH')
    report = json.loads(args.audit.read_text(encoding='utf-8'))
    with args.review.open(encoding='utf-8-sig', newline='') as stream:
        reviews = list(csv.DictReader(stream))
    try:
        scores = evaluate(report['nutrition']['comparisons'], reviews)
    except ValueError as exc:
        raise SystemExit(f'Not ready to score: {exc}') from exc
    result = {'schema_version': 1, 'database_sha256': report['nutrition']['database_sha256'],
              'scores': scores, 'limitations': 'Class-level mapping decisions only; not clinical or photographed-meal nutrition accuracy.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(scores, indent=2))


if __name__ == '__main__':
    main()
