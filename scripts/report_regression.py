#!/usr/bin/env python3
"""Record a later regression/miss as durable learning input; never edits product code."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.ai-harness' / 'runtime'))
from learning import record_reported_regression


def main() -> int:
    parser = argparse.ArgumentParser(description='Record a post-completion regression or miss')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--intent-digest', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--evidence-id', action='append', default=[])
    parser.add_argument('--rca-status', choices=('unproven', 'probable', 'proven'), default='unproven')
    args = parser.parse_args()
    record = record_reported_regression(ROOT, original_run_id=args.run_id, intent_digest=args.intent_digest, summary=args.summary, evidence_ids=args.evidence_id, rca_status=args.rca_status)
    print(json.dumps(record, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
